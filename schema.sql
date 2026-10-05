-- ============================================================
-- SCRIPT DE CREACIÓN DE BASE DE DATOS Y TABLAS - ALAS DEL VIENTO
-- Coro y Escuela de Música - General Alvear, Mendoza
-- NUEVO PARA CONEXION CON DB LOCAL MYSQL
-- ============================================================

-- 1. Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS `alvear365_db`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

-- 2. Seleccionar la base de datos
USE `alvear365_db`;

-- 3. Crear la tabla de eventos
CREATE TABLE IF NOT EXISTS `eventos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre` VARCHAR(255) NOT NULL,
  `descripcion` TEXT,
  `tipo` VARCHAR(100) NOT NULL,
  `fecha_inicio` DATE NOT NULL,
  `fecha_fin` DATE NOT NULL,
  `hora` VARCHAR(10) NOT NULL,
  `costo` VARCHAR(50) DEFAULT '0',
  `lugar` VARCHAR(255) NOT NULL,
  `lugar_corto` VARCHAR(255),
  `direccion` VARCHAR(255),
  `imagen` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Crear la tabla de preinscripciones
CREATE TABLE IF NOT EXISTS `preinscripciones` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `nombre_apellido` VARCHAR(255) NOT NULL,
  `dni` VARCHAR(50) NOT NULL,
  `fecha_nacimiento` VARCHAR(50) NOT NULL,
  `edad` INT NOT NULL,
  `domicilio` VARCHAR(255) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `telefono` VARCHAR(50) NOT NULL,
  `sala` VARCHAR(100) NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Insertar eventos iniciales del Coro Alas del Viento
INSERT INTO `eventos` (`id`, `nombre`, `descripcion`, `tipo`, `fecha_inicio`, `fecha_fin`, `hora`, `costo`, `lugar`, `lugar_corto`, `direccion`, `imagen`) VALUES
(0, 'Concierto de Gala Anual - Coro Alas del Viento', 'Presentación estelar de los coros y ensamble orquestal de la Escuela Alas del Viento. Interpretación de obras sinfónico-corales, música popular argentina y repertorio lírico en el escenario principal del teatro.', 'Música', '2026-10-15', '2026-10-15', '20:30', '0', 'Cine Teatro Antonio Lafalla', 'Cine Teatro Lafalla', 'Av. Alvear Oeste 440, General Alvear, Mendoza', '/static/img/carrusel1.png'),
(1, 'Encuentro Provincial de Coros y Orquestas Infantiles', 'Magno encuentro musical reuniendo a niños y jóvenes músicos de Mendoza. Talleres de canto coral, ensamble instrumental simultáneo y concierto de clausura al aire libre.', 'Educación', '2026-11-20', '2026-11-21', '19:00', '0', 'Plaza Departamental Carlos María de Alvear', 'Plaza Carlos M. de Alvear', 'Av. Alvear Oeste y San Martín, General Alvear, Mendoza', '/static/img/carrusel2.png'),
(2, 'Gira Sinfónica Comunitaria - Alas del Viento en Bowen', 'Concierto itinerante con la participación especial de los alumnos de las Salas de 0 a 5 años, 6 a 11 y 12 a 17 años de la Escuela Alas del Viento en el distrito de Bowen.', 'Música', '2026-12-05', '2026-12-05', '20:00', '0', 'Bowen General Alvear Mendoza', 'Bowen', 'Plaza San Martín, Bowen, General Alvear, Mendoza', '/static/img/carrusel3.png')
ON DUPLICATE KEY UPDATE `nombre` = VALUES(`nombre`);

