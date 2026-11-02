CREATE TABLE IF NOT EXISTS solicitante_docente (
    id_solicitante BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_persona BIGINT NOT NULL UNIQUE,
    codigo_docente VARCHAR(20) NOT NULL,
    departamento VARCHAR(100) NOT NULL,
    cargo VARCHAR(100) NOT NULL,

    FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);