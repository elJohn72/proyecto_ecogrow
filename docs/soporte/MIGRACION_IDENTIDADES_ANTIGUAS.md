# Migración y recuperación de identidades antiguas EcoGrow 2.0

Ámbito: **ECOGROW**, **AISLADO**.

El código de torre identifica el equipo. Conocerlo no transfiere la propiedad: la vinculación exige la prueba de posesión (PoP) y el registro queda en el usuario que ya reclamó la torre.

## Qué no cambia la identidad

Arrancar el ESP32, sincronizar con la API o consultar `ECOGROW:IDENT?` solo lee la NVS. Esas rutas no calculan otro código ni lo guardan.

`ECOGROW_TORRE_CODIGO` en `config.h` es un ejemplo heredado. El firmware no lo copia a `torre_code` al arrancar.

El único comando que persiste un código es `ECOGROW:SET_CODE`. Rechaza placeholders (`TORRE-001`, `EG-TORRE-01`, `DUMMY`, `PRUEBA`, `TEST`, `IDENTIFICADOR_TECNICO`). Por eso un placeholder no se puede “devolver” al hardware: si el código nuevo no quedó escrito, la base se revierte al código anterior y el hardware sigue igual.

## Orden cuando el código antiguo ya está vinculado

1. Leer, sin escribir:

```bash
python3 tools/provision_device.py read --port /dev/cu.usbserial-XXXX
```

La respuesta incluye el código guardado, si es válido, el código sugerido por la MAC y `identity_mutated:false`.

2. Simular la base, sin tocar el ESP32:

```bash
python3 tools/migrate_identities.py --dry-run
python3 tools/migrate_identities.py --dry-run --mac 44:1D:64:F8:70:C4
```

3. Aplicar solo la base si el taller va a coordinar el hardware en otro momento:

```bash
python3 tools/migrate_identities.py --apply --mac 44:1D:64:F8:70:C4
```

Esa transacción actualiza `dispositivos_iot.codigo_torre` y, si existe la torre, `torres.codigo_unico`. Conserva `id_torre`, `usuario_id`, `reclamado_por`, token, PoP, historial y configuración. Si el código canónico ya lo usa otro dispositivo u otra torre, no escribe y deja el caso en taller. Repetir el comando sobre un código ya canónico no lo cambia. Un fallo antes del commit revierte las dos tablas.

4. Coordinar base y NVS, conservando PoP, token y propietario:

```bash
python3 tools/provision_device.py migrate-code --port /dev/cu.usbserial-XXXX
```

Primero migra la fila de esa MAC. Después envía `SET_CODE` y exige readback. No llama a `register_dispositivo_fabrica` y no rota credenciales. Si el readback sigue mostrando el código anterior, la base vuelve al código previo. Si la base ya quedó en el código canónico y el `SET_CODE` falla, no se revierte a un placeholder: se reintenta el `SET_CODE`.

5. Imprimir la etiqueta nueva solo cuando el readback coincide. La etiqueta vive en `docs/soporte/etiquetas/` y no se versiona.

## Recuperación del aprovisionamiento

`provision` escribe un diario local, modo `0600`, en `.provision-state/` junto a la salida. El directorio está en `.gitignore`. El diario guarda la PoP, el código y el token anteriores; no se imprime ni se sube a git.

Antes de mutar, el preflight lee identidad, propietario y token. Si la torre ya está reclamada, se detiene sin escribir.

Si falla el serial, el readback, la base o el proceso:

```bash
python3 tools/provision_device.py recover --port /dev/cu.usbserial-XXXX
```

Cada campo restaurado se vuelve a leer. El diario se borra solo cuando esa lectura coincide. Si un campo no se puede restaurar, el estado queda `repair_required`. En ese caso no hay etiqueta de éxito y no se informa que la identidad quedó conservada.

`provision --force` reasigna el registro a fábrica y no es el camino para conservar un cliente. El cambio de código de una torre ya reclamada es `migrate-code` o `migrate_identities.py --apply`.

## Cuándo el taller debe parar

- Otro dispositivo u otra torre ya tiene el código canónico.
- La MAC no tiene 12 dígitos hexadecimales.
- El ESP32 ya tiene un código válido distinto del sugerido por su MAC. Consultar `IDENT` no lo sustituye; hace falta una decisión explícita.
- El diario queda en `repair_required` porque el valor anterior no pudo verificarse en el hardware.

No usar la base del VPS para ensayar. La prueba de integración crea una base temporal y la elimina al terminar.
