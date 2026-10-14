package com.ecogrow.mobile

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.espressif.provisioning.DeviceConnectionEvent
import com.espressif.provisioning.ESPConstants
import com.espressif.provisioning.ESPDevice
import com.espressif.provisioning.ESPProvisionManager
import com.espressif.provisioning.WiFiAccessPoint
import com.espressif.provisioning.listeners.ProvisionListener
import com.espressif.provisioning.listeners.WiFiScanListener
import org.greenrobot.eventbus.EventBus
import org.greenrobot.eventbus.Subscribe
import org.greenrobot.eventbus.ThreadMode

data class DiscoveredTower(
    val name: String,
    val address: String,
    val rssi: Int,
    val device: BluetoothDevice
)

enum class BleProvStep {
    IDLE,
    SCANNING,
    CONNECTING,
    CONNECTED,
    SCANNING_WIFI,
    PROVISIONING,
    SUCCESS,
    FAILED
}

class BleProvisioningManager(private val context: Context) {
    private val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    private val adapter: BluetoothAdapter? get() = bluetoothManager?.adapter
    private val handler = Handler(Looper.getMainLooper())

    private var scanCallback: ScanCallback? = null
    private var scanTimeoutRunnable: Runnable? = null
    private var currentEspDevice: ESPDevice? = null
    private var isEventBusRegistered = false

    // Estado pendiente para aprovisionamiento
    private var pendingAction: PendingBleAction = PendingBleAction.NONE
    private var pendingSsid: String? = null
    private var pendingPassphrase: String? = null
    private var pendingPop: String? = null
    private var pendingStepCallback: ((BleProvStep, String) -> Unit)? = null
    private var pendingWifiScanCallback: ((List<DiscoveredWifi>) -> Unit)? = null
    private var pendingWifiErrorCallback: ((String) -> Unit)? = null
    private var provTimeoutRunnable: Runnable? = null

    private enum class PendingBleAction {
        NONE,
        SCAN_WIFI,
        PROVISION
    }

    // Mismo UUID que ECOGROW_PROV_SERVICE_UUID_LE en el firmware.
    // No usar el valor por defecto de Arduino-ESP32 (termina en 6b3f1c5adfb4):
    // el teléfono vería el nombre BLE y fallaría al buscar el servicio.

    val isBluetoothSupported: Boolean get() = adapter != null
    val isBluetoothEnabled: Boolean get() = adapter?.isEnabled == true

    @SuppressLint("MissingPermission")
    fun startScan(
        onFound: (DiscoveredTower) -> Unit,
        onError: (String) -> Unit,
        onTimeout: (() -> Unit)? = null
    ) {
        val scanner = adapter?.bluetoothLeScanner
        if (scanner == null) {
            onError("Bluetooth no está disponible o no está activado.")
            return
        }

        stopScan()

        scanCallback = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult?) {
                result?.let { r ->
                    val devName = try { r.device.name } catch (_: SecurityException) { null } ?: r.scanRecord?.deviceName
                    Log.d("EcoGrowBle", "BLE detectado: addr=${r.device.address}, name=$devName, rssi=${r.rssi}")
                    val isEcoGrow = devName != null && (
                        devName.startsWith("PROV_", ignoreCase = true) ||
                        devName.contains("EcoGrow", ignoreCase = true)
                    )
                    if (isEcoGrow) {
                        onFound(
                            DiscoveredTower(
                                name = devName ?: "PROV_EcoGrow",
                                address = r.device.address,
                                rssi = r.rssi,
                                device = r.device
                            )
                        )
                    }
                }
            }

            override fun onBatchScanResults(results: MutableList<ScanResult>?) {
                results?.forEach { onScanResult(ScanSettings.CALLBACK_TYPE_ALL_MATCHES, it) }
            }

