#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"

namespace {
constexpr unsigned long SEND_INTERVAL_MS = 10000;
unsigned long lastSentAt = 0;

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

  StaticJsonDocument<256> payload;
  payload["torre_codigo"] = TORRE_CODIGO;
  payload["dispositivo"] = DEVICE_ID;
  payload["temperatura_aire"] = readAirTemperature();
  payload["humedad_aire"] = readAirHumidity();
  payload["temperatura_agua"] = readWaterTemperature();
  payload["ph"] = readPh();
  payload["ec"] = readEc();
  payload["nivel_agua"] = readWaterLevel();
  payload["luminosidad"] = readLightLevel();

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
}

void loop() {
  const unsigned long now = millis();
  if (now - lastSentAt >= SEND_INTERVAL_MS) {
    lastSentAt = now;
    sendSensorReading();
  }
}
