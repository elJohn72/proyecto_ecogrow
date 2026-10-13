package com.ecogrow.mobile

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject

@Composable
fun TowerDetailScreen(
    detail: JSONObject,
    busy: Boolean,
    onRefresh: () -> Unit,
    onBack: () -> Unit,
    onPumpControl: (Boolean) -> Unit,
    onModeControl: (String) -> Unit,
    onRecipeControl: (Int) -> Unit
) {
    var showPumpConfirmDialog by remember { mutableStateOf<Boolean?>(null) }
    var showBootInfoDialog by remember { mutableStateOf(false) }

    val name = detail.optString("name", "Torre EcoGrow")
    val code = detail.optString("code", "")
    val lastSeen = detail.optString("last_seen", "")
    val isOnline = detail.optBoolean("online", false)

    val sensors = detail.optJSONObject("sensors") ?: JSONObject()
    val pump = detail.optJSONObject("pump") ?: JSONObject()
    val recipe = detail.optJSONObject("recipe") ?: JSONObject()
    val alertText = detail.optString("alert", "")

    // Lecturas físicas reales (sin inventar datos)
    val waterLevelPct = if (sensors.has("nivel_pct") && !sensors.isNull("nivel_pct")) sensors.optDouble("nivel_pct") else null
    val waterLiters = if (sensors.has("litros") && !sensors.isNull("litros")) sensors.optDouble("litros") else null
    val isCalibrated = detail.optBoolean("deposito_calibrado", waterLiters != null)
    val ph = if (sensors.has("ph") && !sensors.isNull("ph")) sensors.optDouble("ph") else null
    val tdsPpm = if (sensors.has("tds_ppm") && !sensors.isNull("tds_ppm")) sensors.optDouble("tds_ppm") else null
    val tempWaterC = if (sensors.has("temperatura_agua_c") && !sensors.isNull("temperatura_agua_c")) sensors.optDouble("temperatura_agua_c") else null

    // Estado físico reportado de bomba
    val pumpReported = pump.optString("reported", "").lowercase()
    val isPumpOn = pumpReported == "on"
    val pumpMode = pump.optString("mode", "AUTO").uppercase()
    val pendingCmd = pump.optString("pending_command", "")

    // Bloqueo de seguridad: si el nivel de agua está bajo (< 15%) o si el sensor reporta water_level_ok == false
    val waterLevelOk = detail.optBoolean("water_level_ok", (waterLevelPct ?: 100.0) >= 15.0)
    val isSafetyLocked = !waterLevelOk

    Scaffold(
        topBar = {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 2.dp
            ) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = onBack) {
                            Text("←", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                        }
                        Column {
                            Text(name, fontWeight = FontWeight.Bold, fontSize = 18.sp, color = MaterialTheme.colorScheme.primary)
                            if (code.isNotBlank()) {
                                Text("Código: $code", fontSize = 11.sp, color = Color.Gray)
                            }
                        }
                    }

                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        IconButton(onClick = { showBootInfoDialog = true }) {
                            Text("ℹ️")
                        }
                        FilledTonalButton(
                            onClick = onRefresh,
                            enabled = !busy,
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text(if (busy) "..." else "↻")
                        }
                    }
                }
            }
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // =========================================================================
            // 1. BARRA DE ESTADO DE CONEXIÓN Y ÚLTIMA LECTURA
            // =========================================================================
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = if (isOnline) Color(0xFFE8F5E9) else Color(0xFFFFEBEE),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Box(
                            Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(if (isOnline) Color(0xFF2E7D32) else Color(0xFFC62828))
                        )
                        Text(
                            if (isOnline) "Torre en Línea" else "Sin Conexión con la Torre",
                            fontWeight = FontWeight.Bold,
                            color = if (isOnline) Color(0xFF1B5E20) else Color(0xFFB71C1C),
                            fontSize = 13.sp
                        )
                    }
                    if (lastSeen.isNotBlank()) {
                        Text(
                            "Última lectura: $lastSeen",
                            fontSize = 11.sp,
                            color = if (isOnline) Color(0xFF2E7D32) else Color(0xFFB71C1C)
                        )
                    }
                }
            }

            // =========================================================================
            // 2. NIVEL DE AGUA Y VOLUMEN (DEPÓSITO)
            // =========================================================================
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "Depósito de Agua",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        if (waterLevelPct != null) {
                            Text(
                                "${String.format("%.1f", waterLevelPct)}%",
                                fontWeight = FontWeight.Bold,
                                fontSize = 22.sp,
                                color = if (waterLevelPct < 20.0) Color(0xFFC62828) else MaterialTheme.colorScheme.primary
                            )
                        } else {
                            Text("Sin datos recientes", fontSize = 13.sp, color = Color.Gray)
                        }
                    }

                    // Barra de Nivel
                    if (waterLevelPct != null) {
                        LinearProgressIndicator(
                            progress = { (waterLevelPct / 100.0).toFloat().coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth().height(10.dp).clip(RoundedCornerShape(5.dp)),
                            color = if (waterLevelPct < 20.0) Color(0xFFC62828) else Color(0xFF1976D2),
                            trackColor = Color(0xFFE0E0E0)
                        )
                    }

                    // Litros y Calibración
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (waterLiters != null && isCalibrated) {
                            Text("Volumen Calibrado: ${String.format("%.1f", waterLiters)} Litros", fontSize = 13.sp, color = Color(0xFF445544))
                        } else {
                            Text("⚠️ Volumen sin calibrar (solo porcentaje)", fontSize = 12.sp, color = Color(0xFFE65100))
                        }

                        if (isSafetyLocked) {
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = Color(0xFFFFEBEE)
                            ) {
                                Text("NIVEL CRÍTICO", modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp), color = Color(0xFFC62828), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // 3. PARÁMETROS QUÍMICOS Y TEMPERATURA
            // =========================================================================
            Text("Condiciones de la Solución Nutritiva", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                // pH
                SensorMetricCard(
                    modifier = Modifier.weight(1f),
                    title = "Acidez (pH)",
                    valueText = ph?.let { String.format("%.2f", it) } ?: "--",
                    unit = "",
                    isOptimal = ph != null && ph in 5.5..6.5,
                    optimalRange = "Ideal: 5.5 - 6.5"
                )

                // TDS
                SensorMetricCard(
                    modifier = Modifier.weight(1f),
                    title = "Nutrientes (TDS)",
                    valueText = tdsPpm?.let { String.format("%.0f", it) } ?: "--",
                    unit = "ppm",
                    isOptimal = tdsPpm != null && tdsPpm in 500.0..950.0,
                    optimalRange = "Receta: 560-840"
                )

                // Temperatura
                SensorMetricCard(
                    modifier = Modifier.weight(1f),
                    title = "Temp. Agua",
                    valueText = tempWaterC?.let { String.format("%.1f", it) } ?: "--",
                    unit = "°C",
                    isOptimal = tempWaterC != null && tempWaterC in 18.0..24.0,
                    optimalRange = "Ideal: 18 - 22°C"
                )
            }

            // =========================================================================
            // 4. CONTROL DE BOMBA Y BLOQUEO DE SEGURIDAD
            // =========================================================================
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("Bomba de Cascada", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text(
                                if (isPumpOn) "🟢 Estado Físico: ENCENDIDA" else "⚪ Estado Físico: APAGADA",
                                fontWeight = FontWeight.SemiBold,
                                color = if (isPumpOn) Color(0xFF2E7D32) else Color(0xFF666666),
                                fontSize = 13.sp
                            )
                        }

                        if (pendingCmd.isNotBlank()) {
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = Color(0xFFFFF3E0)
                            ) {
                                Row(Modifier.padding(horizontal = 8.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                                    CircularProgressIndicator(Modifier.size(12.dp), strokeWidth = 2.dp, color = Color(0xFFE65100))
                                    Spacer(Modifier.width(6.dp))
                                    Text("Orden pendiente ($pendingCmd)", fontSize = 10.sp, color = Color(0xFFE65100))
                                }
                            }
                        }
                    }

                    if (isSafetyLocked) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFFFEBEE),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                "⚠️ Bloqueo de seguridad activo: La bomba no puede encenderse porque el nivel de agua es insuficiente.",
                                modifier = Modifier.padding(10.dp),
                                color = Color(0xFFC62828),
                                fontSize = 12.sp
                            )
                        }
                    }

                    // Botones de acción manual
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Button(
                            onClick = { showPumpConfirmDialog = true },
                            enabled = !busy && !isSafetyLocked && !isPumpOn,
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D)),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("▶ Iniciar Riego", fontWeight = FontWeight.Bold)
                        }

                        Button(
                            onClick = { showPumpConfirmDialog = false },
                            enabled = !busy && isPumpOn,
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC62828)),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("⏹ Detener Bomba", fontWeight = FontWeight.Bold)
                        }
                    }

                    // Selector de Modo (AUTO / MANUAL)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(
                            selected = pumpMode == "AUTO",
                            onClick = { onModeControl("AUTO") },
                            label = { Text("Modo AUTO (Ciclo)") },
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = pumpMode == "MANUAL",
                            onClick = { onModeControl("MANUAL") },
                            label = { Text("Modo MANUAL") },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // =========================================================================
            // 5. RECETA DE CULTIVO
            // =========================================================================
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Receta de Cultivo Activa", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    val recipeName = recipe.optString("name", "Lechuga")
                    Text("Cultivo actual: $recipeName", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)

                    val recipes = listOf("Lechuga (10/20m)", "Espinaca (10/25m)", "Albahaca (12/20m)", "Frutilla (15/30m)")
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        recipes.take(2).forEachIndexed { idx, rName ->
                            OutlinedButton(
                                onClick = { onRecipeControl(idx) },
                                modifier = Modifier.weight(1f),
                                enabled = !busy
                            ) {
                                Text(rName, fontSize = 11.sp)
                            }
                        }
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        recipes.drop(2).forEachIndexed { idx, rName ->
                            OutlinedButton(
                                onClick = { onRecipeControl(idx + 2) },
                                modifier = Modifier.weight(1f),
                                enabled = !busy
                            ) {
                                Text(rName, fontSize = 11.sp)
                            }
                        }
                    }
                }
            }

            // =========================================================================
            // 6. ALERTAS ACTIVAS
            // =========================================================================
            if (alertText.isNotBlank()) {
                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = Color(0xFFF1F5F1),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(14.dp)) {
                        Text("Notificación del Sistema", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = MaterialTheme.colorScheme.primary)
                        Spacer(Modifier.height(4.dp))
                        Text(alertText, fontSize = 13.sp, color = Color(0xFF333333))
                    }
                }
            }
        }
    }

    // Diálogo de Confirmación de Bomba
    showPumpConfirmDialog?.let { wantTurnOn ->
        AlertDialog(
            onDismissRequest = { showPumpConfirmDialog = null },
            title = {
                Text(if (wantTurnOn) "¿Iniciar Cascada de Riego?" else "¿Detener la Bomba?")
            },
            text = {
                Text(
                    if (wantTurnOn)
                        "La bomba comenzará a bombear solución nutritiva hacia las raíces de las plantas en la torre vertical."
                    else
                        "La cascada se detendrá. En modo manual permanecerá apagada hasta tu próxima orden."
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showPumpConfirmDialog = null
                        onPumpControl(wantTurnOn)
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (wantTurnOn) Color(0xFF195C3D) else Color(0xFFC62828)
                    )
                ) {
                    Text(if (wantTurnOn) "Sí, Iniciar" else "Sí, Detener")
                }
            },
            dismissButton = {
                TextButton(onClick = { showPumpConfirmDialog = null }) {
                    Text("Cancelar")
                }
            }
        )
    }

    // Diálogo Informativo de Recuperación y Botón BOOT
    if (showBootInfoDialog) {
        AlertDialog(
            onDismissRequest = { showBootInfoDialog = false },
            title = { Text("Recuperación Física de la Torre") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Instrucciones del botón físico BOOT (GPIO 0):", fontWeight = FontWeight.Bold)
                    Text("• 3 a 8 segundos: Reconfigurar WiFi (Conserva el PIN PoP de la etiqueta y calibraciones).")
                    Text("• 12+ segundos: Restablecimiento de fábrica (Borra NVS por completo).")
                    Text("Servidor de telemetría: Coolify (Let's Encrypt TLS)")
                }
            },
            confirmButton = {
                TextButton(onClick = { showBootInfoDialog = false }) {
                    Text("Entendido")
                }
            }
        )
    }
}

@Composable
private fun SensorMetricCard(
    modifier: Modifier = Modifier,
    title: String,
    valueText: String,
    unit: String,
    isOptimal: Boolean,
    optimalRange: String
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(title, fontSize = 11.sp, color = Color(0xFF666666))
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.Bottom) {
                Text(valueText, fontWeight = FontWeight.Bold, fontSize = 20.sp, color = MaterialTheme.colorScheme.primary)
                if (unit.isNotBlank()) {
                    Spacer(Modifier.width(2.dp))
                    Text(unit, fontSize = 11.sp, color = Color.Gray, modifier = Modifier.padding(bottom = 2.dp))
                }
            }
            Spacer(Modifier.height(4.dp))
            Text(
                if (isOptimal) "✓ $optimalRange" else optimalRange,
                fontSize = 10.sp,
                color = if (isOptimal) Color(0xFF2E7D32) else Color(0xFFE65100),
                fontWeight = if (isOptimal) FontWeight.Bold else FontWeight.Normal
            )
        }
    }
}
