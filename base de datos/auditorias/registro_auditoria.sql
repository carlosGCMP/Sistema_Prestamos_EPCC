CREATE TABLE IF NOT EXISTS registro_auditoria (
    id_registro BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cuenta BIGINT NOT NULL,
    id_tipo_evento BIGINT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accion VARCHAR(100) NOT NULL,
    descripcion TEXT NOT NULL,

    FOREIGN KEY (id_cuenta) REFERENCES cuenta(id_cuenta),
    FOREIGN KEY (id_tipo_evento) REFERENCES tipo_de_evento(id_tipo_evento)
);