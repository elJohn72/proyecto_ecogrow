# Plan técnico: dashboard web y Android nativo EcoGrow 2.0

Fecha: 2026-10-12. Estado: CONSTRUCCIÓN Y DESPLIEGUE EN COOLIFY COMPLETADOS; PR #2 ABIERTO Y VERIFICADO.
Solicitud confirmada: dos entregables, sobre las especificaciones EcoGrow 2.0.

## Resultado previsto

Dashboard web responsive del sistema EcoGrow y aplicación Android nativa Kotlin/
Compose. Ambas interfaces cubren nivel %, litros, TDS ppm, pH, temperatura de agua,
bomba, temporizador de cascada/reposo, recetas y alertas según capacidad disponible.
La actuación segura permanece local al ESP32.

## Orden y verificaciones

1. Recuperar y auditar `firmware_ecogrow2.ino` del paquete técnico de octubre.
   Verificar rutas, payloads, autenticación, persistencia NVS, errores de sensores,
   failsafe y compatibilidad con el código HTTP que sí está en GitHub.
   Entrega: matriz protocolo/función con evidencia de código, sin credenciales.
   El conector Drive actual no extrae texto de su MIME binario; no adivinar rutas.

2. Definir contrato común y adaptadores backend/local. Diferenciar TDS y EC,
   capacidad calibrada, tiempo del dispositivo, antigüedad, estado deseado y
   reportado, bloqueos y receta versionada. Mantener propietarios por torre.
   Acceso local autenticado/emparejado; sin tokens de dispositivo incrustados.
   Entrega: contrato revisable y pruebas de autorización/error con datos PRUEBA.

3. Implementar API JSON sobre servicios Flask. Añadir solo cambios de esquema
   necesarios y migraciones probadas en base temporal, sin tocar producción.
   Preservar rutas HTML y firmware actual hasta verificar adaptación 2.0.
   Verificación: unittest, permisos por torre, CSRF, validación e idempotencia.

4. Implementar dashboard web responsive. Resumen, detalle, control, receta y
   eventos. Navegación para escritorio y teléfono, carga/vacío/error/offline,
   última actualización, fuente local/remota y comandos pendientes/confirmados.
   Verificación: navegador a 360/390/430 px y escritorio; flujo real contra API.

5. Crear proyecto Android Kotlin/Compose con versiones reproducibles de JDK,
   SDK, AGP y Gradle Wrapper verificadas. ViewModels y repositorio por destino
   local/remoto; conexión explícita a torre, refresco y caché de solo lectura.
   Incorporar módulo de aprovisionamiento WiFi mediante BLE: escaneo de dispositivos
   EcoGrow, vinculación segura por Proof of Possession (PoP), escaneo de redes WiFi,
   envío de credenciales y reporte de estado de conexión.
   Borrar datos privados al cerrar sesión/cambiar cuenta. No guardar claves
   en preferencias abiertas. Política de tráfico local acotada y HTTPS remoto.
   Verificación: lint, tests de estado/contrato, APK, emulador y dispositivo real.

6. Integrar y probar con ESP32. Soporte de aprovisionamiento WiFi por BLE oficial
   (Espressif WiFiProv) con persistencia NVS y liberación de memoria Bluetooth tras conexión.
   Botón físico de recuperación (GPIO 0 presionado 5s).
   Recetas/configuración reflejan la respuesta del dispositivo. Cortar WAN y luego enlace local;
   comprobar que los clientes distinguen ambas situaciones y no reenvían comandos caducados.
   Probar sensor de nivel inválido/bajo y reinicio. No confundir GPIO activado con caudal real.
   Entrega: evidencia de actuación, estados seguros y limitaciones pendientes.

7. Despliegue en VPS de pruebas Hostinger (kv2). Preparar configuración de contenedores
   (Docker Compose) aislando app Flask, MySQL y proxy inverso con HTTPS.
   Configurar healthchecks (/health), registros sin secretos y script/workflow de rollback.
   Definir workflow de despliegue automatizado en GitHub Actions usando secretos SSH.

8. Revisión final de UI, seguridad y lógica. Commit/push y PR del HEAD final;
   checks completos antes de marcar listo para revisión humana. Merge/deploy y
   activación sobre hardware operativo necesitan autorización correspondiente.

## Decisiones de integración que resuelve el paso 1

- Ruta real y esquema de API local 2.0, actualmente no inspeccionados.
- Cómo se enlaza la torre 2.0 con el backend existente sin perder modo autónomo.
- Compatibilidad entre recetas NVS y perfiles de fase Flask.
- Estado y acuse del mando de bomba, mediciones inválidas y calidad del dato.
- Emparejamiento y autorización local; topología real para web remota.

No migrar a MQTT/PostgreSQL ni añadir LoRa para fabricar el cliente Android:
son trabajos separados del SDD previo, con evaluación propia. Diseñar adaptadores
para que puedan incorporarse después conservando contrato de interfaz.

## Entrega verificable

- URL de dashboard en entorno de prueba autorizado, usable en web y móvil.
- APK Android nativo compilado, instalado y recorrido de funciones verificado.
- Pruebas backend/Android y evidencia de lectura/control con torre real.
- PR correcto y checks obligatorios del HEAD final verdes.

Este plan no afirma que exista aún un APK, API 2.0 integrada o dashboard nuevo.
El agente constructor desglosa los pasos aprobados en tareas con archivos y
comandos definitivos y continúa el ciclo autónomo hasta completar los gates.
