# Identidad EcoGrow

Ámbito ECOGROW. Recursos creados por solicitud de John el 2026-10-13. Concepto: gota de agua con brote de dos hojas, para cultivo hidropónico y control del agua. PNG con alfa real, sin texto; encabezados mantienen EcoGrow como texto accesible.

## Recursos integrados

- `static/brand/ecogrow-symbol.png`: maestro raster transparente.
- `ecogrow-32.png`, `favicon.ico`: favicon web; 192/512 para reutilización.
- `android/app/src/main/res/drawable-nodpi/ecogrow_symbol.png`: símbolo Compose.
- `mipmap-*/ic_launcher.png` y `mipmap-anydpi-v26/ic_launcher.xml`: launcher y adaptación de máscaras Android.
- `static/brand/palette.json`: tokens; `EcoGrowTheme.kt`: Material 3; `.interface-design/system.md`: criterios de uso.
- `templates/base.html`: favicon, touch icon, theme-color y encabezado.

## Paleta

| Uso | HEX | Contraste sobre blanco |
|---|---|---|
| Verde cultivo / acción principal | #195C3D | 7.96:1 |
| Agua / acción secundaria | #087F8C | 4.75:1 |
| Fondo | #F7FAF7 | — |
| Texto | #172B22 | 14.21:1 sobre fondo |
| Aviso | #946200 | 5.24:1 |
| Error | #B3261E | 6.54:1 |

Los colores semánticos siempre llevan etiqueta: conexión verificada, pendiente, lectura caducada o error. No usar un color como única señal. Los colores son tokens exactos de UI; el PNG generado puede incluir suavizado y variaciones de tono.

## Generación

Herramienta: image_gen integrada, modo logo-brand; una generación y una corrección de limpieza. Exportación de tamaños y formatos desde el raster, sin redibujar identidad ni crear variantes ajenas.

Prompt final: «Clean up this EcoGrow logo for actual app icon production. Preserve the droplet and two-leaf silhouette and transparent background. Remove the obvious dark/green smudge/artifact in lower left completely. Replace all gradient, texture and shading with perfectly uniform solid color fills: teal #087F8C upper droplet, forest green #195C3D lower leaves/stem. Smooth crisp geometric vector-like edges. No highlights, shadows, grain, extra shapes or lettering. Keep transparent negative-space leaf openings. Keep entire shape centered inside square with at least 10 percent transparent padding on each side, particularly bottom; whole logo must fit in the safe central area.»

## Validación

PNG RGBA con alfa 0–255; favicon PNG 32, ICO 16/32/48; exportaciones 192/512. Plantilla Jinja parseada, 19 pruebas test_app y 19 test_provision_device pasan localmente. Android lint/unit/build ejecutados tras integrar recursos. No merge ni deploy; no se modificó firmware ni credenciales.
