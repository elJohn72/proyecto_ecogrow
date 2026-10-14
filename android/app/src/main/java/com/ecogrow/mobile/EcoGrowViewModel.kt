package com.ecogrow.mobile

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class CurrentView {
    LOGIN,
    HOME,
    DETAIL,
    ADD_TOWER
}

data class ScreenState(
    val currentView: CurrentView = CurrentView.LOGIN,
    val busy: Boolean = false,
    val authenticated: Boolean = false,
    val user: String = "",
    val towers: List<Tower> = emptyList(),
    val selectedTowerId: Int? = null,
    val detail: TowerDetailModel? = null,
    val error: String? = null,
    val notice: String? = null,
    val endpoint: String = DEFAULT_API_ENDPOINT
)

class EcoGrowViewModel(application: Application) : AndroidViewModel(application) {
    private val appPrefs = application.getSharedPreferences("ecogrow_mobile_prefs", Context.MODE_PRIVATE)
    private var api: EcoGrowApi

    private val state = MutableStateFlow(
        ScreenState(
            endpoint = DEFAULT_API_ENDPOINT
        )
    )
    val ui = state.asStateFlow()

    init {
        if (appPrefs.contains("saved_endpoint")) {
            appPrefs.edit().remove("saved_endpoint").apply()
        }
        api = EcoGrowApi(application, DEFAULT_API_ENDPOINT, BuildConfig.DEBUG)
        checkExistingSession()
    }

    private fun checkExistingSession() {
        viewModelScope.launch {
            try {
                if (api.hasActiveSession()) {
                    val sessionResp = withContext(Dispatchers.IO) { api.getSession() }
                    val isAuth = sessionResp.optBoolean("authenticated", false)
                    if (isAuth) {
                        val userName = sessionResp.optJSONObject("user")?.optString("name") ?: ""
                        state.value = state.value.copy(
                            authenticated = true,
                            user = userName,
                            currentView = CurrentView.HOME
                        )
                        loadCloudTowers()
                        return@launch
                    }
                }
            } catch (_: Exception) {}
            // Si no hay sesión válida, mostrar pantalla de Login
            state.value = state.value.copy(
                authenticated = false,
                currentView = CurrentView.LOGIN
            )
        }
    }

    private fun action(block: suspend () -> Unit) {
        if (state.value.busy) return
        state.value = state.value.copy(busy = true, error = null, notice = null)
        viewModelScope.launch {
            try {
                block()
            } catch (e: Exception) {
                if (e is ApiFailure && e.status == 401) {
                    api.clear()
                    state.value = state.value.copy(
                        authenticated = false,
                        error = "La sesión ha terminado. Por favor vuelve a ingresar con tu cuenta.",
                        currentView = CurrentView.LOGIN
                    )
                } else {
                    val msg = if (e is ApiFailure || e is IllegalArgumentException) e.message
                    else "No se pudo comunicar con el servidor. Verifica tu conexión a internet."
                    state.value = state.value.copy(error = msg)
                }
            } finally {
                state.value = state.value.copy(busy = false)
            }
        }
    }

    fun navigateTo(view: CurrentView) {
        state.value = state.value.copy(currentView = view, error = null, notice = null)
    }

    fun register(name: String, mail: String, pass: String, passConfirm: String) = action {
        val targetEndpoint = DEFAULT_API_ENDPOINT
        api = EcoGrowApi(getApplication(), targetEndpoint, BuildConfig.DEBUG)

        val response = withContext(Dispatchers.IO) {
            api.register(name.trim(), mail.trim(), pass, passConfirm)
        }
        val isAuth = response.optBoolean("authenticated", false)
        if (!isAuth) throw ApiFailure(400, "No se pudo completar el registro.")

        val userName = response.optJSONObject("user")?.optString("name") ?: name.trim()
        state.value = state.value.copy(
            authenticated = true,
            user = userName,
            currentView = CurrentView.HOME,
            error = null,
            notice = "¡Cuenta creada exitosamente! Bienvenido a EcoGrow."
        )
        loadCloudTowers()
    }

    fun login(mail: String, pass: String) = action {
        val targetEndpoint = DEFAULT_API_ENDPOINT
        api = EcoGrowApi(getApplication(), targetEndpoint, BuildConfig.DEBUG)

        val response = withContext(Dispatchers.IO) {
            api.login(mail.trim(), pass)
        }
        val isAuth = response.optBoolean("authenticated", false)
        if (!isAuth) throw ApiFailure(401, "Credenciales incorrectas.")

        val userName = response.optJSONObject("user")?.optString("name") ?: ""
        state.value = state.value.copy(
            authenticated = true,
            user = userName,
            currentView = CurrentView.HOME,
            error = null
        )
        loadCloudTowers()
    }

