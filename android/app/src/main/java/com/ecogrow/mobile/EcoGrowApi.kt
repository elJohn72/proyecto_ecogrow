package com.ecogrow.mobile

import android.content.Context
import android.content.SharedPreferences
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.TimeUnit

const val DEFAULT_API_ENDPOINT = "https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io"

class MemoryCookies : CookieJar {
    private val cookies = mutableListOf<Cookie>()
    @Synchronized override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        for (cookie in cookies) {
            this.cookies.removeAll { it.name == cookie.name && it.domain == cookie.domain && it.path == cookie.path }
            this.cookies.add(cookie)
        }
    }
    @Synchronized override fun loadForRequest(url: HttpUrl): List<Cookie> =
        cookies.filter { it.expiresAt > System.currentTimeMillis() && it.matches(url) }
    @Synchronized fun clear() = cookies.clear()
    @Synchronized fun hasActiveSession(): Boolean =
        cookies.any { it.name == "session" && it.expiresAt > System.currentTimeMillis() }
}

class PersistentCookieJar(context: Context) : CookieJar {
    private val prefs: SharedPreferences = context.getSharedPreferences("ecogrow_auth_cookies", Context.MODE_PRIVATE)
    private val cookies = mutableListOf<Cookie>()

    init {
        loadFromPrefs()
    }

    private fun loadFromPrefs() {
        val all = prefs.all
        for ((_, value) in all) {
            if (value is String) {
                try {
                    val parts = value.split("|")
                    if (parts.size >= 5) {
                        val name = parts[0]
                        val cookieVal = parts[1]
                        val domain = parts[2]
                        val path = parts[3]
                        val expires = parts[4].toLongOrNull() ?: 0L
                        if (expires > System.currentTimeMillis()) {
                            val builder = Cookie.Builder()
                                .name(name)
                                .value(cookieVal)
                                .domain(domain)
                                .path(path)
                                .expiresAt(expires)
                            if (parts.getOrNull(5) == "secure") builder.secure()
                            if (parts.getOrNull(6) == "httpOnly") builder.httpOnly()
                            cookies.add(builder.build())
                        }
                    }
                } catch (_: Exception) {}
            }
        }
    }

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val editor = prefs.edit()
        for (cookie in cookies) {
            this.cookies.removeAll { it.name == cookie.name && it.domain == cookie.domain && it.path == cookie.path }
            this.cookies.add(cookie)
            val key = "${cookie.domain}_${cookie.name}"
            val serialized = "${cookie.name}|${cookie.value}|${cookie.domain}|${cookie.path}|${cookie.expiresAt}|" +
                    (if (cookie.secure) "secure" else "insecure") + "|" +
                    (if (cookie.httpOnly) "httpOnly" else "plain")
            editor.putString(key, serialized)
        }
        editor.apply()
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val now = System.currentTimeMillis()
        cookies.removeAll { it.expiresAt <= now }
        return cookies.filter { it.matches(url) }
    }

    @Synchronized
    fun clear() {
        cookies.clear()
        prefs.edit().clear().apply()
    }

    @Synchronized
    fun hasActiveSession(): Boolean {
        val now = System.currentTimeMillis()
        return cookies.any { it.name == "session" && it.expiresAt > now }
    }
}

class ApiFailure(val status: Int, message: String) : Exception(message)

fun validatedEndpoint(input: String, debug: Boolean): String {
    val clean = input.trim()
    val url = runCatching { clean.toHttpUrl() }.getOrElse {
        throw IllegalArgumentException("Dirección de servidor no válida. Usa un formato como https://tudominio.com")
    }
    require(url.username.isEmpty() && url.password.isEmpty() && url.query == null && url.fragment == null) {
        "Usa una dirección sin credenciales ni parámetros."
    }
    require(url.encodedPath == "/") {
        "Usa la dirección raíz del servidor sin subrutas."
    }
    require(url.isHttps || (debug && url.host in setOf("localhost", "127.0.0.1", "10.0.2.2"))) {
        "El servidor remoto requiere HTTPS obligatorio (cifrado TLS)."
    }
    return url.toString().trimEnd('/')
}

fun measurement(sensors: JSONObject, key: String, unit: String): String =
    if (!sensors.has(key) || sensors.isNull(key)) "Sin dato" else {
        val value = sensors.optDouble(key, Double.NaN)
        if (!value.isFinite()) "Sin dato" else "%s %s".format(Locale.forLanguageTag("es"), String.format(Locale.forLanguageTag("es"), "%.1f", value), unit).trim()
    }

