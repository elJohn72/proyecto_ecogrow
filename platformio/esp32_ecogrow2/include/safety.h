#pragma once
#include <cmath>
#include <cstdint>

inline bool safeWaterLevel(float percentage, bool calibrated) {
  return calibrated && std::isfinite(percentage) && percentage >= 10.0f && percentage <= 100.0f;
}

inline bool validRecipe(int index, int count) {
  return index >= 0 && index < count;
}

// Comprueba si ha transcurrido la duración del ciclo actual de forma segura frente a desbordamientos
inline bool cycleElapsed(uint32_t nowMs, uint32_t startMs, uint32_t durationMs) {
  // Aritmética modular segura uint32_t: (now - start) mide el intervalo correcto
  // incluso si millis() se reinicia tras ~49.7 días.
  return (uint32_t)(nowMs - startMs) >= durationMs;
}

// Verifica si una orden manual ha excedido el tiempo máximo de seguridad
inline bool manualLimitExceeded(bool pumpOn, uint32_t nowMs, uint32_t startMs, uint32_t maxOnMs) {
  return pumpOn && ((uint32_t)(nowMs - startMs) >= maxOnMs);
}
