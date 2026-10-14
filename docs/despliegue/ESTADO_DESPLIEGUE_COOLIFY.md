# Estado de despliegue EcoGrow en Coolify

Ámbito: **ECOGROW**, **AISLADO**.

## Destino autorizado

- VPS Hostinger KVM2 del laboratorio Andrés Bello: `179.236.74.107`
- Orquestador: Coolify, administración solo por túnel SSH
- Endpoint: `https://w3bmo8epk9iedi7gkqchdpru.179.236.74.107.sslip.io`

El servidor no se edita a mano. El camino es rama, pull request, checks verdes, merge autorizado y el redeploy de Coolify. Esta preparación no fusiona ni redespliega.

## Contraseñas

El registro y el cambio de clave usan `werkzeug.security.generate_password_hash` sin método explícito. En Werkzeug 3.1.5 el método por defecto es scrypt (`scrypt:32768:8:1`). La comprobación es `check_password_hash`. No es bcrypt.

## Comprobación del entorno desplegado

Sonda TLS con el paquete de CA de certifi. No se desactiva la verificación del certificado.

Fecha de la sonda previa a este cambio de código: 2026-10-13.

| Ruta | Método | Código | Lectura |
|---|---|---|---|
| `/health` | GET | 200 | `{"database":"connected","service":"ecogrow","status":"ok"}`, servidor gunicorn |
| `/api/mobile/login` | OPTIONS | 200 | La ruta de login existe en el despliegue actual |
| `/api/iot/sync` | OPTIONS | 200 | La ruta de sincronización existe en el despliegue actual |
| `/api/mobile/register` | OPTIONS | 404 | El despliegue no incluye el registro de PR #6 |
| `/api/mobile/towers/bind` | OPTIONS | 404 | El despliegue no incluye la vinculación de PR #6 |

Ese proceso no es el SHA de esta rama. Un APK compilado contra `/api/mobile/register` y `/api/mobile/towers/bind` no queda demostrado contra el VPS mientras esas rutas respondan 404. Health 200 no equivale a sesión, torre vinculada ni telemetría.

Volver a comprobar, con el mismo cliente TLS, después de un merge y redeploy autorizados:

- `/health`
- OPTIONS de `/api/mobile/register`, `/api/mobile/login` y `/api/mobile/towers/bind`
- un registro de prueba aislado, su sesión, el inventario, una vinculación y una sincronización en ese mismo entorno

La migración de identidades (`tools/migrate_identities.py`) se aplica en la base de ese despliegue solo con autorización, después de `--dry-run`. No se ensaya sobre la base del VPS desde el desarrollo.

## Lo que este código deja listo y lo que no

Listo en la rama, pendiente de autorización para llegar al VPS:

- registro, sesión y vinculación por PoP
- migración SQL sobre `dispositivos_iot.codigo_torre` y `torres.codigo_unico`
- aprovisionamiento con diario y reversión verificada
- firmware que no reescribe la identidad al leerla

Sigue pendiente aunque el CI esté verde:

- aceptación física: WiFi por BLE, primera telemetría, orden remota con ACK, reinicios, cambio de router y dos usuarios con dos torres
- merge y redeploy autorizados
- repetir la sonda anterior sobre el SHA ya desplegado
