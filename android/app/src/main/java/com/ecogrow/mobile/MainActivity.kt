package com.ecogrow.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    private var bleManager: BleProvisioningManager? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bleManager = BleProvisioningManager(this)

        setContent {
            MaterialTheme(colorScheme = lightColorScheme(primary = Color(0xFF176345), secondary = Color(0xFF68724E), background = Color(0xFFF5F7F1), surface = Color.White)) {
                val vm: EcoGrowViewModel = viewModel()
                val state by vm.ui.collectAsStateWithLifecycle()
                var showBleDialog by remember { mutableStateOf(false) }

                Scaffold { inset ->
                    Column(Modifier.fillMaxSize().padding(inset).verticalScroll(rememberScrollState()).padding(22.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column {
                                Text("EcoGrow", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                                Text("Cultiva con información real", style = MaterialTheme.typography.bodyLarge)
                            }
                            IconButton(onClick = { showBleDialog = true }) {
                                Text("📶 BLE", fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.primary)
                            }
                        }
                        if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                        state.error?.let { Surface(color = MaterialTheme.colorScheme.errorContainer, shape = MaterialTheme.shapes.medium) { Text(it, Modifier.padding(16.dp)) } }
                        state.notice?.let { Text(it, color = MaterialTheme.colorScheme.primary) }
                        if (!state.authenticated) {
                            Login(vm, state.busy, onOpenBle = { showBleDialog = true })
                        } else {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(state.user, style = MaterialTheme.typography.labelLarge, modifier = Modifier.weight(1f))
                                TextButton(onClick = vm::logout, enabled = !state.busy) { Text("Salir") }
                            }
                            val detail = state.detail
                            if (detail == null) {
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Tus torres", style = MaterialTheme.typography.headlineSmall)
                                    TextButton(onClick = { showBleDialog = true }) { Text("+ Configurar torre BLE") }
                                }
                                if (state.towers.isEmpty()) Text("No tienes torres asignadas.")
                                state.towers.forEach { tower -> Card(onClick = { vm.select(tower.id) }, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                                    Column(Modifier.padding(20.dp)) { Text(tower.name, style = MaterialTheme.typography.titleLarge); Text(tower.code) }
                                } }
                            } else TowerDetail(detail, vm, state.busy, state.error != null)
                            OutlinedButton(onClick = vm::refresh, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) { Text("Actualizar lecturas") }
                        }
                    }
                }

                if (showBleDialog) {
                    BleProvisioningDialog(
                        bleManager = bleManager,
                        onDismiss = { showBleDialog = false }
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

@Composable private fun Login(vm: EcoGrowViewModel, busy: Boolean, onOpenBle: () -> Unit) {
    var endpoint by remember { mutableStateOf("") }
    var mail by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var local by remember { mutableStateOf(false) }
    Text("Conectar", style = MaterialTheme.typography.headlineSmall)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        FilterChip(selected = !local, onClick = { local = false; password = ""; mail = "" }, label = { Text("Servidor web") })
        FilterChip(selected = local, onClick = { local = true; password = ""; mail = "" }, label = { Text("Torre WiFi") })
    }
    if (!local) OutlinedTextField(value = endpoint, onValueChange = { endpoint = it }, label = { Text("Servidor HTTPS") }, placeholder = { Text("https://tu-servidor") }, singleLine = true, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    else Text("Conéctate al WiFi de tu torre aprovisionada (192.168.4.1). Esta conexión local usa HTTP: utiliza una clave exclusiva de la torre. No introduzcas tu contraseña web.")
    OutlinedTextField(value = mail, onValueChange = { mail = it }, label = { Text(if (local) "Usuario de la torre" else "Correo") }, singleLine = true, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    OutlinedTextField(value = password, onValueChange = { password = it }, label = { Text("Contraseña") }, visualTransformation = PasswordVisualTransformation(), singleLine = true, modifier = Modifier.fillMaxWidth(), enabled = !busy)
    Button(onClick = { if (local) vm.connectLocal(mail, password) else vm.login(endpoint, mail, password); password = "" }, enabled = !busy && mail.isNotBlank() && password.isNotBlank() && (local || endpoint.isNotBlank()), modifier = Modifier.fillMaxWidth()) { Text("Conectar") }
    OutlinedButton(onClick = onOpenBle, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
        Text("Configurar WiFi torre (Bluetooth BLE)")
    }
    Text("Las credenciales y la sesión permanecen en memoria mientras usas la app.", style = MaterialTheme.typography.bodySmall)
}

@Composable private fun TowerDetail(d: JSONObject, vm: EcoGrowViewModel, busy: Boolean, failed: Boolean) {
    val local = d.optString("source") == "local"
    if (!local) TextButton(onClick = vm::back, enabled = !busy) { Text("← Todas las torres") }
    Text(d.getString("name"), style = MaterialTheme.typography.headlineSmall)
    val stale = d.optBoolean("stale", true)
    Text(if (local) "WiFi local · Estado GPIO, no caudal medido" else "Servidor remoto · ${if (stale) "Lecturas antiguas o sin fecha" else "Lecturas recientes"}", style = MaterialTheme.typography.bodyMedium)
    Text(if (d.isNull("updated_at")) "Sin fecha de actualización" else d.optString("updated_at"), style = MaterialTheme.typography.labelMedium)
    val sensors = d.optJSONObject("sensors") ?: JSONObject()
    val metrics = listOf(Triple("Nivel", "nivel_pct", "%"), Triple("Agua", "litros", "L"), Triple("pH", "ph", ""), Triple("TDS", "tds_ppm", "ppm"), Triple("Agua · temperatura", "temperatura_agua_c", "°C"), Triple("EC", "ec_ms_cm", "mS/cm"))
    for (pair in metrics.chunked(2)) Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        pair.forEach { (title, key, unit) -> Card(modifier = Modifier.weight(1f), colors = CardDefaults.cardColors(containerColor = Color.White)) { Column(Modifier.padding(18.dp)) { Text(title, style = MaterialTheme.typography.labelLarge); Spacer(Modifier.height(8.dp)); Text(measurement(sensors, key, unit), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold) } } }
    }
    val alerts = d.optJSONArray("alerts")
    if (alerts != null) for (i in 0 until alerts.length()) Text(alerts.getJSONObject(i).optString("message"), color = MaterialTheme.colorScheme.error)
    val pump = d.optJSONObject("pump") ?: JSONObject()
    Text("Bomba", style = MaterialTheme.typography.titleLarge)
    Text("Solicitado: ${pumpLabel(pump.optString("desired"))} · Reportado: ${pumpLabel(pump.optString("reported"))}")
    Text("Modo: ${pump.optString("mode", "Sin dato")} · ${if (local) "Estado del dispositivo" else "La orden enviada requiere confirmación de la torre"}")
    val capable = d.optJSONObject("capabilities")?.optBoolean("pump_control") == true
    val manual = !local || pump.optString("mode") == "MANUAL"
    var confirmation by remember { mutableStateOf<Boolean?>(null) }
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(onClick = { confirmation = true }, enabled = capable && manual && !stale && !failed && !busy && (!local || d.optBoolean("water_level_ok"))) { Text("Encender") }
        OutlinedButton(onClick = { confirmation = false }, enabled = capable && manual && !failed && !busy) { Text("Apagar") }
    }
    confirmation?.let { on -> AlertDialog(onDismissRequest = { confirmation = null }, title = { Text(if (on) "Encender bomba" else "Apagar bomba") }, text = { Text("Se enviará una orden a esta torre. La lectura GPIO no garantiza circulación de agua.") }, confirmButton = { TextButton(onClick = { confirmation = null; vm.pump(on) }) { Text("Enviar orden") } }, dismissButton = { TextButton(onClick = { confirmation = null }) { Text("Cancelar") } }) }
    if (local) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedButton(onClick = { vm.mode("AUTO") }, enabled = !busy && !failed) { Text("Automático") }
            OutlinedButton(onClick = { vm.mode("MANUAL") }, enabled = !busy && !failed) { Text("Manual") }
        }
    }
    val irrigation = d.optJSONObject("irrigation")
    Text("Ciclo de riego", style = MaterialTheme.typography.titleLarge)
    Text(if (irrigation == null) "Sin configuración reportada" else "Cascada: ${irrigation.opt("on_minutes")} min · Reposo: ${irrigation.opt("off_minutes")} min")
    Text("Receta", style = MaterialTheme.typography.titleLarge)
    val recipe = d.optJSONObject("recipe")
    Text(recipe?.optString(if (local) "name" else "phase", "Sin receta") ?: "Sin receta")
    if (local && d.optJSONObject("capabilities")?.optBoolean("recipe_edit") == true) {
        var selection by remember { mutableStateOf<Int?>(null) }
        val recipeNames = listOf("Lechuga", "Espinaca", "Albahaca", "Frutilla / Fresa")
        recipeNames.forEachIndexed { index, name -> OutlinedButton(onClick = { selection = index }, enabled = !busy && !failed, modifier = Modifier.fillMaxWidth()) { Text(name) } }
        selection?.let { index -> AlertDialog(onDismissRequest = { selection = null }, title = { Text("Cambiar receta") }, text = { Text("La torre aplicará la receta '${recipeNames.getOrElse(index) { "" }}'. Comprueba el cultivo y los parámetros de la solución antes de continuar.") }, confirmButton = { TextButton(onClick = { selection = null; vm.recipe(index) }) { Text("Aplicar") } }, dismissButton = { TextButton(onClick = { selection = null }) { Text("Cancelar") } }) }
    }
    val events = d.optJSONArray("events")
    if (events != null && events.length() > 0) { Text("Actividad reciente", style = MaterialTheme.typography.titleLarge); for (i in 0 until minOf(5, events.length())) { val e = events.getJSONObject(i); Text("${e.optString("created_at")} · ${e.optString("action")} ${e.optString("reason")}") } }
}
private fun pumpLabel(value: String) = when(value) { "on" -> "Encendida"; "off" -> "Apagada"; else -> "Sin confirmación" }

