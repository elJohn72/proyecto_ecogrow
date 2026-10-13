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
import org.json.JSONArray
import org.json.JSONObject

data class Tower(val id: Int, val name: String, val code: String, val localIp: String? = null)

enum class CurrentView {
    HOME,
    DETAIL,
    ADD_TOWER,
    LOGIN
}

data class ScreenState(
    val currentView: CurrentView = CurrentView.HOME,
    val busy: Boolean = false,
    val authenticated: Boolean = false,
    val user: String = "",
    val towers: List<Tower> = emptyList(),
    val detail: JSONObject? = null,
    val error: String? = null,
    val notice: String? = null
)

class EcoGrowViewModel(application: Application) : AndroidViewModel(application) {
    private val prefs = application.getSharedPreferences("ecogrow_mobile_prefs", Context.MODE_PRIVATE)
    private val state = MutableStateFlow(ScreenState())
    val ui = state.asStateFlow()

    private var api: EcoGrowApi? = null
    private var local: LocalTowerApi? = null

    init {
        loadSavedTowers()
    }

    private fun loadSavedTowers() {
        val savedJson = prefs.getString("saved_towers_json", "[]") ?: "[]"
        try {
            val arr = JSONArray(savedJson)
            val list = mutableListOf<Tower>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                list.add(
                    Tower(
                        id = obj.optInt("id", i + 1),
                        name = obj.optString("name", "Torre EcoGrow"),
                        code = obj.optString("code", ""),
                        localIp = if (obj.has("local_ip")) obj.optString("local_ip") else null
                    )
                )
            }
            state.value = state.value.copy(towers = list)
        } catch (_: Exception) {}
    }

    private fun saveTowers(list: List<Tower>) {
        val arr = JSONArray()
        list.forEach { t ->
            val obj = JSONObject()
            obj.put("id", t.id)
            obj.put("name", t.name)
            obj.put("code", t.code)
            t.localIp?.let { obj.put("local_ip", it) }
            arr.put(obj)
        }
        prefs.edit().putString("saved_towers_json", arr.toString()).apply()
    }

    private fun action(block: suspend () -> Unit) {
        if (state.value.busy) return
        state.value = state.value.copy(busy = true, error = null, notice = null)
        viewModelScope.launch {
            try {
                block()
            } catch (e: Exception) {
                if (e is ApiFailure && e.status == 401) {
                    api?.clear()
                    state.value = state.value.copy(
                        authenticated = false,
                        error = "La sesión terminó. Vuelve a ingresar.",
                        currentView = CurrentView.LOGIN
                    )
                } else {
                    val msg = if (e is ApiFailure || e is IllegalArgumentException) e.message
                    else "Sin conexión con la torre o servidor. Verifica la red y vuelve a intentar."
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

    fun onTowerProvisioned(towerName: String, pop: String, ip: String?) {
        val currentTowers = state.value.towers.toMutableList()
        val nextId = (currentTowers.maxOfOrNull { it.id } ?: 0) + 1
        val newTower = Tower(
            id = nextId,
            name = towerName,
            code = "EG-${towerName.takeLast(4)}",
            localIp = ip ?: "192.168.4.1"
        )
        if (currentTowers.none { it.name == towerName }) {
            currentTowers.add(newTower)
            state.value = state.value.copy(towers = currentTowers)
            saveTowers(currentTowers)
        }

        // Conectar automáticamente a la nueva torre para ver su dashboard
        val targetIp = ip ?: "http://192.168.4.1"
        connectLocal(user = "admin", password = pop, baseUrl = targetIp)
    }

    fun login(endpoint: String, mail: String, password: String) = action {
        api?.clear()
        local = null
        val client = EcoGrowApi(endpoint, BuildConfig.DEBUG)
        api = client
        val response = withContext(Dispatchers.IO) {
            client.get("session")
            client.post("login", JSONObject().put("mail", mail.trim()).put("password", password))
        }
        val isAuth = response.optBoolean("authenticated")
        val userName = response.optJSONObject("user")?.optString("name") ?: ""
        state.value = state.value.copy(authenticated = isAuth, user = userName, currentView = CurrentView.HOME)
        loadCloudTowers()
    }

    private suspend fun loadCloudTowers() {
        val client = api ?: return
        val json = withContext(Dispatchers.IO) { client.get("towers") }.getJSONArray("towers")
        val towersList = (0 until json.length()).map {
            val t = json.getJSONObject(it)
            Tower(t.getInt("id"), t.getString("name"), t.getString("code"))
        }
        state.value = state.value.copy(towers = towersList)
        saveTowers(towersList)
        if (towersList.size == 1) {
            loadDetail(towersList.first().id)
        }
    }

    fun refresh() = action {
        val id = state.value.detail?.optInt("id", 0) ?: 0
        if (id == 0 && local == null) {
            if (api != null) loadCloudTowers() else loadSavedTowers()
        } else {
            loadDetail(id)
        }
    }

    fun select(id: Int) = action {
        loadDetail(id)
    }

    private suspend fun loadDetail(id: Int) {
        val detail = withContext(Dispatchers.IO) {
            local?.detail() ?: api!!.get("towers/$id")
        }
        state.value = state.value.copy(detail = detail, currentView = CurrentView.DETAIL)
    }

    fun back() {
        state.value = state.value.copy(
            detail = null,
            error = null,
            notice = null,
            currentView = CurrentView.HOME
        )
    }

    fun pump(on: Boolean) = action {
        val id = state.value.detail?.optInt("id", 0) ?: 0
        val result = withContext(Dispatchers.IO) {
            local?.request("pump", JSONObject().put("on", on))
                ?: api!!.post("towers/$id/pump", JSONObject().put("state", if (on) "on" else "off"))
        }
        loadDetail(id)
        state.value = state.value.copy(
            notice = result.optString("message", "Orden de bomba enviada correctamente.")
        )
    }

    fun connectLocal(user: String = "admin", password: String = "ecogrow20", baseUrl: String = "http://192.168.4.1") = action {
        api?.clear()
        api = null
        val normalizedUrl = if (baseUrl.startsWith("http")) baseUrl else "http://$baseUrl"
        local = LocalTowerApi(user, password, normalizedUrl)
        loadDetail(0)
        val host = normalizedUrl.removePrefix("http://").removePrefix("https://").trimEnd('/')
        state.value = state.value.copy(
            authenticated = true,
            user = "Torre Local ($host)",
            currentView = CurrentView.DETAIL
        )
    }

    fun mode(mode: String) = action {
        val id = state.value.detail?.optInt("id", 0) ?: 0
        val result = withContext(Dispatchers.IO) {
            local?.request("mode", JSONObject().put("mode", mode))
                ?: api!!.post("towers/$id/mode", JSONObject().put("mode", mode))
        }
        loadDetail(id)
        state.value = state.value.copy(
            notice = result.optString("message", "Modo cambiado a $mode. Esperando ciclo de la torre.")
        )
    }

    fun recipe(index: Int) = action {
        val id = state.value.detail?.optInt("id", 0) ?: 0
        val result = withContext(Dispatchers.IO) {
            local?.request("recipe", JSONObject().put("recipe_idx", index))
                ?: api!!.post("towers/$id/recipe", JSONObject().put("recipe_idx", index))
        }
        loadDetail(id)
        state.value = state.value.copy(
            notice = result.optString("message", "Receta de cultivo actualizada en la torre.")
        )
    }

    fun logout() = action {
        try {
            withContext(Dispatchers.IO) { api?.post("logout", JSONObject()) }
        } finally {
            api?.clear()
            api = null
            local = null
            state.value = ScreenState(currentView = CurrentView.HOME)
            loadSavedTowers()
        }
    }
}
