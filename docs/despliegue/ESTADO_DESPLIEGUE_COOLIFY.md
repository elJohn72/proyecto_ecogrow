# Estado de despliegue EcoGrow en Coolify

Ámbito: **ECOGROW**, **AISLADO**.

## Destino autorizado

- VPS Hostinger KVM2 del laboratorio Andrés Bello: `179.236.74.107`
- Orquestador: Coolify, administración solo por túnel SSH
- Endpoint: `https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io`

El servidor no se edita a mano. El camino es rama, pull request, checks verdes, merge autorizado y el redeploy de Coolify.

## Contraseñas

El registro y el cambio de clave usan `werkzeug.security.generate_password_hash` sin método explícito. En Werkzeug 3.1.5 el método por defecto es scrypt (`scrypt:32768:8:1`). La comprobación es `check_password_hash`. No es bcrypt.

## Comprobación del entorno desplegado

Sonda TLS con el paquete de CA de certifi. No se desactiva la verificación del certificado.

Fecha de la sonda posterior al redeploy: 2026-10-13, 23:58 hora local. El proceso en Coolify es el commit `3567f19e3aea545d9b352aa42ba6bb075f76dc92` (`main`), que incluye `44cde1c`. El contenedor de la aplicación quedó healthy. La base `ecogrow-db` no se reemplazó.

| Ruta | Método | Código | Lectura |
|---|---|---|---|
| `/health` | GET | 200 | `{"database":"connected","service":"ecogrow","status":"ok"}`, servidor gunicorn |
| `/api/mobile/login` | OPTIONS | 200 | La ruta de login existe |
| `/api/mobile/register` | OPTIONS | 200 | La ruta de registro existe |
| `/api/mobile/towers/bind` | OPTIONS | 200 | La ruta de vinculación existe |
| `/api/iot/sync` | OPTIONS | 200 | La ruta de sincronización existe |

Comprobación en ese mismo entorno, con TLS verificado:

- Un registro aislado `PRUEBA` creó la sesión y respondió 201.
- `GET /api/mobile/towers` respondió 200 con cero torres para esa sesión.
- Vincular un código inexistente respondió 404 `unregistered_device`. No se creó una torre.
- `POST /api/iot/sync` sin token respondió 401.
- Esa cuenta de prueba se eliminó después. No había dispositivos ni códigos placeholder en el inventario.

Un push a `main` que toque la aplicación ejecuta `.github/workflows/deploy.yml`. Ese job entra por SSH con una clave que solo puede encolar el redeploy de `ecogrow-app` y espera a que Coolify lo termine. El panel administrativo sigue cerrado. Si el secreto `ECOGROW_DEPLOY_SSH_KEY` no está en GitHub, el job falla en vez de marcar un éxito vacío.

## Lo que este despliegue no demuestra

Sigue pendiente la aceptación física: WiFi por BLE, primera telemetría, orden remota con ACK, reinicios, cambio de router y dos usuarios con dos torres. Health 200 no equivale a telemetría ni a una torre vinculada.
