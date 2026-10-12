package com.ecogrow.mobile

import okhttp3.Credentials
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/** Sólo el AP de una torre aprovisionada. Nunca recibe cookies ni credenciales cloud. */
class LocalTowerApi(user: String, password: String, private val baseUrl: String = "http://192.168.4.1") {
    private val authorization = Credentials.basic(user, password)
    private val client = OkHttpClient.Builder().followRedirects(false).callTimeout(10, TimeUnit.SECONDS).build()
    fun request(route: String, body: JSONObject? = null): JSONObject {
        val r = Request.Builder().url("$baseUrl/api/$route").header("Authorization", authorization)
        if (body != null) r.post(body.toString().toRequestBody("application/json".toMediaType()))
        client.newCall(r.build()).execute().use {
            if (!it.isSuccessful) throw ApiFailure(it.code, if (it.code == 401) "Credenciales de torre incorrectas." else "La torre rechazó la operación.")
            return JSONObject(it.body?.string() ?: "{}")
        }
    }
    fun detail(): JSONObject {
        val s = request("status")
        val sensors = JSONObject()
        for ((destination, source) in mapOf("ph" to "ph_val", "tds_ppm" to "tds_ppm", "nivel_pct" to "water_level_pct", "litros" to "water_liters", "temperatura_agua_c" to "temp_water")) sensors.put(destination, s.opt(source) ?: JSONObject.NULL)
        sensors.put("ec_ms_cm", JSONObject.NULL)
        val pump = JSONObject().put("desired", JSONObject.NULL).put("reported", if (s.getBoolean("pump_state")) "on" else "off").put("mode", s.getString("pump_mode")).put("status", "reported")
        val recipe = s.optJSONObject("recipe")
        return JSONObject().put("id", 0).put("name", "Torre WiFi local").put("source", "local").put("sensors", sensors).put("stale", false)
            .put("updated_at", "Consulta directa a la torre").put("pump", pump).put("recipe", recipe ?: JSONObject.NULL)
            .put("water_level_ok", s.optBoolean("water_level_ok", false))
            .put("alerts", org.json.JSONArray().apply { val alert = s.optString("alert"); if (alert.isNotBlank()) put(JSONObject().put("message", alert)) })
            .put("capabilities", JSONObject().put("pump_control", true).put("recipe_edit", true).put("local_connection", true))
    }
}
