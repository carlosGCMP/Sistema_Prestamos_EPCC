CREATE TABLE IF NOT EXISTS version_de_la_politica (
    id_version BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_politica BIGINT NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    contenido TEXT NOT NULL,

    FOREIGN KEY (id_politica) REFERENCES politicas_del_prestamo(id_politica)
);