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
import com.espressif.provisioning.ESPConstants
import com.espressif.provisioning.ESPDevice
import com.espressif.provisioning.ESPProvisionManager
import com.espressif.provisioning.listeners.ProvisionListener
import com.espressif.provisioning.listeners.WiFiScanListener

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
        pop: String = "ecogrow20",
        onStepChanged: (BleProvStep, String) -> Unit
    ) {
        if (ssid.isBlank()) {
            onStepChanged(BleProvStep.FAILED, "El nombre de la red WiFi (SSID) no puede estar vacío.")
            return
        }

        val devName = try { device.name } catch (_: SecurityException) { null } ?: "EcoGrow"
        onStepChanged(BleProvStep.CONNECTING, "Conectando con torre $devName...")

        try {
            currentEspDevice?.disconnectDevice()
            val manager = ESPProvisionManager.getInstance(context)
            val espDevice = manager.createESPDevice(ESPConstants.TransportType.TRANSPORT_BLE, ESPConstants.SecurityType.SECURITY_1)
            espDevice.proofOfPossession = pop.ifBlank { "ecogrow20" }
            espDevice.primaryServiceUuid = ESP_PROV_SERVICE_UUID
            currentEspDevice = espDevice

            espDevice.connectBLEDevice(device, ESP_PROV_SERVICE_UUID)
            onStepChanged(BleProvStep.CONNECTED, "Conectado por BLE. Negociando seguridad Security 1 y enviando credenciales...")

            espDevice.provision(ssid, passphrase, object : ProvisionListener {
                override fun createSessionFailed(e: Exception?) {
                    handler.post {
                        onStepChanged(BleProvStep.FAILED, "Error en sesión Security 1: PIN de posesión incorrecto (${e?.message ?: "Revisa el PIN"})")
                    }
                }

                override fun wifiConfigSent() {
                    handler.post {
                        onStepChanged(BleProvStep.PROVISIONING, "Credenciales transferidas a la torre. Conectando al router...")
                    }
                }

                override fun wifiConfigFailed(e: Exception?) {
                    handler.post {
                        onStepChanged(BleProvStep.FAILED, "Fallo al enviar configuración WiFi: ${e?.message}")
                    }
                }

                override fun wifiConfigApplied() {
                    handler.post {
                        onStepChanged(BleProvStep.PROVISIONING, "Configuración aplicada. Comprobando enlace de la torre...")
                    }
                }

                override fun wifiConfigApplyFailed(e: Exception?) {
                    handler.post {
                        onStepChanged(BleProvStep.FAILED, "La torre no pudo aplicar la configuración WiFi: ${e?.message}")
                    }
                }

                override fun provisioningFailedFromDevice(reason: ESPConstants.ProvisionFailureReason?) {
                    handler.post {
                        val motivo = when (reason) {
                            ESPConstants.ProvisionFailureReason.AUTH_FAILED -> "Contraseña de red WiFi incorrecta."
                            ESPConstants.ProvisionFailureReason.DEVICE_DISCONNECTED -> "La torre se desconectó antes de confirmar el enlace."
                            else -> "La torre no pudo conectar a la red WiFi ($reason)."
                        }
                        onStepChanged(BleProvStep.FAILED, motivo)
                    }
                }

                override fun deviceProvisioningSuccess() {
                    handler.post {
                        onStepChanged(BleProvStep.SUCCESS, "¡Torre conectada a la red WiFi '$ssid' exitosamente!")
                    }
                }

                override fun onProvisioningFailed(e: Exception?) {
                    handler.post {
                        onStepChanged(BleProvStep.FAILED, "Error de aprovisionamiento: ${e?.message}")
                    }
                }
            })
        } catch (e: SecurityException) {
            onStepChanged(BleProvStep.FAILED, "Permisos de Bluetooth revocados.")
        } catch (e: Exception) {
            onStepChanged(BleProvStep.FAILED, "Excepción al conectar BLE: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    fun close() {
        stopScan()
        try {
            currentEspDevice?.disconnectDevice()
        } catch (_: Exception) {}
        currentEspDevice = null
    }
}
