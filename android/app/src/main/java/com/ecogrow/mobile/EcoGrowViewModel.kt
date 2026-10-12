package com.ecogrow.mobile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

data class Tower(val id: Int, val name: String, val code: String)
data class ScreenState(val busy: Boolean = false, val authenticated: Boolean = false, val user: String = "", val towers: List<Tower> = emptyList(), val detail: JSONObject? = null, val error: String? = null, val notice: String? = null)

class EcoGrowViewModel : ViewModel() {
    private val state = MutableStateFlow(ScreenState())
    val ui = state.asStateFlow()
    private var api: EcoGrowApi? = null
    private var local: LocalTowerApi? = null
    private fun action(block: suspend () -> Unit) {
        if (state.value.busy) return
        state.value = state.value.copy(busy = true, error = null, notice = null)
        viewModelScope.launch {
            try { block() }
            catch (e: Exception) {
                if (e is ApiFailure && e.status == 401) { api?.clear(); state.value = ScreenState(error = "La sesión terminó. Vuelve a ingresar.") }
                else state.value = state.value.copy(error = if (e is ApiFailure || e is IllegalArgumentException) e.message else "Sin conexión. Comprueba el servidor y actualiza antes de controlar la torre.")
            } finally { state.value = state.value.copy(busy = false) }
        }
    }
    fun login(endpoint: String, mail: String, password: String) = action {
        api?.clear(); local = null
        state.value = ScreenState(busy = true)
        val client = EcoGrowApi(endpoint, BuildConfig.DEBUG); api = client
        val response = withContext(Dispatchers.IO) { client.get("session"); client.post("login", JSONObject().put("mail", mail.trim()).put("password", password)) }
        state.value = state.value.copy(authenticated = response.optBoolean("authenticated"), user = response.optJSONObject("user")?.optString("name") ?: "")
        loadTowers()
    }
    private suspend fun loadTowers() {
        val json = withContext(Dispatchers.IO) { api!!.get("towers") }.getJSONArray("towers")
        state.value = state.value.copy(towers = (0 until json.length()).map { val t = json.getJSONObject(it); Tower(t.getInt("id"), t.getString("name"), t.getString("code")) })
    }
    fun refresh() = action { val id = state.value.detail?.getInt("id"); if (id == null) loadTowers() else loadDetail(id) }
    fun select(id: Int) = action { loadDetail(id) }
    private suspend fun loadDetail(id: Int) { val detail = withContext(Dispatchers.IO) { local?.detail() ?: api!!.get("towers/$id") }; state.value = state.value.copy(detail = detail) }
    fun back() { state.value = state.value.copy(detail = null, error = null, notice = null) }
    fun pump(on: Boolean) = action {
        val id = state.value.detail!!.getInt("id")
        val result = withContext(Dispatchers.IO) { local?.request("pump", JSONObject().put("on", on)) ?: api!!.post("towers/$id/pump", JSONObject().put("state", if (on) "on" else "off")) }
        loadDetail(id)
        state.value = state.value.copy(notice = result.optString("message", "Orden enviada. Falta confirmación del dispositivo."))
    }
    fun connectLocal(user: String, password: String) = action {
        require(user.isNotBlank() && password.isNotBlank()) { "Introduce las credenciales aprovisionadas de la torre." }
        api?.clear(); api = null; local = LocalTowerApi(user, password)
        state.value = ScreenState(busy = true)
        loadDetail(0)
        state.value = state.value.copy(authenticated = true, user = "Conexión local")
    }
    fun mode(mode: String) = action { withContext(Dispatchers.IO) { local!!.request("mode", JSONObject().put("mode", mode)) }; loadDetail(0) }
    fun recipe(index: Int) = action { withContext(Dispatchers.IO) { local!!.request("recipe", JSONObject().put("recipe_idx", index)) }; loadDetail(0) }
    fun logout() = action {
        try { withContext(Dispatchers.IO) { api?.post("logout", JSONObject()) } }
        finally { api?.clear(); api = null; local = null; state.value = ScreenState() }
    }
}
