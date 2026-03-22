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

CREATE TABLE IF NOT EXISTS productos (
    id_producto INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL UNIQUE,
    cantidad INT NOT NULL,
    precio DECIMAL(10,2) NOT NULL,
    descripcion VARCHAR(255) NOT NULL
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
