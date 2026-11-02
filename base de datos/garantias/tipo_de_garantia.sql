CREATE TABLE IF NOT EXISTS tipo_de_garantia (
    id_tipo_garantia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_tipo_garantia VARCHAR(100) NOT NULL UNIQUE
);