CREATE TABLE IF NOT EXISTS categoria_del_bien (
    id_categoria BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tipo_bien BIGINT NOT NULL,
    nombre_categoria VARCHAR(100) NOT NULL,

    FOREIGN KEY (id_tipo_bien) REFERENCES tipo_de_bien(id_tipo_bien),

    UNIQUE (id_tipo_bien, nombre_categoria)
);