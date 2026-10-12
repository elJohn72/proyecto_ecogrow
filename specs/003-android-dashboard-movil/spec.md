# EcoGrow: Android nativo y dashboard móvil

Fecha: 2026-10-12. Estado: BORRADOR PARA REVISIÓN DE JOHN.
Ámbito: ECOGROW. Modo: AISLADO. Sin cruce de datos con otras marcas.

## Objetivo y solicitud confirmada

John solicita una aplicación nativa Android para controlar las nuevas mejoras
de EcoGrow y, adicionalmente, un dashboard para móvil. El inventario de esas
mejoras y si el dashboard es web o está dentro de la app requieren respuesta.
Este documento especifica una propuesta; no representa software implementado.

## Evidencia del sistema actual

Repositorio: https://github.com/elJohn72/proyecto_ecogrow.
Checkout inspeccionado: `~/Repositorios Githup/03-proyectos/proyecto_ecogrow`.
Base inspeccionada: `da94b71`, rama `main`, sin cambios locales antes de esta spec.
La ficha AJENZA aún apunta a una carpeta distinta; usar el checkout verificado.

- Backend Flask 3.1.2, Flask-Login 0.6.3, MySQL/MariaDB y plantillas Jinja.
- `/dashboard`: panel autenticado de una torre seleccionada.
- `/sensores`: monitoreo y formularios de control del relé.
- `POST /monitoreo/rele/<torre_id>` valida propietario y CSRF; devuelve redirección HTML.
- `POST /api/iot/sync` recibe telemetría y estado reportado; devuelve control al dispositivo.
- `platformio/esp32_rele_base/README.md`: sincronización HTTP cada 10 segundos
  configurable, con apagado por pérdida de WiFi/API.
- La visión multi-torre de AJENZA describe MQTT, pero las rutas y el firmware
  revisados usan HTTP. La app no depende de una migración a MQTT.
- `tests/test_app.py` contiene pruebas unittest. No hay workflow en el checkout
  inspeccionado. La implementación necesitará definir sus checks verificables.

## Supuestos visibles y preguntas pendientes

1. Propuesta: dos clientes, app Android y dashboard web responsive adicional.
   PENDIENTE_CONFIRMAR con John.
2. Ambos consumen el mismo backend y permisos, sin duplicar reglas agronómicas.
3. MVP propuesto: torres, sensores, bomba, alertas e historial.
   Inventario definitivo: PENDIENTE_DATOS de las nuevas mejoras.
4. Control mediante internet/API. Bluetooth, BLE, conexión directa WiFi y
   aprovisionamiento del ESP32 no están confirmados.
5. Modelo Android y versión mínima: PENDIENTE. URL real del backend y
   entorno de prueba con hardware: PENDIENTE. No inventar dominios ni cuentas.
6. Notificaciones en segundo plano: requisito y proveedor PENDIENTE.
7. Especificación, plan y tareas requieren revisión antes de implementación.

## Tecnología propuesta

Android: Kotlin y Jetpack Compose, ViewModel y StateFlow para estado de pantalla.
Interfaz realmente nativa, sin encapsular la web en WebView. Versiones de Kotlin,
AGP, Gradle, Compose, JDK y SDK se fijarán como conjunto compatible en el plan.
No seleccionar versiones por memoria ni añadir dependencias antes de revisar el plan.

Web: extender Flask/Jinja, CSS y JavaScript existentes. Conservar MySQL como
fuente de verdad. API JSON versionada para los clientes; las rutas sugeridas
abajo todavía no existen.

Referencias oficiales:
- https://developer.android.com/develop/ui/compose/first
- https://developer.android.com/topic/architecture/data-layer/offline-first

## Experiencia y pantallas propuestas

- Inicio: torres autorizadas, estado de conexión, alertas y última actualización.
- Detalle de torre: pH, EC, nivel, temperaturas, humedad y luminosidad solo
  cuando el hardware y la API proporcionen la lectura correspondiente.
- Control: estado reportado de bomba, orden solicitada y resultado independiente.
- Cultivo: ciclo/fase activa y rangos que derive el backend.
- Historial: lecturas y eventos con fecha, unidades y filtros.

Toda pantalla contempla carga, vacío, fallo, sesión caducada y lectura antigua.
Mostrar `SIN_DATO` si falta una medición; nunca convertir ausencia en cero ni
mostrar que un dispositivo está conectado por el mero hecho de tener datos guardados.

El dashboard web debe funcionar desde 360 px sin desplazamiento horizontal,
con navegación accesible y controles táctiles de al menos 48 px. En Android,
usar semántica accesible, tamaños táctiles equivalentes y escalado de texto.

## Contrato propuesto y límites del control

