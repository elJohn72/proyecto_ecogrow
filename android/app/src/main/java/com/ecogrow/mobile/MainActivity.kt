package com.ecogrow.mobile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import org.json.JSONObject

data class DiscoveredWifi(
    val ssid: String,
    val level: Int,
    val isSecure: Boolean,
    val isCurrent: Boolean
)

@Suppress("DEPRECATION")
fun getAvailableWifiNetworks(context: Context): List<DiscoveredWifi> {
    val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager ?: return emptyList()
    val currentSsid = try {
        wifiManager.connectionInfo?.ssid?.removePrefix("\"")?.removeSuffix("\"")?.takeIf { it != "<unknown ssid>" && it.isNotBlank() }
    } catch (_: Exception) { null }

    val scanResults = try {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            wifiManager.scanResults
        } else emptyList()
    } catch (_: Exception) { emptyList() }

    val map = mutableMapOf<String, DiscoveredWifi>()
    currentSsid?.let {
        map[it] = DiscoveredWifi(ssid = it, level = -50, isSecure = true, isCurrent = true)
    }
    scanResults.forEach { r ->
        val s = r.SSID
        if (!s.isNullOrBlank() && !map.containsKey(s)) {
            val secure = r.capabilities.contains("WPA") || r.capabilities.contains("WEP")
            map[s] = DiscoveredWifi(ssid = s, level = r.level, isSecure = secure, isCurrent = s == currentSsid)
        }
    }
    return map.values.sortedWith(compareByDescending<DiscoveredWifi> { it.isCurrent }.thenByDescending { it.level })
}

class MainActivity : ComponentActivity() {
    private var bleManager: BleProvisioningManager? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bleManager = BleProvisioningManager(this)

