package com.ecogrow.mobile

import okhttp3.Cookie
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class EcoGrowTest {

    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        server = MockWebServer()
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun testValidatedEndpointHttps() {
        val endpoint = validatedEndpoint("https://api.ecogrow.io/", debug = false)
        assertEquals("https://api.ecogrow.io", endpoint)
    }

    @Test
    fun testValidatedEndpointRejectsHttpInProduction() {
        assertThrows(IllegalArgumentException::class.java) {
            validatedEndpoint("http://api.ecogrow.io/", debug = false)
        }
    }

    @Test
    fun testValidatedEndpointAllowsLocalhostInDebug() {
        val endpoint = validatedEndpoint("http://localhost:5000/", debug = true)
        assertEquals("http://localhost:5000", endpoint)
    }

    @Test
    fun testValidatedEndpointRejectsCredentialsOrQueryParams() {
        assertThrows(IllegalArgumentException::class.java) {
            validatedEndpoint("https://user:pass@api.ecogrow.io/", debug = false)
        }
        assertThrows(IllegalArgumentException::class.java) {
            validatedEndpoint("https://api.ecogrow.io/?token=123", debug = false)
        }
    }

    @Test
    fun testMeasurementFormatting() {
        val json = JSONObject().apply {
            put("ph", 6.2)
            put("tds_ppm", 560.0)
            put("missing_val", JSONObject.NULL)
            put("invalid_val", "not_a_number")
        }

        val phFormatted = measurement(json, "ph", "")
        assertTrue(phFormatted.contains("6") && phFormatted.contains("2"))

        val tdsFormatted = measurement(json, "tds_ppm", "ppm")
        assertTrue(tdsFormatted.contains("560") && tdsFormatted.endsWith("ppm"))

        assertEquals("Sin dato", measurement(json, "missing_val", "%"))
        assertEquals("Sin dato", measurement(json, "non_existent_key", "°C"))
        assertEquals("Sin dato", measurement(json, "invalid_val", "L"))
    }

    @Test
    fun testMemoryCookiesHandling() {
        val jar = MemoryCookies()
        val url = "https://api.ecogrow.io/".toHttpUrl()
        val cookie = Cookie.Builder()
            .name("session")
            .value("token_abc")
            .domain("api.ecogrow.io")
            .path("/")
            .expiresAt(System.currentTimeMillis() + 100000)
            .build()

        jar.saveFromResponse(url, listOf(cookie))
        val loaded = jar.loadForRequest(url)
        assertEquals(1, loaded.size)
        assertEquals("token_abc", loaded[0].value)

        jar.clear()
        val afterClear = jar.loadForRequest(url)
        assertTrue(afterClear.isEmpty())
    }

    @Test
    fun testEcoGrowApiSessionAndCsrfFlow() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"authenticated": false, "csrf_token": "csrf_12345"}""")
        )
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"authenticated": true, "user": {"name": "John"}, "csrf_token": "csrf_67890"}""")
        )

        server.start()
        val baseUrl = server.url("/").toString()
        val api = EcoGrowApi(baseUrl, debug = true)

        val sessionRes = api.get("session")
        assertFalse(sessionRes.getBoolean("authenticated"))
        assertEquals("csrf_12345", sessionRes.getString("csrf_token"))

        val loginRes = api.post("login", JSONObject().put("mail", "john@ecogrow.io").put("password", "secret"))
        assertTrue(loginRes.getBoolean("authenticated"))

        val recordedSessionReq = server.takeRequest()
        assertEquals("/api/mobile/session", recordedSessionReq.path)

        val recordedLoginReq = server.takeRequest()
        assertEquals("/api/mobile/login", recordedLoginReq.path)
        assertEquals("csrf_12345", recordedLoginReq.getHeader("X-CSRF-Token"))
    }

    @Test
    fun testLocalTowerApiDetailMapping() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """{
                        "pump_state": true,
                        "pump_mode": "AUTO",
                        "water_level_ok": true,
                        "water_level_pct": 82.5,
                        "water_liters": 24.75,
                        "tds_ppm": 650.0,
                        "ph_val": 6.1,
                        "temp_water": 22.4,
                        "time_left_sec": 480,
                        "alert": "Torre en Funcionamiento Normal",
                        "recipe": {"idx": 0, "name": "Lechuga", "ppm_min": 560.0, "ppm_max": 840.0, "ph_min": 5.8, "ph_max": 6.2}
                    }""".trimIndent()
                )
        )
        server.start()
    }
}
