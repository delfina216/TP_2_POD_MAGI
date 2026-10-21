"""
pipeline.py — Flujo de procesamiento (Paso 3 de la consigna).

    leer → normalizar campos → validar esquema → limpiar (con rechazos)
         → seleccionar vigentes → buscar estaciones → verificar → exportar

Ninguna función de este módulo sabe si los datos vinieron de un CSV o de un
JSON: reciben la lista de diccionarios que entrega fuentes.py.
"""

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from validaciones import (
    ErrorValidacion,
    convertir_precio,
    normalizar_texto,
    parsear_fecha_dato,
)

# ---------------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------------

# Nombre de columna en el archivo original  ->  nombre interno del programa.
# Si el archivo descargado usa otros nombres, se ajusta SOLO este diccionario.
ALIAS_COLUMNAS = {
    "idempresa": "estacion_id",
    "empresa": "empresa",
    "empresabandera": "bandera",
    "direccion": "direccion",
    "localidad": "localidad",
    "provincia": "provincia",
    "producto": "producto",
    "tipohorario": "horario",
    "precio": "precio",
    "fecha_vigencia": "fecha_vigencia",
}

COLUMNAS_REQUERIDAS = (
    "estacion_id", "empresa", "direccion", "localidad",
    "provincia", "producto", "horario", "precio", "fecha_vigencia",
)
COLUMNAS_OPCIONALES = ("bandera",)


class ErrorEsquema(Exception):
    """Al archivo le faltan columnas necesarias para el análisis."""


class ErrorResultado(Exception):
    """El resultado no cumple una propiedad que debería cumplir siempre."""


def normalizar_campos(registros):
    """Renombra columnas a los nombres internos y descarta las que no se usan.

    Los encabezados se comparan en minúsculas y sin espacios, así 'Precio'
    y 'precio' se reconocen igual.
    """
    resultado = []
    for fila in registros:
        nueva = {}
        for clave, valor in fila.items():
            interna = ALIAS_COLUMNAS.get(clave.strip().lower())
            if interna:
                nueva[interna] = valor
        for opcional in COLUMNAS_OPCIONALES:
            nueva.setdefault(opcional, "")
        resultado.append(nueva)
    return resultado


def validar_esquema(registros):
    """Comprueba que estén todas las columnas requeridas. No modifica los datos."""
    if not registros:
        raise ErrorEsquema("No hay registros para analizar.")
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in registros[0]]
    if faltantes:
        originales = [k for k, v in ALIAS_COLUMNAS.items() if v in faltantes]
        raise ErrorEsquema(
            "Faltan columnas necesarias: " + ", ".join(originales)
            + ". Revisar ALIAS_COLUMNAS en pipeline.py si el archivo usa otros nombres."
        )


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------

def _clave(registro):
    """Identifica 'el mismo precio informado': estación + producto + horario + fecha."""
    return (registro["estacion_id"], registro["producto"],
            registro["horario"], registro["fecha_vigencia"])


def limpiar_datos(registros):
    """Convierte tipos, normaliza texto y separa registros válidos de rechazados.

    Devuelve (validos, rechazos). Cada rechazo conserva la fila original
    (numerada desde 1, como en una planilla) y el MOTIVO, para poder auditarlo.

    Decisiones de limpieza (también documentadas en el README):
      1. Campos de texto obligatorios vacíos → rechazo.
      2. Fecha con formato inválido o inexistente → rechazo.
      3. Precio faltante, no numérico, <= 0 o > PRECIO_MAXIMO → rechazo.
      4. Duplicado exacto (misma clave y mismo precio) → se conserva uno solo;
         las copias se rechazan como 'duplicado'.
      5. Contradicción (misma clave y PRECIOS DISTINTOS) → se rechazan todas las
         versiones, porque no hay criterio objetivo para elegir una.
    """
    candidatos, rechazos = [], []

    for numero, fila in enumerate(registros, start=1):
        try:
            candidatos.append((numero, fila, _convertir_fila(fila)))
        except ErrorValidacion as e:
            rechazos.append(_rechazo(numero, fila, str(e)))

    # Agrupar por clave para detectar duplicados y contradicciones.
    grupos = defaultdict(list)
    for numero, original, registro in candidatos:
        grupos[_clave(registro)].append((numero, original, registro))

    validos = []
    for grupo in grupos.values():
        precios = {registro["precio"] for _, _, registro in grupo}
        if len(precios) > 1:
            for numero, original, _ in grupo:
                rechazos.append(_rechazo(
                    numero, original,
                    "precio contradictorio: misma estación, producto, horario y fecha "
                    f"con precios distintos {sorted(precios)}",
                ))
            continue
        validos.append(grupo[0][2])  # se conserva la primera aparición
        for numero, original, _ in grupo[1:]:
            rechazos.append(_rechazo(numero, original, "duplicado exacto"))

    rechazos.sort(key=lambda r: r["fila"])
    return validos, rechazos


