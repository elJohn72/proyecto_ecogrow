/**
 * EcoGrow — Fase 1: ESP32 DevKit + modulo rele + bomba
 *
 * - Sincroniza cada SYNC_INTERVAL_MS con POST /api/iot/sync
 * - Aplica el comando rele_principal devuelto por el servidor
 * - LED de estado en GPIO 2 (LED integrado en muchos DevKit)
 * - Failsafe: apaga bomba si WiFi o API fallan demasiado tiempo
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

namespace {

bool relayEnabled = false;
unsigned long lastSyncAt = 0;
unsigned long lastWifiOkAt = 0;
unsigned long lastApiOkAt = 0;
unsigned long lastLedToggleAt = 0;
bool ledOn = false;
uint8_t consecutiveApiFailures = 0;

void applyRelay(bool enabled) {
  if (relayEnabled == enabled) {
    return;
  }
  relayEnabled = enabled;
  const int level = RELAY_ACTIVE_LOW ? (enabled ? LOW : HIGH) : (enabled ? HIGH : LOW);
  digitalWrite(RELAY_PIN, level);
  Serial.print(F("[rele] "));
  Serial.println(enabled ? F("ENCENDIDO (bomba ON)") : F("APAGADO (bomba OFF)"));
}

void setStatusLed(bool on) {
  if (on == ledOn) {
    return;
  }
  ledOn = on;
#if defined(STATUS_LED_PIN)
  digitalWrite(STATUS_LED_PIN, on ? HIGH : LOW);
#endif
}

void blinkStatusLed(unsigned long now, unsigned long intervalMs) {
#if defined(STATUS_LED_PIN)
  if (now - lastLedToggleAt >= intervalMs) {
    lastLedToggleAt = now;
    setStatusLed(!ledOn);
  }
#else
  (void)now;
  (void)intervalMs;
#endif
}

bool parseServerCommand(const char* command) {
  if (command == nullptr) {
    return relayEnabled;
  }
  String normalized = String(command);
  normalized.toLowerCase();
  normalized.trim();
  if (normalized == "encendido" || normalized == "on" || normalized == "1" ||
      normalized == "encendida") {
    return true;
  }
  if (normalized == "apagado" || normalized == "off" || normalized == "0" ||
      normalized == "apagada") {
    return false;
  }
  return relayEnabled;
}

bool connectToWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.println(F("[wifi] Reconectando..."));
  WiFi.disconnect(true);
  delay(100);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - started) < WIFI_CONNECT_TIMEOUT_MS) {
    blinkStatusLed(millis(), 200);
    delay(100);
  }

  if (WiFi.status() == WL_CONNECTED) {
    lastWifiOkAt = millis();
    Serial.print(F("[wifi] Conectado. IP: "));
    Serial.println(WiFi.localIP());
    setStatusLed(true);
    return true;
  }

  Serial.println(F("[wifi] Sin conexion"));
  return false;
}

void checkFailsafe(unsigned long now) {
#if PUMP_FAILSAFE_ENABLED
  const bool wifiStale = (now - lastWifiOkAt) > WIFI_FAILSAFE_MS;
  const bool apiStale = (now - lastApiOkAt) > API_FAILSAFE_MS;
  if ((wifiStale || apiStale) && relayEnabled) {
    Serial.println(F("[failsafe] Apagando bomba por perdida de enlace con EcoGrow"));
    applyRelay(false);
  }
#endif
}

bool syncWithEcoGrow() {
  if (!connectToWifi()) {
    consecutiveApiFailures++;
    return false;
  }

  HTTPClient http;
  http.setConnectTimeout(8000);
  http.setTimeout(12000);
  http.begin(API_SYNC_URL);
  http.addHeader(F("Content-Type"), F("application/json"));
  http.addHeader(F("X-API-Token"), API_TOKEN);

  StaticJsonDocument<320> payload;
  payload[F("torre_codigo")] = TORRE_CODIGO;
  payload[F("dispositivo")] = DEVICE_ID;
  payload[F("rele_principal")] = relayEnabled;

  String body;
  serializeJson(payload, body);

  Serial.print(F("[api] POST "));
  Serial.println(API_SYNC_URL);
  const int code = http.POST(body);
  Serial.print(F("[api] HTTP "));
  Serial.println(code);

  bool ok = false;
  if (code == 200) {
    const String response = http.getString();
    StaticJsonDocument<512> doc;
    const DeserializationError err = deserializeJson(doc, response);
    if (!err && doc[F("ok")] == true) {
      const char* command = doc[F("comandos")][F("rele_principal")] | "apagado";
      applyRelay(parseServerCommand(command));
      if (!doc[F("sensor_warning")].isNull()) {
        Serial.print(F("[api] aviso: "));
        Serial.println(doc[F("sensor_warning")].as<const char*>());
      }
      if (doc[F("actuador")].is<JsonObject>()) {
        Serial.print(F("[api] bomba BD: "));
        Serial.print(doc[F("actuador")][F("estado")].as<const char*>());
        Serial.print(F(" modo="));
        Serial.println(doc[F("actuador")][F("modo")].as<const char*>());
      }
      lastApiOkAt = millis();
      consecutiveApiFailures = 0;
      ok = true;
    } else {
      Serial.println(F("[api] JSON invalido o ok=false"));
      Serial.println(response);
    }
  } else if (code > 0) {
    Serial.println(http.getString());
  } else {
    Serial.println(http.errorToString(code));
  }

  http.end();

  if (!ok) {
    consecutiveApiFailures++;
  }
  return ok;
}

#if LOCAL_BUTTON_PIN >= 0
void pollLocalButton() {
  static bool lastPressed = false;
  static unsigned long lastBounce = 0;
  const bool pressed = digitalRead(LOCAL_BUTTON_PIN) == LOW;
  const unsigned long now = millis();

  if (pressed != lastPressed && (now - lastBounce) > 50) {
    lastBounce = now;
    lastPressed = pressed;
    if (pressed) {
      applyRelay(!relayEnabled);
      Serial.println(F("[boton] Toggle local (solo prueba de banco)"));
    }
  }
}
#endif

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println(F("=== EcoGrow ESP32 Fase 1 (rele + bomba) ==="));

  pinMode(RELAY_PIN, OUTPUT);
  applyRelay(false);

#if defined(STATUS_LED_PIN)
  pinMode(STATUS_LED_PIN, OUTPUT);
  setStatusLed(false);
#endif

#if LOCAL_BUTTON_PIN >= 0
  pinMode(LOCAL_BUTTON_PIN, INPUT_PULLUP);
  Serial.println(F("[init] Boton GPIO0: toggle local de rele"));
#endif

  connectToWifi();
  syncWithEcoGrow();
  lastSyncAt = millis();
  lastApiOkAt = millis();
  lastWifiOkAt = millis();
}

void loop() {
  const unsigned long now = millis();

#if LOCAL_BUTTON_PIN >= 0
  pollLocalButton();
#endif

  if (WiFi.status() == WL_CONNECTED) {
    lastWifiOkAt = now;
  }

  if (now - lastSyncAt >= SYNC_INTERVAL_MS) {
    lastSyncAt = now;
    syncWithEcoGrow();
  }

  checkFailsafe(now);

  if (WiFi.status() != WL_CONNECTED) {
    blinkStatusLed(now, 400);
  } else if (consecutiveApiFailures > 0) {
    blinkStatusLed(now, 800);
  } else {
    setStatusLed(true);
  }

  delay(20);
}