            override fun onScanFailed(errorCode: Int) {
                Log.e("EcoGrowBle", "Error escaneo BLE: $errorCode")
                onError("Error en escaneo BLE: código $errorCode")
            }
        }

        try {
            val scanSettings = ScanSettings.Builder()
                .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
                .build()
            scanner.startScan(null, scanSettings, scanCallback)
            Log.d("EcoGrowBle", "Escaneo BLE iniciado en modo LOW_LATENCY")

            val timeoutRunnable = Runnable {
                stopScan()
                onTimeout?.invoke()
            }
            scanTimeoutRunnable = timeoutRunnable
            handler.postDelayed(timeoutRunnable, 12000)
        } catch (e: SecurityException) {
            onError("Permisos de Bluetooth denegados.")
        } catch (e: Exception) {
            onError("No se pudo iniciar el escaneo BLE: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    fun stopScan() {
        scanTimeoutRunnable?.let {
            handler.removeCallbacks(it)
            scanTimeoutRunnable = null
        }
        scanCallback?.let {
            try {
                adapter?.bluetoothLeScanner?.stopScan(it)
            } catch (_: Exception) {}
            scanCallback = null
        }
    }

    /**
     * Conecta a la torre vía BLE con Security 1 y solicita la lista de redes WiFi
     * que la antena del ESP32 detecta en su entorno físico.
     */
    @SuppressLint("MissingPermission")
    fun scanWifiFromTower(
        device: BluetoothDevice,
        pop: String,
        onNetworksFound: (List<DiscoveredWifi>) -> Unit,
        onError: (String) -> Unit
    ) {
        val cleanPop = sanitizePop(pop)
        if (cleanPop.length != 8) {
            onError("El PIN PoP debe tener exactamente 8 caracteres Base32.")
            return
        }

        cancelProvisioning()
        pendingAction = PendingBleAction.SCAN_WIFI
        pendingPop = cleanPop
        pendingWifiScanCallback = onNetworksFound
        pendingWifiErrorCallback = onError

        try {
            if (!isEventBusRegistered) {
                EventBus.getDefault().register(this)
                isEventBusRegistered = true
            }

            // Timeout de 30 segundos
            provTimeoutRunnable = Runnable {
                cancelProvisioning()
                onError("Tiempo de espera agotado al consultar redes WiFi desde la torre.")
            }
            handler.postDelayed(provTimeoutRunnable!!, 30000)

            val manager = ESPProvisionManager.getInstance(context)
            val espDevice = manager.createESPDevice(ESPConstants.TransportType.TRANSPORT_BLE, ESPConstants.SecurityType.SECURITY_1)
            espDevice.proofOfPossession = cleanPop
            espDevice.primaryServiceUuid = ESP_PROV_SERVICE_UUID
            currentEspDevice = espDevice

            espDevice.connectBLEDevice(device, ESP_PROV_SERVICE_UUID)
        } catch (e: SecurityException) {
            cancelProvisioning()
            onError("Permisos de Bluetooth denegados.")
        } catch (e: Exception) {
            cancelProvisioning()
            onError("Error al conectar con la torre: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    fun provisionTower(
        device: BluetoothDevice,
        ssid: String,
        passphrase: String,
        pop: String,
        onStepChanged: (BleProvStep, String) -> Unit
    ) {
        val cleanSsid = ssid.trim()
        if (cleanSsid.isBlank()) {
            onStepChanged(BleProvStep.FAILED, "El nombre de la red WiFi (SSID) no puede estar vacío.")
            return
        }
        val cleanPop = sanitizePop(pop)
        if (cleanPop.length != 8) {
            onStepChanged(BleProvStep.FAILED, "Se requiere el PIN PoP de 8 caracteres de la etiqueta de la torre.")
            return
        }

        cancelProvisioning()
        pendingAction = PendingBleAction.PROVISION
        pendingSsid = cleanSsid
        pendingPassphrase = passphrase
        pendingPop = cleanPop
        pendingStepCallback = onStepChanged

        val devName = try { device.name } catch (_: SecurityException) { null } ?: "EcoGrow"
        onStepChanged(BleProvStep.CONNECTING, "Iniciando enlace Bluetooth con torre $devName...")

        try {
            if (!isEventBusRegistered) {
                EventBus.getDefault().register(this)
                isEventBusRegistered = true
            }

            // Timeout de seguridad de 35 segundos
            provTimeoutRunnable = Runnable {
                Log.w("EcoGrowBle", "Timeout alcanzado durante aprovisionamiento BLE")
                cancelProvisioning()
                onStepChanged(BleProvStep.FAILED, "Tiempo de espera agotado al conectar o aprovisionar la torre.")
            }
            handler.postDelayed(provTimeoutRunnable!!, 35000)

            val manager = ESPProvisionManager.getInstance(context)
            val espDevice = manager.createESPDevice(ESPConstants.TransportType.TRANSPORT_BLE, ESPConstants.SecurityType.SECURITY_1)
            espDevice.proofOfPossession = cleanPop
            espDevice.primaryServiceUuid = ESP_PROV_SERVICE_UUID
            currentEspDevice = espDevice

            espDevice.connectBLEDevice(device, ESP_PROV_SERVICE_UUID)
            onStepChanged(BleProvStep.CONNECTING, "Conectando y descubriendo servicios GATT de la torre...")
        } catch (e: SecurityException) {
            cancelProvisioning()
            onStepChanged(BleProvStep.FAILED, "Permisos de Bluetooth denegados.")
        } catch (e: Exception) {
            cancelProvisioning()
            onStepChanged(BleProvStep.FAILED, "Excepción al conectar BLE: ${e.message}")
        }
    }

    @Subscribe(threadMode = ThreadMode.MAIN)
    fun onDeviceConnectionEvent(event: DeviceConnectionEvent) {
        Log.d("EcoGrowBle", "DeviceConnectionEvent recibido: eventType=${event.eventType}, pendingAction=$pendingAction")
        when (event.eventType) {
            ESPConstants.EVENT_DEVICE_CONNECTED -> {
                val espDevice = currentEspDevice ?: return

                when (pendingAction) {
                    PendingBleAction.SCAN_WIFI -> {
                        val scanCallback = pendingWifiScanCallback
                        val errCallback = pendingWifiErrorCallback
                        Log.d("EcoGrowBle", "Solicitando escaneo de redes WiFi al ESP32...")
                        espDevice.scanNetworks(object : WiFiScanListener {
                            override fun onWifiListReceived(wifiList: java.util.ArrayList<WiFiAccessPoint>?) {
                                handler.post {
                                    cleanupProvisioning()
                                    val mapped = (wifiList ?: emptyList()).map { ap ->
                                        DiscoveredWifi(
                                            ssid = ap.wifiName ?: "",
                                            level = ap.rssi,
                                            isSecure = ap.security > 0,
                                            isCurrent = false
                                        )
                                    }.filter { it.ssid.isNotBlank() }
                                    Log.d("EcoGrowBle", "Redes recibidas del ESP32: ${mapped.size}")
                                    scanCallback?.invoke(mapped)
                                }
                            }

                            override fun onWiFiScanFailed(e: java.lang.Exception?) {
                                handler.post {
                                    cleanupProvisioning()
                                    val msg = if (e?.message?.contains("pop", ignoreCase = true) == true ||
                                        e?.message?.contains("session", ignoreCase = true) == true) {
                                        "Error de autenticación Security 1: Clave PoP incorrecta."
                                    } else {
                                        "Fallo al escanear redes WiFi desde la torre: ${e?.message}"
                                    }
                                    errCallback?.invoke(msg)
                                }
                            }
                        })
                    }

                    PendingBleAction.PROVISION -> {
                        val ssid = pendingSsid ?: return
                        val passphrase = pendingPassphrase ?: ""
                        val callback = pendingStepCallback ?: return

                        callback(BleProvStep.CONNECTED, "Conexión BLE establecida y servicios listos.")
                        callback(BleProvStep.PROVISIONING, "Autenticando Security 1 y transfiriendo credenciales...")

                        espDevice.provision(ssid, passphrase, object : ProvisionListener {
                            override fun createSessionFailed(e: Exception?) {
                                handler.post {
                                    cleanupProvisioning()
                                    val msg = if (e?.message?.contains("pop", ignoreCase = true) == true ||
                                        e?.message?.contains("session", ignoreCase = true) == true ||
                                        e?.message?.contains("handshake", ignoreCase = true) == true) {
                                        "Error en sesión Security 1: PIN / clave PoP incorrecta."
                                    } else {
                                        "Error en sesión Security 1: ${e?.message ?: "Verifica el PIN"}"
                                    }
                                    callback(BleProvStep.FAILED, msg)
                                }
                            }

                            override fun wifiConfigSent() {
                                handler.post {
                                    callback(BleProvStep.PROVISIONING, "Credenciales transferidas a la torre. Conectando al router...")
                                }
                            }

                            override fun wifiConfigFailed(e: Exception?) {
                                handler.post {
                                    cleanupProvisioning()
                                    callback(BleProvStep.FAILED, "Fallo al enviar configuración WiFi a la torre: ${e?.message}")
                                }
                            }

                            override fun wifiConfigApplied() {
                                handler.post {
                                    callback(BleProvStep.PROVISIONING, "Configuración recibida por el ESP32. Esperando asignación de IP...")
                                }
                            }

                            override fun wifiConfigApplyFailed(e: Exception?) {
                                handler.post {
                                    cleanupProvisioning()
                                    callback(BleProvStep.FAILED, "La torre no pudo aplicar la configuración WiFi: ${e?.message}")
                                }
                            }

                            override fun provisioningFailedFromDevice(reason: ESPConstants.ProvisionFailureReason?) {
                                handler.post {
                                    cleanupProvisioning()
                                    val motivo = when (reason) {
                                        ESPConstants.ProvisionFailureReason.AUTH_FAILED -> "Contraseña de red WiFi incorrecta o rechazada por el router."
                                        ESPConstants.ProvisionFailureReason.DEVICE_DISCONNECTED -> "La torre se desconectó antes de confirmar el enlace."
                                        else -> "La torre no pudo conectar a la red WiFi ($reason)."
                                    }
                                    callback(BleProvStep.FAILED, motivo)
                                }
                            }

                            override fun deviceProvisioningSuccess() {
                                handler.post {
                                    cleanupProvisioning()
                                    callback(BleProvStep.SUCCESS, "¡Torre conectada a la red WiFi '$ssid' exitosamente!")
                                }
                            }

                            override fun onProvisioningFailed(e: Exception?) {
                                handler.post {
                                    cleanupProvisioning()
                                    callback(BleProvStep.FAILED, "Error de aprovisionamiento: ${e?.message}")
                                }
                            }
                        })
                    }

                    PendingBleAction.NONE -> {}
                }
            }
            ESPConstants.EVENT_DEVICE_CONNECTION_FAILED -> {
                val action = pendingAction
                val provCb = pendingStepCallback
                val wifiErrCb = pendingWifiErrorCallback
                cancelProvisioning()
                val err = "Fallo al conectar por BLE con la torre. Comprueba que esté encendida y cercana."
                if (action == PendingBleAction.SCAN_WIFI) wifiErrCb?.invoke(err)
                else provCb?.invoke(BleProvStep.FAILED, err)
            }
            ESPConstants.EVENT_DEVICE_DISCONNECTED -> {
                if (pendingAction != PendingBleAction.NONE) {
                    val action = pendingAction
                    val provCb = pendingStepCallback
                    val wifiErrCb = pendingWifiErrorCallback
                    cancelProvisioning()
                    val err = "La torre se desconectó por Bluetooth antes de completar la acción."
                    if (action == PendingBleAction.SCAN_WIFI) wifiErrCb?.invoke(err)
                    else provCb?.invoke(BleProvStep.FAILED, err)
                }
            }
        }
    }

    fun cancelProvisioning() {
        cleanupProvisioning()
        try {
            currentEspDevice?.disconnectDevice()
        } catch (_: Exception) {}
        currentEspDevice = null
    }

    private fun cleanupProvisioning() {
        provTimeoutRunnable?.let {
            handler.removeCallbacks(it)
            provTimeoutRunnable = null
        }
        if (isEventBusRegistered) {
            try {
                EventBus.getDefault().unregister(this)
            } catch (_: Exception) {}
            isEventBusRegistered = false
        }
        pendingAction = PendingBleAction.NONE
        pendingSsid = null
        pendingPassphrase = null
        pendingPop = null
        pendingStepCallback = null
        pendingWifiScanCallback = null
        pendingWifiErrorCallback = null
    }

    @SuppressLint("MissingPermission")
    fun close() {
        stopScan()
        cancelProvisioning()
    }

    companion object {
        const val ESP_PROV_SERVICE_UUID = "021a9004-0382-4aea-bff4-6b3f1b5adfb4"

        fun sanitizePop(input: String): String {
            val trimmed = input.trim()
            if (trimmed.startsWith("{") && trimmed.contains("\"pop\"")) {
                try {
                    val obj = org.json.JSONObject(trimmed)
                    return obj.optString("pop", trimmed).replace(Regex("[^0-9A-Za-z]"), "").uppercase()
                } catch (_: Exception) {}
            }
            return trimmed.replace(Regex("[^0-9A-Za-z]"), "").uppercase()
        }
    }
}
