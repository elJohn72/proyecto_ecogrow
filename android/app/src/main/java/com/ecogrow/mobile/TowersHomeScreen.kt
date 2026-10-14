package com.ecogrow.mobile

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun TowersHomeScreen(
    towers: List<Tower>,
    user: String,
    busy: Boolean,
    onSelectTower: (Int) -> Unit,
    onAddTowerClick: () -> Unit,
    onRefresh: () -> Unit,
    onLogout: () -> Unit
) {
    Scaffold(
        topBar = {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 2.dp
            ) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp, vertical = 14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Image(
                                painter = painterResource(R.drawable.ecogrow_symbol),
                                contentDescription = null,
                                modifier = Modifier.size(24.dp)
                            )
                            Text(
                                "EcoGrow",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF195C3D)
                            )
                        }
                        Text(
                            if (user.isNotBlank()) "Operador: $user" else "Gestión de Torres Hidropónicas",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFF666666)
                        )
                    }

                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        FilledTonalButton(
                            onClick = onRefresh,
                            enabled = !busy,
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(if (busy) "..." else "↻ Refrescar")
                        }

                        TextButton(onClick = onLogout) {
                            Text("Salir", color = Color(0xFF888888), fontSize = 13.sp)
                        }
                    }
                }
            }
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onAddTowerClick,
                containerColor = Color(0xFF195C3D),
                contentColor = Color.White,
                shape = RoundedCornerShape(16.dp),
                icon = { Text("＋", fontSize = 20.sp, fontWeight = FontWeight.Bold) },
                text = { Text("Añadir Torre", fontWeight = FontWeight.Bold) }
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 18.dp, vertical = 14.dp)
        ) {
            if (busy) {
                LinearProgressIndicator(
                    Modifier
                        .fillMaxWidth()
                        .padding(bottom = 12.dp),
                    color = Color(0xFF195C3D)
                )
            }

            if (towers.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(20.dp),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                    ) {
                        Column(
                            Modifier.padding(28.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(14.dp)
                        ) {
                            Image(
                                painterResource(R.drawable.ecogrow_symbol),
                                contentDescription = null,
                                modifier = Modifier.size(64.dp)
                            )
                            Text(
                                "No hay torres vinculadas todavía",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF195C3D)
                            )
                            Text(
                                "Configura tu primera torre EcoGrow usando el asistente guiado por Bluetooth para conectarla a tu WiFi y comenzar a monitorearla desde cualquier lugar.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = Color(0xFF666666),
                                textAlign = TextAlign.Center
                            )

                            Spacer(Modifier.height(8.dp))

                            Button(
                                onClick = onAddTowerClick,
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF195C3D))
                            ) {
                                Text("＋ Vincular Primera Torre", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            } else {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(bottom = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        "Mis Torres Hidropónicas (${towers.size})",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF172B22)
                    )
                }

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(towers, key = { it.id }) { tower ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onSelectTower(tower.id) },
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .padding(18.dp)
                                    .fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(14.dp)
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .size(46.dp)
                                            .clip(CircleShape)
                                            .background(Color(0xFFE8F5E9)),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Image(
                                            painter = painterResource(R.drawable.ecogrow_symbol),
                                            contentDescription = null,
                                            modifier = Modifier.size(24.dp)
                                        )
                                    }

                                    Column {
                                        Text(
                                            tower.name,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 16.sp,
                                            color = Color(0xFF172B22)
                                        )
                                        Text(
                                            "Código: ${tower.code}",
                                            fontSize = 12.sp,
                                            color = Color(0xFF888888)
                                        )
                                    }
                                }

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Surface(
                                        shape = RoundedCornerShape(8.dp),
                                        color = Color(0xFFF1F8F5)
                                    ) {
                                        Text(
                                            "Abrir →",
                                            fontSize = 13.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            color = Color(0xFF195C3D),
                                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
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
}
