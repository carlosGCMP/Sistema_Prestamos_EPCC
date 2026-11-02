CREATE TABLE IF NOT EXISTS ampliacion_devolucion_prestamo (
    id_ampliacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_prestamo BIGINT NOT NULL,
    fecha_ampliacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    nueva_fecha_devolucion TIMESTAMP NOT NULL,
    observaciones TEXT,

    FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo)
);