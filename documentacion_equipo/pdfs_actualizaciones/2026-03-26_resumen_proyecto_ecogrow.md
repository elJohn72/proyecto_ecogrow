# EcoGrow - Documento general del proyecto

## 1. Descripcion general

EcoGrow es una aplicacion web academica desarrollada con Flask para gestionar un sistema hidropónico con enfoque en monitoreo, operacion y apoyo a la toma de decisiones. El proyecto integra autenticacion de usuarios, panel privado, gestion de torres, seguimiento de cultivos, inventario local, telemetria IoT y una capa de asistencia inteligente para el agricultor.

El objetivo principal es centralizar en una sola plataforma el estado operativo de una torre hidropónica, permitiendo consultar datos en tiempo real, gestionar cultivos, revisar eventos de control y recibir recomendaciones tecnicas basadas en sensores.

## 2. Objetivos del sistema

- Gestionar usuarios con acceso autenticado.
- Registrar y administrar torres hidropónicas.
- Asociar cultivos y fases productivas a cada torre.
- Recibir y almacenar lecturas de sensores desde un dispositivo IoT.
- Visualizar pH, EC, temperatura y nivel de agua.
- Generar eventos de control y alertas operativas.
- Ofrecer un asistente tipo Agricultor IA para interpretar el estado del cultivo.
- Permitir acciones asistidas sobre la torre cuando el usuario lo autoriza.

## 3. Tecnologias utilizadas

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy
- MySQL Connector for Python
- MySQL / MariaDB
- SQLite para persistencia local del inventario
- HTML, CSS y Jinja2
- ESP32 con PlatformIO para integracion IoT
- Integracion opcional con Gemini para respuestas enriquecidas del asistente IA

## 4. Arquitectura general

La aplicacion sigue una estructura modular basada en blueprints de Flask. Cada modulo separa responsabilidades funcionales y ayuda a mantener la organizacion del proyecto.

Componentes principales:

- `app.py`: inicializa Flask, seguridad, login, base local y registro de blueprints.
- `blueprints/auth.py`: registro, login y logout.
- `blueprints/torres.py`: manejo de torres, seleccion de torre y dashboard principal.
- `blueprints/cultivos.py`: CRUD de cultivos.
- `blueprints/sensores.py`: monitoreo, telemetria, alertas y contexto operativo.
- `blueprints/mysql.py`: gestion CRUD de usuarios y productos en MySQL.
- `blueprints/inventario.py`: inventario local con SQLite y archivos.
- `blueprints/ai.py`: Agricultor IA, consultas inteligentes y control asistido de torre.
- `Conexión/conexion.py`: acceso centralizado a MySQL, creacion de tablas y consultas de negocio.

## 5. Base de datos y persistencia

EcoGrow usa dos tipos de persistencia:

1. MySQL / MariaDB:
   - usuarios
   - torres
   - cultivos
   - ciclos de cultivo
   - lecturas de sensores
   - configuracion de control
   - actuadores de torre
   - programaciones de riego
   - alertas del sistema
   - eventos de control

2. SQLite / archivos locales:
   - inventario local y sincronizacion de archivos auxiliares

La autenticacion se apoya en MySQL y las contrasenas se almacenan con hash.

## 6. Modulos funcionales

### 6.1 Autenticacion

Permite registro de usuarios, inicio y cierre de sesion. Las rutas privadas quedan protegidas y el sistema carga el usuario autenticado desde MySQL.

### 6.2 Gestion de torres

Cada usuario puede registrar una o varias torres. Una torre activa se guarda en sesion para operar el panel principal, el monitoreo y los flujos de cultivo.

### 6.3 Gestion de cultivos

El sistema permite registrar cultivos y asociarlos a una torre mediante ciclos de cultivo. Cada ciclo tiene una fase activa y notas operativas.

### 6.4 Monitoreo y sensores

El modulo de sensores recibe datos desde un ESP32 u otro nodo compatible mediante un endpoint protegido por token. Entre las variables monitoreadas se encuentran:

- temperatura del aire
- humedad del aire
- temperatura del agua
- pH
- EC
- nivel de agua
- luminosidad

Con estas lecturas, el sistema muestra paneles de monitoreo, calcula estados de riesgo y registra sugerencias operativas.

### 6.5 Control y eventos operativos

EcoGrow mantiene configuraciones de control por torre y administra actuadores logicos como:

