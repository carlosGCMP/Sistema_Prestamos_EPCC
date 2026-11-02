CREATE TABLE IF NOT EXISTS matricula_realizada (
    id_matricula BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_solicitante BIGINT NOT NULL,
    id_semestre BIGINT NOT NULL,
    fecha_matricula TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_solicitante) REFERENCES solicitante_estudiante(id_solicitante),
    UNIQUE (id_solicitante, id_semestre)
    FOREIGN KEY (id_semestre) REFERENCES semestre_academico(id_semestre)
);