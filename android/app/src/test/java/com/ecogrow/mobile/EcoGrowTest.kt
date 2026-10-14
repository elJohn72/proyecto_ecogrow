package com.ecogrow.mobile

import okhttp3.Cookie
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.json.JSONArray
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
        assertTrue(jar.hasActiveSession())

        jar.clear()
        val afterClear = jar.loadForRequest(url)
        assertTrue(afterClear.isEmpty())
        assertFalse(jar.hasActiveSession())
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

        val sessionRes = api.getSession()
        assertFalse(sessionRes.getBoolean("authenticated"))
        assertEquals("csrf_12345", sessionRes.getString("csrf_token"))

        val loginRes = api.login("john@ecogrow.io", "secret")
        assertTrue(loginRes.getBoolean("authenticated"))

        val recordedSessionReq = server.takeRequest()
        assertEquals("/api/mobile/session", recordedSessionReq.path)

        val recordedLoginReq = server.takeRequest()
        assertEquals("/api/mobile/login", recordedLoginReq.path)
        assertEquals("csrf_12345", recordedLoginReq.getHeader("X-CSRF-Token"))
    }

    @Test
    fun testEcoGrowApiListTowersAndBind() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"towers": [{"id": 1, "name": "Torre Alfa", "code": "EG-A1B2"}]}""")
        )
        server.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"ok": true, "tower": {"id": 2, "name": "Torre Beta", "code": "EG-C3D4"}}""")
        )

        server.start()
        val baseUrl = server.url("/").toString()
        val api = EcoGrowApi(baseUrl, debug = true)

        val list = api.listTowers()
        assertEquals(1, list.size)
        assertEquals("Torre Alfa", list[0].name)
        assertEquals("EG-A1B2", list[0].code)

        val bound = api.bindTower("EG-C3D4", "ABCDEF12", "Torre Beta")
        assertEquals(2, bound.id)
        assertEquals("Torre Beta", bound.name)
        assertEquals("EG-C3D4", bound.code)
    }

    @Test
    fun testTowerDetailModelParsingRealContract() {
        val rawJson = JSONObject().apply {
            put("id", 5)
            put("name", "Torre Hidropónica Principal")
            put("code", "EG-70C4")
            put("source", "remote")
            put("updated_at", "2026-10-13T21:40:00")
            put("stale", false)
            put("sensors", JSONObject().apply {
                put("ph", 6.15)
                put("tds_ppm", 680.0)
                put("ec_ms_cm", 1.36)
                put("nivel_pct", 78.0)
                put("litros", 23.4)
                put("temperatura_agua_c", 21.8)
            })
            put("pump", JSONObject().apply {
                put("desired", "on")
                put("reported", "on")
                put("mode", "AUTO")
                put("status", "executed")
                put("command_id", "cmd_9999")
                put("expires_at", 1790000000L)
            })
            put("recipe", JSONObject().apply {
                put("crop", "Lechuga")
                put("phase", "Vegetativo")
                put("notes", "Cascada vertical 15 min ON / 45 min OFF")
            })
            put("alerts", JSONArray().apply {
                put(JSONObject().apply {
                    put("id", 1)
                    put("severity", "info")
                    put("message", "Nivel óptimo de solución nutritiva")
                    put("created_at", "2026-10-13T20:00:00")
                })
            })
            put("capabilities", JSONObject().apply {
                put("pump_control", true)
                put("mode_control", true)
                put("recipe_edit", true)
                put("liters", true)
                put("pump_reported", true)
            })
        }

        val model = TowerDetailModel.fromJson(rawJson)

        assertEquals(5, model.id)
        assertEquals("Torre Hidropónica Principal", model.name)
        assertEquals("EG-70C4", model.code)
        assertEquals("remote", model.source)
        assertEquals("2026-10-13T21:40:00", model.updatedAt)
        assertFalse(model.stale)

        // Sensores
        assertEquals("6.15", model.sensors.phFormatted())
        assertEquals("680 ppm", model.sensors.tdsFormatted())
        assertEquals("1.36 mS/cm", model.sensors.ecFormatted())
        assertEquals("78%", model.sensors.nivelFormatted())
        assertEquals("23.4 L", model.sensors.litrosFormatted())
        assertEquals("21.8 °C", model.sensors.tempFormatted())

        // Bomba
        assertTrue(model.pump.isPhysicallyOn)
        assertFalse(model.pump.isPhysicallyOff)
        assertEquals("AUTO", model.pump.mode)
        assertEquals("executed", model.pump.status)
        assertEquals("cmd_9999", model.pump.commandId)

        // Receta
        assertNotNull(model.recipe)
        assertEquals("Lechuga", model.recipe?.crop)
        assertEquals("Vegetativo", model.recipe?.phase)

        // Alertas
        assertEquals(1, model.alerts.size)
        assertEquals("Nivel óptimo de solución nutritiva", model.alerts[0].message)

        // Capacidades
        assertTrue(model.capabilities.pumpControl)
        assertTrue(model.capabilities.litersCalibrated)
        assertTrue(model.capabilities.pumpReported)
        assertTrue(model.canRequestPumpOn())
    }

    @Test
    fun testPumpOnRequiresTurnOnLevel() {
        fun model(level: Double?, stale: Boolean = false): TowerDetailModel {
            val json = JSONObject().apply {
                put("id", 1)
                put("stale", stale)
                put("sensors", JSONObject().apply {
                    if (level != null) put("nivel_pct", level)
                })
                put("safety", JSONObject().apply {
                    put("level_cutoff_pct", 20.0)
                    put("level_turn_on_pct", 25.0)
                })
            }
            return TowerDetailModel.fromJson(json)
        }
        assertFalse(model(null).canRequestPumpOn())
        assertFalse(model(24.0).canRequestPumpOn())
        assertTrue(model(25.0).canRequestPumpOn())
        assertFalse(model(80.0, stale = true).canRequestPumpOn())
    }

    @Test
    fun testTowerDetailModelHandlesMissingSensorsWithoutCrash() {
        val emptyJson = JSONObject().apply {
            put("id", 1)
            put("name", "Torre Sin Datos")
            put("code", "EG-0000")
            put("stale", true)
        }

        val model = TowerDetailModel.fromJson(emptyJson)
        assertTrue(model.stale)
        assertEquals("Sin dato", model.sensors.phFormatted())
        assertEquals("Sin dato", model.sensors.tdsFormatted())
        assertEquals("Sin dato", model.sensors.nivelFormatted())
        assertEquals("Sin calibrar", model.sensors.litrosFormatted())
        assertEquals("Sin dato", model.sensors.tempFormatted())
        assertNull(model.recipe)
        assertTrue(model.alerts.isEmpty())
        assertFalse(model.pump.isPhysicallyOn)
    }

    @Test
    fun testBleProvStepsAndDeviceModel() {
        val steps = BleProvStep.values()
        assertTrue(steps.contains(BleProvStep.IDLE))
        assertTrue(steps.contains(BleProvStep.SCANNING))
        assertTrue(steps.contains(BleProvStep.CONNECTING))
        assertTrue(steps.contains(BleProvStep.CONNECTED))
        assertTrue(steps.contains(BleProvStep.SCANNING_WIFI))
        assertTrue(steps.contains(BleProvStep.PROVISIONING))
        assertTrue(steps.contains(BleProvStep.SUCCESS))
        assertTrue(steps.contains(BleProvStep.FAILED))
    }

    @Test
    fun testSanitizePopDirectAndQrJson() {
        assertEquals("A7K9M2PX", BleProvisioningManager.sanitizePop("A7K9M2PX"))
        assertEquals("A7K9M2PX", BleProvisioningManager.sanitizePop("  a7k9m2px  "))
        assertEquals("A7K9M2PX", BleProvisioningManager.sanitizePop("A7K9-M2PX"))

        val jsonQr = """{"ver":"v1","name":"PROV_EcoGrow_70C4","pop":"A7K9M2PX","transport":"ble"}"""
        assertEquals("A7K9M2PX", BleProvisioningManager.sanitizePop(jsonQr))
        assertEquals(
            "021a9004-0382-4aea-bff4-6b3f1b5adfb4",
            BleProvisioningManager.ESP_PROV_SERVICE_UUID
        )
    }

    @Test
    fun testAddTowerStepsAndNavigationViews() {
        val steps = AddTowerStep.values()
        assertEquals(8, steps.size)
        assertTrue(steps.contains(AddTowerStep.INSTRUCTIONS))
        assertTrue(steps.contains(AddTowerStep.PERMISSIONS))
        assertTrue(steps.contains(AddTowerStep.SCAN_BLE))
        assertTrue(steps.contains(AddTowerStep.ENTER_PIN))
        assertTrue(steps.contains(AddTowerStep.SCAN_WIFI))
        assertTrue(steps.contains(AddTowerStep.ENTER_PASSWORD))
        assertTrue(steps.contains(AddTowerStep.PROVISIONING))
        assertTrue(steps.contains(AddTowerStep.SUCCESS))

        val views = CurrentView.values()
        assertEquals(4, views.size)
        assertTrue(views.contains(CurrentView.HOME))
        assertTrue(views.contains(CurrentView.DETAIL))
        assertTrue(views.contains(CurrentView.ADD_TOWER))
        assertTrue(views.contains(CurrentView.LOGIN))
    }

    @Test
    fun testTowerModelInstantiation() {
        val tower = Tower(1, "Torre Sala", "EG-70C4")
        assertEquals(1, tower.id)
        assertEquals("Torre Sala", tower.name)
        assertEquals("EG-70C4", tower.code)
    }

    @Test
    fun testRegisterApiSuccess() {
        val sessionJson = """{"authenticated":false,"user":null,"csrf_token":"CSRF_123"}"""
        val registerJson = """{"authenticated":true,"user":{"id":5,"name":"Operador Test","mail":"test@ecogrow.io"},"csrf_token":"CSRF_456"}"""

        server.enqueue(MockResponse().setResponseCode(200).setBody(sessionJson))
        server.enqueue(MockResponse().setResponseCode(201).setBody(registerJson))

        server.start()
        val baseUrl = server.url("/").toString()
        val api = EcoGrowApi(baseUrl, debug = true)

        val result = api.register("Operador Test", "test@ecogrow.io", "Pass12345!", "Pass12345!")
        assertTrue(result.getBoolean("authenticated"))
        val user = result.getJSONObject("user")
        assertEquals(5, user.getInt("id"))
        assertEquals("Operador Test", user.getString("name"))
        assertEquals("test@ecogrow.io", user.getString("mail"))

        val recordedSessionReq = server.takeRequest()
        assertEquals("/api/mobile/session", recordedSessionReq.path)

        val recordedRegisterReq = server.takeRequest()
        assertEquals("/api/mobile/register", recordedRegisterReq.path)
        assertEquals("CSRF_123", recordedRegisterReq.getHeader("X-CSRF-Token"))
    }

    @Test
    fun testRegisterApiServerRejection() {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"authenticated":false,"csrf_token":"CSRF_123"}"""))
        server.enqueue(MockResponse().setResponseCode(400).setBody("""{"error":"password_mismatch","message":"Las contraseñas no coinciden."}"""))

        server.start()
        val baseUrl = server.url("/").toString()
        val api = EcoGrowApi(baseUrl, debug = true)

        assertThrows(ApiFailure::class.java) {
            api.register("Operador Test", "test@ecogrow.io", "Pass12345!", "Mismatch!")
        }
    }
}
