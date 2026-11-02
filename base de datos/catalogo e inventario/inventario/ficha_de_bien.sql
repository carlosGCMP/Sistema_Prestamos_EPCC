CREATE TABLE IF NOT EXISTS ficha_de_bien (
    id_ficha BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_bien BIGINT NOT NULL UNIQUE,
    id_solicitante BIGINT NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_bien) REFERENCES bien(id_bien),
    FOREIGN KEY (id_solicitante) REFERENCES solicitante(id_solicitante)
);