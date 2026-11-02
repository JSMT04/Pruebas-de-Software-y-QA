"""
Módulo de transformación para el pipeline ETL.

Implementa funciones de limpieza y validación de datos siguiendo
los principios de calidad ISO/IEC 25010 (Adecuación funcional, Fiabilidad).
"""

import re


def normalizar_email(email: str) -> str:
    """
    Limpia espacios, convierte a minúsculas y valida el formato del email.

    Args:
        email: Cadena de texto con el email a normalizar.

    Returns:
        Email normalizado (sin espacios, en minúsculas y validado).

    Raises:
        ValueError: Si el email es None, vacío o tiene formato inválido.

    Examples:
        >>> normalizar_email("  USUARIO@EXAMPLE.COM  ")
        'usuario@example.com'
        >>> normalizar_email("user+tag@example.org")
        'user+tag@example.org'
    """
    if email is None:
        raise ValueError("El email no puede ser nulo")

    email = email.strip().lower()

    if not email:
        raise ValueError("El email no puede estar vacío")

    # Patrón RFC 5322 simplificado — admite + en la parte local
    patron = r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$"
    if not re.match(patron, email):
        raise ValueError(f"Formato de email inválido: '{email}'")

    return email


def calcular_total(precio: float, cantidad: int, descuento: float = 0.0) -> float:
    """
    Calcula el total de una venta aplicando un descuento porcentual.

    Fórmula: total = precio * cantidad * (1 - descuento), redondeado a 2 decimales.

    Args:
        precio: Precio unitario del artículo (debe ser >= 0).
        cantidad: Número de unidades (debe ser >= 0).
        descuento: Fracción de descuento en el rango [0.0, 1.0]. Default: 0.0.

    Returns:
        Total calculado redondeado a 2 decimales.

    Raises:
        ValueError: Si precio < 0, cantidad < 0 o descuento no está en [0, 1].

    Examples:
        >>> calcular_total(100.0, 2, 0.5)
        100.0
        >>> calcular_total(29.99, 3, 0.1)
        80.97
    """
    if precio < 0:
        raise ValueError(f"El precio no puede ser negativo: {precio}")
    if cantidad < 0:
        raise ValueError(f"La cantidad no puede ser negativa: {cantidad}")
    if not (0.0 <= descuento <= 1.0):
        raise ValueError(
            f"El descuento debe estar en el rango [0, 1], recibido: {descuento}"
        )

    return round(precio * cantidad * (1 - descuento), 2)
