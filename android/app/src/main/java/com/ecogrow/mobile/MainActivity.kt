package com.ecogrow.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    private var bleManager: BleProvisioningManager? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        bleManager = BleProvisioningManager(this)

        setContent {
            EcoGrowTheme {
                val vm: EcoGrowViewModel = viewModel()
                val state by vm.ui.collectAsStateWithLifecycle()

                Box(Modifier.fillMaxSize()) {
                    when (state.currentView) {
                        CurrentView.LOGIN -> {
                            LoginScreen(
                                busy = state.busy,
                                errorMessage = state.error,
                                onLogin = { mail, pass ->
                                    vm.login(mail, pass)
                                }
                            )
                        }

                        CurrentView.HOME -> {
                            TowersHomeScreen(
                                towers = state.towers,
                                user = state.user,
                                busy = state.busy,
                                onSelectTower = { vm.select(it) },
                                onAddTowerClick = { vm.navigateTo(CurrentView.ADD_TOWER) },
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
                                LaunchedEffect(Unit) {
                                    vm.navigateTo(CurrentView.HOME)
                                }
                            }
                        }

                        CurrentView.ADD_TOWER -> {
                            AddTowerScreen(
                                bleManager = bleManager,
                                onCancel = { vm.navigateTo(CurrentView.HOME) },
                                onTowerAddedAndBound = { code, pop, name, onComplete ->
                                    vm.onTowerProvisionedAndBind(
                                        code = code,
                                        pop = pop,
                                        name = name,
                                        onSuccess = { tower -> onComplete(true, null, tower.id) },
                                        onError = { err -> onComplete(false, err, null) }
                                    )
                                },
                                onFetchTowerDetail = { towerId ->
                                    vm.getTowerDetailAsync(towerId)
                                }
                            )
                        }
                    }

                    // Notificaciones flotantes
                    state.error?.let { err ->
                        if (state.currentView != CurrentView.LOGIN) {
                            Snackbar(
                                modifier = Modifier
                                    .align(Alignment.BottomCenter)
                                    .padding(16.dp),
                                containerColor = Color(0xFFB3261E),
                                action = {
                                    TextButton(onClick = { vm.refresh() }) {
                                        Text("Reintentar", color = Color.White)
                                    }
                                }
                            ) {
                                Text(err, color = Color.White)
                            }
                        }
                    }

                    state.notice?.let { notice ->
                        Snackbar(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .padding(16.dp),
                            containerColor = Color(0xFF195C3D),
                            contentColor = Color.White
                        ) {
                            Text(notice)
                        }
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
