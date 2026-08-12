-- Script SQL de Creación y Carga del Tracker Universitario (Plan Completo de Estudios)
SET client_encoding = 'UTF8';

-- Eliminar tablas existentes para asegurar una reinstalación limpia
DROP TABLE IF EXISTS horarios_cursada CASCADE;
DROP TABLE IF EXISTS parciales CASCADE;
DROP TABLE IF EXISTS correlativas CASCADE;
DROP TABLE IF EXISTS materias CASCADE;

-- 1. Crear tabla materias
CREATE TABLE materias (
    id INT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL UNIQUE,
    nivel INT NOT NULL CHECK (nivel > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'Pendiente' CHECK (estado IN ('Pendiente', 'Regular', 'Aprobada')),
    nota_final INT CHECK (nota_final IS NULL OR (nota_final >= 1 AND nota_final <= 10)),
    veces_cursada INT DEFAULT 0 CHECK (veces_cursada >= 0)
);

-- 2. Crear tabla correlativas (relación muchos a muchos)
CREATE TABLE correlativas (
    materia_id INT REFERENCES materias(id) ON DELETE CASCADE,
    correlativa_id INT REFERENCES materias(id) ON DELETE CASCADE,
    tipo_requisito VARCHAR(20) NOT NULL CHECK (tipo_requisito IN ('Regularizada', 'Aprobada')),
    PRIMARY KEY (materia_id, correlativa_id, tipo_requisito),
    CONSTRAINT chk_no_autoreferencia CHECK (materia_id <> correlativa_id)
);

-- 3. Crear índices optimizados para búsquedas rápidas y JOINs eficientes
CREATE INDEX idx_materias_estado ON materias(estado);
CREATE INDEX idx_materias_nivel ON materias(nivel);
CREATE INDEX idx_correlativas_lookup ON correlativas(materia_id, correlativa_id);

-- 4. Insertar materias (Plan de Estudios Oficial - 36 Materias + Seminario Analista)
INSERT INTO materias (id, nombre, nivel, estado) VALUES
-- Nivel 1 (Todos inicializados como Pendientes por defecto)
(1, 'Análisis Matemático I', 1, 'Pendiente'),
(2, 'Álgebra y Geometría Analítica', 1, 'Pendiente'),
(3, 'Física I', 1, 'Pendiente'),
(4, 'Inglés I', 1, 'Pendiente'),
(5, 'Lógica y Estructuras Discretas', 1, 'Pendiente'),
(6, 'Algoritmo y Estructura de Datos', 1, 'Pendiente'),
(7, 'Arquitectura de Computadoras', 1, 'Pendiente'),
(8, 'Sistemas y Proceso de Negocios', 1, 'Pendiente'),
(11, 'Ingeniería y Sociedad', 1, 'Pendiente'),

-- Nivel 2
(9, 'Análisis Matemático II', 2, 'Pendiente'),
(10, 'Física II', 2, 'Pendiente'),
(12, 'Inglés II', 2, 'Pendiente'),
(13, 'Sintaxis y Semántica de los Lenguajes', 2, 'Pendiente'),
(14, 'Paradigmas de Programación', 2, 'Pendiente'),
(15, 'Sistemas Operativos', 2, 'Pendiente'),
(16, 'Análisis de Sistemas de Información', 2, 'Pendiente'),
(17, 'Probabilidad y Estadística', 2, 'Pendiente'),
(18, 'Economía', 2, 'Pendiente'),

-- Nivel 3
(19, 'Base de Datos', 3, 'Pendiente'),
(20, 'Desarrollo de Software', 3, 'Pendiente'),
(21, 'Comunicación de Datos', 3, 'Pendiente'),
(22, 'Análisis Numérico', 3, 'Pendiente'),
(23, 'Diseño de Sistemas de Información', 3, 'Pendiente'),
(99, 'Seminario Integrador (Analista)', 3, 'Pendiente'),

-- Nivel 4
(24, 'Legislación', 4, 'Pendiente'),
(25, 'Ingeniería y Calidad de Software', 4, 'Pendiente'),
(26, 'Redes de Datos', 4, 'Pendiente'),
(27, 'Investigación Operativa', 4, 'Pendiente'),
(28, 'Simulación', 4, 'Pendiente'),
(29, 'Tecnologías Para la Automatización', 4, 'Pendiente'),
(30, 'Administración de Sistemas de Información', 4, 'Pendiente'),
(31, 'Inteligencia Artificial', 4, 'Pendiente'),
(32, 'Ciencia de Datos', 4, 'Pendiente'),
(33, 'Sistemas de Gestión', 4, 'Pendiente'),

-- Nivel 5
(34, 'Gestión Gerencial', 5, 'Pendiente'),
(35, 'Seguridad en los Sistemas de Información', 5, 'Pendiente'),
(36, 'Proyecto Final', 5, 'Pendiente');

-- 5. Insertar relaciones de correlatividad

-- === NIVEL 2 ===
-- Análisis Matemático II (9)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(9, 1, 'Regularizada'),
(9, 2, 'Regularizada');

-- Física II (10)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(10, 1, 'Regularizada'),
(10, 3, 'Regularizada');

-- Inglés II (12)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(12, 4, 'Regularizada');

-- Sintaxis y Semántica de los Lenguajes (13)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(13, 5, 'Regularizada'),
(13, 6, 'Regularizada');

-- Paradigmas de Programación (14)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(14, 5, 'Regularizada'),
(14, 6, 'Regularizada');

-- Sistemas Operativos (15)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(15, 7, 'Regularizada');

-- Análisis de Sistemas de Información (16)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(16, 6, 'Regularizada'),
(16, 8, 'Regularizada');

-- Probabilidad y Estadística (17)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(17, 1, 'Regularizada'),
(17, 2, 'Regularizada');

-- Economía (18)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(18, 1, 'Aprobada'),
(18, 2, 'Aprobada');


-- === NIVEL 3 ===
-- Base de Datos (19)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(19, 13, 'Regularizada'),
(19, 16, 'Regularizada'),
(19, 5, 'Aprobada'),
(19, 6, 'Aprobada');

-- Desarrollo de Software (20)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(20, 14, 'Regularizada'),
(20, 12, 'Regularizada'),
(20, 5, 'Aprobada'),
(20, 6, 'Aprobada');

-- Comunicación de Datos (21)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(21, 3, 'Aprobada'),
(21, 7, 'Aprobada');

-- Análisis Numérico (22)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(22, 9, 'Regularizada'),
(22, 1, 'Aprobada'),
(22, 2, 'Aprobada');

-- Diseño de Sistemas de Información (23)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(23, 14, 'Regularizada'),
(23, 16, 'Regularizada'),
(23, 4, 'Aprobada'),
(23, 6, 'Aprobada'),
(23, 8, 'Aprobada');

-- Seminario Integrador (Analista) (99)
-- Requiere regularizar Análisis de Sistemas (16)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(99, 16, 'Regularizada');
-- Requiere aprobar todas las materias del 1 al 23
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(99, 1, 'Aprobada'),
(99, 2, 'Aprobada'),
(99, 3, 'Aprobada'),
(99, 4, 'Aprobada'),
(99, 5, 'Aprobada'),
(99, 6, 'Aprobada'),
(99, 7, 'Aprobada'),
(99, 8, 'Aprobada'),
(99, 9, 'Aprobada'),
(99, 10, 'Aprobada'),
(99, 11, 'Aprobada'),
(99, 12, 'Aprobada'),
(99, 13, 'Aprobada'),
(99, 14, 'Aprobada'),
(99, 15, 'Aprobada'),
(99, 16, 'Aprobada'),
(99, 17, 'Aprobada'),
(99, 18, 'Aprobada'),
(99, 19, 'Aprobada'),
(99, 20, 'Aprobada'),
(99, 21, 'Aprobada'),
(99, 22, 'Aprobada'),
(99, 23, 'Aprobada');


-- === NIVEL 4 ===
-- Legislación (24)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(24, 11, 'Regularizada');

-- Ingeniería y Calidad de Software (25)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(25, 19, 'Regularizada'),
(25, 20, 'Regularizada'),
(25, 23, 'Regularizada'),
(25, 13, 'Aprobada'),
(25, 14, 'Aprobada');

-- Redes de Datos (26)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(26, 15, 'Regularizada'),
(26, 21, 'Regularizada');

-- Investigación Operativa (27)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(27, 17, 'Regularizada'),
(27, 22, 'Regularizada');

-- Simulación (28)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(28, 17, 'Regularizada'),
(28, 9, 'Aprobada');

-- Tecnologías Para la Automatización (29)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(29, 10, 'Regularizada'),
(29, 22, 'Regularizada'),
(29, 9, 'Aprobada');

-- Administración de Sistemas de Información (30)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(30, 18, 'Regularizada'),
(30, 23, 'Regularizada'),
(30, 16, 'Aprobada');

-- Inteligencia Artificial (31)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(31, 28, 'Regularizada'),
(31, 17, 'Aprobada'),
(31, 22, 'Aprobada');

-- Ciencia de Datos (32)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(32, 28, 'Regularizada'),
(32, 17, 'Aprobada'),
(32, 19, 'Aprobada');

-- Sistemas de Gestión (33)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(33, 18, 'Regularizada'),
(33, 27, 'Regularizada'),
(33, 23, 'Aprobada');


-- === NIVEL 5 ===
-- Gestión Gerencial (34)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(34, 24, 'Regularizada'),
(34, 30, 'Regularizada'),
(34, 18, 'Aprobada');

-- Seguridad en los Sistemas de Información (35)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(35, 26, 'Regularizada'),
(35, 30, 'Regularizada'),
(35, 20, 'Aprobada'),
(35, 21, 'Aprobada');

-- Proyecto Final (36)
-- Cursar: regularizar Ingeniería de Software (25), Redes (26) y Administración de Sistemas (30)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(36, 25, 'Regularizada'),
(36, 26, 'Regularizada'),
(36, 30, 'Regularizada');
-- Rendir: Aprobadas todas las previas (1 al 35 y 99)
INSERT INTO correlativas (materia_id, correlativa_id, tipo_requisito) VALUES
(36, 1, 'Aprobada'),
(36, 2, 'Aprobada'),
(36, 3, 'Aprobada'),
(36, 4, 'Aprobada'),
(36, 5, 'Aprobada'),
(36, 6, 'Aprobada'),
(36, 7, 'Aprobada'),
(36, 8, 'Aprobada'),
(36, 9, 'Aprobada'),
(36, 10, 'Aprobada'),
(36, 11, 'Aprobada'),
(36, 12, 'Aprobada'),
(36, 13, 'Aprobada'),
(36, 14, 'Aprobada'),
(36, 15, 'Aprobada'),
(36, 16, 'Aprobada'),
(36, 17, 'Aprobada'),
(36, 18, 'Aprobada'),
(36, 19, 'Aprobada'),
(36, 20, 'Aprobada'),
(36, 21, 'Aprobada'),
(36, 22, 'Aprobada'),
(36, 23, 'Aprobada'),
(36, 24, 'Aprobada'),
(36, 25, 'Aprobada'),
(36, 26, 'Aprobada'),
(36, 27, 'Aprobada'),
(36, 28, 'Aprobada'),
(36, 29, 'Aprobada'),
(36, 30, 'Aprobada'),
(36, 31, 'Aprobada'),
(36, 32, 'Aprobada'),
(36, 33, 'Aprobada'),
(36, 34, 'Aprobada'),
(36, 35, 'Aprobada'),
(36, 99, 'Aprobada');

-- 6. Crear tabla parciales para la agenda de exámenes
CREATE TABLE parciales (
    id SERIAL PRIMARY KEY,
    materia_id INT NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    fecha TIMESTAMP NOT NULL,
    descripcion TEXT
);

CREATE INDEX idx_parciales_fecha ON parciales(fecha);

-- 7. Crear tabla horarios_cursada para el horario semanal de materias
CREATE TABLE horarios_cursada (
    id SERIAL PRIMARY KEY,
    materia_id INT NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
    dia_semana INT NOT NULL CHECK (dia_semana BETWEEN 1 AND 6),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    aula_comision VARCHAR(100),
    CONSTRAINT chk_horario_valido CHECK (hora_fin > hora_inicio)
);

CREATE INDEX idx_horarios_dia ON horarios_cursada(dia_semana, hora_inicio);
