CREATE TABLE IF NOT EXISTS solicitud_de_reserva (
    id_solicitud BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_solicitante BIGINT NOT NULL,
    id_unidad_fisica BIGINT NOT NULL,
    fecha_solicitud TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_reserva TIMESTAMP NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',

    FOREIGN KEY (id_solicitante) REFERENCES solicitante(id_solicitante),
    FOREIGN KEY (id_unidad_fisica) REFERENCES unidad_fisica(id_unidad_fisica)
);