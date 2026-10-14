#pragma once

#include <cmath>
#include <cstdio>
#include <cstring>

// Clasifica lecturas de banco. Un ADC a mitad de escala no demuestra que la sonda
// esté conectada. Un valor recortado a 0 o a 14 no es una medición.

enum SensorState : int {
  SENSOR_OK = 0,
  SENSOR_NOT_CALIBRATED = 1,
  SENSOR_TIMEOUT = 2,
  SENSOR_SATURATED = 3,
  SENSOR_OUT_OF_RANGE = 4,
  SENSOR_DISCONNECTED = 5,
  SENSOR_INVALID = 6
};

inline const char* sensorStateName(SensorState state) {
  switch (state) {
    case SENSOR_OK: return "ok";
    case SENSOR_NOT_CALIBRATED: return "no_calibrado";
    case SENSOR_TIMEOUT: return "timeout";
    case SENSOR_SATURATED: return "saturado";
    case SENSOR_OUT_OF_RANGE: return "fuera_de_rango";
    case SENSOR_DISCONNECTED: return "desconectado";
    case SENSOR_INVALID: return "invalido";
  }
  return "invalido";
}

inline bool adcRail(int raw) {
  return raw < 0 || raw <= 40 || raw >= 4055;
}

struct PhPoints {
  float v1;
  float ph1;
  float v2;
  float ph2;
  bool ok;
};

inline PhPoints parsePhCalibration(const char* text) {
  PhPoints points{0, 0, 0, 0, false};
  if (text == nullptr || text[0] == '\0') return points;
  float v1 = 0, ph1 = 0, v2 = 0, ph2 = 0;
  if (std::sscanf(text, "%f,%f,%f,%f", &v1, &ph1, &v2, &ph2) != 4) return points;
  if (!(v1 > 0.05f && v1 < 3.20f && v2 > 0.05f && v2 < 3.20f)) return points;
  if (!(ph1 >= 0.0f && ph1 <= 14.0f && ph2 >= 0.0f && ph2 <= 14.0f)) return points;
  if (std::fabs(v2 - v1) < 0.05f || std::fabs(ph2 - ph1) < 0.5f) return points;
  points.v1 = v1;
  points.ph1 = ph1;
  points.v2 = v2;
  points.ph2 = ph2;
  points.ok = true;
  return points;
}

inline float phFromCalibration(float volts, const PhPoints& points, bool rail, bool* valid) {
  if (valid) *valid = false;
  if (!points.ok || rail || !std::isfinite(volts)) return NAN;
  const float span = points.v2 - points.v1;
  if (std::fabs(span) < 0.05f) return NAN;
  const float ph = points.ph1 + (volts - points.v1) * (points.ph2 - points.ph1) / span;
  if (!std::isfinite(ph) || ph < 0.0f || ph > 14.0f) return NAN;
  if (valid) *valid = true;
  return ph;
}

struct TankPoints {
  float heightCm;
  float minDistanceCm;
  float capacityL;
  bool volumeLinear;
  bool ok;
};

inline TankPoints parseTankCalibration(const char* text) {
  TankPoints tank{0, 0, 0, false, false};
  if (text == nullptr || text[0] == '\0') return tank;
  float height = 0, minimum = 0, capacity = 0;
  int linear = 0;
  if (std::sscanf(text, "%f,%f,%f,%d", &height, &minimum, &capacity, &linear) != 4) return tank;
  if (!(height > minimum && minimum >= 1.0f && height <= 300.0f && capacity > 0.0f && capacity <= 500.0f)) return tank;
  if (linear != 0 && linear != 1) return tank;
  tank.heightCm = height;
  tank.minDistanceCm = minimum;
  tank.capacityL = capacity;
  tank.volumeLinear = linear == 1;
  tank.ok = true;
  return tank;
}

inline bool parseTdsFactor(const char* text, float* factor) {
  if (text == nullptr || factor == nullptr) return false;
  float value = 0;
  if (std::sscanf(text, "%f", &value) != 1) return false;
  if (!(value >= 0.2f && value <= 5.0f)) return false;
  *factor = value;
  return true;
}

struct LevelResult {
  SensorState state;
  float distanceCm;
  float percent;
  float liters;
};

inline LevelResult interpretLevel(bool echo, float distanceCm, const TankPoints& tank) {
  LevelResult result{SENSOR_TIMEOUT, NAN, NAN, NAN};
  if (!echo || !std::isfinite(distanceCm) || distanceCm <= 0.0f) return result;
  result.distanceCm = distanceCm;
  if (!tank.ok) {
    result.state = SENSOR_NOT_CALIBRATED;
    return result;
  }
  if (distanceCm < tank.minDistanceCm || distanceCm > tank.heightCm + 2.0f) {
    result.state = SENSOR_OUT_OF_RANGE;
    return result;
  }
  const float span = tank.heightCm - tank.minDistanceCm;
  const float percent = ((tank.heightCm - distanceCm) / span) * 100.0f;
  if (!std::isfinite(percent) || percent < 0.0f || percent > 100.0f) {
    result.state = SENSOR_OUT_OF_RANGE;
    return result;
  }
  result.state = SENSOR_OK;
  result.percent = percent;
  if (tank.volumeLinear) result.liters = (percent / 100.0f) * tank.capacityL;
  return result;
}

inline SensorState interpretTemperature(bool present, float celsius, float* validOut) {
  if (validOut) *validOut = NAN;
  if (!present) return SENSOR_DISCONNECTED;
  if (!std::isfinite(celsius) || celsius <= -100.0f) return SENSOR_DISCONNECTED;
  if (celsius < 0.0f || celsius > 60.0f) return SENSOR_OUT_OF_RANGE;
  if (validOut) *validOut = celsius;
  return SENSOR_OK;
}

inline float tdsFromVoltage(float volts, float tempC, float factor, bool calibrated, bool rail, bool* valid) {
  if (valid) *valid = false;
  if (!calibrated || rail || !std::isfinite(volts) || !std::isfinite(tempC) || factor <= 0.0f) return NAN;
  if (tempC < 0.0f || tempC > 60.0f) return NAN;
  const float coefficient = 1.0f + 0.02f * (tempC - 25.0f);
  if (coefficient <= 0.2f) return NAN;
  const float compensated = volts / coefficient;
  const float tds = (133.42f * compensated * compensated * compensated
                     - 255.86f * compensated * compensated
                     + 857.39f * compensated) * 0.5f * factor;
  if (!std::isfinite(tds) || tds < 0.0f || tds > 4000.0f) return NAN;
  if (valid) *valid = true;
  return tds;
}
