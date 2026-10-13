package com.ecogrow.mobile

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
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
    private var pendingSsid: String? = null
    private var pendingPassphrase: String? = null
    private var pendingPop: String? = null
    private var pendingStepCallback: ((BleProvStep, String) -> Unit)? = null
    private var provTimeoutRunnable: Runnable? = null

    // UUID canónico del servicio WiFiProv de Espressif sobre BLE
    val ESP_PROV_SERVICE_UUID = "021a9004-0382-4aea-bff4-6b3f1b5adfb4"

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

    @SuppressLint("MissingPermission")
    fun provisionTower(
        device: BluetoothDevice,
        ssid: String,
        passphrase: String,
        pop: String,
        onStepChanged: (BleProvStep, String) -> Unit
    ) {
        if (ssid.isBlank()) {
            onStepChanged(BleProvStep.FAILED, "El nombre de la red WiFi (SSID) no puede estar vacío.")
            return
        }
        if (pop.isBlank()) {
            onStepChanged(BleProvStep.FAILED, "Se requiere la clave PoP (Proof of Possession) de la torre.")
            return
        }

        cancelProvisioning()

        val devName = try { device.name } catch (_: SecurityException) { null } ?: "EcoGrow"
        onStepChanged(BleProvStep.CONNECTING, "Iniciando conexión BLE con torre $devName...")

        try {
            pendingSsid = ssid
            pendingPassphrase = passphrase
            pendingPop = pop
            pendingStepCallback = onStepChanged

            if (!isEventBusRegistered) {
                EventBus.getDefault().register(this)
                isEventBusRegistered = true
            }

            // Timeout de seguridad de 35 segundos para conexión y aprovisionamiento completo
            val timeoutRunnable = Runnable {
                Log.w("EcoGrowBle", "Timeout alcanzado durante aprovisionamiento BLE")
                cancelProvisioning()
                onStepChanged(BleProvStep.FAILED, "Tiempo de espera agotado al conectar o aprovisionar la torre.")
            }
            provTimeoutRunnable = timeoutRunnable
            handler.postDelayed(timeoutRunnable, 35000)

            val manager = ESPProvisionManager.getInstance(context)
            val espDevice = manager.createESPDevice(ESPConstants.TransportType.TRANSPORT_BLE, ESPConstants.SecurityType.SECURITY_1)
            espDevice.proofOfPossession = pop
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
        Log.d("EcoGrowBle", "DeviceConnectionEvent recibido: eventType=${event.eventType}")
        when (event.eventType) {
            ESPConstants.EVENT_DEVICE_CONNECTED -> {
                val ssid = pendingSsid ?: return
                val passphrase = pendingPassphrase ?: ""
                val espDevice = currentEspDevice ?: return
                val callback = pendingStepCallback ?: return

                callback(BleProvStep.CONNECTED, "Conexión BLE y servicios GATT listos.")
                callback(BleProvStep.PROVISIONING, "Negociando Security 1 y transfiriendo credenciales WiFi...")

                espDevice.provision(ssid, passphrase, object : ProvisionListener {
                    override fun createSessionFailed(e: Exception?) {
                        handler.post {
                            cleanupProvisioning()
                            val msg = if (e?.message?.contains("pop", ignoreCase = true) == true ||
                                e?.message?.contains("session", ignoreCase = true) == true ||
                                e?.message?.contains("handshake", ignoreCase = true) == true) {
                                "Error en sesión Security 1: Clave PoP incorrecta."
                            } else {
                                "Error en sesión Security 1: ${e?.message ?: "Revisa el PIN/PoP"}"
                            }
                            callback(BleProvStep.FAILED, msg)
                        }
                    }

                    override fun wifiConfigSent() {
                        handler.post {
                            callback(BleProvStep.PROVISIONING, "Credenciales transferidas a la torre. Conectando al router WiFi...")
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
                            callback(BleProvStep.PROVISIONING, "Configuración recibida por el ESP32. Comprobando IP en la red...")
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
            ESPConstants.EVENT_DEVICE_CONNECTION_FAILED -> {
                val callback = pendingStepCallback
                cancelProvisioning()
                callback?.invoke(BleProvStep.FAILED, "Fallo al conectar por BLE con la torre. Comprueba que esté encendida.")
            }
            ESPConstants.EVENT_DEVICE_DISCONNECTED -> {
                if (pendingStepCallback != null) {
                    val callback = pendingStepCallback
                    cancelProvisioning()
                    callback?.invoke(BleProvStep.FAILED, "La torre se desconectó por BLE antes de completar la configuración.")
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
        pendingSsid = null
        pendingPassphrase = null
        pendingPop = null
        pendingStepCallback = null
    }

    @SuppressLint("MissingPermission")
    fun close() {
        stopScan()
        cancelProvisioning()
    }
}
