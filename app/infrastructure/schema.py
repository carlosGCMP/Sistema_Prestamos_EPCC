"""Comprobación del esquema sin cambiar columnas, convertir datos ni ejecutar SQL externo."""

from sqlalchemy import Connection, Enum, MetaData, inspect


def validar_esquema(conexion: Connection, metadata: MetaData) -> None:
    """Impide inicializar sobre tablas incompatibles antes de crear otras nuevas."""
    inspector = inspect(conexion)
    tablas_existentes = set(inspector.get_table_names())
    antiguas = tablas_existentes & {"accounts", "categories", "reservations", "physical_units"}
    if antiguas:
        raise RuntimeError(
            "Esta base conserva el esquema anterior en inglés. No se crearon tablas paralelas. "
            "Respalda los datos y utiliza una base vacía "
            "o recrea expresamente la base de desarrollo."
        )
    problemas: list[str] = []

    for tabla in metadata.sorted_tables:
        if tabla.name not in tablas_existentes:
            continue

        columnas = {columna["name"]: columna for columna in inspector.get_columns(tabla.name)}
        for columna in tabla.columns:
            nombre = f"{tabla.name}.{columna.name}"
            if columna.name not in columnas:
                problemas.append(f"Falta la columna {nombre}.")
                continue

            actual = columnas[columna.name]
            tipo_esperado = columna.type.compile(dialect=conexion.dialect)
            tipo_actual = actual["type"].compile(dialect=conexion.dialect)
            if tipo_actual != tipo_esperado:
                problemas.append(f"{nombre}: tipo {tipo_actual}; se esperaba {tipo_esperado}.")
            if actual["nullable"] != columna.nullable:
                problemas.append(f"{nombre}: la restricción de valores nulos no coincide.")

            if isinstance(columna.type, Enum) and isinstance(actual["type"], Enum):
                valores_faltantes = set(columna.type.enums) - set(actual["type"].enums)
                if valores_faltantes:
                    valores = ", ".join(sorted(valores_faltantes))
                    problemas.append(f"{nombre}: faltan los estados o roles {valores}.")

        clave_actual = inspector.get_pk_constraint(tabla.name)["constrained_columns"]
        clave_esperada = [columna.name for columna in tabla.primary_key]
        if clave_actual != clave_esperada:
            problemas.append(f"{tabla.name}: la clave primaria no coincide con el modelo.")

        for nombre, columna_extra in columnas.items():
            if (
                nombre not in tabla.columns
                and not columna_extra["nullable"]
                and columna_extra.get("default") is None
                and not columna_extra.get("identity")
                and not columna_extra.get("computed")
            ):
                problemas.append(f"{tabla.name}.{nombre}: columna obligatoria no prevista.")

    if problemas:
        raise RuntimeError(
            "La base de datos tiene un esquema incompatible con los modelos. "
            "No se modificaron sus tablas ni sus datos. "
            "Revisa la estructura o configura otra base vacía en DATABASE_URL.\n- "
            + "\n- ".join(problemas)
        )
