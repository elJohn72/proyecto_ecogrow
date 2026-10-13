# EcoGrow — sistema visual

Ámbito ECOGROW. Dirección: Utility & Function, base tinted, profundidad borders-only, espaciado 8px. Usuario: operador que necesita conectar una torre y entender agua, nutrientes y riego.

Tokens compartidos: `static/brand/palette.json`; Android: `EcoGrowTheme.kt`; web: variables en `static/style.css`. Verde bosque #195C3D para acciones/cultivo; turquesa #087F8C para agua; fondo #F7FAF7, superficie blanca; texto #172B22. Advertencia #946200 y error #B3261E acompañados siempre de texto/icono. Blanco sobre colores principales. No usar turquesa para afirmar conexión exitosa.

Espaciado: 8/16/24/32; radio 12 en controles, 16 en contenedores. Objetivos táctiles mínimos de 48dp en Android. Tipografía Material 3 existente y Plus Jakarta Sans en web. Valores numéricos alineados, SIN_DATO explícito, sin reemplazar lecturas desconocidas por ceros.

Logo: gota y brote de dos hojas, fondo transparente. Usar símbolo para favicon/launcher y símbolo + texto real EcoGrow para encabezados. El icono adaptativo Android coloca el símbolo dentro de su zona segura; no añadir texto a 16/32px.

La identidad visual no acredita el funcionamiento BLE ni corrige el contrato de datos. Hallazgos funcionales en docs/auditoria/REVISION_SEPTIMA_2026-10-13.md.
