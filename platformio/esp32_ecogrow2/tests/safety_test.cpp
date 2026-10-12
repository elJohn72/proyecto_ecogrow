#include "safety.h"
#include <cassert>
#include <limits>
int main() {
  assert(!safeWaterLevel(85, false));
  assert(!safeWaterLevel(std::numeric_limits<float>::quiet_NaN(), true));
  assert(!safeWaterLevel(std::numeric_limits<float>::infinity(), true));
  assert(!safeWaterLevel(9.99f, true));
  assert(safeWaterLevel(10, true));
  assert(!safeWaterLevel(101, true));
  assert(validRecipe(0,4)); assert(validRecipe(3,4));
  assert(!validRecipe(-1,4)); assert(!validRecipe(4,4));
}
