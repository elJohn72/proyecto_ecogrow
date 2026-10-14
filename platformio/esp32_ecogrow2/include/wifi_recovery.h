#pragma once

#include <cstdint>

// Si la red guardada no responde, la torre vuelve a anunciarse por Bluetooth
// para elegir otra desde el teléfono. El PIN y el código de la torre no se tocan.
// Un corte breve no debe borrar la red: solo después de este tiempo sin IP,
// y nunca mientras el teléfono ya está en la configuración Bluetooth.
inline uint32_t ecogrowWifiLostBeforeBleMs() { return 60000; }

inline bool ecogrowShouldReopenBle(bool bleActive, bool wifiReady, uint32_t downForMs) {
  if (bleActive || wifiReady) return false;
  return downForMs >= ecogrowWifiLostBeforeBleMs();
}

// El fin del aprovisionamiento Bluetooth no es una caída de WiFi.
// Si ya hay IP, no se arma el temporizador que a los 60 s borra la red.
struct EcogrowLink {
  bool bleActive;
  bool wifiReady;
  uint32_t wifiDownSince;
};

inline void ecogrowNoteGotIp(EcogrowLink& link) {
  link.wifiReady = true;
  link.wifiDownSince = 0;
}

inline void ecogrowNoteStaDown(EcogrowLink& link, uint32_t nowMs) {
  link.wifiReady = false;
  if (link.wifiDownSince == 0) link.wifiDownSince = nowMs == 0 ? 1 : nowMs;
}

inline void ecogrowNoteProvStart(EcogrowLink& link) {
  link.bleActive = true;
}

inline void ecogrowNoteProvEnd(EcogrowLink& link) {
  link.bleActive = false;
}
