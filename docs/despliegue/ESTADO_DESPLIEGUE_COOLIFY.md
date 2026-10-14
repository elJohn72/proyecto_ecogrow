# Estado de Despliegue en VPS Coolify (EcoGrow 2.0)

Ámbito: **ECOGROW**, **AISLADO**.

---

## 1. Identificación del Entorno de Producción / Staging

- **VPS:** Hostinger KVM2 Laboratorio Andrés Bello (`179.236.74.107`)
- **Orquestador:** Coolify
- **Endpoint Autorizado:** `https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io`
- **Regla Estricta:** Producción no se toca a mano bajo ninguna circunstancia. El servidor es el resultado exclusivo de un despliegue automatizado vía Git / Coolify.

---

## 2. Diagnóstico en Vivo (Revisión 10 - 2026-10-13)

Comprobación realizada mediante sondas HTTP seguras (OPTIONS y GET de lectura, sin modificar datos ni emitir órdenes de bomba):

| Ruta | Método | Código HTTP | Diagnóstico |
|---|---|---|---|
| `/health` | GET | **200 OK** | El contenedor y la base de datos están operativos |
| `/api/mobile/login` | OPTIONS | **200 OK** | Endpoint de login disponible |
| `/api/mobile/register` | OPTIONS | **404 Not Found** | Despliegue actual en VPS corresponde a versión previa a PR #6 |
| `/api/mobile/towers/bind` | OPTIONS | **404 Not Found** | Despliegue actual en VPS corresponde a versión previa a PR #6 |

---

## 3. Estado del Código en PR #6

En la rama `codex/ecogrow-audit-9-resolution` (PR #6):
1. **Rutas y API Móvil:**
   - `POST /api/mobile/register`: Creación de cuenta con bcrypt y sesión inmediata.
   - `POST /api/mobile/towers/bind`: Vinculación atómica verificando código y prueba de posesión PoP.
   - 102 pruebas unitarias automatizadas (`test_mobile.py`, `test_provision_device.py`, `test_migrate_identities.py`, etc.) pasando al 100%.
2. **Aplicación Android:**
   - Compilación exitosa en release/debug.
   - Sin opciones de servidor ni campos LAN; consume exclusivamente el endpoint centralizado HTTPS.
   - Estados de telemetría reales (distingue vinculación exitosa sin telemetría de telemetría confirmada en tiempo real).
3. **Firmware ESP32:**
   - Compilado y verificado en PlatformIO (`SUCCESS`).
   - Comando `ECOGROW:VERIFY_DEVICE_TOKEN:` para verificación de secreto sin exposición.
   - Auto-migración de códigos de prototipo (`TORRE-001`, `EG-TORRE-01`, `DUMMY`) a canónicos por MAC.

---

## 4. Procedimiento de Despliegue tras Aprobación

1. **Revisión y Aprobación:** Validar los checks del PR #6 en GitHub.
2. **Merge a `main`:** Fusionar la rama `codex/ecogrow-audit-9-resolution` en la rama `main`.
3. **Disparar Redeploy en Coolify:**
   - Acceder al panel de Coolify en el VPS Andrés Bello.
   - Ir a la aplicación EcoGrow Backend.
   - Pulsar el botón **Redeploy** (o dejar que el webhook de GitHub lo active automáticamente).
4. **Verificación Post-Despliegue:**
   Ejecutar la verificación de endpoints:
   ```bash
   curl -s -k -X OPTIONS -o /dev/null -w "%{http_code}\n" https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io/api/mobile/register
   curl -s -k -X OPTIONS -o /dev/null -w "%{http_code}\n" https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io/api/mobile/towers/bind
   ```
   Ambos deben responder `200`.
