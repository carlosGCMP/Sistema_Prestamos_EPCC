CREATE TABLE IF NOT EXISTS devolucion_del_prestamo (
    id_devolucion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_prestamo BIGINT NOT NULL UNIQUE,
    fecha_devolucion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observaciones TEXT,

    FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo)
);