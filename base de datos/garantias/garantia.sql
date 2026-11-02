CREATE TABLE IF NOT EXISTS garantia (
    id_garantia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_prestamo BIGINT NOT NULL,
    id_tipo_garantia BIGINT NOT NULL,
    id_estado BIGINT NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo),
    FOREIGN KEY (id_tipo_garantia) REFERENCES tipo_de_garantia(id_tipo_garantia),
    FOREIGN KEY (id_estado) REFERENCES estado_de_la_garantia(id_estado)
);