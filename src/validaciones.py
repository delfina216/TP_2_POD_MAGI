"""
validaciones.py — Reglas de validación reutilizables (Paso 4: expresión regular
y validaciones con mensajes comprensibles).

Se separan en un módulo propio porque las usan tanto pipeline.py (para limpiar
los datos) como modelo.py (para validar los parámetros que escribe el usuario).
"""

import re
import unicodedata
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Expresiones regulares
# ---------------------------------------------------------------------------

PATRON_FECHA_DMA = re.compile(
    r"^(?P<dia>\d{2})/(?P<mes>\d{2})/(?P<anio>\d{4})"
    r"(?: (?P<hora>\d{2}):(?P<minuto>\d{2})(?::(?P<segundo>\d{2}))?)?$"
)

# Fecha (y hora opcional) tal como puede venir en el dataset:
#   2026-09-15
#   2026-09-15 10:30
#   2026-09-15 10:30:00
#   2026-09-15T10:30:00.000Z   (variante ISO 8601)
# Grupos: año, mes, día, hora, minuto, segundo.
PATRON_FECHA_ISO = re.compile(
    r"^(?P<anio>\d{4})-(?P<mes>\d{2})-(?P<dia>\d{2})"          # AAAA-MM-DD (obligatorio)
    r"(?:[ T](?P<hora>\d{2}):(?P<minuto>\d{2})(?::(?P<segundo>\d{2}))?"  # hora opcional HH:MM[:SS]
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"  # fracción y zona horaria opcionales
)

PATRONES_FECHA_DATO = (PATRON_FECHA_DMA, PATRON_FECHA_ISO)

# Fecha de consulta que escribe el usuario: solo AAAA-MM-DD.
PATRON_FECHA_CONSULTA = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

# Límites de plausibilidad (documentados en el README).
FECHA_MINIMA = date(2016, 1, 1)   # el sistema de la Res. 314/2016 empieza ese año
PRECIO_MAXIMO = 100_000.0         # $/unidad; cota de sentido común contra errores de carga


class ErrorValidacion(ValueError):
    """Un valor no cumple una regla. El mensaje explica cuál y por qué."""


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def normalizar_texto(texto):
    """Pasa a mayúsculas, quita tildes y espacios repetidos.

    Así 'Rosario', ' ROSARIO ' y 'rosário' se comparan como iguales.
    Ejemplo: normalizar_texto('  Cañada  de Gómez ') -> 'CANADA DE GOMEZ'
    """
    if texto is None:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return " ".join(sin_tildes.upper().split())


# ---------------------------------------------------------------------------
# Fechas: la regex controla el FORMATO; datetime controla el CALENDARIO.
# ---------------------------------------------------------------------------

def parsear_fecha_dato(texto):
    """Convierte la fecha de vigencia del dataset en datetime.

    Dos controles, porque una regex sola no alcanza:
      1) la regex verifica que el texto TENGA forma de fecha;
      2) datetime(...) verifica que la fecha EXISTA (rechaza 2026-02-30, mes 13,
         hora 25, etc.).
    """
    texto_limpio = (texto or "").strip()
    coincidencia = None
    for patron in PATRONES_FECHA_DATO:
        coincidencia = patron.match(texto_limpio)
        if coincidencia:
            break
    if not coincidencia:
        raise ErrorValidacion(f"fecha con formato inválido: '{texto}'")
    partes = coincidencia.groupdict()
    try:
        fecha = datetime(
            int(partes["anio"]), int(partes["mes"]), int(partes["dia"]),
            int(partes["hora"] or 0), int(partes["minuto"] or 0),
            int(partes["segundo"] or 0),
        )
    except ValueError:
        raise ErrorValidacion(f"fecha inexistente en el calendario: '{texto}'") from None
    if fecha.date() < FECHA_MINIMA:
        raise ErrorValidacion(f"fecha anterior a {FECHA_MINIMA}: '{texto}'")
    return fecha


def parsear_fecha_consulta(texto):
    """Valida la fecha que escribe el usuario (AAAA-MM-DD) y devuelve un date."""
    coincidencia = PATRON_FECHA_CONSULTA.match((texto or "").strip())
    if not coincidencia:
        raise ErrorValidacion(
            f"La fecha de consulta '{texto}' debe tener el formato AAAA-MM-DD "
            f"(por ejemplo 2026-09-30)."
        )
    anio, mes, dia = (int(g) for g in coincidencia.groups())
    try:
        return date(anio, mes, dia)
    except ValueError:
        raise ErrorValidacion(
            f"La fecha de consulta '{texto}' no existe en el calendario."
        ) from None


# ---------------------------------------------------------------------------
# Precios
# ---------------------------------------------------------------------------

def convertir_precio(texto):
    """Convierte el precio a float y controla que esté en un rango plausible.

    Acepta punto decimal ('1250.50') y, si no hay punto, coma decimal ('1250,50').
    """
    limpio = (texto or "").strip()
    if not limpio:
        raise ErrorValidacion("precio faltante")
    if "," in limpio and "." not in limpio:
        limpio = limpio.replace(",", ".")
    try:
        precio = float(limpio)
    except ValueError:
        raise ErrorValidacion(f"precio no numérico: '{texto}'") from None
    if precio != precio:  # NaN no es igual a sí mismo
        raise ErrorValidacion(f"precio no numérico: '{texto}'")
    if precio <= 0:
        raise ErrorValidacion(f"precio no positivo: {precio}")
    if precio > PRECIO_MAXIMO:
        raise ErrorValidacion(f"precio fuera de rango (> {PRECIO_MAXIMO:.0f}): {precio}")
    return precio
