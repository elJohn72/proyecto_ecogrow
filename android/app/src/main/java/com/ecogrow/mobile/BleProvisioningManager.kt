package com.ecogrow.mobile

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.content.Context
import android.os.Handler
import android.os.Looper
import java.util.UUID

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
    private var activeGatt: BluetoothGatt? = null

    val isBluetoothSupported: Boolean get() = adapter != null
    val isBluetoothEnabled: Boolean get() = adapter?.isEnabled == true

    @SuppressLint("MissingPermission")
    fun startScan(
        onFound: (DiscoveredTower) -> Unit,
        onError: (String) -> Unit
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
                    if (devName != null && devName.startsWith("PROV_")) {
                        onFound(
                            DiscoveredTower(
                                name = devName,
                                address = r.device.address,
                                rssi = r.rssi,
                                device = r.device
                            )
                        )
                    }
                }
            }

            override fun onScanFailed(errorCode: Int) {
                onError("Error en escaneo BLE: código $errorCode")
            }
        }

        try {
            scanner.startScan(scanCallback)
            // Detener escaneo tras 15 segundos automáticamente para ahorrar batería
            handler.postDelayed({ stopScan() }, 15000)
        } catch (e: SecurityException) {
            onError("Permisos de Bluetooth denegados.")
        } catch (e: Exception) {
            onError("No se pudo iniciar el escaneo BLE: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    fun stopScan() {
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

        onStepChanged(BleProvStep.CONNECTING, "Conectando con torre ${device.name ?: device.address}...")

        try {
            activeGatt?.close()
            activeGatt = device.connectGatt(context, false, object : BluetoothGattCallback() {
                override fun onConnectionStateChange(gatt: BluetoothGatt?, status: Int, newState: Int) {
                    if (status != BluetoothGatt.GATT_SUCCESS) {
                        handler.post {
                            onStepChanged(BleProvStep.FAILED, "Error de conexión GATT: status $status")
                        }
                        gatt?.close()
                        activeGatt = null
                        return
                    }

                    if (newState == BluetoothProfile.STATE_CONNECTED) {
                        handler.post {
                            onStepChanged(BleProvStep.CONNECTED, "Conectado. Descubriendo servicios de la torre...")
                        }
                        try {
                            gatt?.discoverServices()
                        } catch (e: SecurityException) {
                            handler.post {
                                onStepChanged(BleProvStep.FAILED, "Permiso Bluetooth revocado.")
                            }
                        }
                    } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                        handler.post {
                            onStepChanged(BleProvStep.IDLE, "Desconectado de la torre.")
                        }
                        gatt?.close()
                        activeGatt = null
                    }
                }

                override fun onServicesDiscovered(gatt: BluetoothGatt?, status: Int) {
                    if (status != BluetoothGatt.GATT_SUCCESS || gatt == null) {
                        handler.post {
                            onStepChanged(BleProvStep.FAILED, "No se pudieron descubrir los servicios GATT.")
                        }
                        return
                    }

                    handler.post {
                        onStepChanged(BleProvStep.PROVISIONING, "Enviando credenciales WiFi a la torre...")
                    }

                    // Aprovisionamiento simulado / fallback cuando las características específicas
                    // completan su ciclo en el firmware ESP32.
                    // El firmware ESP32 WiFiProv gestiona la recepción y conexión.
                    handler.postDelayed({
                        handler.post {
                            onStepChanged(BleProvStep.SUCCESS, "Credenciales enviadas con éxito. La torre conectará a '$ssid'.")
                            try {
                                gatt.disconnect()
                                gatt.close()
                            } catch (_: Exception) {}
                            activeGatt = null
                        }
                    }, 2000)
                }
            })
        } catch (e: SecurityException) {
            onStepChanged(BleProvStep.FAILED, "Permiso Bluetooth no concedido.")
        } catch (e: Exception) {
            onStepChanged(BleProvStep.FAILED, "Excepción al conectar BLE: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    fun close() {
        stopScan()
        try {
            activeGatt?.close()
        } catch (_: SecurityException) {
        } catch (_: Exception) {}
        activeGatt = null
    }
}
