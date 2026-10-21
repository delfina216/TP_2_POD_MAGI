"""
Pruebas de la aplicación (Paso 5 de la consigna).

Ejecutar desde la carpeta raíz del proyecto:
    python -m unittest discover -s tests -v

Los datos de prueba (tests/fixtures/) están construidos A MANO con valores
conocidos, para poder saber de antemano cuál es el resultado correcto.
Contienen 19 filas: 12 válidas y 7 que deben rechazarse por motivos distintos.
"""

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from fuentes import ErrorLectura, FuenteCSV, FuenteJSON, obtener_fuente  # noqa: E402
from modelo import ConsultaPrecio, ErrorConsulta  # noqa: E402
from pipeline import (  # noqa: E402
    ErrorEsquema,
    buscar_desactualizadas,
    buscar_estaciones,
    limpiar_datos,
    normalizar_campos,
    resumir_resultado,
    seleccionar_vigentes,
    validar_esquema,
    verificar_resultado,
)
from validaciones import (  # noqa: E402
    ErrorValidacion,
    convertir_precio,
    normalizar_texto,
    parsear_fecha_dato,
)

FIXTURES = RAIZ / "tests" / "fixtures"
CSV_PRUEBA = FIXTURES / "precios_prueba.csv"
JSON_PRUEBA = FIXTURES / "precios_prueba.json"
NAFTA = "Nafta (súper) entre 92 y 95 Ron"


def preparar(ruta):
    """Ejecuta el flujo hasta la limpieza, igual que main.py."""
    registros = normalizar_campos(obtener_fuente(ruta).cargar(ruta))
    validar_esquema(registros)
    return limpiar_datos(registros)


def consultar(ruta, localidad="Rosario", producto=NAFTA, fecha="2026-09-30", horario="Diurno",
              max_dias=ConsultaPrecio.MAX_DIAS_POR_DEFECTO):
    validos, _ = preparar(ruta)
    consulta = ConsultaPrecio(localidad, producto, fecha, horario, max_dias)
    resultado = buscar_estaciones(seleccionar_vigentes(validos, consulta.fecha), consulta)
    verificar_resultado(resultado, consulta)
    return resultado


# ---------------------------------------------------------------------------
# 1. Casos normales
# ---------------------------------------------------------------------------

class TestCasoNormal(unittest.TestCase):

    def test_estacion_con_varias_actualizaciones_devuelve_la_vigente(self):
        # Estación 101: 1200 (01/08), 1290 (10/09), 1350 (05/10).
        # Al 30/09 el precio vigente es 1290.
        resultado = consultar(CSV_PRUEBA)
        estacion_101 = [r for r in resultado if r["estacion_id"] == "101"]
        self.assertEqual(len(estacion_101), 1)
        self.assertEqual(estacion_101[0]["precio"], 1290.0)

    def test_ranking_completo_y_ordenado(self):
        resultado = consultar(CSV_PRUEBA)
        ids = [r["estacion_id"] for r in resultado]
        # 102 y 104 empatan en 1250: desempata el nombre de la empresa.
        self.assertEqual(ids, ["107", "102", "104", "103", "101", "106"])

    def test_resumen(self):
        resumen = resumir_resultado(consultar(CSV_PRUEBA))
        self.assertEqual(resumen["estaciones"], 6)
        self.assertEqual(resumen["minimo"], 1180.0)
        self.assertEqual(resumen["maximo"], 1299.0)

    def test_precio_del_mismo_dia_de_la_consulta_se_incluye(self):
        # Estación 107 actualizó el 30/09 a las 18:00: cuenta para el 30/09.
        resultado = consultar(CSV_PRUEBA)
        self.assertEqual(resultado[0]["estacion_id"], "107")
        self.assertEqual(resultado[0]["precio"], 1180.0)

    def test_normaliza_localidad_con_minusculas_y_espacios(self):
        # La estación 106 tiene localidad 'rosario ' y debe aparecer igual.
        ids = [r["estacion_id"] for r in consultar(CSV_PRUEBA, localidad="ROSARIO")]
        self.assertIn("106", ids)

    def test_no_mezcla_horarios(self):
        resultado = consultar(CSV_PRUEBA, horario="Nocturno")
        self.assertEqual([(r["estacion_id"], r["precio"]) for r in resultado], [("101", 1310.0)])

    def test_precio_viejo_queda_fuera_del_ranking(self):
        resultado = consultar(CSV_PRUEBA, max_dias=20)
        ids = [r["estacion_id"] for r in resultado]
        self.assertNotIn("103", ids)
        self.assertEqual(ids, ["107", "102", "104", "101", "106"])

    def test_estaciones_desactualizadas_se_informan(self):
        validos, _ = preparar(CSV_PRUEBA)
        consulta = ConsultaPrecio("Rosario", NAFTA, "2026-09-30", max_dias=20)
        viejas = buscar_desactualizadas(seleccionar_vigentes(validos, consulta.fecha), consulta)
        self.assertEqual([r["estacion_id"] for r in viejas], ["103"])


