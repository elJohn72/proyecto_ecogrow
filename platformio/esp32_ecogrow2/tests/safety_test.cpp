#include "safety.h"
#include "identity_policy.h"
#include "prov_uuid.h"
#include "wifi_recovery.h"
#include "sensor_diag.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>

int main() {
  // Pruebas de nivel de agua
  assert(!safeWaterLevel(85, false));
  assert(!safeWaterLevel(std::numeric_limits<float>::quiet_NaN(), true));
  assert(!safeWaterLevel(std::numeric_limits<float>::infinity(), true));
  assert(!safeWaterLevel(19.9f, true, true));
  assert(safeWaterLevel(20.0f, true, true));
  assert(!safeWaterLevel(24.9f, true, false));
  assert(safeWaterLevel(25.0f, true, false));
  assert(!safeWaterLevel(101, true));
  assert(!bootPumpOutputHigh());
  assert(!bootStartsAutoOn());
  assert(manualOnLimitMs(0) == 15UL * 60UL * 1000UL);
  assert(manualOnLimitMs(20UL * 60UL * 1000UL) == 15UL * 60UL * 1000UL);
  assert(pumpOffLatencyBoundMs() <= 3000);
  assert(!levelSampleFresh(5000, 0));
  assert(!levelSampleFresh(8000, 1000));
  assert(levelSampleFresh(4000, 2000));
  assert(!shouldApplyPumpCommand(true, false, true, true));
  assert(!shouldApplyPumpCommand(false, true, true, true));
  assert(!shouldApplyPumpCommand(false, false, true, false));
  assert(shouldApplyPumpCommand(false, false, false, false));
  assert(shouldApplyPumpCommand(false, false, true, true));

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

  char prov_uuid[37];
  ecogrowProvServiceUuidString(prov_uuid);
  assert(std::strcmp(prov_uuid, "021a9004-0382-4aea-bff4-6b3f1b5adfb4") == 0);
  assert(ECOGROW_PROV_SERVICE_UUID_LE[3] == 0x1b);

  assert(!ecogrowShouldReopenBle(true, false, 120000));
  assert(!ecogrowShouldReopenBle(false, true, 120000));
  assert(!ecogrowShouldReopenBle(false, false, 59999));
  assert(ecogrowShouldReopenBle(false, false, 60000));

  EcogrowLink link{};
  ecogrowNoteGotIp(link);
  ecogrowNoteProvEnd(link);
  assert(!link.bleActive);
  assert(link.wifiReady);
  assert(link.wifiDownSince == 0);
  assert(!ecogrowShouldReopenBle(link.bleActive, link.wifiReady, 120000));
  ecogrowNoteStaDown(link, 1000);
  ecogrowNoteProvEnd(link);
  assert(!link.wifiReady);
  assert(link.wifiDownSince == 1000);

  PhPoints ph = parsePhCalibration("1.50,4.00,2.10,7.00");
  assert(ph.ok);
  bool phValid = false;
  assert(std::fabs(phFromCalibration(1.50f, ph, false, &phValid) - 4.0f) < 0.02f);
  assert(phValid);
  phValid = true;
  assert(std::isnan(phFromCalibration(1.50f, ph, true, &phValid)));
  assert(!phValid);
  assert(!parsePhCalibration("0.01,4,2.1,7").ok);

  TankPoints tank = parseTankCalibration("40,25,18,0");
  assert(tank.ok);
  assert(!tank.volumeLinear);
  LevelResult level = interpretLevel(true, 30.0f, tank);
  assert(level.state == SENSOR_OK);
  assert(std::fabs(level.percent - (10.0f / 15.0f) * 100.0f) < 0.1f);
  assert(std::isnan(level.liters));
  tank.volumeLinear = true;
  level = interpretLevel(true, 30.0f, tank);
  assert(std::isfinite(level.liters));
  assert(interpretLevel(false, 30.0f, tank).state == SENSOR_TIMEOUT);
  TankPoints empty{};
  assert(interpretLevel(true, 30.0f, empty).state == SENSOR_NOT_CALIBRATED);

  float temp = 0;
  assert(interpretTemperature(false, 22.0f, &temp) == SENSOR_DISCONNECTED);
  assert(interpretTemperature(true, 22.0f, &temp) == SENSOR_OK);
  assert(std::fabs(temp - 22.0f) < 0.01f);
  assert(interpretTemperature(true, 80.0f, &temp) == SENSOR_OUT_OF_RANGE);
  bool tdsValid = false;
  assert(std::isnan(tdsFromVoltage(1.0f, NAN, 1.0f, true, false, &tdsValid)));
  assert(!tdsValid);
  assert(std::isfinite(tdsFromVoltage(0.8f, 25.0f, 1.0f, true, false, &tdsValid)));
  assert(tdsValid);
  assert(std::isnan(tdsFromVoltage(0.8f, 25.0f, 1.0f, true, true, &tdsValid)));
  float factor = 0;
  assert(parseTdsFactor("1.0", &factor) && factor == 1.0f);
  assert(!parseTdsFactor("12", &factor));

  return 0;
}
