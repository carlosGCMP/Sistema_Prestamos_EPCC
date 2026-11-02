CREATE TABLE IF NOT EXISTS registro_de_reserva (
    id_reserva BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_solicitante BIGINT NOT NULL,
    id_unidad_fisica BIGINT NOT NULL,
    fecha_reserva TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa',

    FOREIGN KEY (id_solicitante) REFERENCES solicitante(id_solicitante),
    FOREIGN KEY (id_unidad_fisica) REFERENCES unidad_fisica(id_unidad_fisica),

    CHECK (fecha_expiracion > fecha_reserva)
);