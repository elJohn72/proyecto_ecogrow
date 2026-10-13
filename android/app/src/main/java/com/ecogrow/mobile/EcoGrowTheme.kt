package com.ecogrow.mobile

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Tokens compartidos con static/brand/palette.json.
private val EcoGrowColors = lightColorScheme(
    primary = Color(0xFF195C3D), onPrimary = Color.White,
    primaryContainer = Color(0xFFD8EEDB), onPrimaryContainer = Color(0xFF072113),
    secondary = Color(0xFF087F8C), onSecondary = Color.White,
    background = Color(0xFFF7FAF7), onBackground = Color(0xFF172B22),
    surface = Color.White, onSurface = Color(0xFF172B22),
    surfaceVariant = Color(0xFFEEF3EE), onSurfaceVariant = Color(0xFF4C6652),
    outline = Color(0xFF718077), error = Color(0xFFB3261E)
)

@Composable
fun EcoGrowTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = EcoGrowColors, content = content)
}
