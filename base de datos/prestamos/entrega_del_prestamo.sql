CREATE TABLE IF NOT EXISTS entrega_del_prestamo (
    id_entrega BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_prestamo BIGINT NOT NULL UNIQUE,
    fecha_entrega TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observaciones TEXT,

    FOREIGN KEY (id_prestamo) REFERENCES prestamo(id_prestamo)
);