#include "safety.h"
#include "identity_policy.h"
#include <cassert>
#include <cstdint>
#include <cstring>
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

  // Leer la identidad no persiste otro código. SET_CODE rechaza placeholders.
  assert(!ecogrowIdentityReadPersists());
  assert(ecogrowIsPlaceholderCode("TORRE-001"));
  assert(ecogrowIsPlaceholderCode("EG-TORRE-01"));
  assert(ecogrowIsPlaceholderCode(""));
  assert(ecogrowIsPlaceholderCode(nullptr));
  assert(!ecogrowExplicitSetMayPersist("TORRE-001"));
  assert(!ecogrowExplicitSetMayPersist("PRUEBA"));
  assert(ecogrowExplicitSetMayPersist("EG-TORRE-F870C4"));
  uint8_t mac[6] = {0x44, 0x1D, 0x64, 0xF8, 0x70, 0xC4};
  char suggested[32];
  ecogrowSuggestCodeFromMac(mac, suggested, sizeof(suggested));
  assert(std::strcmp(suggested, "EG-TORRE-F870C4") == 0);

  return 0;
}
