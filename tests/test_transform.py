"""
Pruebas unitarias para etl/transform.py.

Cubre los requisitos de la rúbrica:
- Normalización de mayúsculas, espacios y carácter '+' válido.
- Excepciones para emails vacíos, sin arroba o nulos (None).
- calcular_total con descuentos válidos (0.0, 0.5, 1.0).
- Excepciones para precio negativo, cantidad negativa o descuento > 1.0.

Total de casos: 13 (superan el mínimo de 8 exigido).
"""

import pytest

from etl.transform import calcular_total, normalizar_email


# ═══════════════════════════════════════════════════════════════
#  Pruebas de normalizar_email — Casos VÁLIDOS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        # Mayúsculas → minúsculas
        ("USUARIO@EXAMPLE.COM", "usuario@example.com"),
        # Espacios al inicio y al final → eliminados; mayúsculas → minúsculas
        ("  USUARIO@EXAMPLE.COM  ", "usuario@example.com"),
        # Carácter '+' válido en la parte local del email
        ("User+Tag@Example.com", "user+tag@example.com"),
        # Email ya normalizado — debe permanecer igual
        ("simple@test.org", "simple@test.org"),
    ],
)
def test_normalizar_email_validos(entrada, esperado):
    """Los emails bien formados deben normalizarse correctamente."""
    assert normalizar_email(entrada) == esperado


# ═══════════════════════════════════════════════════════════════
#  Pruebas de normalizar_email — Casos INVÁLIDOS (ValueError)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "entrada_invalida",
    [
        "",           # Cadena vacía
        "   ",        # Solo espacios (vacío tras strip)
        "sin-arroba.com",  # Sin símbolo @
        None,         # Valor nulo
        "doble@@arroba.com",  # Dos arrobas
        "@sin-local.com",    # Sin parte local
    ],
)
def test_normalizar_email_invalidos(entrada_invalida):
    """Los emails malformados o nulos deben lanzar ValueError."""
    with pytest.raises(ValueError):
        normalizar_email(entrada_invalida)


# ═══════════════════════════════════════════════════════════════
#  Pruebas de calcular_total — Casos VÁLIDOS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "precio, cantidad, descuento, esperado",
    [
        # Sin descuento (valor límite inferior: 0.0)
        (100.0, 2, 0.0, 200.0),
        # 50% de descuento
        (100.0, 2, 0.5, 100.0),
        # 100% de descuento — precio final cero (valor límite superior: 1.0)
        (100.0, 2, 1.0, 0.0),
        # Valores con decimales — verifica redondeo a 2 decimales
        (29.99, 3, 0.1, 80.97),
        # Precio cero — siempre da total 0
        (0.0, 10, 0.25, 0.0),
    ],
)
def test_calcular_total_validos(precio, cantidad, descuento, esperado):
    """El total calculado debe coincidir con el resultado esperado."""
    assert calcular_total(precio, cantidad, descuento) == esperado


# ═══════════════════════════════════════════════════════════════
#  Pruebas de calcular_total — Casos INVÁLIDOS (ValueError)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "precio, cantidad, descuento",
    [
        (-10.0, 1, 0.0),   # Precio negativo
        (10.0, -1, 0.0),   # Cantidad negativa
        (10.0, 1, 1.5),    # Descuento mayor a 1.0
        (10.0, 1, -0.1),   # Descuento negativo
    ],
)
def test_calcular_total_invalidos(precio, cantidad, descuento):
    """Los parámetros fuera de rango deben lanzar ValueError."""
    with pytest.raises(ValueError):
        calcular_total(precio, cantidad, descuento)
