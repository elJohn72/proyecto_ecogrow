#pragma once
#include <cmath>
inline bool safeWaterLevel(float percentage, bool calibrated) {
  return calibrated && std::isfinite(percentage) && percentage >= 10.0f && percentage <= 100.0f;
}
inline bool validRecipe(int index, int count) { return index >= 0 && index < count; }