@Composable
private fun BleProvisioningDialog(
    bleManager: BleProvisioningManager?,
    onDismiss: () -> Unit
) {
    var towers by remember { mutableStateOf<List<DiscoveredTower>>(emptyList()) }
    var selectedTower by remember { mutableStateOf<DiscoveredTower?>(null) }
    var ssid by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var pop by remember { mutableStateOf("ecogrow20") }
    var statusMessage by remember { mutableStateOf("Busca torres EcoGrow con Bluetooth activado.") }
    var provStep by remember { mutableStateOf(BleProvStep.IDLE) }
    var isScanning by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Configurar WiFi (BLE)") },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    "Si la torre perdió WiFi, mantén pulsado el botón BOOT (GPIO 0) durante 5 segundos para reactivar el modo BLE.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                if (bleManager?.isBluetoothSupported != true) {
                    Text("Bluetooth no soportado en este dispositivo.", color = MaterialTheme.colorScheme.error)
                } else if (!bleManager.isBluetoothEnabled) {
                    Text("Activa el Bluetooth de tu teléfono para continuar.", color = MaterialTheme.colorScheme.error)
                } else {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Button(
                            onClick = {
                                towers = emptyList()
                                isScanning = true
                                statusMessage = "Buscando torres EcoGrow cercanas..."
                                bleManager.startScan(
                                    onFound = { found ->
                                        if (towers.none { it.address == found.address }) {
                                            towers = towers + found
                                        }
                                    },
                                    onError = { err ->
                                        isScanning = false
                                        statusMessage = err
                                    }
                                )
                            },
                            enabled = !isScanning && provStep != BleProvStep.PROVISIONING
                        ) {
                            Text(if (isScanning) "Buscando..." else "Buscar torres")
                        }

                        if (isScanning) {
                            OutlinedButton(onClick = {
                                bleManager.stopScan()
                                isScanning = false
                                statusMessage = "Búsqueda detenida."
                            }) {
                                Text("Detener")
                            }
                        }
                    }

                    if (towers.isNotEmpty()) {
                        Text("Torres detectadas:", style = MaterialTheme.typography.titleSmall)
                        towers.forEach { tower ->
                            val selected = selectedTower?.address == tower.address
                            FilterChip(
                                selected = selected,
                                onClick = {
                                    selectedTower = tower
                                    statusMessage = "Torre seleccionada: ${tower.name}"
                                },
                                label = { Text("${tower.name} (${tower.rssi} dBm)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }

                    selectedTower?.let { tower ->
                        HorizontalDivider(Modifier.padding(vertical = 4.dp))
                        Text("Red WiFi para ${tower.name}:", style = MaterialTheme.typography.titleSmall)
                        OutlinedTextField(
                            value = ssid,
                            onValueChange = { ssid = it },
                            label = { Text("Nombre de red WiFi (SSID)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            enabled = provStep != BleProvStep.PROVISIONING
                        )
                        OutlinedTextField(
                            value = password,
                            onValueChange = { password = it },
                            label = { Text("Contraseña WiFi") },
                            visualTransformation = PasswordVisualTransformation(),
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            enabled = provStep != BleProvStep.PROVISIONING
                        )
                        OutlinedTextField(
                            value = pop,
                            onValueChange = { pop = it },
                            label = { Text("Clave PoP (Proof of Possession)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            enabled = provStep != BleProvStep.PROVISIONING
                        )

                        Button(
                            onClick = {
                                bleManager.provisionTower(
                                    device = tower.device,
                                    ssid = ssid.trim(),
                                    passphrase = password,
                                    pop = pop.trim()
                                ) { step, msg ->
                                    provStep = step
                                    statusMessage = msg
                                }
                            },
                            enabled = ssid.isNotBlank() && provStep != BleProvStep.PROVISIONING,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(if (provStep == BleProvStep.PROVISIONING) "Enviando..." else "Enviar configuración a torre")
                        }
                    }

                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        shape = MaterialTheme.shapes.small,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = statusMessage,
                            modifier = Modifier.padding(12.dp),
                            style = MaterialTheme.typography.bodyMedium
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
