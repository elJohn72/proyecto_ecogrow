#include "safety.h"
#include <cassert>
#include <limits>

int main() {
  // Pruebas de nivel de agua
  assert(!safeWaterLevel(85, false));
  assert(!safeWaterLevel(std::numeric_limits<float>::quiet_NaN(), true));
  assert(!safeWaterLevel(std::numeric_limits<float>::infinity(), true));
  assert(!safeWaterLevel(9.99f, true));
  assert(safeWaterLevel(10, true));
  assert(!safeWaterLevel(101, true));

  // Pruebas de recetas
  assert(validRecipe(0, 4));
  assert(validRecipe(3, 4));
  assert(!validRecipe(-1, 4));
  assert(!validRecipe(4, 4));

  // Pruebas de temporización y rollover monotónico
  // Caso normal: tiempo transcurrido
  assert(cycleElapsed(600000UL, 0UL, 600000UL));
  assert(!cycleElapsed(599999UL, 0UL, 600000UL));

  // Caso rollover de unsigned long (millis se desborda en 4294967295)
  unsigned long startBeforeRollover = 4294967200UL;
  unsigned long nowAfterRollover = 100UL; // Transcurrieron 100 + (4294967295 - 4294967200 + 1) = 196 ms
  assert(cycleElapsed(nowAfterRollover, startBeforeRollover, 195UL));
  assert(!cycleElapsed(nowAfterRollover, startBeforeRollover, 200UL));

  // Protección de límite manual
  assert(manualLimitExceeded(true, 700000UL, 100000UL, 600000UL));
  assert(!manualLimitExceeded(false, 700000UL, 100000UL, 600000UL));
  assert(!manualLimitExceeded(true, 500000UL, 100000UL, 600000UL));

  return 0;
}
