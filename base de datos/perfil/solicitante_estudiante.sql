CREATE TABLE IF NOT EXISTS solicitante_estudiante (
    id_solicitante BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_persona BIGINT NOT NULL UNIQUE,
    codigo_universitario VARCHAR(20) NOT NULL,
    programa_academico VARCHAR(100) NOT NULL,
    semestre INT NOT NULL,

    FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);