def _convertir_fila(fila):
    """Devuelve la fila con tipos correctos o lanza ErrorValidacion con el motivo."""
    registro = {}
    for campo in ("estacion_id", "empresa", "direccion", "localidad",
                  "provincia", "producto", "horario"):
        valor = normalizar_texto(fila.get(campo))
        if not valor:
            raise ErrorValidacion(f"campo '{campo}' vacío")
        registro[campo] = valor
    registro["bandera"] = normalizar_texto(fila.get("bandera"))
    registro["precio"] = convertir_precio(fila.get("precio"))
    registro["fecha_vigencia"] = parsear_fecha_dato(fila.get("fecha_vigencia"))
    return registro


def _rechazo(numero, fila, motivo):
    return {"fila": numero, "motivo": motivo, **fila}


# ---------------------------------------------------------------------------
# Análisis
# ---------------------------------------------------------------------------

def seleccionar_vigentes(validos, fecha_referencia):
    """Para cada estación + producto + horario, elige el precio vigente a la fecha.

    Precio vigente = el informado con la fecha MÁS RECIENTE que NO sea posterior
    al día consultado (se incluye todo ese día).

    Ejemplo: actualizaciones del 01/08, 10/09 y 05/10; consulta al 30/09
             → vigente el del 10/09 (el del 05/10 todavía no existía).
    """
    vigentes = {}
    for registro in validos:
        if registro["fecha_vigencia"].date() > fecha_referencia:
            continue  # actualización posterior a la consulta: se excluye
        clave = (registro["estacion_id"], registro["producto"], registro["horario"])
        actual = vigentes.get(clave)
        if actual is None or registro["fecha_vigencia"] > actual["fecha_vigencia"]:
            vigentes[clave] = registro
    return list(vigentes.values())


def buscar_estaciones(vigentes, consulta):
    """Aplica la consulta (localidad, producto, horario) y ordena por precio."""
    return consulta.aplicar(vigentes)


def buscar_desactualizadas(vigentes, consulta):
    return consulta.desactualizados(vigentes)


def listar_productos(validos, localidad=None):
    """Productos distintos disponibles (opcionalmente, en una localidad)."""
    loc = normalizar_texto(localidad) if localidad else None
    return sorted({r["producto"] for r in validos if loc is None or r["localidad"] == loc})


def verificar_resultado(resultado, consulta):
    """Controla propiedades que el resultado SIEMPRE debe cumplir.

    Si alguna falla, hay un error de programación: se avisa en lugar de
    entregar una respuesta incorrecta en silencio.
    """
    vistos = set()
    for registro in resultado:
        if registro["fecha_vigencia"].date() > consulta.fecha:
            raise ErrorResultado("Hay un precio posterior a la fecha de consulta.")
        if not consulta.es_reciente(registro):
            raise ErrorResultado(
                f"Hay un precio con más de {consulta.max_dias} días de antigüedad."
            )
        if not consulta.coincide(registro):
            raise ErrorResultado("Hay un registro que no coincide con la consulta.")
        if registro["estacion_id"] in vistos:
            raise ErrorResultado(f"Estación repetida: {registro['estacion_id']}.")
        vistos.add(registro["estacion_id"])
    precios = [r["precio"] for r in resultado]
    if precios != sorted(precios):
        raise ErrorResultado("El resultado no está ordenado por precio.")


def resumir_resultado(resultado):
    """Cantidad de estaciones, precio mínimo, máximo, promedio y diferencia %."""
    if not resultado:
        return {"estaciones": 0}
    precios = [r["precio"] for r in resultado]
    minimo, maximo = min(precios), max(precios)
    return {
        "estaciones": len(precios),
        "minimo": minimo,
        "maximo": maximo,
        "promedio": round(mean(precios), 2),
        "diferencia_pct": round(100 * (maximo - minimo) / minimo, 2),
    }


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------

COLUMNAS_SALIDA = ("posicion", "empresa", "bandera", "direccion", "localidad",
                   "producto", "horario", "precio", "vigente_desde", "estacion_id")


def exportar_consulta(resultado, ruta):
    """Guarda el ranking en CSV, con la fecha desde la que rige cada precio."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS_SALIDA)
        escritor.writeheader()
        for posicion, r in enumerate(resultado, start=1):
            escritor.writerow({
                "posicion": posicion,
                "empresa": r["empresa"],
                "bandera": r["bandera"],
                "direccion": r["direccion"],
                "localidad": r["localidad"],
                "producto": r["producto"],
                "horario": r["horario"],
                "precio": f"{r['precio']:.2f}",
                "vigente_desde": r["fecha_vigencia"].isoformat(sep=" "),
                "estacion_id": r["estacion_id"],
            })
    return ruta


def guardar_rechazos(rechazos, ruta):
    """Guarda las filas rechazadas con su número de fila y motivo."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    columnas = ["fila", "motivo"]
    for r in rechazos:
        columnas += [c for c in r if c not in columnas]
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas, restval="")
        escritor.writeheader()
        escritor.writerows(rechazos)
    return ruta
