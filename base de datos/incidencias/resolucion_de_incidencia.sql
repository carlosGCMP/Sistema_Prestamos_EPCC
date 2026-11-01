CREATE TABLE IF NOT EXISTS resolucion_de_incidencia (
    id_resolucion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_incidencia BIGINT NOT NULL UNIQUE,
    fecha_resolucion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,

    FOREIGN KEY (id_incidencia) REFERENCES incidencia(id_incidencia)
);