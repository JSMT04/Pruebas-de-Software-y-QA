"""
Módulo de pipeline ETL para carga de datos de clientes.

Lee un archivo CSV, normaliza los emails y los inserta en una base de datos
SQLite usando INSERT OR REPLACE para garantizar la idempotencia de la operación.
"""

import csv
import sqlite3

from etl.transform import normalizar_email


def ejecutar_pipeline(ruta_csv: str, con: sqlite3.Connection) -> dict:
    """
    Ejecuta el pipeline ETL: extrae datos de un CSV, transforma emails
    y los carga en la tabla 'clientes' de la base de datos SQLite.

    La operación es IDEMPOTENTE: ejecutar el pipeline varias veces sobre
    el mismo CSV produce siempre el mismo estado final en la base de datos,
    sin duplicar registros (gracias a INSERT OR REPLACE sobre PRIMARY KEY).

    Args:
        ruta_csv: Ruta al archivo CSV con columnas 'nombre' y 'email'.
        con: Conexión activa a una base de datos SQLite.

    Returns:
        Diccionario con estadísticas de ejecución:
        - 'insertados': Número de registros insertados o actualizados exitosamente.
        - 'errores': Número de filas omitidas por email inválido o clave faltante.

    Example:
        >>> import sqlite3
        >>> con = sqlite3.connect(":memory:")
        >>> resultado = ejecutar_pipeline("clientes.csv", con)
        >>> resultado["insertados"]
        3
    """
    # Crear tabla si no existe (operación idempotente)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            email  TEXT PRIMARY KEY,
            nombre TEXT NOT NULL
        )
        """
    )

    insertados = 0
    errores = 0

    with open(ruta_csv, newline="", encoding="utf-8") as archivo_csv:
        lector = csv.DictReader(archivo_csv)
        for fila in lector:
            try:
                email_limpio = normalizar_email(fila["email"])
                nombre = fila["nombre"].strip()
                con.execute(
                    "INSERT OR REPLACE INTO clientes (email, nombre) VALUES (?, ?)",
                    (email_limpio, nombre),
                )
                insertados += 1
            except (ValueError, KeyError):
                errores += 1

    con.commit()
    return {"insertados": insertados, "errores": errores}
