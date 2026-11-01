CREATE TABLE IF NOT EXISTS semestre_academico (
    id_semestre BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_semestre VARCHAR(50) NOT NULL UNIQUE,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    CHECK (fecha_fin > fecha_inicio)
);