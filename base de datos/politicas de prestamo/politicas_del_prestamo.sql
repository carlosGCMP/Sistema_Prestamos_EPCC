CREATE TABLE IF NOT EXISTS politicas_del_prestamo (
    id_politica BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_tipo_bien BIGINT NOT NULL,
    tipo_solicitante VARCHAR(30) NOT NULL,
    tiempo_maximo_prestamo INT NOT NULL,
    tiempo_maximo_prorroga INT NOT NULL,
    cantidad_maxima_prorrogas INT NOT NULL,

    FOREIGN KEY (id_tipo_bien) REFERENCES tipo_de_bien(id_tipo_bien),

    UNIQUE (id_tipo_bien, tipo_solicitante)
);