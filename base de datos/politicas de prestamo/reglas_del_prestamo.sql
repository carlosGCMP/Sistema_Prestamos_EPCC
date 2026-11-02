CREATE TABLE IF NOT EXISTS reglas_del_prestamo (
    id_regla BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tipo_bien BIGINT NOT NULL,
    tipo_solicitante VARCHAR(30) NOT NULL,
    cantidad_maxima_prestamos INT NOT NULL,
    cantidad_maxima_bienes INT NOT NULL,
    permitido BOOLEAN NOT NULL DEFAULT TRUE,

    FOREIGN KEY (id_tipo_bien) REFERENCES tipo_de_bien(id_tipo_bien),

    UNIQUE (id_tipo_bien, tipo_solicitante)
);