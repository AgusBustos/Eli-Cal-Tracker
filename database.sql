-- Script SQL de Creación y Carga del Tracker Universitario Multi-Usuario
SET client_encoding = 'UTF8';

-- Eliminar tablas existentes
DROP TABLE IF EXISTS horarios_cursada CASCADE;
DROP TABLE IF EXISTS parciales CASCADE;
DROP TABLE IF EXISTS correlativas CASCADE;
DROP TABLE IF EXISTS usuario_materias CASCADE;
DROP TABLE IF EXISTS materias CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- 1. Crear tabla usuarios
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Crear tabla materias (Catálogo base oficial)
CREATE TABLE materias (
    id INT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL UNIQUE,
    nivel INT NOT NULL CHECK (nivel > 0)
);

-- 3. Crear tabla usuario_materias (El progreso de cada usuario)
CREATE TABLE usuario_materias (
    usuario_id INT REFERENCES usuarios(id) ON DELETE CASCADE,
    materia_id INT REFERENCES materias(id) ON DELETE CASCADE,
    estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente' CHECK (estado IN ('Pendiente', 'Regular', 'Aprobada')),
    nota_final INT CHECK (nota_final IS NULL OR (nota_final >= 1 AND nota_final <= 10)),
    veces_cursada INT DEFAULT 0 CHECK (veces_cursada >= 0),
    PRIMARY KEY (usuario_id, materia_id)
);

-- 4. Crear tabla correlativas
CREATE TABLE correlativas (
    materia_id INT REFERENCES materias(id) ON DELETE CASCADE,
    correlativa_id INT REFERENCES materias(id) ON DELETE CASCADE,
    tipo_requisito VARCHAR(20) NOT NULL CHECK (tipo_requisito IN ('Regularizada', 'Aprobada')),
    PRIMARY KEY (materia_id, correlativa_id, tipo_requisito),
    CONSTRAINT chk_no_autoreferencia CHECK (materia_id <> correlativa_id)
);

-- 5. Crear tabla parciales
CREATE TABLE parciales (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    materia_id INT NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    fecha TIMESTAMP NOT NULL,
    descripcion TEXT
);
CREATE INDEX idx_parciales_fecha_usuario ON parciales(usuario_id, fecha);

-- 6. Crear tabla horarios_cursada
CREATE TABLE horarios_cursada (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    materia_id INT NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
    dia_semana INT NOT NULL CHECK (dia_semana BETWEEN 1 AND 6),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    aula_comision VARCHAR(100),
    CONSTRAINT chk_horario_valido CHECK (hora_fin > hora_inicio)
);
CREATE INDEX idx_horarios_usuario ON horarios_cursada(usuario_id, dia_semana);

-- === INSERTS DE CATÁLOGO OFICIAL ===
INSERT INTO materias (id, nombre, nivel) VALUES
(1, 'Análisis Matemático I', 1), (2, 'Álgebra y Geometría Analítica', 1), (3, 'Física I', 1),
(4, 'Inglés I', 1), (5, 'Lógica y Estructuras Discretas', 1), (6, 'Algoritmo y Estructura de Datos', 1),
(7, 'Arquitectura de Computadoras', 1), (8, 'Sistemas y Proceso de Negocios', 1), (11, 'Ingeniería y Sociedad', 1),
(9, 'Análisis Matemático II', 2), (10, 'Física II', 2), (12, 'Inglés II', 2),
(13, 'Sintaxis y Semántica de los Lenguajes', 2), (14, 'Paradigmas de Programación', 2), (15, 'Sistemas Operativos', 2),
(16, 'Análisis de Sistemas de Información', 2), (17, 'Probabilidad y Estadística', 2), (18, 'Economía', 2),
(19, 'Base de Datos', 3), (20, 'Desarrollo de Software', 3), (21, 'Comunicación de Datos', 3),
(22, 'Análisis Numérico', 3), (23, 'Diseño de Sistemas de Información', 3), (99, 'Seminario Integrador (Analista)', 3),
(24, 'Legislación', 4), (25, 'Ingeniería y Calidad de Software', 4), (26, 'Redes de Datos', 4),
(27, 'Investigación Operativa', 4), (28, 'Simulación', 4), (29, 'Tecnologías Para la Automatización', 4),
(30, 'Administración de Sistemas de Información', 4), (31, 'Inteligencia Artificial', 4), (32, 'Ciencia de Datos', 4),
(33, 'Sistemas de Gestión', 4), (34, 'Gestión Gerencial', 5), (35, 'Seguridad en los Sistemas de Información', 5),
(36, 'Proyecto Final', 5);

INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(9, 1, 'Regularizada'),(9, 2, 'Regularizada'),(10, 1, 'Regularizada'),(10, 3, 'Regularizada'),
(12, 4, 'Regularizada'),(13, 5, 'Regularizada'),(13, 6, 'Regularizada'),(14, 5, 'Regularizada'),
(14, 6, 'Regularizada'),(15, 7, 'Regularizada'),(16, 6, 'Regularizada'),(16, 8, 'Regularizada'),
(17, 1, 'Regularizada'),(17, 2, 'Regularizada'),(18, 1, 'Aprobada'),(18, 2, 'Aprobada'),
(19, 13, 'Regularizada'),(19, 16, 'Regularizada'),(19, 5, 'Aprobada'),(19, 6, 'Aprobada'),
(20, 14, 'Regularizada'),(20, 12, 'Regularizada'),(20, 5, 'Aprobada'),(20, 6, 'Aprobada'),
(21, 3, 'Aprobada'),(21, 7, 'Aprobada'),(22, 9, 'Regularizada'),(22, 1, 'Aprobada'),
(22, 2, 'Aprobada'),(23, 14, 'Regularizada'),(23, 16, 'Regularizada'),(23, 4, 'Aprobada'),
(23, 6, 'Aprobada'),(23, 8, 'Aprobada'),(99, 16, 'Regularizada'),(99, 1, 'Aprobada'),
(99, 2, 'Aprobada'),(99, 3, 'Aprobada'),(99, 4, 'Aprobada'),(99, 5, 'Aprobada'),
(99, 6, 'Aprobada'),(99, 7, 'Aprobada'),(99, 8, 'Aprobada'),(99, 9, 'Aprobada'),
(99, 10, 'Aprobada'),(99, 11, 'Aprobada'),(99, 12, 'Aprobada'),(99, 13, 'Aprobada'),
(99, 14, 'Aprobada'),(99, 15, 'Aprobada'),(99, 16, 'Aprobada'),(99, 17, 'Aprobada'),
(99, 18, 'Aprobada'),(99, 19, 'Aprobada'),(99, 20, 'Aprobada'),(99, 21, 'Aprobada'),
(99, 22, 'Aprobada'),(99, 23, 'Aprobada'),(24, 11, 'Regularizada'),(25, 19, 'Regularizada'),
(25, 20, 'Regularizada'),(25, 23, 'Regularizada'),(25, 13, 'Aprobada'),(25, 14, 'Aprobada'),
(26, 15, 'Regularizada'),(26, 21, 'Regularizada'),(27, 17, 'Regularizada'),(27, 22, 'Regularizada'),
(28, 17, 'Regularizada'),(28, 9, 'Aprobada'),(29, 10, 'Regularizada'),(29, 22, 'Regularizada'),
(29, 9, 'Aprobada'),(30, 18, 'Regularizada'),(30, 23, 'Regularizada'),(30, 16, 'Aprobada'),
(31, 28, 'Regularizada'),(31, 17, 'Aprobada'),(31, 22, 'Aprobada'),(32, 28, 'Regularizada'),
(32, 17, 'Aprobada'),(32, 19, 'Aprobada'),(33, 18, 'Regularizada'),(33, 27, 'Regularizada'),
(33, 23, 'Aprobada'),(34, 24, 'Regularizada'),(34, 30, 'Regularizada'),(34, 18, 'Aprobada'),
(35, 26, 'Regularizada'),(35, 30, 'Regularizada'),(35, 20, 'Aprobada'),(35, 21, 'Aprobada'),
(36, 25, 'Regularizada'),(36, 26, 'Regularizada'),(36, 30, 'Regularizada'),(36, 1, 'Aprobada'),
(36, 2, 'Aprobada'),(36, 3, 'Aprobada'),(36, 4, 'Aprobada'),(36, 5, 'Aprobada'),
(36, 6, 'Aprobada'),(36, 7, 'Aprobada'),(36, 8, 'Aprobada'),(36, 9, 'Aprobada'),
(36, 10, 'Aprobada'),(36, 11, 'Aprobada'),(36, 12, 'Aprobada'),(36, 13, 'Aprobada'),
(36, 14, 'Aprobada'),(36, 15, 'Aprobada'),(36, 16, 'Aprobada'),(36, 17, 'Aprobada'),
(36, 18, 'Aprobada'),(36, 19, 'Aprobada'),(36, 20, 'Aprobada'),(36, 21, 'Aprobada'),
(36, 22, 'Aprobada'),(36, 23, 'Aprobada'),(36, 24, 'Aprobada'),(36, 25, 'Aprobada'),
(36, 26, 'Aprobada'),(36, 27, 'Aprobada'),(36, 28, 'Aprobada'),(36, 29, 'Aprobada'),
(36, 30, 'Aprobada'),(36, 31, 'Aprobada'),(36, 32, 'Aprobada'),(36, 33, 'Aprobada'),
(36, 34, 'Aprobada'),(36, 35, 'Aprobada'),(36, 99, 'Aprobada');

-- Trigger to automatically create usuario_materias for a new user
CREATE OR REPLACE FUNCTION after_usuario_insert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO usuario_materias (usuario_id, materia_id, estado, nota_final, veces_cursada)
    SELECT NEW.id, id, 'Pendiente', NULL, 0 FROM materias;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_usuario_insert
AFTER INSERT ON usuarios
FOR EACH ROW
EXECUTE FUNCTION after_usuario_insert();
