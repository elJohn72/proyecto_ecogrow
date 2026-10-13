package com.ecogrow.mobile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.wifi.WifiManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

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
                var showLoginDialog by remember { mutableStateOf(false) }

                Box(Modifier.fillMaxSize()) {
                    when (state.currentView) {
                        CurrentView.HOME -> {
                            TowersHomeScreen(
                                towers = state.towers,
                                user = state.user,
                                busy = state.busy,
                                onSelectTower = { vm.select(it) },
                                onAddTowerClick = { vm.navigateTo(CurrentView.ADD_TOWER) },
                                onConnectLocalClick = {
                                    vm.connectLocal(user = "admin", password = "ecogrow20", baseUrl = "http://192.168.4.1")
                                },
                                onRefresh = { vm.refresh() },
                                onLogout = { vm.logout() }
                            )
                        }

                        CurrentView.DETAIL -> {
                            val detail = state.detail
                            if (detail != null) {
                                TowerDetailScreen(
                                    detail = detail,
                                    busy = state.busy,
                                    onRefresh = { vm.refresh() },
                                    onBack = { vm.back() },
                                    onPumpControl = { vm.pump(it) },
                                    onModeControl = { vm.mode(it) },
                                    onRecipeControl = { vm.recipe(it) }
                                )
                            } else {
                                // En caso de regresar sin detalle, volver a Home
                                LaunchedEffect(Unit) {
                                    vm.navigateTo(CurrentView.HOME)
                                }
                            }
                        }

                        CurrentView.ADD_TOWER -> {
                            AddTowerScreen(
                                bleManager = bleManager,
                                onCancel = { vm.navigateTo(CurrentView.HOME) },
                                onTowerAdded = { towerName, pop, ip ->
                                    vm.onTowerProvisioned(towerName, pop, ip)
                                }
                            )
                        }

                        CurrentView.LOGIN -> {
                            // Si se navega explícitamente a login
                            LaunchedEffect(Unit) {
                                showLoginDialog = true
                            }
                            TowersHomeScreen(
                                towers = state.towers,
                                user = state.user,
                                busy = state.busy,
                                onSelectTower = { vm.select(it) },
                                onAddTowerClick = { vm.navigateTo(CurrentView.ADD_TOWER) },
                                onConnectLocalClick = {
                                    vm.connectLocal(user = "admin", password = "ecogrow20", baseUrl = "http://192.168.4.1")
                                },
                                onRefresh = { vm.refresh() },
                                onLogout = { vm.logout() }
                            )
                        }
                    }

                    // Notificaciones o Errores Globales flotantes
                    state.error?.let { err ->
                        Snackbar(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .padding(16.dp),
                            action = {
                                TextButton(onClick = { vm.refresh() }) {
                                    Text("Reintentar", color = Color.White)
                                }
                            }
                        ) {
                            Text(err)
                        }
                    }

                    state.notice?.let { notice ->
                        Snackbar(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .padding(16.dp),
                            containerColor = MaterialTheme.colorScheme.primaryContainer,
                            contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                        ) {
                            Text(notice)
                        }
                    }

                    // Diálogo de Login en Servidor Cloud Coolify si se solicita
                    if (showLoginDialog) {
                        CloudLoginDialog(
                            onDismiss = { showLoginDialog = false },
                            onLogin = { endpoint, mail, pass ->
                                showLoginDialog = false
                                vm.login(endpoint, mail, pass)
                            }
                        )
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        bleManager?.close()
    }
}

@Composable
fun CloudLoginDialog(
    onDismiss: () -> Unit,
    onLogin: (endpoint: String, mail: String, pass: String) -> Unit
) {
    var endpoint by remember { mutableStateOf("https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io") }
    var mail by remember { mutableStateOf("") }
    var pass by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Conectar con Servidor Coolify", fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Ingresa con tu cuenta de operador para sincronizar tus torres en la nube:", style = MaterialTheme.typography.bodySmall)
                OutlinedTextField(
                    value = endpoint,
                    onValueChange = { endpoint = it },
                    label = { Text("Servidor FQDN (HTTPS TLS)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = mail,
                    onValueChange = { mail = it },
                    label = { Text("Correo Electrónico") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = pass,
                    onValueChange = { pass = it },
                    label = { Text("Contraseña") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onLogin(endpoint, mail, pass) },
                enabled = mail.isNotBlank() && pass.isNotBlank()
            ) {
                Text("Iniciar Sesión")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancelar")
            }
        }
    )
}
