# Guía de Despliegue en VPS Hostinger kv2 (EcoGrow)

Esta guía detalla los pasos para alojar el backend, el dashboard web responsive y la API móvil de EcoGrow en el VPS de pruebas Hostinger (`kv2`), garantizando aislamiento y seguridad.

---

## 1. Topología del Despliegue

```text
[ Internet / Clientes ]
       │
       ▼  (Puertos 80 y 443 - HTTPS)
┌───────────────────────────────────────────────┐
│ Hostinger VPS kv2 (Ubuntu 24.04 LTS)          │
│                                               │
│ ┌───────────────────────────────────────────┐ │
│ │ Proxy Reverso Caddy (caddy:2.8-alpine)    │ │
│ │ • Terminación TLS automática              │ │
│ │ • Compresión zstd/gzip y cabeceras HSTS   │ │
│ └─────────────────────┬─────────────────────┘ │
│                       │ HTTP puerto 8000      │
│                       ▼ (Red interna bridge)  │
│ ┌───────────────────────────────────────────┐ │
│ │ Backend EcoGrow (Python 3.11 / Gunicorn)  │ │
│ │ • Dashboard Responsive HTML/CSS/JS        │ │
│ │ • API Móvil Android (/api/mobile/*)       │ │
│ │ • Ingesta de Telemetría ESP32             │ │
│ └─────────────────────┬─────────────────────┘ │
│                       │ TCP puerto 3306       │
│                       ▼ (Red interna bridge)  │
│ ┌───────────────────────────────────────────┐ │
│ │ Base de Datos MariaDB 10.11               │ │
│ │ • Volumen aislado ecogrow_db_data         │ │
│ └───────────────────────────────────────────┘ │
└───────────────────────────────────────────────┘
```

---

## 2. Preparación Inicial en el VPS

1. Conectarse por SSH al VPS `kv2`:
   ```bash
   ssh <usuario>@<ip_vps_kv2>
   ```
2. Asegurar que Docker y Docker Compose plugin están instalados:
   ```bash
   docker --version
   docker compose version
   ```
3. Clonar el repositorio en `/opt/ecogrow`:
   ```bash
   sudo mkdir -p /opt/ecogrow
   sudo chown -R $USER:$USER /opt/ecogrow
   git clone https://github.com/elJohn72/proyecto_ecogrow.git /opt/ecogrow
   cd /opt/ecogrow
   ```
4. Configurar las variables de entorno:
   ```bash
   cp deploy/env.example deploy/.env
   chmod 600 deploy/.env
   nano deploy/.env
   ```
   Rellenar `SECRET_KEY`, `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `ECOGROW_SENSOR_API_TOKEN` y `ECOGROW_DOMAIN`.

---

## 3. Ejecución del Despliegue

Ejecutar el script de despliegue automatizado:
```bash
./scripts/deploy_vps.sh
```
El script verifica la configuración, compila la imagen, arranca los servicios y monitorea el health check (`/health`) hasta confirmar su operatividad.

---

## 4. Despliegue Continuo (CI/CD) desde GitHub Actions

El repositorio incluye el workflow `.github/workflows/deploy.yml`. Para habilitarlo, configurar en los **Secrets de GitHub**:
- `HOSTINGER_SSH_HOST`: Dirección IP o hostname del VPS kv2.
- `HOSTINGER_SSH_USER`: Usuario SSH (ej. `root` o deploy user).
- `HOSTINGER_SSH_KEY`: Clave privada SSH con acceso autorizado al VPS.
- `HOSTINGER_SSH_PORT`: Puerto SSH (por defecto 22).

Al hacer push a `main`, el workflow conectará por SSH y ejecutará `scripts/deploy_vps.sh` automáticamente.