class EcoGrowApi(
    context: Context? = null,
    base: String = DEFAULT_API_ENDPOINT,
    debug: Boolean = false
) {
    // Constructor de conveniencia para tests
    constructor(base: String, debug: Boolean = false) : this(null, base, debug)

    val root = validatedEndpoint(base, debug)
    private val jar: CookieJar = if (context != null) PersistentCookieJar(context) else MemoryCookies()
    private val prefs: SharedPreferences? = context?.getSharedPreferences("ecogrow_auth_session", Context.MODE_PRIVATE)
    private var inMemoryCsrf = ""

    private val client = OkHttpClient.Builder()
        .cookieJar(jar)
        .followRedirects(false)
        .followSslRedirects(false)
        .callTimeout(20, TimeUnit.SECONDS)
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    private var csrf: String
        get() = prefs?.getString("csrf_token", "") ?: inMemoryCsrf
        set(value) {
            inMemoryCsrf = value
            prefs?.edit()?.putString("csrf_token", value)?.apply()
        }

    fun clear() {
        csrf = ""
        inMemoryCsrf = ""
        if (jar is PersistentCookieJar) jar.clear()
        else if (jar is MemoryCookies) jar.clear()
        prefs?.edit()?.clear()?.apply()
    }

    fun hasActiveSession(): Boolean =
        if (jar is PersistentCookieJar) jar.hasActiveSession()
        else (jar as MemoryCookies).hasActiveSession()

    fun get(path: String): JSONObject = request(path, null)

    fun post(path: String, body: JSONObject): JSONObject = request(path, body)

    private fun request(path: String, body: JSONObject?): JSONObject {
        val cleanPath = path.trimStart('/')
        val requestBuilder = Request.Builder().url("$root/api/mobile/$cleanPath")
        if (body != null) {
            val token = csrf
            if (token.isNotBlank()) {
                requestBuilder.header("X-CSRF-Token", token)
            }
            requestBuilder.post(body.toString().toRequestBody("application/json".toMediaType()))
        }
        client.newCall(requestBuilder.build()).execute().use { response ->
            val raw = response.body?.string() ?: "{}"
            val payload = runCatching { JSONObject(raw) }.getOrElse {
                throw ApiFailure(response.code, "Respuesta inválida del servidor ($raw).")
            }
            if (!response.isSuccessful) {
                val errorMsg = payload.optString("message", "Error de servidor (código ${response.code}).")
                throw ApiFailure(response.code, errorMsg)
            }
            if (payload.has("csrf_token")) {
                csrf = payload.getString("csrf_token")
            }
            return payload
        }
    }

    fun getSession(): JSONObject = get("session")

    fun register(name: String, mail: String, pass: String, passConfirm: String): JSONObject {
        if (csrf.isBlank()) {
            runCatching { get("session") }
        }
        val payload = JSONObject()
            .put("name", name.trim())
            .put("mail", mail.trim())
            .put("password", pass)
            .put("password_confirm", passConfirm)
        return post("register", payload)
    }

    fun login(mail: String, pass: String): JSONObject {
        if (csrf.isBlank()) {
            runCatching { get("session") }
        }
        val payload = JSONObject().put("mail", mail.trim()).put("password", pass)
        return post("login", payload)
    }

    fun logout(): JSONObject = post("logout", JSONObject())

    fun listTowers(): List<Tower> {
        val json = get("towers")
        val arr = json.optJSONArray("towers") ?: return emptyList()
        val list = mutableListOf<Tower>()
        for (i in 0 until arr.length()) {
            val t = arr.getJSONObject(i)
            list.add(Tower(id = t.getInt("id"), name = t.getString("name"), code = t.getString("code")))
        }
        return list
    }

    fun bindTower(code: String, pop: String, name: String, location: String = ""): Tower {
        val body = JSONObject()
            .put("code", code.trim().uppercase())
            .put("pop", pop.trim().uppercase())
            .put("name", name.trim())
            .put("location", location.trim())
        val res = post("towers/bind", body)
        val tObj = res.getJSONObject("tower")
        return Tower(id = tObj.getInt("id"), name = tObj.getString("name"), code = tObj.getString("code"))
    }

    fun getTowerDetail(towerId: Int): TowerDetailModel {
        val json = get("towers/$towerId")
        return TowerDetailModel.fromJson(json)
    }

    fun commandPump(towerId: Int, state: String): JSONObject {
        return post("towers/$towerId/pump", JSONObject().put("state", state.lowercase()))
    }

    fun commandMode(towerId: Int, mode: String): JSONObject {
        return post("towers/$towerId/mode", JSONObject().put("mode", mode.uppercase()))
    }

    fun commandRecipe(towerId: Int, recipeIdx: Int): JSONObject {
        return post("towers/$towerId/recipe", JSONObject().put("recipe_idx", recipeIdx))
    }
}
