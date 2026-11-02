CREATE TABLE IF NOT EXISTS registro_bienes_fisicos_prestamo (
    id_registro BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_prestamo BIGINT NOT NULL,
    id_unidad_fisica BIGINT NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo),
    FOREIGN KEY (id_unidad_fisica) REFERENCES unidad_fisica(id_unidad_fisica)
);