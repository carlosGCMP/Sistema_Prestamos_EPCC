CREATE TABLE IF NOT EXISTS historial_de_cambios (
    id_historial BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_registro BIGINT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descripcion TEXT NOT NULL,

    FOREIGN KEY (id_registro) REFERENCES registro_auditoria(id_registro)
);