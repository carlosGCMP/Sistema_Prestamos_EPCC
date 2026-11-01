CREATE TABLE IF NOT EXISTS ubicacion_del_bien (
    id_ubicacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_unidad_fisica BIGINT NOT NULL,
    ubicacion VARCHAR(100) NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_unidad_fisica) REFERENCES unidad_fisica(id_unidad_fisica)
);