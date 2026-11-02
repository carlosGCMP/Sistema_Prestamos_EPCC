CREATE TABLE IF NOT EXISTS informacion_estudiante (
    id_informacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_solicitante BIGINT NOT NULL UNIQUE,
    promedio_acumulado DECIMAL(4, 2) NOT NULL,
    creditos_aprobados INT NOT NULL,
    creditos_reprobados INT NOT NULL,
    creditos_cursando INT NOT NULL,

    FOREIGN KEY (id_solicitante) REFERENCES solicitante_estudiante(id_solicitante)

    CHECK (promedio_acumulado >= 0),
    CHECK (creditos_aprobados >= 0),
    CHECK (creditos_reprobados >= 0),
    CHECK (creditos_cursando >= 0)
);