    fun logout() = action {
        withContext(Dispatchers.IO) {
            runCatching { api.logout() }
        }
        api.clear()
        state.value = state.value.copy(
            authenticated = false,
            user = "",
            towers = emptyList(),
            detail = null,
            selectedTowerId = null,
            currentView = CurrentView.LOGIN,
            notice = "Has cerrado sesión correctamente."
        )
    }

    suspend fun loadCloudTowers() {
        val towersList = withContext(Dispatchers.IO) {
            api.listTowers()
        }
        state.value = state.value.copy(towers = towersList)
        if (towersList.size == 1 && state.value.currentView == CurrentView.HOME) {
            // Si solo hay una torre y estamos en Home, podemos pre-cargar su ID
            state.value = state.value.copy(selectedTowerId = towersList.first().id)
        }
    }

    fun refresh() = action {
        when (state.value.currentView) {
            CurrentView.DETAIL -> {
                val id = state.value.selectedTowerId
                if (id != null) {
                    loadDetail(id)
                } else {
                    loadCloudTowers()
                }
            }
            else -> {
                loadCloudTowers()
            }
        }
    }

    fun select(id: Int) = action {
        state.value = state.value.copy(selectedTowerId = id)
        loadDetail(id)
    }

    private suspend fun loadDetail(id: Int) {
        val detailModel = withContext(Dispatchers.IO) {
            api.getTowerDetail(id)
        }
        state.value = state.value.copy(
            detail = detailModel,
            selectedTowerId = id,
            currentView = CurrentView.DETAIL
        )
    }

    fun back() {
        state.value = state.value.copy(
            detail = null,
            selectedTowerId = null,
            currentView = CurrentView.HOME,
            error = null,
            notice = null
        )
    }

    fun pump(turnOn: Boolean) = action {
        val towerId = state.value.selectedTowerId
            ?: throw IllegalStateException("No hay torre seleccionada.")
        val detail = state.value.detail

        if (turnOn) {
            if (detail != null && detail.stale) {
                throw IllegalStateException("Telemetría desactualizada (> 2 min sin reporte). Por seguridad se requiere una lectura reciente para encender la bomba.")
            }
            val level = detail?.sensors?.nivelPct
            if (level != null && level <= 15.0) {
                throw IllegalStateException("Nivel de agua crítico (≤ 15%). Marcha en seco bloqueada por seguridad.")
            }
        }

        val res = withContext(Dispatchers.IO) {
            api.commandPump(towerId, if (turnOn) "on" else "off")
        }
        val msg = res.optString("message", "Orden enviada al servidor.")
        state.value = state.value.copy(notice = msg)
        loadDetail(towerId)
    }

    fun mode(newMode: String) = action {
        val towerId = state.value.selectedTowerId
            ?: throw IllegalStateException("No hay torre seleccionada.")
        val res = withContext(Dispatchers.IO) {
            api.commandMode(towerId, newMode)
        }
        val msg = res.optString("message", "Modo $newMode solicitado.")
        state.value = state.value.copy(notice = msg)
        loadDetail(towerId)
    }

    fun recipe(recipeIdx: Int) = action {
        val towerId = state.value.selectedTowerId
            ?: throw IllegalStateException("No hay torre seleccionada.")
        val res = withContext(Dispatchers.IO) {
            api.commandRecipe(towerId, recipeIdx)
        }
        val msg = res.optString("message", "Receta $recipeIdx solicitada.")
        state.value = state.value.copy(notice = msg)
        loadDetail(towerId)
    }

    fun onTowerProvisionedAndBind(
        code: String,
        pop: String,
        name: String,
        onSuccess: (Tower) -> Unit,
        onError: (String) -> Unit
    ) {
        viewModelScope.launch {
            try {
                state.value = state.value.copy(busy = true)
                val newTower = withContext(Dispatchers.IO) {
                    api.bindTower(code, pop, name, "Laboratorio")
                }
                loadCloudTowers()
                state.value = state.value.copy(
                    selectedTowerId = newTower.id,
                    notice = "Torre '${newTower.name}' vinculada exitosamente."
                )
                onSuccess(newTower)
            } catch (e: Exception) {
                val err = if (e is ApiFailure) e.message ?: "Error al vincular la torre."
                else "No se pudo vincular la torre con la API remota. Verifica tu conexión."
                state.value = state.value.copy(error = err)
                onError(err)
            } finally {
                state.value = state.value.copy(busy = false)
            }
        }
    }

    suspend fun getTowerDetailAsync(towerId: Int): TowerDetailModel? = withContext(Dispatchers.IO) {
        runCatching { api.getTowerDetail(towerId) }.getOrNull()
    }
}
