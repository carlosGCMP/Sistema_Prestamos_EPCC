CREATE TABLE IF NOT EXISTS incidencia (
    id_incidencia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_solicitante BIGINT NOT NULL,
    id_administrador BIGINT NOT NULL,
    id_tipo_incidencia BIGINT NOT NULL,
    id_estado BIGINT NOT NULL,
    fecha_incidencia TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,

    FOREIGN KEY (id_solicitante) REFERENCES solicitante(id_solicitante),
    FOREIGN KEY (id_administrador) REFERENCES administrador(id_administrador),
    FOREIGN KEY (id_tipo_incidencia) REFERENCES tipo_de_incidencia(id_tipo_incidencia),
    FOREIGN KEY (id_estado) REFERENCES estado_de_la_incidencia(id_estado)
);