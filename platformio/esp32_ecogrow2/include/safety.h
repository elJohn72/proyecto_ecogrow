#pragma once
#include <cmath>
#include <cstdint>

// Corte de software, alineado con el nivel mínimo por defecto del servidor (20 %).
// No es la inmersión medida de la bomba: esa cifra la anota el banco.
// Con la bomba apagada hace falta el corte más la histéresis para volver a armar.
inline float waterCutoffPct() { return 20.0f; }
inline float waterHysteresisPct() { return 5.0f; }
inline float waterTurnOnPct() { return waterCutoffPct() + waterHysteresisPct(); }

inline bool waterThresholdsValid(float cutoff, float turnOn) {
  return std::isfinite(cutoff) && std::isfinite(turnOn) && cutoff > 0.0f && cutoff < turnOn && turnOn <= 100.0f;
}

inline bool safeWaterLevel(float percentage, bool calibrated, bool pumpAlreadyOn = false,
                           float cutoff = 20.0f, float turnOn = 25.0f) {
  if (!calibrated || !std::isfinite(percentage) || percentage < 0.0f || percentage > 100.0f) return false;
  if (!waterThresholdsValid(cutoff, turnOn)) return false;
  const float minimum = pumpAlreadyOn ? cutoff : turnOn;
  return percentage >= minimum;
}

// El arranque deja la salida en bajo y no entra solo al ciclo que enciende.
inline bool bootPumpOutputHigh() { return false; }
inline bool bootStartsAutoOn() { return false; }

// Tope del encendido manual. La receta no puede dejar la salida activa sin límite.
inline uint32_t manualOnLimitMs(uint32_t requestedMs) {
  const uint32_t ceiling = 15UL * 60UL * 1000UL;
  if (requestedMs == 0 || requestedMs > ceiling) return ceiling;
  return requestedMs;
}

// Cota de software: la sonda puede tardar su timeout y el HTTP que ya empezó
// sigue bloqueando hasta este límite. No es una medición con osciloscopio.
inline uint32_t ultrasonicTimeoutMs() { return 25; }
inline uint32_t httpSyncTimeoutMs() { return 2000; }
inline uint32_t pumpOffLatencyBoundMs() { return ultrasonicTimeoutMs() + httpSyncTimeoutMs(); }

inline bool levelSampleFresh(uint32_t nowMs, uint32_t sampleMs, uint32_t maxAgeMs = 3000) {
  if (sampleMs == 0 || maxAgeMs == 0) return false;
  return (uint32_t)(nowMs - sampleMs) <= maxAgeMs;
}

// Apagar gana. Una orden ya vista o vencida no vuelve a activar la salida.
inline bool shouldApplyPumpCommand(bool alreadySeen, bool expired, bool requestOn, bool levelAllowsOn) {
  if (alreadySeen || expired) return false;
  if (!requestOn) return true;
  return levelAllowsOn;
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
