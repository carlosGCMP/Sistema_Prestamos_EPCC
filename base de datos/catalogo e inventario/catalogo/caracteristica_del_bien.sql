CREATE TABLE IF NOT EXISTS caracteristica_del_bien (
    id_caracteristica BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_categoria BIGINT NOT NULL,
    nombre_caracteristica VARCHAR(100) NOT NULL,

    FOREIGN KEY (id_categoria) REFERENCES categoria_del_bien(id_categoria),

    UNIQUE (id_categoria, nombre_caracteristica)
);