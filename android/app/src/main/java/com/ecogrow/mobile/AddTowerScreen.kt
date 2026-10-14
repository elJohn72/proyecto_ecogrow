package com.ecogrow.mobile

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.core.content.ContextCompat
import com.google.zxing.BarcodeFormat
import com.google.zxing.BinaryBitmap
import com.google.zxing.DecodeHintType
import com.google.zxing.MultiFormatReader
import com.google.zxing.PlanarYUVLuminanceSource
import com.google.zxing.common.HybridBinarizer
import java.util.concurrent.Executors

enum class AddTowerStep {
    INSTRUCTIONS,       // 1. Qué hacer con la torre físicamente
    PERMISSIONS,        // 2. Comprobar Bluetooth y permisos
    SCAN_BLE,           // 3. Buscar torres BLE en el aire
    ENTER_PIN,          // 4. Seleccionar torre e introducir PIN PoP o escanear QR
    SCAN_WIFI,          // 5. Redes WiFi detectadas por el ESP32 (o manual)
    ENTER_PASSWORD,     // 6. Contraseña WiFi
    PROVISIONING,       // 7. Progreso real de configuración y conexión
    SUCCESS             // 8. Separación: WiFi confirmado vs vinculación en servidor
}

@Composable
fun AddTowerScreen(
    bleManager: BleProvisioningManager?,
    onCancel: () -> Unit,
    onTowerAddedAndBound: (towerCode: String, popProof: String, towerName: String, onComplete: (Boolean, String?, Int?) -> Unit) -> Unit,
    onFetchTowerDetail: (suspend (Int) -> TowerDetailModel?)? = null,
    onOpenTowerDetail: ((Int) -> Unit)? = null
) {
    val context = LocalContext.current
    var currentStep by remember { mutableStateOf(AddTowerStep.INSTRUCTIONS) }

    // Estados conservados entre pasos
    var discoveredTowers by remember { mutableStateOf<List<DiscoveredTower>>(emptyList()) }
    var selectedTower by remember { mutableStateOf<DiscoveredTower?>(null) }
    var canonicalTowerCode by remember { mutableStateOf("") }
    var popInput by remember { mutableStateOf("") }
    var customTowerName by remember { mutableStateOf("") }
    var discoveredWifis by remember { mutableStateOf<List<DiscoveredWifi>>(emptyList()) }
    var selectedSsid by remember { mutableStateOf("") }
    var isManualSsid by remember { mutableStateOf(false) }
    var manualSsidInput by remember { mutableStateOf("") }
    var wifiPassword by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }

    // Estados de carga, progreso y error
    var isScanningBle by remember { mutableStateOf(false) }
    var isScanningWifi by remember { mutableStateOf(false) }
    var provStep by remember { mutableStateOf(BleProvStep.IDLE) }
    var progressMessage by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var showQrCameraScanner by remember { mutableStateOf(false) }

    // Estado del paso 8 (Vinculación Cloud y Telemetría en Tiempo Real)
    var isBindingCloud by remember { mutableStateOf(false) }
    var cloudBindSuccess by remember { mutableStateOf(false) }
    var cloudBindError by remember { mutableStateOf<String?>(null) }
    var boundTowerId by remember { mutableStateOf<Int?>(null) }
    var isPollingTelemetry by remember { mutableStateOf(false) }
    var telemetryConfirmed by remember { mutableStateOf(false) }
    var firstTelemetryData by remember { mutableStateOf<TowerDetailModel?>(null) }
    var pollingTimeout by remember { mutableStateOf(false) }
    var telemetryPollTrigger by remember { mutableStateOf(0) }

    // Permisos Bluetooth
    val requiredPermissions = remember {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        } else {
            arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
        }
    }

    fun hasPermissions(): Boolean {
        return requiredPermissions.all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    var isBtEnabled by remember {
        mutableStateOf(bleManager?.isBluetoothEnabled == true)
    }

    val btEnableLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) {
        isBtEnabled = bleManager?.isBluetoothEnabled == true
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { perms ->
        val allGranted = perms.values.all { it }
        if (allGranted) {
            errorMessage = null
            if (bleManager?.isBluetoothEnabled == true) {
                currentStep = AddTowerStep.SCAN_BLE
            } else {
                btEnableLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
            }
        } else {
            errorMessage = "Se requieren permisos de Bluetooth y Ubicación para detectar torres cercanas."
        }
    }

    fun startBleScan() {
        if (bleManager == null) return
        errorMessage = null
        isScanningBle = true
        discoveredTowers = emptyList()
        progressMessage = "Buscando torres EcoGrow en el aire..."

        bleManager.startScan(
            onFound = { found ->
                if (discoveredTowers.none { it.address == found.address }) {
                    discoveredTowers = discoveredTowers + found
                    if (selectedTower == null) {
                        selectedTower = found
                        customTowerName = "Torre ${found.name.takeLast(4)}"
                    }
                }
            },
            onError = { err ->
                isScanningBle = false
                errorMessage = err
            },
            onTimeout = {
                isScanningBle = false
                if (discoveredTowers.isEmpty()) {
                    errorMessage = "No se detectó ninguna torre EcoGrow cercana. Verifica que esté alimentada."
                }
            }
        )
    }

    LaunchedEffect(currentStep) {
        if (currentStep == AddTowerStep.SCAN_BLE) {
            startBleScan()
        }
    }

    // Modal de Escáner QR con Cámara
    if (showQrCameraScanner) {
        QrCameraScannerDialog(
            onQrScanned = { raw ->
                showQrCameraScanner = false
                try {
                    val trimmed = raw.trim()
                    if (trimmed.startsWith("{")) {
                        val json = org.json.JSONObject(trimmed)
                        if (json.has("code")) {
                            canonicalTowerCode = json.getString("code")
                        }
                        if (json.has("pop")) {
                            popInput = BleProvisioningManager.sanitizePop(json.getString("pop"))
                        }
                        if (json.has("name") && customTowerName.isBlank()) {
                            customTowerName = json.getString("name")
                        }
                    } else {
                        popInput = BleProvisioningManager.sanitizePop(raw)
                    }
                } catch (_: Exception) {
                    popInput = BleProvisioningManager.sanitizePop(raw)
                }
                errorMessage = null
            },
            onDismiss = { showQrCameraScanner = false }
        )
    }

    Scaffold(
        topBar = {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 2.dp
            ) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (currentStep != AddTowerStep.INSTRUCTIONS && currentStep != AddTowerStep.PROVISIONING && currentStep != AddTowerStep.SUCCESS) {
                                IconButton(onClick = {
                                    currentStep = when (currentStep) {
                                        AddTowerStep.PERMISSIONS -> AddTowerStep.INSTRUCTIONS
                                        AddTowerStep.SCAN_BLE -> AddTowerStep.PERMISSIONS
                                        AddTowerStep.ENTER_PIN -> AddTowerStep.SCAN_BLE
                                        AddTowerStep.SCAN_WIFI -> AddTowerStep.ENTER_PIN
                                        AddTowerStep.ENTER_PASSWORD -> AddTowerStep.SCAN_WIFI
                                        else -> AddTowerStep.INSTRUCTIONS
                                    }
                                    errorMessage = null
                                }) {
                                    Text("←", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                            Text(
                                "Añadir Torre EcoGrow",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF195C3D)
                            )
                        }

                        TextButton(onClick = {
                            bleManager?.cancelProvisioning()
                            onCancel()
                        }) {
                            Text("Cancelar", color = Color(0xFF666666))
                        }
                    }

                    // Indicador de pasos (1 al 8)
                    val stepIndex = currentStep.ordinal + 1
                    LinearProgressIndicator(
                        progress = { stepIndex / 8f },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 8.dp)
                            .height(4.dp)
                            .clip(RoundedCornerShape(2.dp)),
                        color = Color(0xFF195C3D),
                        trackColor = Color(0xFFE0E0E0)
                    )
                    Text(
                        "Paso $stepIndex de 8",
                        fontSize = 11.sp,
                        color = Color.Gray,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
            }
        }
    ) { padding ->
        Box(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp)
        ) {
            when (currentStep) {
                // =========================================================================
                // PASO 1: QUÉ HACER CON LA TORRE FÍSICAMENTE
                // =========================================================================
                AddTowerStep.INSTRUCTIONS -> {
                    Column(
                        Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            "Preparación Física de la Torre",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF172B22)
                        )
                        Text(
                            "Antes de comenzar el aprovisionamiento por Bluetooth, sigue estos pasos con tu equipo:",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color(0xFF555555)
                        )

                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                                InstructionItem(
                                    number = "1",
                                    title = "Alimenta el microcontrolador ESP32",
                                    description = "Conecta la fuente de 5V o cable USB a la torre. El LED de encendido debe quedar fijo."
                                )
                                InstructionItem(
                                    number = "2",
                                    title = "Verifica el estado del Bluetooth",
                                    description = "Al encender, la torre emite un anuncio BLE 'PROV_EcoGrow_XXXX'. Si ya estaba configurada, mantén el botón BOOT pulsado entre 3 y 8 segundos para reconfigurar WiFi."
                                )
                                InstructionItem(
                                    number = "3",
                                    title = "Ten a mano la etiqueta física o QR",
                                    description = "Necesitarás el PIN de posesión (8 caracteres) o el código QR impreso en el chasis para autorizar la conexión."
                                )
                            }
                        }

                        Spacer(Modifier.weight(1f))

                        Button(
                            onClick = {
                                if (hasPermissions() && bleManager?.isBluetoothEnabled == true) {
                                    currentStep = AddTowerStep.SCAN_BLE
                                } else {
                                    currentStep = AddTowerStep.PERMISSIONS
                                }
                            },
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                        ) {
                            Text("Comenzar Configuración", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                // =========================================================================
                // PASO 2: BLUETOOTH Y PERMISOS
                // =========================================================================
                AddTowerStep.PERMISSIONS -> {
                    Column(
                        Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            "Permisos y Bluetooth",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF172B22)
                        )
                        Text(
                            "Android requiere permisos de escaneo Bluetooth y ubicación para descubrir dispositivos cercanos:",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color(0xFF555555)
                        )

                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                                StatusCheckItem(
                                    title = "Bluetooth activado",
                                    isOk = bleManager?.isBluetoothEnabled == true,
                                    okText = "Activado",
                                    failText = "Desactivado"
                                )
                                StatusCheckItem(
                                    title = "Permisos de escaneo BLE",
                                    isOk = hasPermissions(),
                                    okText = "Concedidos",
                                    failText = "Pendientes"
                                )
                            }
                        }

                        errorMessage?.let {
                            Text(it, color = Color(0xFFB3261E), fontSize = 13.sp)
                        }

                        Spacer(Modifier.weight(1f))

                        Button(
                            onClick = {
                                if (!hasPermissions()) {
                                    permissionLauncher.launch(requiredPermissions)
                                } else if (bleManager?.isBluetoothEnabled != true) {
                                    btEnableLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
                                } else {
                                    currentStep = AddTowerStep.SCAN_BLE
                                }
                            },
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                        ) {
                            Text(
                                if (!hasPermissions()) "Solicitar Permisos"
                                else if (bleManager?.isBluetoothEnabled != true) "Activar Bluetooth"
                                else "Continuar a Búsqueda",
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                // =========================================================================
                // PASO 3: BÚSQUEDA Y SELECCIÓN DE TORRE BLE
                // =========================================================================
                AddTowerStep.SCAN_BLE -> {
                    Column(
                        Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                "Torres Cercanas Detectadas",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            if (isScanningBle) {
                                CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = Color(0xFF195C3D))
                            } else {
                                TextButton(onClick = { startBleScan() }) {
                                    Text("Reintentar búsqueda", fontSize = 12.sp)
                                }
                            }
                        }

                        if (discoveredTowers.isEmpty()) {
                            Box(
                                modifier = Modifier.weight(1f).fillMaxWidth(),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text("Buscando señal de torres EcoGrow...", color = Color.Gray, fontSize = 14.sp)
                                    Text("Asegúrate de que el ESP32 esté a menos de 5 metros.", color = Color.LightGray, fontSize = 12.sp)
                                }
                            }
                        } else {
                            LazyColumn(
                                modifier = Modifier.weight(1f),
                                verticalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                items(discoveredTowers) { tower ->
                                    val isSelected = selectedTower?.address == tower.address
                                    Card(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable {
                                                selectedTower = tower
                                                customTowerName = "Torre ${tower.name.takeLast(4)}"
                                            },
                                        shape = RoundedCornerShape(12.dp),
                                        colors = CardDefaults.cardColors(
                                            containerColor = if (isSelected) Color(0xFFE8F5E9) else Color.White
                                        ),
                                        border = if (isSelected) androidx.compose.foundation.BorderStroke(2.dp, Color(0xFF195C3D)) else null,
                                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                                    ) {
                                        Row(
                                            Modifier.padding(16.dp).fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Column {
                                                Text(tower.name, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                                Text(tower.address, fontSize = 11.sp, color = Color.Gray)
                                            }
                                            Text("${tower.rssi} dBm", fontSize = 12.sp, color = Color(0xFF195C3D), fontWeight = FontWeight.SemiBold)
                                        }
                                    }
                                }
                            }
                        }

                        errorMessage?.let {
                            Text(it, color = Color(0xFFB3261E), fontSize = 12.sp)
                        }

                        Button(
                            onClick = {
                                bleManager?.stopScan()
                                currentStep = AddTowerStep.ENTER_PIN
                            },
                            enabled = selectedTower != null,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                        ) {
                            Text("Seleccionar Torre", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                // =========================================================================
                // PASO 4: INTRODUCIR PIN POP O ESCANEAR QR CON CÁMARA
                // =========================================================================
                AddTowerStep.ENTER_PIN -> {
                    Column(
                        Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            "Autenticación de Posesión (PIN / QR)",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF172B22)
                        )
                        Text(
                            "Dispositivo: ${selectedTower?.name ?: "EcoGrow"}\nIntroduce el PIN de 8 caracteres o escanea el código QR de la etiqueta:",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color(0xFF555555)
                        )

                        OutlinedButton(
                            onClick = { showQrCameraScanner = true },
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("📷 Escanear Código QR con Cámara", fontWeight = FontWeight.Bold)
                        }

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            HorizontalDivider(Modifier.weight(1f))
                            Text(" O INGRESO MANUAL ", fontSize = 11.sp, color = Color.Gray, modifier = Modifier.padding(horizontal = 8.dp))
                            HorizontalDivider(Modifier.weight(1f))
                        }

                        val isValidTowerCode = canonicalTowerCode.length >= 3 && canonicalTowerCode !in setOf("TORRE-001", "EG-TORRE-01", "DUMMY", "PRUEBA", "TEST")
                        val isCodePlaceholder = canonicalTowerCode.isNotBlank() && !isValidTowerCode

                        OutlinedTextField(
                            value = canonicalTowerCode,
                            onValueChange = {
                                canonicalTowerCode = it.trim().uppercase()
                                errorMessage = null
                            },
                            label = { Text("Código Canónico de la Torre (ej: EG-TORRE-A1B2C3)") },
                            placeholder = { Text("Código de etiqueta física o QR (obligatorio)") },
                            isError = isCodePlaceholder,
                            supportingText = {
                                if (isCodePlaceholder) {
                                    Text("Código inválido o placeholder genérico no permitido.", color = Color(0xFFB3261E))
                                } else if (canonicalTowerCode.isBlank()) {
                                    Text("Obligatorio: ingresa el código de la etiqueta física o escanea el QR.", color = Color.Gray)
                                }
                            },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        )

                        OutlinedTextField(
                            value = popInput,
                            onValueChange = {
                                popInput = BleProvisioningManager.sanitizePop(it)
                                errorMessage = null
                            },
                            label = { Text("PIN de Posesión (8 caracteres Base32)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        )

                        OutlinedTextField(
                            value = customTowerName,
                            onValueChange = { customTowerName = it },
                            label = { Text("Nombre para esta torre (opcional)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        )

                        errorMessage?.let {
                            Text(it, color = Color(0xFFB3261E), fontSize = 13.sp)
                        }

                        Spacer(Modifier.weight(1f))

                        Button(
                            onClick = {
                                val cleanPop = BleProvisioningManager.sanitizePop(popInput)
                                if (cleanPop.length < 8) {
                                    errorMessage = "El PIN debe tener 8 caracteres alfanuméricos válidos."
                                    return@Button
                                }
                                if (!isValidTowerCode) {
                                    errorMessage = "Introduce un código canónico válido de la torre (no se permiten códigos genéricos como TORRE-001 o EG-TORRE-01)."
                                    return@Button
                                }
                                popInput = cleanPop
                                errorMessage = null
                                currentStep = AddTowerStep.SCAN_WIFI
                            },
                            enabled = popInput.length >= 8 && isValidTowerCode,
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                        ) {
                            Text("Continuar a Redes WiFi", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                // =========================================================================
                // PASO 5: REDES WIFI DETECTADAS POR EL ESP32
                // =========================================================================
                AddTowerStep.SCAN_WIFI -> {
                    fun queryWifiFromTower() {
                        val tower = selectedTower ?: return
                        isScanningWifi = true
                        errorMessage = null
                        progressMessage = "Consultando redes WiFi detectadas por la antena del ESP32..."

                        bleManager?.scanWifiFromTower(
                            device = tower.device,
                            pop = popInput,
                            onNetworksFound = { wifis ->
                                isScanningWifi = false
                                discoveredWifis = wifis
                                if (selectedSsid.isBlank() && wifis.isNotEmpty()) {
                                    selectedSsid = wifis.first().ssid
                                }
                            },
                            onError = { err ->
                                isScanningWifi = false
                                errorMessage = err
                            }
                        )
                    }

                    LaunchedEffect(Unit) {
                        if (discoveredWifis.isEmpty()) {
                            queryWifiFromTower()
                        }
                    }

                    Column(
                        Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Redes WiFi Detectadas por la Torre", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                            if (isScanningWifi) {
                                CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp, color = Color(0xFF195C3D))
                            } else {
                                TextButton(onClick = { queryWifiFromTower() }) {
                                    Text("Escanear", fontSize = 12.sp)
                                }
                            }
                        }

                        if (isScanningWifi && discoveredWifis.isEmpty()) {
                            Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    CircularProgressIndicator(color = Color(0xFF195C3D))
                                    Text(progressMessage, fontSize = 12.sp, color = Color.Gray)
                                }
                            }
                        } else {
                            LazyColumn(
                                modifier = Modifier.weight(1f),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                items(discoveredWifis) { wifi ->
                                    val isSelected = !isManualSsid && selectedSsid == wifi.ssid
                                    Card(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable {
                                                isManualSsid = false
                                                selectedSsid = wifi.ssid
                                            },
                                        shape = RoundedCornerShape(10.dp),
                                        colors = CardDefaults.cardColors(
                                            containerColor = if (isSelected) Color(0xFFE8F5E9) else Color.White
                                        ),
                                        border = if (isSelected) androidx.compose.foundation.BorderStroke(2.dp, Color(0xFF195C3D)) else null,
                                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                                    ) {
                                        Row(
                                            Modifier.padding(14.dp).fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                                Text(if (wifi.isSecure) "🔒" else "🔓")
                                                Text(wifi.ssid, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                                            }
                                            Text("${wifi.level} dBm", fontSize = 11.sp, color = Color.Gray)
                                        }
                                    }
                                }

                                item {
                                    Card(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable { isManualSsid = true },
                                        shape = RoundedCornerShape(10.dp),
                                        colors = CardDefaults.cardColors(
                                            containerColor = if (isManualSsid) Color(0xFFE8F5E9) else Color(0xFFF9F9F9)
                                        ),
                                        border = if (isManualSsid) androidx.compose.foundation.BorderStroke(2.dp, Color(0xFF195C3D)) else null
                                    ) {
                                        Column(Modifier.padding(14.dp)) {
                                            Text("＋ Escribir nombre de red manual (SSID oculto)", fontSize = 13.sp, fontWeight = FontWeight.Medium)
                                            if (isManualSsid) {
                                                OutlinedTextField(
                                                    value = manualSsidInput,
                                                    onValueChange = { manualSsidInput = it },
                                                    label = { Text("Nombre de red (SSID)") },
                                                    singleLine = true,
                                                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        errorMessage?.let {
                            Text(it, color = Color(0xFFB3261E), fontSize = 12.sp)
                        }

                        Button(
                            onClick = {
                                val targetSsid = if (isManualSsid) manualSsidInput.trim() else selectedSsid
                                if (targetSsid.isBlank()) {
                                    errorMessage = "Selecciona o escribe una red WiFi."
                                    return@Button
                                }
                                errorMessage = null
                                currentStep = AddTowerStep.ENTER_PASSWORD
                            },
                            enabled = (!isManualSsid && selectedSsid.isNotBlank()) || (isManualSsid && manualSsidInput.isNotBlank()),
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                        ) {
                            Text("Continuar a Contraseña", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                // =========================================================================
                // PASO 6: CONTRASEÑA WIFI
                // =========================================================================
                AddTowerStep.ENTER_PASSWORD -> {
                    val targetSsid = if (isManualSsid) manualSsidInput.trim() else selectedSsid
                    Column(
                        Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            "Contraseña de WiFi",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF172B22)
                        )
                        Text(
                            "Red seleccionada: $targetSsid\nIngresa la contraseña de tu red para que la torre se conecte a internet:",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color(0xFF555555)
                        )

                        OutlinedTextField(
                            value = wifiPassword,
                            onValueChange = { wifiPassword = it },
                            label = { Text("Contraseña WiFi") },
                            singleLine = true,
                            visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                            trailingIcon = {
                                TextButton(onClick = { passwordVisible = !passwordVisible }) {
                                    Text(if (passwordVisible) "Ocultar" else "Ver", fontSize = 12.sp)
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        )

                        Text(
                            "Nota: Las torres EcoGrow operan en bandas de 2.4 GHz estándar.",
                            fontSize = 11.sp,
                            color = Color.Gray
                        )

                        Spacer(Modifier.weight(1f))

                        Button(
                            onClick = {
                                errorMessage = null
                                currentStep = AddTowerStep.PROVISIONING
                            },
                            modifier = Modifier.fillMaxWidth().height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                        ) {
                            Text("Enviar Credenciales a la Torre", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                // =========================================================================
                // PASO 7: PROGRESO REAL DE CONFIGURACIÓN Y CONEXIÓN
                // =========================================================================
                AddTowerStep.PROVISIONING -> {
                    val targetSsid = if (isManualSsid) manualSsidInput.trim() else selectedSsid

                    LaunchedEffect(Unit) {
                        val tower = selectedTower ?: return@LaunchedEffect
                        errorMessage = null
                        bleManager?.provisionTower(
                            device = tower.device,
                            ssid = targetSsid,
                            passphrase = wifiPassword,
                            pop = popInput,
                            onStepChanged = { step, msg ->
                                provStep = step
                                progressMessage = msg
                                if (step == BleProvStep.SUCCESS) {
                                    currentStep = AddTowerStep.SUCCESS
                                } else if (step == BleProvStep.FAILED) {
                                    errorMessage = msg
                                }
                            }
                        )
                    }

                    Column(
                        Modifier.fillMaxSize(),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        if (provStep == BleProvStep.FAILED) {
                            Text("❌ Error de Aprovisionamiento", style = MaterialTheme.typography.titleLarge, color = Color(0xFFB3261E), fontWeight = FontWeight.Bold)
                            Spacer(Modifier.height(12.dp))
                            Text(errorMessage ?: "Fallo desconocido al configurar la torre.", color = Color(0xFF555555), fontSize = 14.sp)
                            Spacer(Modifier.height(24.dp))
                            Button(
                                onClick = { currentStep = AddTowerStep.ENTER_PASSWORD },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                            ) {
                                Text("Reintentar con otra red o clave")
                            }
                        } else {
                            CircularProgressIndicator(modifier = Modifier.size(56.dp), color = Color(0xFF195C3D), strokeWidth = 4.dp)
                            Spacer(Modifier.height(24.dp))
                            Text(
                                "Configurando Torre...",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF172B22)
                            )
                            Spacer(Modifier.height(8.dp))
                            Text(progressMessage, fontSize = 14.sp, color = Color.Gray)
                        }
                    }
                }

                // =========================================================================
                // PASO 8: CONFIRMACIÓN Y VINCULACIÓN EN CLOUD SEPARADA CON TELEMETRÍA REAL
                // =========================================================================
                AddTowerStep.SUCCESS -> {
                    val derivedCode = canonicalTowerCode.trim().uppercase()
                    val towerName = customTowerName.ifBlank { "Torre ${derivedCode.takeLast(4)}" }

                    fun triggerBind() {
                        if (!isBindingCloud) {
                            isBindingCloud = true
                            cloudBindError = null
                            onTowerAddedAndBound(derivedCode, popInput, towerName) { ok, err, newId ->
                                isBindingCloud = false
                                cloudBindSuccess = ok
                                cloudBindError = err
                                boundTowerId = newId
                            }
                        }
                    }

                    LaunchedEffect(Unit) {
                        if (!cloudBindSuccess) {
                            triggerBind()
                        }
                    }

                    // Polling para confirmar la primera telemetría real recibida en el backend
                    LaunchedEffect(cloudBindSuccess, boundTowerId, telemetryPollTrigger) {
                        val towerId = boundTowerId
                        if (cloudBindSuccess && towerId != null && onFetchTowerDetail != null && !telemetryConfirmed) {
                            isPollingTelemetry = true
                            pollingTimeout = false
                            var attempts = 0
                            while (attempts < 10 && !telemetryConfirmed) {
                                kotlinx.coroutines.delay(3000L)
                                attempts++
                                try {
                                    val detail = onFetchTowerDetail.invoke(towerId)
                                    if (detail != null && !detail.stale && detail.updatedAt != null) {
                                        firstTelemetryData = detail
                                        telemetryConfirmed = true
                                        isPollingTelemetry = false
                                        break
                                    }
                                } catch (_: Exception) {
                                    // reintento continuo en siguiente iteración
                                }
                            }
                            if (!telemetryConfirmed) {
                                isPollingTelemetry = false
                                pollingTimeout = true
                            }
                        }
                    }

                    Card(
                        modifier = Modifier.fillMaxWidth().verticalScroll(rememberScrollState()),
                        shape = RoundedCornerShape(20.dp),
                        colors = CardDefaults.cardColors(containerColor = if (cloudBindError != null) Color(0xFFFFF3E0) else Color(0xFFE8F5E9))
                    ) {
                        Column(
                            Modifier.padding(24.dp),
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            val titleText = when {
                                cloudBindSuccess && telemetryConfirmed -> "🎉 ¡Torre Vinculada y Operativa!"
                                cloudBindSuccess && pollingTimeout -> "⚠️ Torre Vinculada · Esperando Primeros Datos"
                                cloudBindSuccess -> "⏳ Torre Vinculada · Esperando Telemetría..."
                                cloudBindError != null -> "⚠️ WiFi Conectado · Vinculación Pendiente"
                                else -> "⏳ WiFi Conectado · Vinculando en la Nube..."
                            }

                            val titleColor = when {
                                cloudBindSuccess && telemetryConfirmed -> Color(0xFF1B5E20)
                                cloudBindSuccess && pollingTimeout -> Color(0xFFE65100)
                                cloudBindSuccess -> Color(0xFF087F8C)
                                cloudBindError != null -> Color(0xFFB3261E)
                                else -> Color(0xFF087F8C)
                            }

                            val descriptionText = when {
                                cloudBindSuccess && telemetryConfirmed -> "Tu torre $derivedCode se conectó a tu router WiFi, ha sido vinculada exitosamente a tu cuenta y sus sensores están transmitiendo en tiempo real."
                                cloudBindSuccess && pollingTimeout -> "Tu torre $derivedCode está vinculada a tu cuenta y conectada al router WiFi, pero aún no se han recibido lecturas de sensores. Puedes reintentar la comprobación de telemetría o ingresar al dashboard para supervisarla."
                                cloudBindSuccess -> "Tu torre $derivedCode se conectó al WiFi y ha sido vinculada a tu cuenta. Esperando la primera lectura de los sensores de la torre..."
                                cloudBindError != null -> "La torre completó la conexión WiFi al router, pero la vinculación remota con la cuenta falló: $cloudBindError"
                                else -> "La torre completó la conexión WiFi al router. Autenticando con el servidor remoto..."
                            }

                            Text(
                                titleText,
                                style = MaterialTheme.typography.headlineSmall,
                                fontWeight = FontWeight.Bold,
                                color = titleColor
                            )

                            Text(
                                descriptionText,
                                style = MaterialTheme.typography.bodyMedium
                            )

                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = Color.White,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text("✓ 1. Conexión BLE y sesión Security 1 verificada", fontSize = 13.sp, color = Color(0xFF2E7D32), fontWeight = FontWeight.SemiBold)
                                    Text("✓ 2. Router WiFi conectado por el ESP32", fontSize = 13.sp, color = Color(0xFF2E7D32), fontWeight = FontWeight.SemiBold)

                                    if (isBindingCloud) {
                                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                            CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp, color = Color(0xFF087F8C))
                                            Text("⏳ 3. Vinculando torre a tu cuenta con prueba criptográfica PoP...", fontSize = 13.sp, color = Color(0xFF087F8C))
                                        }
                                    } else if (cloudBindSuccess) {
                                        Text("✓ 3. Torre vinculada a tu cuenta con autenticación PoP verificada", fontSize = 13.sp, color = Color(0xFF2E7D32), fontWeight = FontWeight.SemiBold)

                                        if (telemetryConfirmed && firstTelemetryData != null) {
                                            val t = firstTelemetryData!!
                                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                                Text("✓ 4. Primera telemetría en tiempo real recibida:", fontSize = 13.sp, color = Color(0xFF2E7D32), fontWeight = FontWeight.SemiBold)
                                                Text(
                                                    "Nivel: ${t.sensors.nivelFormatted()} (${t.sensors.litrosFormatted()}) · pH: ${t.sensors.phFormatted()} · TDS: ${t.sensors.tdsFormatted()} · Temp: ${t.sensors.tempFormatted()}",
                                                    fontSize = 12.sp,
                                                    color = Color(0xFF195C3D),
                                                    fontWeight = FontWeight.Medium
                                                )
                                            }
                                        } else if (pollingTimeout) {
                                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                                Text("⚠️ 4. Sin lecturas de sensores recibidas aún tras la vinculación.", fontSize = 12.sp, color = Color(0xFFE65100), fontWeight = FontWeight.SemiBold)
                                                Text("La torre está enlazada. Si los sensores aún se están inicializando, puedes reintentar la comprobación o ingresar al dashboard.", fontSize = 11.sp, color = Color(0xFF555555))
                                            }
                                        } else {
                                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                                CircularProgressIndicator(Modifier.size(14.dp), strokeWidth = 2.dp, color = Color(0xFF195C3D))
                                                Text("📡 4. Esperando primera telemetría del ciclo desde el servidor remoto...", fontSize = 12.sp, color = Color(0xFF555555))
                                            }
                                        }
                                    } else if (cloudBindError != null) {
                                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                            Text("⚠️ 3. Error al vincular con la cuenta: $cloudBindError", fontSize = 12.sp, color = Color(0xFFB3261E), fontWeight = FontWeight.SemiBold)
                                            Text("Verifica que el PIN PoP coincida con la torre y que el servidor remoto esté accesible.", fontSize = 11.sp, color = Color(0xFF555555))
                                        }
                                    }
                                }
                            }

                            if (cloudBindError != null) {
                                Button(
                                    onClick = { triggerBind() },
                                    enabled = !isBindingCloud,
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D)),
                                    modifier = Modifier.fillMaxWidth().height(50.dp),
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    Text("🔄 Reintentar Vinculación en la Nube", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                }

                                OutlinedButton(
                                    onClick = onCancel,
                                    modifier = Modifier.fillMaxWidth().height(48.dp),
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    Text("Cerrar y Vincular Más Tarde", color = Color(0xFF555555))
                                }
                            } else {
                                if (cloudBindSuccess && pollingTimeout && !telemetryConfirmed) {
                                    Button(
                                        onClick = {
                                            pollingTimeout = false
                                            telemetryPollTrigger++
                                        },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF087F8C)),
                                        modifier = Modifier.fillMaxWidth().height(50.dp),
                                        shape = RoundedCornerShape(12.dp)
                                    ) {
                                        Text("🔄 Reintentar Comprobación de Telemetría", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                    }
                                }

                                Button(
                                    onClick = {
                                        val targetId = boundTowerId
                                        if (cloudBindSuccess && targetId != null && onOpenTowerDetail != null) {
                                            onOpenTowerDetail(targetId)
                                        } else {
                                            onCancel()
                                        }
                                    },
                                    enabled = !isBindingCloud,
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D)),
                                    modifier = Modifier.fillMaxWidth().height(50.dp),
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    Text(
                                        if (cloudBindSuccess) "🚀 Abrir Dashboard de la Torre" else "Entrar al Dashboard",
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 16.sp
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun QrCameraScannerDialog(
    onQrScanned: (String) -> Unit,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasCameraPermission = granted
        if (!granted) {
            onDismiss()
        }
    }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    if (hasCameraPermission) {
        Dialog(onDismissRequest = onDismiss) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(440.dp),
                shape = RoundedCornerShape(20.dp)
            ) {
                Box(Modifier.fillMaxSize()) {
                    AndroidView(
                        factory = { ctx ->
                            val previewView = PreviewView(ctx)
                            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                            cameraProviderFuture.addListener({
                                val cameraProvider = cameraProviderFuture.get()
                                val preview = Preview.Builder().build().also {
                                    it.surfaceProvider = previewView.surfaceProvider
                                }
                                val imageAnalysis = ImageAnalysis.Builder()
                                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                                    .build()

                                val reader = MultiFormatReader().apply {
                                    val hints = mapOf(
                                        DecodeHintType.POSSIBLE_FORMATS to listOf(BarcodeFormat.QR_CODE)
                                    )
                                    setHints(hints)
                                }

                                var isScanned = false
                                imageAnalysis.setAnalyzer(Executors.newSingleThreadExecutor()) { imageProxy ->
                                    if (isScanned) {
                                        imageProxy.close()
                                        return@setAnalyzer
                                    }
                                    val buffer = imageProxy.planes[0].buffer
                                    val data = ByteArray(buffer.remaining())
                                    buffer.get(data)
                                    val width = imageProxy.width
                                    val height = imageProxy.height
                                    val source = PlanarYUVLuminanceSource(
                                        data, width, height, 0, 0, width, height, false
                                    )
                                    val binaryBitmap = BinaryBitmap(HybridBinarizer(source))
                                    try {
                                        val result = reader.decodeWithState(binaryBitmap)
                                        isScanned = true
                                        Handler(Looper.getMainLooper()).post {
                                            onQrScanned(result.text)
                                        }
                                    } catch (_: Exception) {
                                    } finally {
                                        reader.reset()
                                        imageProxy.close()
                                    }
                                }

                                try {
                                    cameraProvider.unbindAll()
                                    cameraProvider.bindToLifecycle(
                                        lifecycleOwner,
                                        CameraSelector.DEFAULT_BACK_CAMERA,
                                        preview,
                                        imageAnalysis
                                    )
                                } catch (e: Exception) {
                                    Log.e("QrScanner", "Fallo al iniciar cámara", e)
                                }
                            }, ContextCompat.getMainExecutor(ctx))
                            previewView
                        },
                        modifier = Modifier.fillMaxSize()
                    )

                    // Overlay guía de escaneo
                    Box(
                        modifier = Modifier
                            .size(240.dp)
                            .align(Alignment.Center)
                            .border(2.dp, Color(0xFF195C3D), RoundedCornerShape(16.dp))
                    )

                    IconButton(
                        onClick = onDismiss,
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .padding(12.dp)
                    ) {
                        Surface(
                            shape = CircleShape,
                            color = Color.Black.copy(alpha = 0.6f),
                            modifier = Modifier.size(36.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text("✕", color = Color.White, fontWeight = FontWeight.Bold)
                            }
                        }
                    }

                    Surface(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(16.dp),
                        shape = RoundedCornerShape(8.dp),
                        color = Color.Black.copy(alpha = 0.7f)
                    ) {
                        Text(
                            "Apunta la cámara al código QR de la etiqueta física",
                            color = Color.White,
                            fontSize = 12.sp,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun InstructionItem(number: String, title: String, description: String) {
    Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primaryContainer),
            contentAlignment = Alignment.Center
        ) {
            Text(number, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary, fontSize = 13.sp)
        }
        Column(Modifier.weight(1f)) {
            Text(title, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            Text(description, fontSize = 12.sp, color = Color(0xFF666666))
        }
    }
}

@Composable
private fun StatusCheckItem(title: String, isOk: Boolean, okText: String, failText: String) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(if (isOk) Color(0xFFE8F5E9) else Color(0xFFFFEBEE))
            .padding(10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(title, fontWeight = FontWeight.Medium, fontSize = 13.sp)
        Text(
            if (isOk) "✓ $okText" else "✗ $failText",
            fontWeight = FontWeight.Bold,
            color = if (isOk) Color(0xFF2E7D32) else Color(0xFFC62828),
            fontSize = 12.sp
        )
    }
}
