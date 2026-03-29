CREATE DATABASE IF NOT EXISTS ecogrow_mysql
CHARACTER SET utf8mb4
COLLATE utf8mb4_general_ci;

USE ecogrow_mysql;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    mail VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS cultivos (
    id_cultivo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    variedad VARCHAR(120) NOT NULL,
    ubicacion VARCHAR(120) NOT NULL,
    estado VARCHAR(80) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS torres (
    id_torre INT AUTO_INCREMENT PRIMARY KEY,
    codigo_unico VARCHAR(80) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    ubicacion VARCHAR(120) NOT NULL,
    usuario_id INT NOT NULL,
    estado VARCHAR(40) NOT NULL DEFAULT 'registrada',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_torres_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id_usuario)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ciclos_cultivo (
    id_ciclo INT AUTO_INCREMENT PRIMARY KEY,
    torre_id INT NOT NULL,
    cultivo_id INT NOT NULL,
    fase VARCHAR(80) NOT NULL,
    notas VARCHAR(255) NOT NULL DEFAULT '',
    estado VARCHAR(40) NOT NULL DEFAULT 'activo',
    iniciado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalizado_en TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_ciclos_torre
        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
        ON DELETE CASCADE,
    CONSTRAINT fk_ciclos_cultivo
        FOREIGN KEY (cultivo_id) REFERENCES cultivos(id_cultivo)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS lecturas_sensores (
    id_lectura INT AUTO_INCREMENT PRIMARY KEY,
    ciclo_id INT NOT NULL,
    dispositivo VARCHAR(100) NOT NULL,
    temperatura_aire DECIMAL(5,2),
    humedad_aire DECIMAL(5,2),
    temperatura_agua DECIMAL(5,2),
    ph DECIMAL(4,2),
    ec DECIMAL(5,2),
    nivel_agua DECIMAL(5,2),
    luminosidad DECIMAL(8,2),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lecturas_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos_cultivo(id_ciclo)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS configuracion_control (
    id_configuracion INT AUTO_INCREMENT PRIMARY KEY,
    torre_id INT NOT NULL UNIQUE,
    module_size_mm INT NOT NULL DEFAULT 80,
    deposito_litros DECIMAL(6,2) NOT NULL DEFAULT 5.00,
    bomba_modelo VARCHAR(120) NOT NULL DEFAULT 'Aqua One Maxi 103',
    head_height_m DECIMAL(5,2) NOT NULL DEFAULT 1.40,
    ph_min DECIMAL(4,2) NOT NULL DEFAULT 6.50,
    ph_max DECIMAL(4,2) NOT NULL DEFAULT 8.50,
    ec_min DECIMAL(5,2) NOT NULL DEFAULT 1.40,
    ec_max DECIMAL(5,2) NOT NULL DEFAULT 2.40,
    temperatura_agua_min DECIMAL(5,2) NOT NULL DEFAULT 18.00,
    temperatura_agua_max DECIMAL(5,2) NOT NULL DEFAULT 24.00,
    nivel_minimo DECIMAL(5,2) NOT NULL DEFAULT 20.00,
    nivel_objetivo DECIMAL(5,2) NOT NULL DEFAULT 85.00,
    irrigation_on_minutes INT NOT NULL DEFAULT 15,
    irrigation_off_minutes INT NOT NULL DEFAULT 60,
    control_mode VARCHAR(40) NOT NULL DEFAULT 'consenso',
    pid_kp DECIMAL(6,3) NOT NULL DEFAULT 0.500,
    pid_ki DECIMAL(6,3) NOT NULL DEFAULT 1.000,
    pid_kd DECIMAL(6,3) NOT NULL DEFAULT 1.000,
    consenso_pid_weight DECIMAL(5,2) NOT NULL DEFAULT 0.80,
    consenso_fuzzy_weight DECIMAL(5,2) NOT NULL DEFAULT 0.20,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_configuracion_torre
        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS actuadores_torre (
    id_actuador INT AUTO_INCREMENT PRIMARY KEY,
    torre_id INT NOT NULL,
    tipo VARCHAR(60) NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    estado VARCHAR(40) NOT NULL DEFAULT 'listo',
    modo VARCHAR(40) NOT NULL DEFAULT 'automatico',
    ultimo_comando VARCHAR(120) NOT NULL DEFAULT 'sin accion',
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_actuador_torre_tipo (torre_id, tipo),
    CONSTRAINT fk_actuador_torre
        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS programaciones_riego (
    id_programacion INT AUTO_INCREMENT PRIMARY KEY,
    torre_id INT NOT NULL UNIQUE,
    habilitado BOOLEAN NOT NULL DEFAULT TRUE,
    minutos_encendido INT NOT NULL DEFAULT 15,
    minutos_apagado INT NOT NULL DEFAULT 60,
    estrategia VARCHAR(80) NOT NULL DEFAULT 'oxigenacion_radicular',
    siguiente_ciclo VARCHAR(80) NOT NULL DEFAULT 'inmediato',
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_programacion_torre
        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alertas_sistema (
    id_alerta INT AUTO_INCREMENT PRIMARY KEY,
    torre_id INT NOT NULL,
    tipo VARCHAR(60) NOT NULL,
    severidad VARCHAR(30) NOT NULL,
    mensaje VARCHAR(255) NOT NULL,
    valor_actual DECIMAL(8,2) NULL,
    umbral_referencia VARCHAR(120) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa',
    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cerrada_en TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_alerta_torre
        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eventos_control (
    id_evento INT AUTO_INCREMENT PRIMARY KEY,
    torre_id INT NOT NULL,
    lectura_id INT NULL,
    algoritmo VARCHAR(40) NOT NULL,
    variable_control VARCHAR(40) NOT NULL,
    error_valor DECIMAL(8,3) NOT NULL,
    salida_pid DECIMAL(8,3) NOT NULL,
    salida_fuzzy DECIMAL(8,3) NOT NULL,
    salida_consenso DECIMAL(8,3) NOT NULL,
    accion_recomendada VARCHAR(120) NOT NULL,
    motivo VARCHAR(255) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_evento_torre
        FOREIGN KEY (torre_id) REFERENCES torres(id_torre)
        ON DELETE CASCADE,
    CONSTRAINT fk_evento_lectura
        FOREIGN KEY (lectura_id) REFERENCES lecturas_sensores(id_lectura)
        ON DELETE SET NULL
);
