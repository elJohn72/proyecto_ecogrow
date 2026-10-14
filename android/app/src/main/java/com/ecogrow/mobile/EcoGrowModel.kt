package com.ecogrow.mobile

import org.json.JSONObject
import java.util.Locale

data class Tower(
    val id: Int,
    val name: String,
    val code: String
)

data class DiscoveredWifi(
    val ssid: String,
    val level: Int,
    val isSecure: Boolean,
    val isCurrent: Boolean = false
)

data class SensorReadings(
    val ph: Double?,
    val tdsPpm: Double?,
    val ecMsCm: Double?,
    val nivelPct: Double?,
    val litros: Double?,
    val temperaturaAguaC: Double?
) {
    fun phFormatted(): String = ph?.let { String.format(Locale.US, "%.2f", it) } ?: "Sin dato"
    fun tdsFormatted(): String = tdsPpm?.let { "${it.toInt()} ppm" } ?: "Sin dato"
    fun ecFormatted(): String = ecMsCm?.let { String.format(Locale.US, "%.2f mS/cm", it) } ?: "Sin dato"
    fun nivelFormatted(): String = nivelPct?.let { "${it.toInt()}%" } ?: "Sin dato"
    fun litrosFormatted(): String = litros?.let { String.format(Locale.US, "%.1f L", it) } ?: "Sin calibrar"
    fun tempFormatted(): String = temperaturaAguaC?.let { String.format(Locale.US, "%.1f °C", it) } ?: "Sin dato"
}

data class PumpStatus(
    val desired: String?,
    val reported: String?,
    val mode: String,
    val status: String,
    val commandId: String?,
    val expiresAt: Long?
) {
    val isPhysicallyOn: Boolean get() = reported?.lowercase() == "on"
    val isPhysicallyOff: Boolean get() = reported?.lowercase() == "off"
    val isPending: Boolean get() = status == "pending" || !commandId.isNullOrBlank()
}

data class RecipeInfo(
    val crop: String,
    val phase: String,
    val notes: String
)

data class AlertItem(
    val id: Int,
    val severity: String,
    val message: String,
    val createdAt: String?
)

data class TowerCapabilities(
    val pumpControl: Boolean,
    val modeControl: Boolean,
    val recipeEdit: Boolean,
    val litersCalibrated: Boolean,
    val pumpReported: Boolean
)

data class TowerDetailModel(
    val id: Int,
    val name: String,
    val code: String,
    val source: String,
    val updatedAt: String?,
    val stale: Boolean,
    val sensors: SensorReadings,
    val pump: PumpStatus,
    val recipe: RecipeInfo?,
    val alerts: List<AlertItem>,
    val capabilities: TowerCapabilities
) {
    fun formattedLastSeen(): String {
        if (updatedAt.isNullOrBlank()) return "Sin telemetría registrada"
        return try {
            val parts = updatedAt.split("T")
            if (parts.size >= 2) {
                val timePart = parts[1].take(8)
                val datePart = parts[0]
                "$datePart · $timePart"
            } else updatedAt
        } catch (_: Exception) {
            updatedAt
        }
    }

    companion object {
        fun fromJson(json: JSONObject): TowerDetailModel {
            val id = json.optInt("id", 0)
            val name = json.optString("name", "Torre EcoGrow")
            val code = json.optString("code", "")
            val source = json.optString("source", "remote")
            val updatedAt = if (json.has("updated_at") && !json.isNull("updated_at")) json.optString("updated_at") else null
            val stale = json.optBoolean("stale", true)

            val sObj = json.optJSONObject("sensors") ?: JSONObject()
            val sensors = SensorReadings(
                ph = if (sObj.has("ph") && !sObj.isNull("ph")) sObj.optDouble("ph") else null,
                tdsPpm = if (sObj.has("tds_ppm") && !sObj.isNull("tds_ppm")) sObj.optDouble("tds_ppm") else null,
                ecMsCm = if (sObj.has("ec_ms_cm") && !sObj.isNull("ec_ms_cm")) sObj.optDouble("ec_ms_cm") else null,
                nivelPct = if (sObj.has("nivel_pct") && !sObj.isNull("nivel_pct")) sObj.optDouble("nivel_pct") else null,
                litros = if (sObj.has("litros") && !sObj.isNull("litros")) sObj.optDouble("litros") else null,
                temperaturaAguaC = if (sObj.has("temperatura_agua_c") && !sObj.isNull("temperatura_agua_c")) sObj.optDouble("temperatura_agua_c") else null
            )

            val pObj = json.optJSONObject("pump") ?: JSONObject()
            val pump = PumpStatus(
                desired = if (pObj.has("desired") && !pObj.isNull("desired")) pObj.optString("desired") else null,
                reported = if (pObj.has("reported") && !pObj.isNull("reported")) pObj.optString("reported") else null,
                mode = pObj.optString("mode", "AUTO").uppercase(),
                status = pObj.optString("status", "unknown"),
                commandId = if (pObj.has("command_id") && !pObj.isNull("command_id")) pObj.optString("command_id") else null,
                expiresAt = if (pObj.has("expires_at") && !pObj.isNull("expires_at")) pObj.optLong("expires_at") else null
            )

            val rObj = json.optJSONObject("recipe")
            val recipe = if (rObj != null) {
                RecipeInfo(
                    crop = rObj.optString("crop", "Sin cultivo"),
                    phase = rObj.optString("phase", "General"),
                    notes = rObj.optString("notes", "")
                )
            } else null

            val alertsList = mutableListOf<AlertItem>()
            val aArr = json.optJSONArray("alerts")
            if (aArr != null) {
                for (i in 0 until aArr.length()) {
                    val aObj = aArr.optJSONObject(i) ?: continue
                    alertsList.add(
                        AlertItem(
                            id = aObj.optInt("id", i + 1),
                            severity = aObj.optString("severity", "info"),
                            message = aObj.optString("message", ""),
                            createdAt = if (aObj.has("created_at") && !aObj.isNull("created_at")) aObj.optString("created_at") else null
                        )
                    )
                }
            }

            val cObj = json.optJSONObject("capabilities") ?: JSONObject()
            val capabilities = TowerCapabilities(
                pumpControl = cObj.optBoolean("pump_control", false),
                modeControl = cObj.optBoolean("mode_control", false),
                recipeEdit = cObj.optBoolean("recipe_edit", false),
                litersCalibrated = cObj.optBoolean("liters", false),
                pumpReported = cObj.optBoolean("pump_reported", false)
            )

            return TowerDetailModel(
                id = id,
                name = name,
                code = code,
                source = source,
                updatedAt = updatedAt,
                stale = stale,
                sensors = sensors,
                pump = pump,
                recipe = recipe,
                alerts = alertsList,
                capabilities = capabilities
            )
        }
    }
}
