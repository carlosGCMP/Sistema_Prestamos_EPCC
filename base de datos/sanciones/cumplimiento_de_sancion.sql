CREATE TABLE IF NOT EXISTS cumplimiento_de_sancion (
    id_cumplimiento BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sancion BIGINT NOT NULL UNIQUE,
    fecha_cumplimiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,

    FOREIGN KEY (id_sancion) REFERENCES sancion(id_sancion)
);