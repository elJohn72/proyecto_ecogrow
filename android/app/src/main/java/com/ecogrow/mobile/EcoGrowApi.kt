package com.ecogrow.mobile

import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class MemoryCookies : CookieJar {
    private val cookies = mutableListOf<Cookie>()
    @Synchronized override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        for (cookie in cookies) { this.cookies.removeAll { it.name == cookie.name && it.domain == cookie.domain && it.path == cookie.path }; this.cookies.add(cookie) }
    }
    @Synchronized override fun loadForRequest(url: HttpUrl): List<Cookie> = cookies.filter { it.expiresAt > System.currentTimeMillis() && it.matches(url) }
    @Synchronized fun clear() = cookies.clear()
}

class ApiFailure(val status: Int, message: String) : Exception(message)

fun validatedEndpoint(input: String, debug: Boolean): String {
    val url = input.trim().toHttpUrl()
    require(url.username.isEmpty() && url.password.isEmpty() && url.query == null && url.fragment == null) { "Usa una dirección sin credenciales ni parámetros." }
    require(url.encodedPath == "/") { "Usa la dirección raíz del servidor." }
    require(url.isHttps || (debug && url.host in setOf("localhost", "127.0.0.1", "10.0.2.2"))) { "El servidor remoto necesita HTTPS." }
    return url.toString().trimEnd('/')
}

class EcoGrowApi(base: String, debug: Boolean = false) {
    private val root = validatedEndpoint(base, debug)
    private val jar = MemoryCookies()
    private val client = OkHttpClient.Builder().cookieJar(jar).followRedirects(false).followSslRedirects(false)
        .callTimeout(20, TimeUnit.SECONDS).build()
    private var csrf = ""
    fun clear() { csrf = ""; jar.clear() }
    fun get(path: String): JSONObject = request(path, null)
    fun post(path: String, body: JSONObject): JSONObject = request(path, body)
    private fun request(path: String, body: JSONObject?): JSONObject {
        val request = Request.Builder().url("$root/api/mobile/$path")
        if (body != null) request.header("X-CSRF-Token", csrf).post(body.toString().toRequestBody("application/json".toMediaType()))
        client.newCall(request.build()).execute().use { response ->
            val payload = runCatching { JSONObject(response.body?.string() ?: "{}") }.getOrElse { throw ApiFailure(response.code, "Respuesta no válida del servidor.") }
            if (!response.isSuccessful) throw ApiFailure(response.code, payload.optString("message", "No se pudo completar la operación."))
            if (payload.has("csrf_token")) csrf = payload.getString("csrf_token")
            return payload
        }
    }
}

fun measurement(sensors: JSONObject, key: String, unit: String): String =
    if (!sensors.has(key) || sensors.isNull(key)) "Sin dato" else {
        val value = sensors.optDouble(key, Double.NaN)
        if (!value.isFinite()) "Sin dato" else "%s %s".format(java.util.Locale.forLanguageTag("es"), String.format(java.util.Locale.forLanguageTag("es"), "%.1f", value), unit).trim()
    }
