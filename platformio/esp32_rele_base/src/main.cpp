#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

namespace {
bool relayEnabled = false;
unsigned long lastSyncAt = 0;

void applyRelay(bool enabled) {
  relayEnabled = enabled;
  const int level = RELAY_ACTIVE_LOW ? (enabled ? LOW : HIGH) : (enabled ? HIGH : LOW);
  digitalWrite(RELAY_PIN, level);
  Serial.print("Rele: ");
  Serial.println(enabled ? "ENCENDIDO" : "APAGADO");
}

void connectToWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

bool parseCommand(const String& command) {
  String normalized = command;
  normalized.toLowerCase();
  if (normalized == "encendido" || normalized == "on" || normalized == "1") {
    return true;
  }
  if (normalized == "apagado" || normalized == "off" || normalized == "0") {
    return false;
  }
  return relayEnabled;
}

void syncWithEcoGrow() {
  if (WiFi.status() != WL_CONNECTED) {
    connectToWifi();
  }

  HTTPClient http;
  http.begin(API_SYNC_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Token", API_TOKEN);

  StaticJsonDocument<256> payload;
  payload["torre_codigo"] = TORRE_CODIGO;
  payload["dispositivo"] = DEVICE_ID;
  payload["rele_principal"] = relayEnabled;

  String body;
  serializeJson(payload, body);

  const int code = http.POST(body);
  Serial.print("HTTP ");
  Serial.println(code);

  if (code == 200) {
    const String response = http.getString();
    StaticJsonDocument<384> doc;
    if (deserializeJson(doc, response) == DeserializationError::Ok && doc["ok"] == true) {
      const char* command = doc["comandos"]["rele_principal"] | "apagado";
      applyRelay(parseCommand(String(command)));
      if (doc["sensor_warning"]) {
        Serial.print("Aviso servidor: ");
        Serial.println(doc["sensor_warning"].as<const char*>());
      }
    } else {
      Serial.println("Respuesta JSON invalida");
      Serial.println(response);
    }
  } else {
    Serial.println(http.getString());
  }

  http.end();
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(RELAY_PIN, OUTPUT);
  applyRelay(false);
  connectToWifi();
  syncWithEcoGrow();
  lastSyncAt = millis();
}

void loop() {
  const unsigned long now = millis();
  if (now - lastSyncAt >= SYNC_INTERVAL_MS) {
    lastSyncAt = now;
    syncWithEcoGrow();
  }
}
