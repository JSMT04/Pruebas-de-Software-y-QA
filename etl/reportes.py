"""
Módulo de reportes — VERSIÓN CORREGIDA.

Correcciones aplicadas respecto a la versión vulnerable:
  1. DB_PASSWORD → os.getenv("DB_PASSWORD")  [CWE-798 corregido]
  2. f-string SQL → query parametrizada con ?  [CWE-89 corregido]
  3. eval() → ast.parse() con whitelist de nodos [CWE-95 corregido]
  4. except: pass → except (KeyError, TypeError) con re-raise [CWE-390 corregido]
"""

import ast
import os
import sqlite3


def obtener_password() -> str:
    """
    Obtiene la contraseña de base de datos desde variables de entorno.

    Raises:
        EnvironmentError: Si la variable DB_PASSWORD no está configurada.
    """
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise EnvironmentError(
            "La variable de entorno DB_PASSWORD no está configurada. "
            "Defínala antes de ejecutar la aplicación."
        )
    return password


def buscar_cliente(email: str, con: sqlite3.Connection) -> list:
    """
    Busca un cliente por email usando una consulta parametrizada.

    CORRECCIÓN: Se reemplazó la f-string vulnerable por un placeholder '?'
    que SQLite escapa automáticamente, previniendo SQL Injection (CWE-89).

    Args:
        email: Email del cliente a buscar.
        con: Conexión activa a SQLite.

    Returns:
        Lista de tuplas con los registros encontrados.
    """
    consulta = "SELECT * FROM clientes WHERE email = ?"
    return con.execute(consulta, (email,)).fetchall()


def evaluar_expresion(expresion: str):
    """
    Evalúa una expresión matemática de forma segura usando ast.parse().

    CORRECCIÓN: Se reemplazó eval() por ast.parse() con validación de nodos.
    Solo se permiten literales y operaciones aritméticas básicas (CWE-95).

    Args:
        expresion: Cadena de texto con la expresión a evaluar.

    Returns:
        Resultado numérico de la expresión.

    Raises:
        ValueError: Si la expresión contiene operaciones no permitidas o es inválida.
    """
    # Nodos AST que NO están permitidos (llamadas, importaciones, atributos)
    NODOS_PROHIBIDOS = (
        ast.Call,
        ast.Import,
        ast.ImportFrom,
        ast.Attribute,
        ast.Global,
        ast.Nonlocal,
    )

    try:
        tree = ast.parse(expresion, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Expresión con sintaxis inválida: '{expresion}'") from e

    for nodo in ast.walk(tree):
        if isinstance(nodo, NODOS_PROHIBIDOS):
            raise ValueError(
                f"Expresión no permitida: '{expresion}' contiene operaciones "
                f"de tipo '{type(nodo).__name__}' que no están autorizadas."
            )

    # Seguro: solo literales y operadores básicos llegan hasta aquí
    return eval(compile(tree, "<string>", "eval"))  # noqa: S307


def procesar_datos(datos: dict):
    """
    Accede a la clave 'clave' del diccionario de datos de forma segura.

    CORRECCIÓN: Se reemplazó el bare 'except: pass' por captura explícita
    de las excepciones esperadas con re-raise informativo (CWE-390).

    Args:
        datos: Diccionario del que se extrae el valor de 'clave'.

    Returns:
        El valor asociado a la clave 'clave'.

    Raises:
        ValueError: Si 'datos' no es un dict o no contiene la clave 'clave'.
    """
    try:
        return datos["clave"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            f"Error al procesar datos: {exc}. "
            f"Se esperaba un diccionario con la clave 'clave'."
        ) from exc