        setContent {
            val customTheme = lightColorScheme(
                primary = Color(0xFF195C3D),
                onPrimary = Color.White,
                primaryContainer = Color(0xFFD8EEDB),
                onPrimaryContainer = Color(0xFF072113),
                secondary = Color(0xFF4C6652),
                background = Color(0xFFF7FAF7),
                surface = Color.White,
                surfaceVariant = Color(0xFFEEF3EE)
            )

            MaterialTheme(colorScheme = customTheme) {
                val vm: EcoGrowViewModel = viewModel()
                val state by vm.ui.collectAsStateWithLifecycle()
                var showBleDialog by remember { mutableStateOf(false) }

                Scaffold { inset ->
                    Column(
                        Modifier
                            .fillMaxSize()
                            .padding(inset)
                            .verticalScroll(rememberScrollState())
                            .padding(horizontal = 20.dp, vertical = 18.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // Header corporativo AJTecnology / EcoGrow
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    "EcoGrow 2.0",
                                    style = MaterialTheme.typography.headlineMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                Text(
                                    "Torre Hidropónica Vertical Inteligente",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = Color(0xFF556859)
                                )
                            }
                            FilledTonalButton(
                                onClick = { showBleDialog = true },
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                            ) {
                                Text("📶 BLE", fontWeight = FontWeight.Bold)
                            }
                        }

                        if (state.busy) {
                            LinearProgressIndicator(Modifier.fillMaxWidth())
                        }

                        state.error?.let {
                            Surface(
                                color = MaterialTheme.colorScheme.errorContainer,
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text(
                                    it,
                                    Modifier.padding(14.dp),
                                    color = MaterialTheme.colorScheme.onErrorContainer,
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }
                        }

                        state.notice?.let {
                            Surface(
                                color = MaterialTheme.colorScheme.primaryContainer,
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text(
                                    it,
                                    Modifier.padding(14.dp),
                                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                                    style = MaterialTheme.typography.bodyMedium
                                )
                            }
                        }

                        if (!state.authenticated) {
                            HomeConnectionScreen(
                                vm = vm,
                                busy = state.busy,
                                onOpenBle = { showBleDialog = true }
                            )
                        } else {
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Surface(
                                    color = MaterialTheme.colorScheme.primaryContainer,
                                    shape = RoundedCornerShape(20.dp)
                                ) {
                                    Text(
                                        text = state.user,
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = FontWeight.SemiBold,
                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                                    )
                                }
                                TextButton(onClick = vm::logout, enabled = !state.busy) {
                                    Text("Desconectar")
                                }
                            }

                            val detail = state.detail
                            if (detail != null) {
                                TowerDetail(detail, vm, state.busy, state.error != null)
                            } else if (state.towers.isNotEmpty()) {
                                Text("Torres disponibles en tu cuenta:", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                state.towers.forEach { tower ->
                                    Card(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable { vm.select(tower.id) },
                                        shape = RoundedCornerShape(12.dp),
                                        colors = CardDefaults.cardColors(containerColor = Color.White),
                                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                                    ) {
                                        Row(
                                            Modifier.padding(16.dp).fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Column {
                                                Text(tower.name, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyLarge)
                                                Text(tower.code, style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                                            }
                                            Text("Abrir torre →", color = Color(0xFF195C3D), fontWeight = FontWeight.SemiBold)
                                        }
                                    }
                                }
                            } else if (!state.busy) {
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(12.dp),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                                ) {
                                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Text("No hay torres vinculadas a esta cuenta.", fontWeight = FontWeight.Bold)
                                        Text("Aprovisiona una nueva torre por Bluetooth para registrarla en el sistema.", style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            } else {
                                Text("Cargando torres...", style = MaterialTheme.typography.bodyLarge)
                            }

                            OutlinedButton(
                                onClick = vm::refresh,
                                enabled = !state.busy,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("🔄 Actualizar lecturas en vivo")
                            }
                        }
                    }
                }

                if (showBleDialog) {
                    BleProvisioningDialog(
                        bleManager = bleManager,
                        onDismiss = { showBleDialog = false },
                        onOpenLocalDashboard = { ip, pin ->
                            showBleDialog = false
                            vm.connectLocal(user = "admin", password = pin.ifBlank { "ecogrow20" }, baseUrl = ip)
                        }
                    )
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        bleManager?.close()
    }
}

/**
 * Pantalla principal de conexión sin fricción:
 * 1. Acceso directo a Torre Local para probar bomba y sensores sin login obligatorio.
 * 2. Asistente BLE.
 * 3. Sincronización Web opcional.
 */
@Composable
private fun HomeConnectionScreen(
    vm: EcoGrowViewModel,
    busy: Boolean,
    onOpenBle: () -> Unit
) {
    var localIp by remember { mutableStateOf("192.168.4.1") }
    var localPin by remember { mutableStateOf("ecogrow20") }
    var showCloudLogin by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "🌿 Torre Local (Directo)",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            Text(
                "Conéctate a tu torre física para verificar el encendido de la bomba, modos de riego y sensores en tiempo real sin requerir internet.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF4A5D4E)
            )

            OutlinedTextField(
                value = localIp,
                onValueChange = { localIp = it },
                label = { Text("IP de la Torre (ej: 192.168.4.1)") },
                placeholder = { Text("192.168.4.1") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy,
                shape = RoundedCornerShape(12.dp)
            )

            OutlinedTextField(
                value = localPin,
                onValueChange = { localPin = it },
                label = { Text("PIN / Clave de Acceso Local") },
                placeholder = { Text("ecogrow20") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                enabled = !busy,
                shape = RoundedCornerShape(12.dp)
            )

            Button(
                onClick = { vm.connectLocal(user = "admin", password = localPin.trim().ifBlank { "ecogrow20" }, baseUrl = localIp.trim()) },
                enabled = !busy && localIp.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("⚡ Probar y Verificar Torre Ahora", fontWeight = FontWeight.Bold, fontSize = 16.sp)
            }

            OutlinedButton(
                onClick = onOpenBle,
                enabled = !busy,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("📶 Configurar WiFi por Bluetooth (Estilo Ezviz)", fontWeight = FontWeight.SemiBold)
            }
        }
    }

    // Sección colapsable opcional de conexión con servidor cloud
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .clickable { showCloudLogin = !showCloudLogin },
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "☁️ Sincronizar con Servidor Web / Nube",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(if (showCloudLogin) "▲" else "▼", style = MaterialTheme.typography.titleMedium)
            }

            AnimatedVisibility(visible = showCloudLogin) {
                var endpoint by remember { mutableStateOf("") }
                var mail by remember { mutableStateOf("") }
                var password by remember { mutableStateOf("") }

                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = endpoint,
                        onValueChange = { endpoint = it },
                        label = { Text("Servidor HTTPS") },
                        placeholder = { Text("https://tu-servidor") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = mail,
                        onValueChange = { mail = it },
                        label = { Text("Correo electrónico") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        label = { Text("Contraseña") },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Button(
                        onClick = { vm.login(endpoint, mail, password) },
                        enabled = !busy && mail.isNotBlank() && password.isNotBlank() && endpoint.isNotBlank(),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Iniciar Sesión Cloud")
                    }
                }
            }
        }
    }
}

/**
 * Panel de Control y Verificación de la Torre:
 * Controles de bomba táctiles, modo AUTO/MANUAL, sensores en tiempo real y recetas.
 */
@Composable
private fun TowerDetail(d: JSONObject, vm: EcoGrowViewModel, busy: Boolean, failed: Boolean) {
    val local = d.optString("source") == "local"
    val pump = d.optJSONObject("pump") ?: JSONObject()
    val reportedStr = if (pump.isNull("reported")) null else pump.optString("reported")
    val desiredStr = if (pump.isNull("desired")) null else pump.optString("desired")
    val pumpState = reportedStr == "on" || (reportedStr == null && desiredStr == "on")
    val waterOk = d.optBoolean("water_level_ok", true)
    val canTurnOff = !busy && !failed && (pumpState || reportedStr == null || desiredStr == "on")
    val canTurnOn = !busy && !failed && waterOk && !pumpState
    val pumpMode = pump.optString("mode", "MANUAL")

    // Tarjeta Principal de Control de Bomba
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (pumpState) Color(0xFFE8F5E9) else Color.White
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(
            Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "Bomba y Cascada Vertical",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
                Surface(
                    color = if (reportedStr == "on") Color(0xFF2E7D32) else if (reportedStr == "off") Color(0xFF757575) else Color(0xFFE65100),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        if (reportedStr == "on") "🟢 ACTIVA" else if (reportedStr == "off") "⚪ DETENIDA" else if (desiredStr != null) "⏳ PENDIENTE" else "❓ SIN ACUSE",
                        color = Color.White,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
            }

            if (!waterOk) {
                Surface(
                    color = MaterialTheme.colorScheme.errorContainer,
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Text(
                        "⚠️ Nivel de agua insuficiente en el depósito (<10%). Activación bloqueada por seguridad.",
                        modifier = Modifier.padding(10.dp),
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            Text(
                text = if (reportedStr == "on")
                    "La cascada vertical está en marcha (confirmada por el controlador)."
                else if (reportedStr == "off")
                    "Bomba apagada (confirmada por el controlador). Oxigenación radicular."
                else if (desiredStr != null)
                    "Orden enviada ($desiredStr). Esperando reporte del microcontrolador."
                else
                    "Sin confirmación física de la bomba. Verifica la conexión.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF4A5D4E)
            )

            // Botones de acción directa de Bomba
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Button(
                    onClick = { vm.pump(true) },
                    enabled = canTurnOn,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("▶ Iniciar Cascada", fontWeight = FontWeight.Bold)
                }

                Button(
                    onClick = { vm.pump(false) },
                    enabled = canTurnOff,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC62828)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("⏹ Detener Bomba", fontWeight = FontWeight.Bold)
                }
            }

            // Selector de Modo
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = pumpMode == "AUTO",
                    onClick = { vm.mode("AUTO") },
                    label = { Text("Modo AUTO (Ciclo Riego/Oxígeno)") },
                    modifier = Modifier.weight(1f)
                )
                FilterChip(
                    selected = pumpMode == "MANUAL",
                    onClick = { vm.mode("MANUAL") },
                    label = { Text("Modo MANUAL") },
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }

    // Cuadrícula de Sensores
    Text("Lecturas de Sensores en Depósito", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    val sensors = d.optJSONObject("sensors") ?: JSONObject()
    val metrics = listOf(
        Triple("Nivel de Agua", "nivel_pct", "%"),
        Triple("Volumen Estimado", "litros", "L"),
        Triple("Acidez (pH)", "ph", ""),
        Triple("Nutrientes (TDS)", "tds_ppm", "ppm"),
        Triple("Temperatura Agua", "temperatura_agua_c", "°C")
    )

    for (pair in metrics.chunked(2)) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            pair.forEach { (title, key, unit) ->
                Card(
                    modifier = Modifier.weight(1f),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    shape = RoundedCornerShape(16.dp),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(title, style = MaterialTheme.typography.labelMedium, color = Color(0xFF556859))
                        Spacer(Modifier.height(6.dp))
                        Text(
                            measurement(sensors, key, unit),
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
            if (pair.size == 1) Spacer(Modifier.weight(1f))
        }
    }

    // Selector de Receta
    Text("Receta de Cultivo Activa", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            val recipe = d.optJSONObject("recipe")
            Text(
                "Receta: ${recipe?.optString("name", "Lechuga") ?: "Lechuga"}",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )

            val recipeNames = listOf("Lechuga (10/20m)", "Espinaca (10/25m)", "Albahaca (12/20m)", "Frutilla (15/30m)")
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                recipeNames.take(2).forEachIndexed { idx, name ->
                    OutlinedButton(
                        onClick = { vm.recipe(idx) },
                        modifier = Modifier.weight(1f),
                        enabled = !busy && !failed
                    ) {
                        Text(name, fontSize = 12.sp)
                    }
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                recipeNames.drop(2).forEachIndexed { idx, name ->
                    OutlinedButton(
                        onClick = { vm.recipe(idx + 2) },
                        modifier = Modifier.weight(1f),
                        enabled = !busy && !failed
                    ) {
                        Text(name, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

/**
 * Diálogo de Aprovisionamiento BLE estilo Ezviz:
 * 1. Escanea y selecciona la torre Bluetooth (PROV_EcoGrow_XXXX).
 * 2. Escanea y presenta un listado de redes WiFi disponibles con señal y candado.
 * 3. Selecciona la red con 1 toque e introduce la contraseña.
 * 4. Botón directo "Entrar a Probar Torre Ahora" al terminar.
 */
@Composable
private fun BleProvisioningDialog(
    bleManager: BleProvisioningManager?,
    onDismiss: () -> Unit,
    onOpenLocalDashboard: (String, String) -> Unit
) {
    val context = LocalContext.current
    var towers by remember { mutableStateOf<List<DiscoveredTower>>(emptyList()) }
    var selectedTower by remember { mutableStateOf<DiscoveredTower?>(null) }

    var wifiList by remember { mutableStateOf<List<DiscoveredWifi>>(emptyList()) }
    var selectedWifiSsid by remember { mutableStateOf("") }
    var customSsid by remember { mutableStateOf("") }
    var isManualSsid by remember { mutableStateOf(false) }

    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var pop by remember { mutableStateOf("ecogrow20") }
    var showAdvanced by remember { mutableStateOf(false) }

    var statusMessage by remember { mutableStateOf("Busca torres EcoGrow cercanas por Bluetooth.") }
    var provStep by remember { mutableStateOf(BleProvStep.IDLE) }
    var isScanning by remember { mutableStateOf(false) }

    // Cargar redes WiFi del entorno
    LaunchedEffect(Unit) {
        wifiList = getAvailableWifiNetworks(context)
        wifiList.firstOrNull()?.let {
            selectedWifiSsid = it.ssid
        }
    }

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

    val triggerScan: () -> Unit = {
        towers = emptyList()
        isScanning = true
        statusMessage = "Buscando torres EcoGrow en el aire..."
        bleManager?.startScan(
            onFound = { found ->
                if (towers.none { it.address == found.address }) {
                    towers = towers + found
                    if (selectedTower == null) selectedTower = found
                    statusMessage = "¡Torre detectada! Selecciona tu red WiFi abajo."
                }
            },
            onError = { err ->
                isScanning = false
                statusMessage = err
            },
            onTimeout = {
                isScanning = false
                if (towers.isEmpty()) {
                    statusMessage = "No se detectaron torres. Mantén pulsado BOOT por 5 segundos si el ESP32 ya tenía WiFi."
                }
            }
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { perms ->
        val granted = perms.values.all { it }
        if (granted) {
            triggerScan()
            wifiList = getAvailableWifiNetworks(context)
        } else {
            statusMessage = "Permisos requeridos denegados."
        }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Vincular Torre (Estilo Ezviz)", fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Paso 1: Búsqueda de Torre BLE
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("1. Torre EcoGrow:", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    Button(
                        onClick = {
                            val hasPerms = requiredPermissions.all {
                                ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
                            }
                            if (hasPerms) triggerScan() else permissionLauncher.launch(requiredPermissions)
                        },
                        enabled = !isScanning && provStep != BleProvStep.PROVISIONING
                    ) {
                        Text(if (isScanning) "Buscando..." else "Buscar")
                    }
                }

                if (towers.isNotEmpty()) {
                    towers.forEach { tower ->
                        val selected = selectedTower?.address == tower.address
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { selectedTower = tower },
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                            )
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Text(tower.name, fontWeight = FontWeight.Bold)
                                    Text("Señal: ${tower.rssi} dBm", style = MaterialTheme.typography.bodySmall)
                                }
                                RadioButton(selected = selected, onClick = { selectedTower = tower })
                            }
                        }
                    }
                }

                // Paso 2: Listado de Redes WiFi (Estilo Ezviz)
                selectedTower?.let { tower ->
                    HorizontalDivider(Modifier.padding(vertical = 4.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("2. Elige tu red WiFi (2.4 GHz):", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                        TextButton(onClick = { wifiList = getAvailableWifiNetworks(context) }) {
                            Text("Refrescar")
                        }
                    }

                    if (wifiList.isNotEmpty() && !isManualSsid) {
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            wifiList.take(6).forEach { wifi ->
                                val selected = selectedWifiSsid == wifi.ssid
                                Surface(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { selectedWifiSsid = wifi.ssid },
                                    shape = RoundedCornerShape(10.dp),
                                    color = if (selected) MaterialTheme.colorScheme.primaryContainer else Color(0xFFF1F5F1),
                                    border = if (selected) ButtonDefaults.outlinedButtonBorder else null
                                ) {
                                    Row(
                                        modifier = Modifier.padding(10.dp),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Text(if (wifi.isSecure) "🔒 " else "📶 ")
                                            Column {
                                                Text(wifi.ssid, fontWeight = FontWeight.SemiBold)
                                                if (wifi.isCurrent) {
                                                    Text("★ Red actual de tu celular", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelSmall)
                                                }
                                            }
                                        }
                                        RadioButton(selected = selected, onClick = { selectedWifiSsid = wifi.ssid })
                                    }
                                }
                            }

                            TextButton(onClick = { isManualSsid = true }) {
                                Text("✎ Ingresar otra red manualmente...")
                            }
                        }
                    } else {
                        OutlinedTextField(
                            value = customSsid,
                            onValueChange = { customSsid = it },
                            label = { Text("Nombre de red WiFi (SSID)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        if (wifiList.isNotEmpty()) {
                            TextButton(onClick = { isManualSsid = false }) {
                                Text("← Volver a lista de redes detectadas")
                            }
                        }
                    }

                    val effectiveSsid = if (isManualSsid) customSsid else selectedWifiSsid

                    // Campo de Contraseña con Mostrar/Ocultar
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        label = { Text("Contraseña de WiFi") },
                        visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                        trailingIcon = {
                            TextButton(onClick = { passwordVisible = !passwordVisible }) {
                                Text(if (passwordVisible) "Ocultar" else "Ver")
                            }
                        },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        enabled = provStep != BleProvStep.PROVISIONING
                    )

                    // Opciones avanzadas (PoP oculto)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { showAdvanced = !showAdvanced },
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(if (showAdvanced) "▲ Menos opciones" else "▼ Opciones avanzadas (PoP)", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                    }

                    if (showAdvanced) {
                        OutlinedTextField(
                            value = pop,
                            onValueChange = { pop = it },
                            label = { Text("Clave PoP (Preconfigurada)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    // Botón de Enviar Configuración
                    Button(
                        onClick = {
                            bleManager?.provisionTower(
                                device = tower.device,
                                ssid = effectiveSsid.trim(),
                                passphrase = password,
                                pop = pop.trim()
                            ) { step, msg ->
                                provStep = step
                                statusMessage = msg
                            }
                        },
                        enabled = effectiveSsid.isNotBlank() && provStep != BleProvStep.PROVISIONING,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(if (provStep == BleProvStep.PROVISIONING) "Enviando configuración..." else "Vincular Torre a esta Red")
                    }
                }

                // Tarjeta de Éxito y Salto Inmediato al Dashboard
                if (provStep == BleProvStep.SUCCESS) {
                    Surface(
                        color = Color(0xFFE8F5E9),
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("✅ ¡Torre vinculada con éxito!", fontWeight = FontWeight.Bold, color = Color(0xFF2E7D32))
                            Text("Las credenciales fueron transferidas. Ya puedes ingresar directamente a encender la bomba y probar el funcionamiento.", style = MaterialTheme.typography.bodySmall)
                            Button(
                                onClick = { onOpenLocalDashboard("http://192.168.4.1", pop) },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D)),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("🚀 Entrar a Probar Torre Ahora", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                } else {
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = statusMessage,
                            modifier = Modifier.padding(10.dp),
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                bleManager?.stopScan()
                onDismiss()
            }) {
                Text("Cerrar")
            }
        }
    )
}
