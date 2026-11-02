CREATE TABLE IF NOT EXISTS administrador (
    id_administrador BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cuenta BIGINT NOT NULL UNIQUE,

    FOREIGN KEY (id_cuenta) REFERENCES cuenta(id_cuenta)
);