- bomba principal
- valvula de agua
- valvula de nutrientes AB Mix
- dosificador de pH

Ademas, registra eventos de control con informacion como algoritmo, variable afectada, salida de consenso, accion recomendada y motivo tecnico.

### 6.6 Inventario

El sistema incluye un modulo independiente de inventario con persistencia local para productos y movimientos basicos, pensado como apoyo administrativo.

## 7. Agricultor IA

Se incorporo un nuevo modulo llamado Agricultor IA con el objetivo de darle al usuario una experiencia de consulta tecnica en lenguaje natural.

Capacidades principales:

- responder preguntas como "como esta mi planta"
- interpretar datos recientes del cultivo
- explicar riesgos asociados a pH, EC, temperatura o nivel de agua
- generar una recomendacion accionable
- ejecutar una sugerencia sobre la torre solo si el usuario da permiso explicito

Funcionamiento:

- construye contexto con cultivo activo, lecturas recientes, alertas, actuadores y eventos
- genera una recomendacion deterministica segura
- si existe `GEMINI_API_KEY`, complementa la respuesta con Gemini
- si no existe clave, sigue funcionando con analisis local

Ejemplos de acciones asistidas:

- recargar deposito
- aplicar pH Up
- aplicar pH Down
- dosificar AB Mix
- diluir con agua
- aumentar o reducir frecuencia de riego

Todas estas acciones quedan registradas como eventos de control asistido por IA.

## 8. Flujo general de uso

1. El usuario se registra o inicia sesion.
2. Registra una torre o selecciona una ya existente.
3. Asocia un cultivo y define la fase activa.
4. El nodo IoT envia telemetria al endpoint del sistema.
5. EcoGrow guarda lecturas, calcula alertas y eventos de control.
6. El usuario consulta el dashboard, monitoreo o Agricultor IA.
7. Si el asistente propone una accion y el usuario la autoriza, el sistema actualiza el estado de la torre de forma asistida.

## 9. Rutas importantes

Publicas:

- `/`
- `/about`
- `/contactos`
- `/demo`
- `/login`
- `/registro`

Protegidas:

- `/dashboard`
- `/torres`
- `/torres/registrar`
- `/torres/cultivo`
- `/cultivos`
- `/sensores`
- `/inventario`
- `/mysql`
- `/agricultor-ia`

API destacada:

- `/api/sensores/lectura`
- `/api/agricultor-ia/chat`
- `/api/ai_advice/<torre_id>`

## 10. Seguridad y buenas practicas

- autenticacion con Flask-Login
- formularios protegidos con token CSRF
- endpoint IoT protegido con token de dispositivo
- hash de contrasenas en usuarios
- validacion de propiedad de torre por usuario
- acciones del asistente limitadas a la torre autorizada por el usuario

## 11. Estructura documental para el equipo

Se creo la carpeta `documentacion_equipo/` para almacenar material no relacionado con codigo, sin alterar la arquitectura del software.

Subcarpetas recomendadas:

- `esquematicos/`
- `pdfs_actualizaciones/`
- `entregables/`
- `recursos_multimedia/`
- `notas_equipo/`
- `presentaciones/`

Esto permite compartir PDFs, exposiciones, diagramas, capturas y documentos del proyecto con el equipo de trabajo de forma ordenada.

## 12. Estado actual del proyecto

Actualmente EcoGrow cuenta con:

- autenticacion funcional
- gestion de torres y cultivos
- monitoreo de sensores
- eventos de control y alertas
- inventario local
- integracion con MySQL / XAMPP
- modulo Agricultor IA con permiso de control asistido
- carpeta de documentacion colaborativa para el equipo

## 13. Proyeccion de mejoras

Posibles siguientes pasos:

- historial conversacional del Agricultor IA
- comandos reales hacia hardware fisico
- reportes PDF automaticos por cultivo o torre
- paneles graficos historicos de sensores
- roles avanzados de usuario y administrador
- integracion mas profunda entre IA y automatizacion IoT

## 14. Conclusion

EcoGrow es una plataforma academica con una base solida para gestionar sistemas hidropónicos inteligentes. Combina software web, persistencia relacional, monitoreo IoT y una capa de apoyo inteligente orientada al agricultor. Su arquitectura modular facilita continuar el proyecto, documentarlo y presentar avances al equipo o a docentes.
