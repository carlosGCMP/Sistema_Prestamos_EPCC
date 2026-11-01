CREATE TABLE IF NOT EXISTS sancion (
    id_sancion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_prestamo BIGINT NOT NULL,
    id_tipo_sancion BIGINT NOT NULL,
    id_estado BIGINT NOT NULL,
    fecha_sancion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,

    FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo),
    FOREIGN KEY (id_tipo_sancion) REFERENCES tipo_de_sancion(id_tipo_sancion),
    FOREIGN KEY (id_estado) REFERENCES estado_de_la_sancion(id_estado)
);