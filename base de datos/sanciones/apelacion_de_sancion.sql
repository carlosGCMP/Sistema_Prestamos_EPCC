CREATE TABLE IF NOT EXISTS apelacion_de_sancion (
    id_apelacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sancion BIGINT NOT NULL UNIQUE,
    fecha_apelacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,

    FOREIGN KEY (id_sancion) REFERENCES sancion(id_sancion)
);