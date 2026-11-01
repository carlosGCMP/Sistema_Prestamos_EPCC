CREATE TABLE IF NOT EXISTS prestamo_aprobado_de_reserva (
    id_prestamo_aprobado BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reserva BIGINT NOT NULL UNIQUE,
    fecha_aprobacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    CHECK (fecha_fin > fecha_inicio),

    FOREIGN KEY (id_reserva) REFERENCES registro_de_reserva(id_reserva)
);