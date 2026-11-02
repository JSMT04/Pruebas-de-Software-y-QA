"""
Pruebas de integración para el pipeline ETL y el módulo de reportes.

Cubre los requisitos de la rúbrica:
- Fixtures con sqlite3.connect(":memory:") y tmp_path.
- Prueba explícita de IDEMPOTENCIA: 2 ejecuciones → mismo número de filas.
- Prueba de comportamiento ante CSV con emails inválidos.
- Prueba de resistencia a SQL Injection en buscar_cliente (versión corregida).
- Pruebas de evaluar_expresion, procesar_datos y obtener_password.
"""

import os
import sqlite3

import pytest

from etl.pipeline import ejecutar_pipeline
from etl.reportes import buscar_cliente, evaluar_expresion, obtener_password, procesar_datos


# ═══════════════════════════════════════════════════════════════
#  Fixtures compartidos
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def con():
    """Proporciona una conexión SQLite en memoria, aislada por prueba."""
    conexion = sqlite3.connect(":memory:")
    yield conexion
    conexion.close()


@pytest.fixture
def csv_valido(tmp_path):
    """CSV con 3 registros completamente válidos."""
    archivo = tmp_path / "clientes_validos.csv"
    contenido = (
        "nombre,email\n"
        "Alice Gómez,alice@test.com\n"
        "Bob Smith,BOB@TEST.COM\n"       # Mayúsculas → se normalizan
        "Carla López,  carla@test.com  " # Espacios → se limpian
    )
    archivo.write_text(contenido, encoding="utf-8")
    return str(archivo)


@pytest.fixture
def csv_con_invalidos(tmp_path):
    """CSV con 1 email válido y 2 inválidos."""
    archivo = tmp_path / "clientes_mixtos.csv"
    contenido = (
        "nombre,email\n"
        "Alice Gómez,alice@test.com\n"  # Válido
        "Bob Smith,sin-arroba\n"        # Inválido — sin @
        "Carla López,\n"                # Inválido — vacío
    )
    archivo.write_text(contenido, encoding="utf-8")
    return str(archivo)


# ═══════════════════════════════════════════════════════════════
#  Pruebas de integración del pipeline
# ═══════════════════════════════════════════════════════════════


def test_pipeline_inserta_registros_validos(con, csv_valido):
    """El pipeline debe insertar exactamente 3 registros desde el CSV válido."""
    resultado = ejecutar_pipeline(csv_valido, con)

    assert resultado["insertados"] == 3
    assert resultado["errores"] == 0

    total_filas = con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    assert total_filas == 3


def test_pipeline_normaliza_emails(con, csv_valido):
    """Los emails deben almacenarse normalizados (minúsculas, sin espacios)."""
    ejecutar_pipeline(csv_valido, con)

    emails = {row[0] for row in con.execute("SELECT email FROM clientes")}
    assert "bob@test.com" in emails       # BOB@TEST.COM → normalizado
    assert "carla@test.com" in emails     # espacios eliminados
    assert "alice@test.com" in emails


def test_pipeline_idempotencia(con, csv_valido):
    """
    PRUEBA DE IDEMPOTENCIA:
    Ejecutar el pipeline dos veces seguidas sobre el mismo CSV debe dejar
    exactamente el mismo número de filas, sin duplicar registros.

    Garantizado por INSERT OR REPLACE sobre email PRIMARY KEY.
    """
    # Primera ejecución
    resultado_1 = ejecutar_pipeline(csv_valido, con)
    filas_tras_primera = con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]

    # Segunda ejecución sobre los mismos datos
    resultado_2 = ejecutar_pipeline(csv_valido, con)
    filas_tras_segunda = con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]

    # Ambas ejecuciones deben insertar los mismos registros (REPLACE los existentes)
    assert resultado_1["insertados"] == 3
    assert resultado_2["insertados"] == 3

    # El conteo de filas debe ser EXACTAMENTE el mismo — sin duplicados
    assert filas_tras_primera == filas_tras_segunda == 3


