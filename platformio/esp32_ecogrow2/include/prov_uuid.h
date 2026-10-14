#pragma once

#include <cstdint>
#include <cstdio>

// UUID little-endian que WiFiProv anuncia por BLE.
// El valor por defecto de Arduino-ESP32 cambia el cuarto byte a 0x1c
// (021a9004-0382-4aea-bff4-6b3f1c5adfb4). La app busca el servicio
// Espressif 021a9004-0382-4aea-bff4-6b3f1b5adfb4. Si no coinciden, el
// teléfono ve el nombre PROV_EcoGrow y luego falla el enlace GATT.
static const uint8_t ECOGROW_PROV_SERVICE_UUID_LE[16] = {
    0xb4, 0xdf, 0x5a, 0x1b, 0x3f, 0x6b, 0xf4, 0xbf,
    0xea, 0x4a, 0x82, 0x03, 0x04, 0x90, 0x1a, 0x02,
};

inline void ecogrowProvServiceUuidString(char out[37]) {
    const uint8_t *b = ECOGROW_PROV_SERVICE_UUID_LE;
    std::snprintf(
        out,
        37,
        "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
        b[15], b[14], b[13], b[12],
        b[11], b[10],
        b[9], b[8],
        b[7], b[6],
        b[5], b[4], b[3], b[2], b[1], b[0]);
}
