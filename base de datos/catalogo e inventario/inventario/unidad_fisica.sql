CREATE TABLE IF NOT EXISTS unidad_fisica (
    id_unidad_fisica BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ficha BIGINT NOT NULL UNIQUE,
    numero_serie VARCHAR(100) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'disponible',
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_ficha) REFERENCES ficha_de_bien(id_ficha)
);