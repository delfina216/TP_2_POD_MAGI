"""
fuentes.py — Lectura de datos (Paso 4 de la consigna: abstracción común para fuentes).

Idea central:
    FuenteDatos es una clase base abstracta que define UN contrato: cargar(ruta).
    FuenteCSV y FuenteJSON cumplen ese contrato, cada una con su formato.
    Las dos devuelven la misma ESTRUCTURA:
        una lista de diccionarios {nombre_columna: valor_en_texto}.
    El texto de un mismo número puede variar ('1275.50' en CSV, '1275.5' en JSON,
    que no guarda ceros finales); por eso la equivalencia entre formatos se
    comprueba después de convertir los tipos, en la limpieza.

¿Por qué devolver todo como texto?
    En un CSV todo llega como texto ("1250.5"); en un JSON el precio puede llegar
    como número (1250.5). Si cada fuente devolviera tipos distintos, el resto del
    programa tendría que saber de qué archivo vinieron los datos. Uniformando a
    texto acá, la conversión de tipos se hace UNA sola vez, en pipeline.py, y el
    resto del programa no depende del formato de origen (eso pide la consigna).
"""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path


class ErrorLectura(Exception):
    """Se lanza cuando un archivo no existe o no tiene la estructura esperada."""


class FuenteDatos(ABC):
    """Contrato común para cualquier fuente de datos tabulares.

    Usa el patrón "método plantilla": cargar() hace los pasos comunes
    (verificar que el archivo exista, uniformar los valores) y delega en
    _leer() lo único que cambia entre formatos.
    """

    extension = ""  # cada subclase indica qué extensión maneja

    def cargar(self, ruta):
        """Lee el archivo y devuelve una lista de diccionarios con valores en texto."""
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorLectura(f"No se encontró el archivo de datos: {ruta}")
        try:
            filas = self._leer(ruta)
        except UnicodeDecodeError as e:
            raise ErrorLectura(f"El archivo {ruta} no está en UTF-8: {e}") from e
        if not filas:
            raise ErrorLectura(f"El archivo {ruta} no contiene registros.")
        return [self._uniformar(fila) for fila in filas]

    @abstractmethod
    def _leer(self, ruta):
        """Cada formato implementa cómo se lee. Debe devolver una lista de dicts."""

    @staticmethod
    def _uniformar(fila):
        """Convierte cada valor a texto sin espacios sobrantes; None pasa a ''."""
        return {
            str(clave).strip(): ("" if valor is None else str(valor).strip())
            for clave, valor in fila.items()
        }


class FuenteCSV(FuenteDatos):
    """Lee archivos CSV con encabezado en la primera fila."""

    extension = ".csv"

    def _leer(self, ruta):
        # utf-8-sig: si el archivo trae BOM (marca invisible que agrega Excel),
        # se descarta y no "ensucia" el nombre de la primera columna.
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            lector = csv.DictReader(f)
            if not lector.fieldnames:
                raise ErrorLectura(f"El CSV {ruta} no tiene fila de encabezado.")
            return list(lector)


class FuenteJSON(FuenteDatos):
    """Lee archivos JSON cuya raíz es una LISTA de objetos (estructura acordada).

    Ejemplo válido:
        [ {"localidad": "ROSARIO", "precio": 1250.5, ...}, {...} ]
    """

    extension = ".json"

    def _leer(self, ruta):
        with open(ruta, encoding="utf-8") as f:
            try:
                contenido = json.load(f)
            except json.JSONDecodeError as e:
                raise ErrorLectura(f"El JSON {ruta} está mal formado: {e}") from e
        if not isinstance(contenido, list):
            raise ErrorLectura(
                f"El JSON {ruta} debe ser una lista de objetos; "
                f"se encontró {type(contenido).__name__}."
            )
        for i, elemento in enumerate(contenido):
            if not isinstance(elemento, dict):
                raise ErrorLectura(f"El elemento {i} del JSON {ruta} no es un objeto.")
        return contenido


def obtener_fuente(ruta):
    """Elige la fuente según la extensión del archivo (polimorfismo).

    main.py no necesita saber si el archivo es CSV o JSON: pide una fuente
    y llama a cargar(). Para agregar un formato nuevo alcanza con otra subclase.
    """
    sufijo = Path(ruta).suffix.lower()
    for clase in (FuenteCSV, FuenteJSON):
        if clase.extension == sufijo:
            return clase()
    raise ErrorLectura(
        f"Formato no soportado: '{sufijo}'. Se aceptan archivos .csv y .json."
    )
