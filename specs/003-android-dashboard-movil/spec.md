# EcoGrow: Android nativo y dashboard móvil

Fecha: 2026-10-12. Estado: CONSTRUCCIÓN Y DESPLIEGUE EN COOLIFY COMPLETADOS; PR #2 ABIERTO Y VERIFICADO.
Ámbito: ECOGROW. Modo: AISLADO. Sin cruce de datos con otras marcas.

## Objetivo y solicitud confirmada

John solicita una aplicación nativa Android para controlar las nuevas mejoras
de EcoGrow y, adicionalmente, un dashboard para móvil. John confirmó el
2026-10-12 que quiere app Android y dashboard web móvil como dos clientes.
John indicó usar las especificaciones que se han estado mejorando. Se recuperó
la propuesta EcoGrow 2.0 de octubre desde Drive y se toma como alcance funcional.
La solicitud actual confirma dashboard web y aplicación Android nativa separados.
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

## Fuente funcional recuperada: EcoGrow 2.0

Documentación de octubre consultada en Drive con ámbito ECOGROW:
- [Índice técnico](https://drive.google.com/file/d/1qQLoBmJQDn9g5sQvJ6qzT2UXkbP1Nqlq/view).
- [Informe 2.0](https://drive.google.com/file/d/1bHYb6RwYn39ULubnTk82PVVC4QxEbzAn/view).
- [Validación de hardware](https://drive.google.com/file/d/19D69HaJv1DRnYn8Y_yBytZl1bzkmhSWw/view).
- [Manual de puesta en marcha](https://drive.google.com/file/d/11PO2ZVGV8J3YaLdZRGgCt2zoV6Pdptu5/view).

El informe describe un prototipo con servidor web local en ESP32, almacenamiento
NVS y acceso por WiFi AP/LAN. La documentación marca las pruebas físicas como
PENDIENTE_MONTAJE: especificar el hardware no demuestra que esté instalado.

| Mejora documentada | Función en web y Android |
| --- | --- |
| Nivel ultrasónico JSN-SR04T | Porcentaje y litros del depósito; estado/calibración |
| TDS analógico con compensación térmica | Lectura en ppm y comparación con receta |
| pH | Lectura y rango de la receta activa |
| Temperatura de agua DS18B20 | Lectura en °C y estado de sensor |
| Bomba y cascada | Control manual/automático, estado y temporizador riego/reposo |
| Recetas en NVS | Lechuga, espinaca, albahaca y frutilla/fresa según fuente 2.0 |
| Protección de bomba por nivel | Mostrar bloqueo local por nivel inferior al 10% |
| WiFi AP/LAN | Acceso local a la torre sin depender de WAN |

Los valores de receta son parámetros documentados pendientes de validación
agronómica; no se presentan como mediciones. Litros requieren geometría/capacidad
calibradas, no asumir que todo tanque tiene 30 L. TDS ppm y EC mS/cm son magnitudes
distintas: no renombrar el campo EC legacy como TDS ni convertir sin factor conocido.
El umbral local 2.0 y los perfiles Flask deben reconciliarse; no reemplazar límites
en dispositivos reales desde una pantalla.

El informe 2.0 elimina DHT22, boya duplicada y buzzer del núcleo. Iluminación y
dosificación figuran en fases posteriores del roadmap: no habilitar sus comandos
sin capacidad declarada y validada. La interfaz base prioriza los cuatro sensores
del depósito y la bomba, sin mostrar ambiente como equipo instalado.

El archivo `firmware_ecogrow2.ino` existe en Drive. El conector rechazó su lectura
por MIME `application/octet-stream`; no se inspeccionó el contrato de rutas JSON.
Obtener ese código con un mecanismo compatible antes de afirmar integración 2.0.
No copiar contraseñas WiFi de los documentos a esta spec ni al APK.

El SDD de julio reserva 003 para MQTT y 004–007 para otros frentes. El nombre
003-android-dashboard-movil se creó antes de recuperar ese SDD; mantener esta
carpeta como identificador de esta rama y no sobrescribir aquellas especificaciones.

## Decisiones y dependencias pendientes

1. CONFIRMADO por John: dos clientes, app Android y dashboard web responsive adicional.
2. Ambos consumen el mismo backend y permisos, sin duplicar reglas agronómicas.
3. Alcance: las mejoras 2.0 de la tabla anterior; torres, alertas e historial
   se extienden sobre el backend actual cuando exista almacenamiento real.
4. Acceso local WiFi AP/LAN basado en documentación 2.0 y acceso al backend web.
   Recuperar contrato firmware y definir emparejamiento antes del control local.
   Bluetooth BLE CONFIRMADO por John para aprovisionamiento inicial y cambio de red WiFi del ESP32.
   El control y monitoreo continuo se realiza por WiFi/HTTP; BLE se reserva para aprovisionamiento.
5. VPS de pruebas Hostinger (kv2) CONFIRMADO por John para alojar el backend y dashboard web
   con aislamiento de contenedores (Docker), base de datos de prueba, HTTPS y health checks.
   La app Android consumirá la API HTTPS de dicho VPS de pruebas.
6. Notificaciones en segundo plano: requisito y proveedor PENDIENTE.
7. John aprobó el alcance y el plan incorporando aprovisionamiento WiFi vía BLE y despliegue en VPS kv2.

## Tecnología propuesta

Android: Kotlin y Jetpack Compose, ViewModel y StateFlow para estado de pantalla.
Interfaz realmente nativa, sin encapsular la web en WebView. Versiones de Kotlin,
AGP, Gradle, Compose, JDK y SDK se fijarán como conjunto compatible en el plan.
No seleccionar versiones por memoria ni añadir dependencias antes de revisar el plan.

Web: dashboard Flask/Jinja responsive para navegador de escritorio y teléfono.
Conservar MySQL en el sistema actual y NVS como configuración local del ESP32.
API/adaptadores con representación común para ambos clientes. Una web alojada
remotamente no debe consultar directamente una IP privada del ESP32: usar el
panel servido localmente o un enlace edge/backend autorizado. El modo remoto
requiere conectividad del dispositivo con el backend; no lo da una IP AP privada.

Referencias oficiales:
- https://developer.android.com/develop/ui/compose/first
- https://developer.android.com/topic/architecture/data-layer/offline-first

## Experiencia y pantallas propuestas

- Inicio: torres autorizadas, estado de conexión, alertas y última actualización.
- Detalle de torre 2.0: pH, TDS ppm, nivel %, litros y temperatura de agua;
  EC se muestra por separado solo si el origen identifica unidad/factor.
- Control: estado reportado de bomba, orden solicitada y resultado independiente.
- Cultivo: receta activa, ciclo/fase y rangos, con procedencia y configuración
  confirmada por dispositivo; conservar los perfiles del backend existente.
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

El cliente no envía órdenes sin conexión al destino ni las acumula para después.
Sin internet pero con WiFi local, puede controlar una torre emparejada mediante
su API local validada. Distinguir ausencia de WAN de pérdida de enlace con la torre.
Puede mostrar la última lectura con su antigüedad. Nivel crítico, tiempo máximo
de bomba y demás bloqueos físicos requieren protección local verificada; una
pantalla o validación remota no sustituye el failsafe del ESP32.

Dosificación, iluminación y actuadores adicionales permanecen en fases futuras
del roadmap y se habilitan solo con capacidades/protocolo verificados.
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

## Aprovisionamiento WiFi mediante Bluetooth BLE

El objetivo es permitir configurar y cambiar la red WiFi del ESP32 desde la app Android
sin necesidad de flashear nuevamente el microcontrolador ni usar cables.

### Flujo de aprovisionamiento
1. **Fase de Anuncio BLE:** Al no disponer de WiFi conectada o al activarse manualmente,
   el ESP32 inicia anuncios BLE con el servicio oficial de aprovisionamiento (nombre `PROV_EcoGrow_XXXX`).
2. **Descubrimiento en Android:** La pantalla «Configurar WiFi de la torre» en Android realiza
   escaneo BLE filtrando dispositivos EcoGrow y solicita permisos Bluetooth (`BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `ACCESS_FINE_LOCATION`).
3. **Vinculación Segura (Proof of Possession - PoP):** Se establece la sesión BLE segura
   verificando un PIN/PoP de confirmación de posesión física.
4. **Escaneo de Redes:** El ESP32 escanea las redes WiFi disponibles en su entorno y
   devuelve la lista de SSIDs detectados a la aplicación móvil vía BLE.
5. **Envío de Credenciales:** El usuario selecciona el SSID, escribe la contraseña y Android
   transmite las credenciales cifradas al ESP32.
6. **Conexión y Persistencia:** El ESP32 almacena las credenciales en memoria NVS, se asocia
   a la red WiFi y reporta a Android su estado y la dirección IP obtenida.
7. **Liberación de Memoria:** Al completarse la conexión exitosa, el ESP32 detiene el anuncio BLE
   y libera la memoria Bluetooth para garantizar la estabilidad de los ciclos de cultivo.
8. **Recuperación física:** Pulsación prolongada (5 segundos) en el botón físico de la torre
   (GPIO 0 / BOOT) borra las credenciales WiFi y reinicia el modo de aprovisionamiento BLE.

## Despliegue en VPS de Pruebas Hostinger (kv2)

El backend de EcoGrow y el dashboard web se alojan en el VPS de pruebas «kv2» de Hostinger.

### Arquitectura en VPS
- **Aislamiento en Contenedores:** Despliegue mediante `docker-compose.yml` aislando la aplicación
  Flask (con Gunicorn), la base de datos MySQL (con volumen `ecogrow_data_vps` persistente) y un proxy
  inverso Caddy/Nginx para terminación TLS/HTTPS automática.
- **Sin colisión:** Asignación de puertos y nombres de contenedor aislados (`ecogrow-app`, `ecogrow-db`)
  para no interferir con otros servicios que puedan coexistir en kv2.
- **Datos de prueba:** Entorno configurado exclusivamente con datos marcados `PRUEBA`.
- **Salud y Rollback:** Endpoint `/health` verificado tras el despliegue; si el contenedor falla en
  arrancar o responder, el script de despliegue restaura la versión anterior.
- **Workflow CI/CD:** Despliegue automatizado mediante `.github/workflows/deploy.yml` vía SSH
  usando secretos en el repositorio (`HOSTINGER_SSH_HOST`, `HOSTINGER_SSH_USER`, `HOSTINGER_SSH_KEY`).
  Las credenciales reales nunca se versionan en Git.

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

El plan está aprobado. Otro agente debe leer `HANDOFF_OTRO_AGENTE.md`, concretar
`tasks.md`, completar y corregir el WIP y ejecutar las verificaciones del plan.
