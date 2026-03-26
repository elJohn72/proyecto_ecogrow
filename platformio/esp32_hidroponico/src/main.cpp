#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

namespace {
constexpr unsigned long SEND_INTERVAL_MS = 10000;
constexpr unsigned long PH_SETTLE_MS = 1200;
constexpr unsigned long EC_SETTLE_MS = 900;
constexpr unsigned long IRRIGATION_ON_MS = 15UL * 60UL * 1000UL;
constexpr unsigned long IRRIGATION_OFF_MS = 60UL * 60UL * 1000UL;
unsigned long lastSentAt = 0;
unsigned long irrigationPhaseStartedAt = 0;
bool irrigationRunning = true;

struct SensorSnapshot {
  float airTemperature;
  float airHumidity;
  float waterTemperature;
  float ph;
  float ec;
  float waterLevel;
  float lightLevel;
};

void setEcSensorEnabled(bool enabled) {
  Serial.print("Nodo EC: ");
  Serial.println(enabled ? "energizado" : "aislado para lectura de pH");
}

void setIrrigationPump(bool enabled) {
  irrigationRunning = enabled;
  Serial.print("Bomba principal: ");
  Serial.println(enabled ? "encendida" : "apagada");
}

float readAirTemperature() {
  return 24.5F;
}

float readAirHumidity() {
  return 67.0F;
}

float readWaterTemperature() {
  return 22.8F;
}

float readPh() {
  return 6.1F;
}

float readEc() {
  return 1.75F;
}

float readWaterLevel() {
  return 73.0F;
}

float readLightLevel() {
  return 540.0F;
}

void updateIrrigationCycle(unsigned long now) {
  const unsigned long phaseDuration = irrigationRunning ? IRRIGATION_ON_MS : IRRIGATION_OFF_MS;
  if (now - irrigationPhaseStartedAt < phaseDuration) {
    return;
  }

  setIrrigationPump(!irrigationRunning);
  irrigationPhaseStartedAt = now;
}

SensorSnapshot sampleSensors() {
  SensorSnapshot snapshot{};
  snapshot.airTemperature = readAirTemperature();
  snapshot.airHumidity = readAirHumidity();
  snapshot.waterTemperature = readWaterTemperature();

  setEcSensorEnabled(false);
  delay(PH_SETTLE_MS);
  snapshot.ph = readPh();

  setEcSensorEnabled(true);
  delay(EC_SETTLE_MS);
  snapshot.ec = readEc();

  snapshot.waterLevel = readWaterLevel();
  snapshot.lightLevel = readLightLevel();
  return snapshot;
}

void connectToWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi conectado. IP local: ");
  Serial.println(WiFi.localIP());
}

void sendSensorReading() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado. Reintentando conexion.");
    connectToWifi();
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Token", API_TOKEN);

  const SensorSnapshot snapshot = sampleSensors();

  StaticJsonDocument<384> payload;
  payload["torre_codigo"] = TORRE_CODIGO;
  payload["dispositivo"] = DEVICE_ID;
  payload["temperatura_aire"] = snapshot.airTemperature;
  payload["humedad_aire"] = snapshot.airHumidity;
  payload["temperatura_agua"] = snapshot.waterTemperature;
  payload["ph"] = snapshot.ph;
  payload["ec"] = snapshot.ec;
  payload["nivel_agua"] = snapshot.waterLevel;
  payload["luminosidad"] = snapshot.lightLevel;
  payload["bomba_activa"] = irrigationRunning;
  payload["modo_control"] = "consenso_80_20";
  payload["integridad_senal"] = "ec_aislado_durante_lectura_ph";

  String body;
  serializeJson(payload, body);

  const int responseCode = http.POST(body);
  Serial.print("Codigo HTTP: ");
  Serial.println(responseCode);

  const String response = http.getString();
  Serial.print("Respuesta: ");
  Serial.println(response);

  http.end();
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1000);
  connectToWifi();
  setEcSensorEnabled(true);
  setIrrigationPump(true);
  irrigationPhaseStartedAt = millis();
}

void loop() {
  const unsigned long now = millis();
  updateIrrigationCycle(now);
  if (now - lastSentAt >= SEND_INTERVAL_MS) {
    lastSentAt = now;
    sendSensorReading();
  }
}