Separar autenticación de usuarios y de dispositivos. El token de sensores
actual nunca se incluye en el APK ni en el JavaScript del navegador.
Diseño de sesión móvil, revocación y protección local: a concretar en el plan.

Propuesta de recursos JSON versionados:
- sesión de usuario;
- lista de torres y detalle por identificador explícito;
- última lectura e historial por torre;
- alertas por torre;
- solicitud de comando y consulta de su resultado.

Cada recurso comprueba autorización sobre la torre en el servidor. Respuestas
JSON coherentes para 400, 401, 403/404 y conflictos, sin redirecciones HTML en API.
Mantener CSRF en el cliente web y en cualquier autenticación basada en cookies.

Los comandos distinguen solicitado, pendiente, confirmado, rechazado y vencido.
Una respuesta HTTP exitosa del backend no confirma actuación física. Definir
identificador, caducidad, idempotencia y acuse de dispositivo antes de habilitar
control nativo. Verificar cómo ampliar el protocolo HTTP existente sin romperlo.

El cliente no envía órdenes sin conexión ni las acumula para ejecutarlas después.
Puede mostrar la última lectura con su antigüedad. Nivel crítico, tiempo máximo
de bomba y demás bloqueos físicos requieren protección local verificada; una
pantalla o validación remota no sustituye el failsafe del ESP32.

Dosificación, iluminación y actuadores adicionales quedan PENDIENTE_CONFIRMAR.
La IA sigue siendo asesora y no puede saltarse protecciones deterministas.

## Estructura prevista

```text
android/                         # Proyecto nativo propuesto, aún no creado
blueprints/                      # API y rutas Flask
services/                        # Reglas compartidas, sin duplicación por cliente
templates/dashboard.html         # Panel web móvil
static/                          # Estilos y actualización de interfaz
tests/test_app.py                # Regresión backend existente
specs/003-android-dashboard-movil/# Especificación; luego plan y tareas revisados
```

## Estilo de código

Seguir capas de la constitución: blueprints → servicios/modelos → datos.
Python mantiene convenciones existentes. Kotlin usa clases PascalCase, funciones
camelCase y estado explícito; por ejemplo, este contrato ilustrativo sin datos reales:

```kotlin
data class TowerUiState(
    val isLoading: Boolean = false,
    val lastReadingAt: String? = null,
    val commandPending: Boolean = false,
    val errorMessage: String? = null,
)
```

## Comandos y entorno

Comandos actuales documentados, no ejecutados para este cambio de documentación:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m flask --app app run
git diff --check
```

Comandos Android previstos después de crear y verificar Gradle Wrapper:

```bash
cd android
./gradlew --no-daemon lintDebug testDebugUnitTest assembleDebug
./gradlew --no-daemon connectedDebugAndroidTest
```

El plan debe fijar runtime y dependencias reproducibles, base MySQL temporal,
emulador/Android físico y comandos definitivos de CI. No declarar estos comandos
Android disponibles hoy ni build validado hasta generar y probar el proyecto.

## Estrategia de pruebas y criterios de éxito

- Mantener regresión unittest y probar sesión, CSRF, expiración, validación y
  acceso cruzado a torres ajenas en API y web.
- Pruebas de contrato para lectura ausente/antigua, unidades y errores JSON.
- Probar comandos repetidos, vencidos, dispositivo offline y rechazo por nivel.
- Pruebas Android de ViewModel y UI: carga, fallo, pérdida de red y sesión.
- Flujo real: login → torre autorizada → lectura → orden → estado confirmado.
- Probar con una torre física, desconectar WiFi y comprobar estado seguro.
  Mientras no haya hardware disponible, marcar evidencia física PENDIENTE.
- Validar web a 360, 390 y 430 px, texto ampliado y navegación accesible.
- Entregar APK de prueba instalado y verificado en el Android acordado,
  dashboard probado y evidencia de checks del HEAD final.

## Fronteras

Siempre: respetar ECOGROW, no inventar datos, proteger permisos por torre,
identificar lecturas antiguas, probar antes de entregar y versionar solo archivos propios.

Revisar con John: esta spec, inventario de mejoras, plan y tareas; migración del
esquema necesaria para comandos/sesiones; requisitos de acceso local y avisos.
Merge y deploy requieren su autorización independiente.

Nunca: secretos en APK/git/chat, usar cuentas de otra marca, actuar sobre hardware
real sin un entorno de prueba acordado, editar producción manualmente o presentar
una orden pendiente como actuación confirmada.

## Próxima fase

Tras las respuestas y revisión de John, concretar el alcance, generar `plan.md`
y `tasks.md` y validar el plan antes de implementar conforme a Spec Kit.
