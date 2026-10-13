package com.ecogrow.mobile

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat

enum class AddTowerStep {
    INSTRUCTIONS,       // 1. Qué hacer con la torre físicamente
    PERMISSIONS,        // 2. Comprobar Bluetooth y permisos
    SCAN_BLE,           // 3. Buscar torres BLE en el aire
    ENTER_PIN,          // 4. Seleccionar torre e introducir PIN PoP
    SCAN_WIFI,          // 5. Redes WiFi detectadas por el ESP32 (o manual)
    ENTER_PASSWORD,     // 6. Contraseña WiFi
    PROVISIONING,       // 7. Progreso real de configuración y conexión
    SUCCESS             // 8. Confirmación y acceso al dashboard
}

@Composable
fun AddTowerScreen(
    bleManager: BleProvisioningManager?,
    onCancel: () -> Unit,
    onTowerAdded: (towerName: String, pop: String, ip: String?) -> Unit
) {
    val context = LocalContext.current
    var currentStep by remember { mutableStateOf(AddTowerStep.INSTRUCTIONS) }

    // Estados conservados entre pasos (sin pérdida de datos introducidos)
    var discoveredTowers by remember { mutableStateOf<List<DiscoveredTower>>(emptyList()) }
    var selectedTower by remember { mutableStateOf<DiscoveredTower?>(null) }
    var popInput by remember { mutableStateOf("") }
    var discoveredWifis by remember { mutableStateOf<List<DiscoveredWifi>>(emptyList()) }
    var selectedSsid by remember { mutableStateOf("") }
    var isManualSsid by remember { mutableStateOf(false) }
    var manualSsidInput by remember { mutableStateOf("") }
    var wifiPassword by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }

    // Estados de carga y error accionable
    var isScanningBle by remember { mutableStateOf(false) }
    var isScanningWifi by remember { mutableStateOf(false) }
    var provStep by remember { mutableStateOf(BleProvStep.IDLE) }
    var progressMessage by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Permisos Bluetooth requeridos según versión de Android
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

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { perms ->
        val allGranted = perms.values.all { it }
        if (allGranted) {
            errorMessage = null
            currentStep = AddTowerStep.SCAN_BLE
        } else {
            errorMessage = "Se requieren permisos de Bluetooth y Ubicación para detectar torres cercanas."
        }
    }

    // Función para buscar torres BLE
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
                    if (selectedTower == null) selectedTower = found
                }
            },
            onError = { err ->
                isScanningBle = false
                errorMessage = err
            },
            onTimeout = {
                isScanningBle = false
                if (discoveredTowers.isEmpty()) {
                    errorMessage = "No se detectó ninguna torre EcoGrow cercana. Verifica que esté encendida."
                }
            }
        )
    }

    // Al entrar en el paso SCAN_BLE, iniciar búsqueda automáticamente
    LaunchedEffect(currentStep) {
        if (currentStep == AddTowerStep.SCAN_BLE) {
            startBleScan()
        }
    }

    // Cabecera superior con botón Cancelar y Pasos
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
                        Text(
                            "Añadir Torre EcoGrow",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        TextButton(onClick = {
                            bleManager?.cancelProvisioning()
                            bleManager?.stopScan()
                            onCancel()
                        }) {
                            Text("Cancelar", color = Color(0xFF666666))
                        }
                    }

                    // Indicador de Progreso por Pasos
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        AddTowerStep.values().filter { it != AddTowerStep.SUCCESS }.forEachIndexed { idx, step ->
                            val isCompleted = step.ordinal < currentStep.ordinal
                            val isCurrent = step == currentStep
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .height(4.dp)
                                    .clip(RoundedCornerShape(2.dp))
                                    .background(
                                        when {
                                            isCompleted -> MaterialTheme.colorScheme.primary
                                            isCurrent -> MaterialTheme.colorScheme.primary
                                            else -> Color(0xFFE0E0E0)
                                        }
                                    )
                            )
                        }
                    }
                }
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Mensaje de Error accionable si existe
            errorMessage?.let { err ->
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = err,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // =========================================================================
            // PASO 1: INSTRUCCIONES FÍSICAS DE LA TORRE
            // =========================================================================
            if (currentStep == AddTowerStep.INSTRUCTIONS) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        Text(
                            "🌱 Paso 1: Preparación de la Torre",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            "Antes de comenzar, asegúrate de que tu torre hidropónica esté lista para vincularse:",
                            style = MaterialTheme.typography.bodyMedium
                        )

                        InstructionItem(
                            number = "1",
                            title = "Conecta la torre a la corriente",
                            description = "El microcontrolador ESP32 encenderá y comenzará a emitir su señal Bluetooth de configuración."
                        )

                        InstructionItem(
                            number = "2",
                            title = "¿Cambiaste de router WiFi?",
                            description = "Si la torre ya tenía otra red guardada, mantén presionado el botón BOOT entre 3 y 8 segundos para reactivar el Bluetooth conservando tu PIN de posesión."
                        )

                        InstructionItem(
                            number = "3",
                            title = "Ten a mano la etiqueta física",
                            description = "Necesitarás el código PIN o QR impreso en el chasis de la torre para autenticar la conexión."
                        )

                        Spacer(Modifier.height(8.dp))
                        Button(
                            onClick = {
                                if (hasPermissions() && bleManager?.isBluetoothEnabled == true) {
                                    currentStep = AddTowerStep.SCAN_BLE
                                } else {
                                    currentStep = AddTowerStep.PERMISSIONS
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("Mi Torre está Encendida · Continuar", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // =========================================================================
            // PASO 2: COMPROBACIÓN DE BLUETOOTH Y PERMISOS
            // =========================================================================
            if (currentStep == AddTowerStep.PERMISSIONS) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        Text(
                            "📡 Paso 2: Permisos de Conexión",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            "Para comunicarse con la torre mediante Bluetooth Low Energy (BLE), la app requiere los permisos necesarios del sistema operativo:",
                            style = MaterialTheme.typography.bodyMedium
                        )

                        val btEnabled = bleManager?.isBluetoothEnabled == true
                        val permsOk = hasPermissions()

                        StatusCheckItem(
                            title = "Bluetooth en este Celular",
                            isOk = btEnabled,
                            okText = "Bluetooth Activado",
                            failText = "Bluetooth Apagado"
                        )

                        StatusCheckItem(
                            title = "Permisos de Escaneo Cercano (BLE)",
                            isOk = permsOk,
                            okText = "Permisos Concedidos",
                            failText = "Permisos Pendientes"
                        )

                        if (!btEnabled) {
                            OutlinedButton(
                                onClick = {
                                    val enableBtIntent = Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)
                                    context.startActivity(enableBtIntent)
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Activar Bluetooth")
                            }
                        }

                        if (!permsOk) {
                            Button(
                                onClick = { permissionLauncher.launch(requiredPermissions) },
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("Conceder Permisos", fontWeight = FontWeight.Bold)
                            }
                        } else if (btEnabled) {
                            Button(
                                onClick = { currentStep = AddTowerStep.SCAN_BLE },
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("Buscar Torres Cercanas", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // PASO 3: BÚSQUEDA DE TORRES BLE EN EL AIRE
            // =========================================================================
            if (currentStep == AddTowerStep.SCAN_BLE) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                "🔍 Paso 3: Torres Detectadas",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                            if (isScanningBle) {
                                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                            } else {
                                TextButton(onClick = { startBleScan() }) {
                                    Text("Reescanear")
                                }
                            }
                        }

                        if (discoveredTowers.isEmpty()) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 24.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text("Buscando señal Bluetooth de la torre...", color = Color.Gray)
                                    Spacer(Modifier.height(8.dp))
                                    Text("Asegúrate de estar a menos de 5 metros de la torre.", fontSize = 12.sp, color = Color.Gray)
                                }
                            }
                        } else {
                            Text("Selecciona tu torre de la lista:", style = MaterialTheme.typography.bodySmall)
                            discoveredTowers.forEach { tower ->
                                val selected = selectedTower?.address == tower.address
                                Surface(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { selectedTower = tower },
                                    shape = RoundedCornerShape(12.dp),
                                    color = if (selected) MaterialTheme.colorScheme.primaryContainer else Color(0xFFF6FAF6),
                                    border = if (selected) androidx.compose.foundation.BorderStroke(1.5.dp, MaterialTheme.colorScheme.primary) else null
                                ) {
                                    Row(
                                        Modifier.padding(14.dp),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Column {
                                            Text(tower.name, fontWeight = FontWeight.Bold)
                                            Text("Dirección: ${tower.address} · Señal: ${tower.rssi} dBm", fontSize = 12.sp, color = Color(0xFF555555))
                                        }
                                        RadioButton(selected = selected, onClick = { selectedTower = tower })
                                    }
                                }
                            }

                            Button(
                                onClick = {
                                    bleManager?.stopScan()
                                    currentStep = AddTowerStep.ENTER_PIN
                                },
                                enabled = selectedTower != null,
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("Vincular ${selectedTower?.name ?: "Torre"}", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // PASO 4: INTRODUCIR PIN POP O ESCANEAR QR
            // =========================================================================
            if (currentStep == AddTowerStep.ENTER_PIN) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        Text(
                            "🔐 Paso 4: Clave PoP de la Torre",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            "Ingresa el PIN de 8 caracteres que se encuentra en la etiqueta física de tu torre ${selectedTower?.name}:",
                            style = MaterialTheme.typography.bodyMedium
                        )

                        OutlinedTextField(
                            value = popInput,
                            onValueChange = { input ->
                                popInput = BleProvisioningManager.sanitizePop(input)
                            },
                            label = { Text("PIN PoP (8 caracteres Base32)") },
                            placeholder = { Text("Ej: A7K9M2PX") },
                            supportingText = {
                                Text("Puedes escribir el PIN o pegar el texto completo del código QR.")
                            },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )

                        val popValido = popInput.length == 8

                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedButton(
                                onClick = { currentStep = AddTowerStep.SCAN_BLE },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Atrás")
                            }
                            Button(
                                onClick = {
                                    val tower = selectedTower ?: return@Button
                                    errorMessage = null
                                    isScanningWifi = true
                                    currentStep = AddTowerStep.SCAN_WIFI
                                    bleManager?.scanWifiFromTower(
                                        device = tower.device,
                                        pop = popInput,
                                        onNetworksFound = { networks ->
                                            isScanningWifi = false
                                            discoveredWifis = networks
                                            if (selectedSsid.isBlank() && networks.isNotEmpty()) {
                                                selectedSsid = networks.first().ssid
                                            }
                                        },
                                        onError = { err ->
                                            isScanningWifi = false
                                            errorMessage = err
                                        }
                                    )
                                },
                                enabled = popValido,
                                modifier = Modifier.weight(2f),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("Buscar Redes WiFi", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // PASO 5: REDES WIFI DETECTADAS POR EL ESP32
            // =========================================================================
            if (currentStep == AddTowerStep.SCAN_WIFI) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                "📶 Paso 5: Red WiFi para la Torre",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                            if (isScanningWifi) {
                                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                            }
                        }

                        if (isScanningWifi) {
                            Text(
                                "La torre está escaneando las redes WiFi a su alrededor con su propia antena...",
                                style = MaterialTheme.typography.bodySmall,
                                color = Color.Gray
                            )
                        } else {
                            if (!isManualSsid && discoveredWifis.isNotEmpty()) {
                                Text("Selecciona la red WiFi (2.4 GHz) a la que se conectará la torre:", style = MaterialTheme.typography.bodySmall)

                                discoveredWifis.take(6).forEach { wifi ->
                                    val selected = selectedSsid == wifi.ssid
                                    Surface(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable { selectedSsid = wifi.ssid },
                                        shape = RoundedCornerShape(10.dp),
                                        color = if (selected) MaterialTheme.colorScheme.primaryContainer else Color(0xFFF1F5F1)
                                    ) {
                                        Row(
                                            Modifier.padding(12.dp),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Text(if (wifi.isSecure) "🔒 " else "📶 ")
                                                Text(wifi.ssid, fontWeight = FontWeight.SemiBold)
                                            }
                                            RadioButton(selected = selected, onClick = { selectedSsid = wifi.ssid })
                                        }
                                    }
                                }

                                TextButton(onClick = { isManualSsid = true }) {
                                    Text("✎ Ingresar red oculta o manual...")
                                }
                            } else {
                                OutlinedTextField(
                                    value = manualSsidInput,
                                    onValueChange = { manualSsidInput = it },
                                    label = { Text("Nombre de Red (SSID Manual)") },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth()
                                )
                                if (discoveredWifis.isNotEmpty()) {
                                    TextButton(onClick = { isManualSsid = false }) {
                                        Text("← Volver a lista de redes detectadas")
                                    }
                                }
                            }

                            val effectiveSsid = if (isManualSsid) manualSsidInput.trim() else selectedSsid

                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                OutlinedButton(
                                    onClick = { currentStep = AddTowerStep.ENTER_PIN },
                                    modifier = Modifier.weight(1f)
                                ) {
                                    Text("Atrás")
                                }
                                Button(
                                    onClick = { currentStep = AddTowerStep.ENTER_PASSWORD },
                                    enabled = effectiveSsid.isNotBlank(),
                                    modifier = Modifier.weight(2f),
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    Text("Siguiente", fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // PASO 6: CONTRASEÑA WIFI Y CONFIRMACIÓN
            // =========================================================================
            if (currentStep == AddTowerStep.ENTER_PASSWORD) {
                val effectiveSsid = if (isManualSsid) manualSsidInput.trim() else selectedSsid
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                        Text(
                            "🔑 Paso 6: Contraseña de WiFi",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            "Ingresa la contraseña de la red '$effectiveSsid' para que la torre pueda navegar y transmitir datos:",
                            style = MaterialTheme.typography.bodyMedium
                        )

                        OutlinedTextField(
                            value = wifiPassword,
                            onValueChange = { wifiPassword = it },
                            label = { Text("Contraseña de WiFi") },
                            visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                            trailingIcon = {
                                TextButton(onClick = { passwordVisible = !passwordVisible }) {
                                    Text(if (passwordVisible) "Ocultar" else "Ver")
                                }
                            },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )

                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedButton(
                                onClick = { currentStep = AddTowerStep.SCAN_WIFI },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Atrás")
                            }
                            Button(
                                onClick = {
                                    val tower = selectedTower ?: return@Button
                                    errorMessage = null
                                    currentStep = AddTowerStep.PROVISIONING
                                    progressMessage = "Iniciando transferencia de credenciales..."

                                    bleManager?.provisionTower(
                                        device = tower.device,
                                        ssid = effectiveSsid,
                                        passphrase = wifiPassword,
                                        pop = popInput
                                    ) { step, msg ->
                                        provStep = step
                                        progressMessage = msg
                                        if (step == BleProvStep.SUCCESS) {
                                            currentStep = AddTowerStep.SUCCESS
                                        } else if (step == BleProvStep.FAILED) {
                                            errorMessage = msg
                                        }
                                    }
                                },
                                modifier = Modifier.weight(2f),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("Conectar Torre", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // PASO 7: PROGRESO REAL DE CONFIGURACIÓN
            // =========================================================================
            if (currentStep == AddTowerStep.PROVISIONING) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(
                        Modifier.padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        CircularProgressIndicator(Modifier.size(48.dp), color = MaterialTheme.colorScheme.primary)

                        Text(
                            "Configurando tu Torre EcoGrow",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )

                        Text(
                            text = progressMessage,
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color(0xFF445544)
                        )

                        if (errorMessage != null) {
                            Button(
                                onClick = {
                                    // Permitir reintentar sin perder contraseña ni PIN
                                    currentStep = AddTowerStep.ENTER_PASSWORD
                                },
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("Reintentar con Otra Clave")
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // PASO 8: ÉXITO Y ENTRADA AL DASHBOARD
            // =========================================================================
            if (currentStep == AddTowerStep.SUCCESS) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5E9))
                ) {
                    Column(
                        Modifier.padding(24.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Text(
                            "🎉 ¡Torre Vinculada Exitosamente!",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF1B5E20)
                        )

                        Text(
                            "Tu torre ${selectedTower?.name ?: "EcoGrow"} ya está conectada al router WiFi y comenzó a comunicarse con el servidor.",
                            style = MaterialTheme.typography.bodyMedium
                        )

                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = Color.White,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text("✓ Conexión BLE y sesión Security 1 verificada", fontSize = 12.sp, color = Color(0xFF2E7D32))
                                Text("✓ Credenciales WiFi aplicadas en el ESP32", fontSize = 12.sp, color = Color(0xFF2E7D32))
                                Text("✓ IP asignada y enlace HTTPS TLS activo", fontSize = 12.sp, color = Color(0xFF2E7D32))
                            }
                        }

                        Button(
                            onClick = {
                                val towerName = selectedTower?.name ?: "EcoGrow"
                                onTowerAdded(towerName, popInput, null)
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D)),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("🚀 Abrir Dashboard de la Torre", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                        }
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
