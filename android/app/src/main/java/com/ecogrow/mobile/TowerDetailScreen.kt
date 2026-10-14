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

@Composable
fun TowerDetailScreen(
    detail: TowerDetailModel,
    busy: Boolean,
    onRefresh: () -> Unit,
    onBack: () -> Unit,
    onPumpControl: (Boolean) -> Unit,
    onModeControl: (String) -> Unit,
    onRecipeControl: (Int) -> Unit
) {
    var showPumpConfirmDialog by remember { mutableStateOf<Boolean?>(null) }
    var showBootInfoDialog by remember { mutableStateOf(false) }

    // Sondeo periódico de telemetría remota cada 10s mientras la pantalla esté activa
    LaunchedEffect(detail.id) {
        while (true) {
            kotlinx.coroutines.delay(10000L)
            onRefresh()
        }
    }

    val isWaterLow = (detail.sensors.nivelPct != null && detail.sensors.nivelPct <= 15.0)
    val isSafetyLocked = detail.stale || isWaterLow

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
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        IconButton(onClick = onBack) {
                            Text("←", fontSize = 22.sp, fontWeight = FontWeight.Bold)
                        }
                        Column {
                            Text(
                                detail.name,
                                fontWeight = FontWeight.Bold,
                                fontSize = 18.sp,
                                color = Color(0xFF195C3D)
                            )
                            Text("Código: ${detail.code}", fontSize = 11.sp, color = Color.Gray)
                        }
                    }

                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        IconButton(onClick = { showBootInfoDialog = true }) {
                            Text("ℹ️", fontSize = 16.sp)
                        }
                        FilledTonalButton(
                            onClick = onRefresh,
                            enabled = !busy,
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
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
            // 1. ESTADO DE TELEMETRÍA Y CONEXIÓN
            // =========================================================================
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = if (!detail.stale) Color(0xFFE8F5E9) else Color(0xFFFFF3E0),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Box(
                            Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(if (!detail.stale) Color(0xFF2E7D32) else Color(0xFFE65100))
                        )
                        Text(
                            if (!detail.stale) "Torre en Línea" else "Telemetría Desactualizada",
                            fontWeight = FontWeight.Bold,
                            color = if (!detail.stale) Color(0xFF1B5E20) else Color(0xFFBF360C),
                            fontSize = 13.sp
                        )
                    }
                    Text(
                        detail.formattedLastSeen(),
                        fontSize = 11.sp,
                        color = if (!detail.stale) Color(0xFF2E7D32) else Color(0xFFBF360C)
                    )
                }
            }

            // =========================================================================
            // 2. ALERTAS DEL SISTEMA
            // =========================================================================
            if (detail.alerts.isNotEmpty()) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEBEE))
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(
                            "⚠️ Alertas Activas (${detail.alerts.size})",
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFB3261E),
                            fontSize = 14.sp
                        )
                        detail.alerts.forEach { alert ->
                            Text(
                                "• ${alert.message}",
                                fontSize = 12.sp,
                                color = Color(0xFF7F0000)
                            )
                        }
                    }
                }
            }

            // =========================================================================
            // 3. NIVEL DE AGUA Y VOLUMEN (DEPÓSITO)
            // =========================================================================
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Depósito de Solución", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = Color(0xFF172B22))
                        Text(
                            detail.sensors.nivelFormatted(),
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp,
                            color = if (isWaterLow) Color(0xFFB3261E) else Color(0xFF087F8C)
                        )
                    }

                    // Barra visual de nivel
                    val progress = ((detail.sensors.nivelPct ?: 0.0) / 100.0).toFloat().coerceIn(0f, 1f)
                    LinearProgressIndicator(
                        progress = { progress },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(10.dp)
                            .clip(RoundedCornerShape(5.dp)),
                        color = if (isWaterLow) Color(0xFFB3261E) else Color(0xFF087F8C),
                        trackColor = Color(0xFFEEEEEE)
                    )

                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("Volumen Calibrado:", fontSize = 12.sp, color = Color.Gray)
                        Text(
                            detail.sensors.litrosFormatted(),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF333333)
                        )
                    }

                    if (isWaterLow) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFFFEBEE),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                "⚠️ Nivel crítico (≤ 15%). La bomba no puede encenderse para prevenir marcha en seco.",
                                color = Color(0xFFB3261E),
                                fontSize = 12.sp,
                                modifier = Modifier.padding(10.dp)
                            )
                        }
                    }
                }
            }

            // =========================================================================
            // 4. PARÁMETROS QUÍMICOS Y TEMPERATURA
            // =========================================================================
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    Text("Condición del Agua", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = Color(0xFF172B22))

                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        MetricCard(
                            modifier = Modifier.weight(1f),
                            label = "pH Solución",
                            value = detail.sensors.phFormatted(),
                            subtext = "Ideal: 5.5 - 6.5",
                            color = Color(0xFF195C3D)
                        )
                        MetricCard(
                            modifier = Modifier.weight(1f),
                            label = "TDS / Nutrientes",
                            value = detail.sensors.tdsFormatted(),
                            subtext = "Sensor analógico",
                            color = Color(0xFF087F8C)
                        )
                        MetricCard(
                            modifier = Modifier.weight(1f),
                            label = "Temp. Agua",
                            value = detail.sensors.tempFormatted(),
                            subtext = "DS18B20",
                            color = Color(0xFF946200)
                        )
                    }
                }
            }

            // =========================================================================
            // 5. CONTROL DE BOMBA Y MODO DE RIEGO
            // =========================================================================
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Bomba Principal", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = Color(0xFF172B22))

                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = if (detail.pump.isPhysicallyOn) Color(0xFFE8F5E9) else Color(0xFFF5F5F5)
                        ) {
                            Text(
                                if (detail.pump.isPhysicallyOn) "BOMBA ACTIVA" else if (detail.pump.isPhysicallyOff) "BOMBA DETENIDA" else "SIN REPORTE FÍSICO",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (detail.pump.isPhysicallyOn) Color(0xFF2E7D32) else Color(0xFF666666),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }

                    if (detail.pump.isPending) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFFFF8E1),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(10.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = Color(0xFFF57F17))
                                Text(
                                    "Orden en tránsito: esperando confirmación física del ESP32...",
                                    fontSize = 12.sp,
                                    color = Color(0xFFF57F17),
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }

                    // Selector de Modo (AUTO / MANUAL)
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Modo Operativo:", fontSize = 13.sp, color = Color(0xFF555555))

                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            FilterChip(
                                selected = detail.pump.mode == "AUTO",
                                onClick = { if (detail.pump.mode != "AUTO") onModeControl("AUTO") },
                                label = { Text("AUTO") }
                            )
                            FilterChip(
                                selected = detail.pump.mode == "MANUAL",
                                onClick = { if (detail.pump.mode != "MANUAL") onModeControl("MANUAL") },
                                label = { Text("MANUAL") }
                            )
                        }
                    }

                    // Botones de acción de bomba
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Button(
                            onClick = { showPumpConfirmDialog = true },
                            enabled = !busy && !isSafetyLocked && !detail.pump.isPhysicallyOn,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                        ) {
                            Text("Encender")
                        }

                        OutlinedButton(
                            onClick = { showPumpConfirmDialog = false },
                            enabled = !busy && detail.pump.isPhysicallyOn,
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("Apagar", color = Color(0xFFB3261E))
                        }
                    }

                    if (isSafetyLocked) {
                        Text(
                            text = if (detail.stale) "* Encendido bloqueado: telemetría desactualizada." else "* Encendido bloqueado: nivel de agua crítico.",
                            fontSize = 11.sp,
                            color = Color(0xFFB3261E)
                        )
                    }
                }
            }

            // =========================================================================
            // 6. RECETA DE CULTIVO
            // =========================================================================
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Receta de Cultivo Activa", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = Color(0xFF172B22))

                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                detail.recipe?.crop ?: "Sin cultivo activo",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color(0xFF195C3D)
                            )
                            Text(
                                "Fase: ${detail.recipe?.phase ?: "General"}",
                                fontSize = 12.sp,
                                color = Color.Gray
                            )
                        }
                    }

                    Text("Cambiar perfil nutricional y cascada:", fontSize = 12.sp, color = Color(0xFF555555))

                    val recetas = listOf("Lechuga (0)", "Espinaca (1)", "Albahaca (2)", "Frutilla (3)")
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        recetas.forEachIndexed { idx, nombre ->
                            OutlinedButton(
                                onClick = { onRecipeControl(idx) },
                                enabled = !busy,
                                modifier = Modifier.weight(1f),
                                contentPadding = PaddingValues(horizontal = 4.dp, vertical = 6.dp),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Text(nombre.split(" ")[0], fontSize = 11.sp)
                            }
                        }
                    }
                }
            }
        }
    }

    // Diálogo modal de confirmación antes de accionar la bomba
    showPumpConfirmDialog?.let { turnOn ->
        AlertDialog(
            onDismissRequest = { showPumpConfirmDialog = null },
            title = {
                Text(
                    if (turnOn) "Confirmar Encendido de Bomba" else "Confirmar Apagado de Bomba",
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Text(
                    if (turnOn) "¿Deseas solicitar el encendido de la cascada vertical de la torre? Se verificará el nivel de agua antes de la confirmación física."
                    else "¿Deseas solicitar el apagado de la bomba?"
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showPumpConfirmDialog = null
                        onPumpControl(turnOn)
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (turnOn) Color(0xFF195C3D) else Color(0xFFB3261E)
                    )
                ) {
                    Text("Confirmar")
                }
            },
            dismissButton = {
                TextButton(onClick = { showPumpConfirmDialog = null }) {
                    Text("Cancelar")
                }
            }
        )
    }

    // Diálogo informativo del botón físico BOOT
    if (showBootInfoDialog) {
        AlertDialog(
            onDismissRequest = { showBootInfoDialog = false },
            title = { Text("Recuperación Física (Botón BOOT / GPIO 0)", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        "EcoGrow implementa dos niveles de recuperación física mediante el botón BOOT del ESP32:",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        "1. Reconfigurar WiFi (Pulsar 3 a 8 segundos):\nBorra la red WiFi y reactiva el anuncio BLE sin perder la identidad de la torre ni el PIN PoP de la etiqueta.",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF087F8C)
                    )
                    Text(
                        "2. Restablecimiento de Fábrica (Pulsar continuo >= 12 segundos):\nBorra toda la memoria NVS, incluyendo la clave PoP y calibraciones. Requiere generar nueva etiqueta en taller.",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFFB3261E)
                    )
                }
            },
            confirmButton = {
                Button(onClick = { showBootInfoDialog = false }) {
                    Text("Entendido")
                }
            }
        )
    }
}

@Composable
private fun MetricCard(
    modifier: Modifier = Modifier,
    label: String,
    value: String,
    subtext: String,
    color: Color
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = Color(0xFFF7FAF7)
    ) {
        Column(
            Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(label, fontSize = 11.sp, color = Color.Gray)
            Text(value, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = color)
            Text(subtext, fontSize = 9.sp, color = Color(0xFF888888))
        }
    }
}
