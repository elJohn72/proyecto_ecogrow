#include <cstring>
#include <esp_err.h>
#include <esp_timer.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/portmacro.h>

// El núcleo de Arduino y el gestor de aprovisionamiento leen la misma lista
// de redes. La primera lectura la borra del controlador. Si Arduino gana esa
// carrera, el teléfono recibe cero redes aunque la antena sí las haya visto.
// Esta capa guarda una copia unos segundos y se la entrega al segundo lector.

namespace {
constexpr uint16_t kMaxShared = 16;
constexpr int64_t kFreshUs = 3000000;

portMUX_TYPE scanMux = portMUX_INITIALIZER_UNLOCKED;
wifi_ap_record_t shared[kMaxShared];
uint16_t sharedCount = 0;
int64_t sharedAt = 0;

bool cacheFreshLocked(int64_t now) {
  return sharedCount > 0 && (now - sharedAt) < kFreshUs;
}

void rememberLocked(const wifi_ap_record_t *records, uint16_t count, int64_t now) {
  if (count == 0 || records == nullptr) return;
  uint16_t n = count > kMaxShared ? kMaxShared : count;
  std::memcpy(shared, records, n * sizeof(wifi_ap_record_t));
  sharedCount = n;
  sharedAt = now;
}
}  // namespace

extern "C" esp_err_t __real_esp_wifi_scan_get_ap_num(uint16_t *number);
extern "C" esp_err_t __real_esp_wifi_scan_get_ap_records(uint16_t *number, wifi_ap_record_t *ap_records);

extern "C" esp_err_t __wrap_esp_wifi_scan_get_ap_num(uint16_t *number) {
  esp_err_t err = __real_esp_wifi_scan_get_ap_num(number);
  if (err != ESP_OK || number == nullptr || *number != 0) return err;
  portENTER_CRITICAL(&scanMux);
  if (cacheFreshLocked(esp_timer_get_time())) *number = sharedCount;
  portEXIT_CRITICAL(&scanMux);
  return err;
}

extern "C" esp_err_t __wrap_esp_wifi_scan_get_ap_records(uint16_t *number, wifi_ap_record_t *ap_records) {
  if (number == nullptr || ap_records == nullptr) return ESP_ERR_INVALID_ARG;
  uint16_t live = 0;
  esp_err_t liveErr = __real_esp_wifi_scan_get_ap_num(&live);
  if (liveErr == ESP_OK && live == 0) {
    portENTER_CRITICAL(&scanMux);
    bool fresh = cacheFreshLocked(esp_timer_get_time());
    uint16_t n = 0;
    if (fresh) {
      n = *number < sharedCount ? *number : sharedCount;
      if (n > 0) std::memcpy(ap_records, shared, n * sizeof(wifi_ap_record_t));
    }
    portEXIT_CRITICAL(&scanMux);
    if (fresh) {
      *number = n;
      return ESP_OK;
    }
  }
  esp_err_t err = __real_esp_wifi_scan_get_ap_records(number, ap_records);
  if (err == ESP_OK && number != nullptr && *number > 0) {
    portENTER_CRITICAL(&scanMux);
    rememberLocked(ap_records, *number, esp_timer_get_time());
    portEXIT_CRITICAL(&scanMux);
  }
  return err;
}