def test_pipeline_emails_invalidos_se_omiten(con, csv_con_invalidos):
    """
    El pipeline debe omitir silenciosamente los emails inválidos
    e insertar únicamente los válidos.
    """
    resultado = ejecutar_pipeline(csv_con_invalidos, con)

    assert resultado["insertados"] == 1
    assert resultado["errores"] == 2

    total_filas = con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    assert total_filas == 1


# ═══════════════════════════════════════════════════════════════
#  Prueba de seguridad — Resistencia a SQL Injection
# ═══════════════════════════════════════════════════════════════


def test_buscar_cliente_resiste_sql_injection(con, csv_valido):
    """
    Verifica que buscar_cliente (versión corregida con query parametrizada)
    NO devuelve registros ante un vector clásico de SQL Injection.

    Vector de ataque: ' OR '1'='1
    Sin parametrización, este vector devuelve TODOS los registros.
    Con query parametrizada, se busca literalmente ese string → lista vacía.
    """
    ejecutar_pipeline(csv_valido, con)

    # Vector clásico de SQL Injection
    vector_inyeccion = "' OR '1'='1"
    resultado = buscar_cliente(vector_inyeccion, con)

    # La consulta parametrizada debe retornar lista vacía (ningún cliente
    # tiene ese string exacto como email)
    assert resultado == [], (
        f"FALLO DE SEGURIDAD: buscar_cliente devolvió {len(resultado)} registros "
        f"con el vector de inyección '{vector_inyeccion}'"
    )


def test_buscar_cliente_encuentra_registro_existente(con, csv_valido):
    """buscar_cliente debe encontrar registros que sí existen."""
    ejecutar_pipeline(csv_valido, con)

    resultado = buscar_cliente("alice@test.com", con)
    assert len(resultado) == 1
    assert resultado[0][0] == "alice@test.com"


# ═══════════════════════════════════════════════════════════════
#  Pruebas de evaluar_expresion (módulo reportes — versión segura)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "expresion, esperado",
    [
        ("2 + 2", 4),
        ("10 * 3 - 5", 25),
        ("100 / 4", 25.0),
        ("2 ** 8", 256),
    ],
)
def test_evaluar_expresion_validas(expresion, esperado):
    """Expresiones matemáticas válidas deben evaluarse correctamente."""
    assert evaluar_expresion(expresion) == esperado


@pytest.mark.parametrize(
    "expresion_prohibida",
    [
        "__import__('os').system('ls')",  # Llamada de función prohibida
        "1 +",                            # Sintaxis inválida
    ],
)
def test_evaluar_expresion_prohibidas(expresion_prohibida):
    """Expresiones con operaciones prohibidas o sintaxis inválida deben lanzar ValueError."""
    with pytest.raises(ValueError):
        evaluar_expresion(expresion_prohibida)


# ═══════════════════════════════════════════════════════════════
#  Pruebas de procesar_datos (módulo reportes — versión segura)
# ═══════════════════════════════════════════════════════════════


def test_procesar_datos_clave_existente():
    """procesar_datos debe retornar el valor de 'clave' si existe."""
    assert procesar_datos({"clave": 42}) == 42


@pytest.mark.parametrize(
    "datos_invalidos",
    [
        {},     # Diccionario sin la clave 'clave'
        None,   # No es un diccionario
    ],
)
def test_procesar_datos_invalidos(datos_invalidos):
    """procesar_datos debe lanzar ValueError cuando los datos son inválidos."""
    with pytest.raises(ValueError):
        procesar_datos(datos_invalidos)


# ═══════════════════════════════════════════════════════════════
#  Pruebas de obtener_password (módulo reportes — versión segura)
# ═══════════════════════════════════════════════════════════════


def test_obtener_password_con_variable_configurada(monkeypatch):
    """obtener_password debe retornar el valor de DB_PASSWORD si está definida."""
    monkeypatch.setenv("DB_PASSWORD", "mi_password_seguro")
    assert obtener_password() == "mi_password_seguro"


def test_obtener_password_sin_variable(monkeypatch):
    """obtener_password debe lanzar EnvironmentError si DB_PASSWORD no está definida."""
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    with pytest.raises(EnvironmentError):
        obtener_password()