# ---------------------------------------------------------------------------
# 2. Entradas inválidas y casos límite
# ---------------------------------------------------------------------------

class TestEntradasInvalidas(unittest.TestCase):

    def test_localidad_sin_resultados_devuelve_lista_vacia(self):
        self.assertEqual(consultar(CSV_PRUEBA, localidad="Ushuaia"), [])

    def test_fecha_anterior_a_todos_los_datos_devuelve_lista_vacia(self):
        self.assertEqual(consultar(CSV_PRUEBA, fecha="2026-01-01"), [])

    def test_rechazos_con_motivo(self):
        _, rechazos = preparar(CSV_PRUEBA)
        motivos = {r["fila"]: r["motivo"] for r in rechazos}
        self.assertEqual(len(rechazos), 7)
        self.assertEqual(motivos[10], "duplicado exacto")
        self.assertIn("contradictorio", motivos[11])
        self.assertIn("contradictorio", motivos[12])
        self.assertIn("no numérico", motivos[13])
        self.assertIn("inexistente", motivos[14])
        self.assertIn("no positivo", motivos[15])
        self.assertIn("localidad", motivos[16])

    def test_fecha_de_consulta_mal_escrita(self):
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("Rosario", NAFTA, "30/09/2026")

    def test_fecha_de_consulta_inexistente(self):
        # Pasa la regex (formato correcto) pero no existe en el calendario.
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("Rosario", NAFTA, "2026-02-30")

    def test_horario_invalido(self):
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("Rosario", NAFTA, "2026-09-30", horario="Tarde")

    def test_antiguedad_maxima_invalida(self):
        for invalido in (0, -5, "abc", ""):
            with self.subTest(max_dias=invalido):
                with self.assertRaises(ErrorConsulta):
                    ConsultaPrecio("Rosario", NAFTA, "2026-09-30", max_dias=invalido)

    def test_localidad_vacia(self):
        with self.assertRaises(ErrorConsulta):
            ConsultaPrecio("   ", NAFTA, "2026-09-30")

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorLectura):
            FuenteCSV().cargar(FIXTURES / "no_existe.csv")

    def test_formato_no_soportado(self):
        with self.assertRaises(ErrorLectura):
            obtener_fuente("datos.xlsx")

    def test_json_que_no_es_lista(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "malo.json"
            ruta.write_text('{"precio": 100}', encoding="utf-8")
            with self.assertRaises(ErrorLectura):
                FuenteJSON().cargar(ruta)

    def test_faltan_columnas(self):
        registros = normalizar_campos([{"localidad": "Rosario", "precio": "100"}])
        with self.assertRaises(ErrorEsquema):
            validar_esquema(registros)


class TestValidaciones(unittest.TestCase):

    def test_regex_y_calendario_de_fechas(self):
        self.assertEqual(parsear_fecha_dato("2026-09-15").day, 15)
        self.assertEqual(parsear_fecha_dato("2026-09-15 10:30:00").hour, 10)
        self.assertEqual(parsear_fecha_dato("2026-09-15T10:30:00.000Z").minute, 30)
        for invalida in ("2026-9-15", "2026-09-15 25:00", "2026-13-01", "2015-12-31", ""):
            with self.subTest(invalida=invalida):
                with self.assertRaises(ErrorValidacion):
                    parsear_fecha_dato(invalida)

    def test_fecha_formato_archivo_oficial(self):
        fecha = parsear_fecha_dato("15/09/2026 10:30")
        self.assertEqual((fecha.year, fecha.month, fecha.day, fecha.hour, fecha.minute),
                         (2026, 9, 15, 10, 30))
        self.assertEqual(parsear_fecha_dato("01/04/2024 10:11"),
                         parsear_fecha_dato("2024-04-01 10:11"))
        for invalida in ("30/02/2026 10:00", "15/13/2026", "15/9/2026", "15-09-2026",
                         "01/01/0001 00:00", "02/12/2012 06:00"):
            with self.subTest(invalida=invalida):
                with self.assertRaises(ErrorValidacion):
                    parsear_fecha_dato(invalida)

    def test_precios(self):
        self.assertEqual(convertir_precio("1250.50"), 1250.5)
        self.assertEqual(convertir_precio("1250,50"), 1250.5)
        for invalido in ("", "abc", "0", "-3", "nan", "1000000"):
            with self.subTest(invalido=invalido):
                with self.assertRaises(ErrorValidacion):
                    convertir_precio(invalido)

    def test_normalizar_texto(self):
        self.assertEqual(normalizar_texto("  Cañada  de Gómez "), "CANADA DE GOMEZ")


# ---------------------------------------------------------------------------
# 3. Propiedades del resultado
# ---------------------------------------------------------------------------

class TestPropiedades(unittest.TestCase):

    def test_csv_y_json_equivalentes_dan_el_mismo_resultado(self):
        self.assertEqual(consultar(CSV_PRUEBA), consultar(JSON_PRUEBA))

    def test_csv_y_json_rechazan_las_mismas_filas(self):
        _, rechazos_csv = preparar(CSV_PRUEBA)
        _, rechazos_json = preparar(JSON_PRUEBA)
        self.assertEqual([(r["fila"], r["motivo"]) for r in rechazos_csv],
                         [(r["fila"], r["motivo"]) for r in rechazos_json])

    def test_ninguna_fila_se_pierde(self):
        # Conservación: leídas = válidas + rechazadas.
        registros = normalizar_campos(FuenteCSV().cargar(CSV_PRUEBA))
        validos, rechazos = limpiar_datos(registros)
        self.assertEqual(len(registros), len(validos) + len(rechazos))
        self.assertEqual((len(validos), len(rechazos)), (12, 7))

    def test_ningun_precio_posterior_a_la_consulta(self):
        for fecha in ("2026-08-15", "2026-09-30", "2026-10-31"):
            with self.subTest(fecha=fecha):
                resultado = consultar(CSV_PRUEBA, fecha=fecha)
                limite = date.fromisoformat(fecha)
                self.assertTrue(all(r["fecha_vigencia"].date() <= limite for r in resultado))

    def test_ningun_precio_mas_viejo_que_el_limite(self):
        for max_dias in (1, 10, 20, 90):
            with self.subTest(max_dias=max_dias):
                resultado = consultar(CSV_PRUEBA, max_dias=max_dias)
                limite = date(2026, 9, 30)
                self.assertTrue(all((limite - r["fecha_vigencia"].date()).days <= max_dias
                                    for r in resultado))

    def test_actualizacion_posterior_queda_excluida(self):
        # Al 30/09 la 107 vale 1180; su baja a 1170 (01/10) recién aplica desde el 01/10.
        self.assertEqual(consultar(CSV_PRUEBA, fecha="2026-09-30")[0]["precio"], 1180.0)
        self.assertEqual(consultar(CSV_PRUEBA, fecha="2026-10-01")[0]["precio"], 1170.0)

    def test_una_sola_fila_por_estacion(self):
        ids = [r["estacion_id"] for r in consultar(CSV_PRUEBA)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_mismas_entradas_mismo_resultado(self):
        self.assertEqual(consultar(CSV_PRUEBA), consultar(CSV_PRUEBA))


MUESTRA_CSV = RAIZ / "data" / "muestra.csv"
MUESTRA_JSON = RAIZ / "data" / "muestra.json"


@unittest.skipUnless(MUESTRA_CSV.is_file() and MUESTRA_JSON.is_file(),
                     "falta la muestra real en data/")
class TestMuestraReal(unittest.TestCase):

    def test_ninguna_fila_se_pierde_y_todas_son_validas(self):
        registros = normalizar_campos(obtener_fuente(MUESTRA_CSV).cargar(MUESTRA_CSV))
        validar_esquema(registros)
        validos, rechazos = limpiar_datos(registros)
        self.assertEqual(len(registros), len(validos) + len(rechazos))
        self.assertEqual(rechazos, [])

    def test_csv_y_json_reales_dan_el_mismo_resultado(self):
        resultado_csv = consultar(MUESTRA_CSV, fecha="2026-09-30")
        self.assertGreater(len(resultado_csv), 0)
        self.assertEqual(resultado_csv, consultar(MUESTRA_JSON, fecha="2026-09-30"))


if __name__ == "__main__":
    unittest.main()
