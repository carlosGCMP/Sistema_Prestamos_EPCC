CREATE TABLE IF NOT EXISTS tipo_de_incidencia (
    id_tipo_incidencia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_tipo_incidencia VARCHAR(100) NOT NULL UNIQUE
);