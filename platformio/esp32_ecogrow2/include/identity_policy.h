#pragma once

#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

// Política de identidad EcoGrow 2.0.
// Leer la identidad (arranque, sincronización o ECOGROW:IDENT?) no persiste
// un código nuevo. Solo un SET_CODE explícito de taller puede escribir NVS,
// y nunca acepta placeholders.

inline void ecogrowTrimUpper(const char* input, char* out, size_t outLen) {
  if (outLen == 0) return;
  out[0] = '\0';
  if (!input) return;
  while (*input && std::isspace(static_cast<unsigned char>(*input))) input++;
  size_t n = 0;
  while (input[n] != '\0' && n + 1 < outLen) {
    out[n] = static_cast<char>(std::toupper(static_cast<unsigned char>(input[n])));
    n++;
  }
  while (n > 0 && std::isspace(static_cast<unsigned char>(out[n - 1]))) n--;
  out[n] = '\0';
}

inline bool ecogrowIsPlaceholderCode(const char* code) {
  char norm[80];
  ecogrowTrimUpper(code, norm, sizeof(norm));
  if (norm[0] == '\0') return true;
  const size_t len = std::strlen(norm);
  if (len < 3 || len > 64) return true;
  static const char* blocked[] = {
      "TORRE-001",
      "EG-TORRE-01",
      "DUMMY",
      "PRUEBA",
      "TEST",
      "IDENTIFICADOR_TECNICO",
      nullptr};
  for (int i = 0; blocked[i] != nullptr; i++) {
    if (std::strcmp(norm, blocked[i]) == 0) return true;
  }
  return false;
}

inline bool ecogrowCodeIsValid(const char* code) {
  return !ecogrowIsPlaceholderCode(code);
}

// Consultar IDENT, arrancar o sincronizar no debe guardar otro código.
inline bool ecogrowIdentityReadPersists() { return false; }

// SET_CODE solo persiste un código que ya es válido y no es placeholder.
inline bool ecogrowExplicitSetMayPersist(const char* newCode) {
  return ecogrowCodeIsValid(newCode);
}

inline void ecogrowSuggestCodeFromMac(const uint8_t mac[6], char* out, size_t outLen) {
  if (!out || outLen == 0) return;
  std::snprintf(out, outLen, "EG-TORRE-%02X%02X%02X", mac[3], mac[4], mac[5]);
}
