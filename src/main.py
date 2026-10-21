"""
main.py — Punto de entrada de la aplicación (Paso 3: ejecución desde una
instrucción documentada, sin depender de celdas de notebook).

Uso:
    python src/main.py --datos data/muestra.csv --localidad Rosario \
        --producto "Nafta (súper) entre 92 y 95 Ron" --fecha 2026-09-30

    python src/main.py --datos data/muestra.json --localidad Rosario --listar-productos

Códigos de salida: 0 = éxito, 1 = error de datos o de parámetros.
"""

import argparse
import sys
from pathlib import Path

from fuentes import ErrorLectura, obtener_fuente
from modelo import ConsultaPrecio, ErrorConsulta
from pipeline import (
    ErrorEsquema,
    ErrorResultado,
    buscar_desactualizadas,
    buscar_estaciones,
    exportar_consulta,
    guardar_rechazos,
    limpiar_datos,
    listar_productos,
    normalizar_campos,
    resumir_resultado,
    seleccionar_vigentes,
    validar_esquema,
    verificar_resultado,
)


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(
        description="Buscador de precios vigentes de combustibles por localidad."
    )
    parser.add_argument("--datos", required=True, help="Archivo .csv o .json de precios.")
    parser.add_argument("--localidad", help="Localidad a consultar (ej.: Rosario).")
    parser.add_argument("--producto", help="Combustible, tal como figura en los datos.")
    parser.add_argument("--fecha", help="Fecha de referencia AAAA-MM-DD.")
    parser.add_argument("--horario", default="Diurno", help="Diurno (por defecto) o Nocturno.")
    parser.add_argument("--max-dias", default=ConsultaPrecio.MAX_DIAS_POR_DEFECTO,
                        help="Antigüedad máxima de un precio, en días "
                             f"(por defecto {ConsultaPrecio.MAX_DIAS_POR_DEFECTO}). "
                             "Las estaciones con precios más viejos no entran en el ranking.")
    parser.add_argument("--salida", default="outputs", help="Carpeta de salida (por defecto outputs/).")
    parser.add_argument("--listar-productos", action="store_true",
                        help="Muestra los productos disponibles y termina.")
    return parser.parse_args(argv)


def preparar_datos(ruta):
    """leer → normalizar campos → validar esquema → limpiar."""
    fuente = obtener_fuente(ruta)
    registros = fuente.cargar(ruta)
    registros = normalizar_campos(registros)
    validar_esquema(registros)
    validos, rechazos = limpiar_datos(registros)
    return registros, validos, rechazos


def mostrar_tabla(resultado):
    print(f"{'#':>3}  {'Precio':>10}  {'Vigente desde':<16}  Estación")
    print("-" * 78)
    for i, r in enumerate(resultado, start=1):
        estacion = f"{r['empresa']} ({r['bandera'] or 'sin bandera'}) - {r['direccion']}"
        print(f"{i:>3}  {r['precio']:>10.2f}  {r['fecha_vigencia']:%Y-%m-%d %H:%M}  {estacion}")


def ejecutar(argv=None):
    args = leer_argumentos(argv)
    registros, validos, rechazos = preparar_datos(args.datos)

    print(f"Registros leídos: {len(registros)} | válidos: {len(validos)} "
          f"| rechazados: {len(rechazos)}")

    if args.listar_productos:
        productos = listar_productos(validos, args.localidad)
        print("Productos disponibles" + (f" en {args.localidad}:" if args.localidad else ":"))
        for p in productos:
            print(f"  - {p}")
        return 0

    faltantes = [n for n in ("localidad", "producto", "fecha") if not getattr(args, n)]
    if faltantes:
        raise ErrorConsulta("Faltan parámetros: " + ", ".join("--" + f for f in faltantes))

    consulta = ConsultaPrecio(args.localidad, args.producto, args.fecha, args.horario,
                              args.max_dias)
    vigentes = seleccionar_vigentes(validos, consulta.fecha)
    resultado = buscar_estaciones(vigentes, consulta)
    verificar_resultado(resultado, consulta)
    desactualizadas = buscar_desactualizadas(vigentes, consulta)

    salida = Path(args.salida)
    ruta_rechazos = guardar_rechazos(rechazos, salida / "rechazos.csv")

    print(f"\nConsulta: {consulta.describir()}")
    if desactualizadas:
        mas_reciente = max(r["fecha_vigencia"] for r in desactualizadas)
        print(f"Estaciones excluidas por precio desactualizado: {len(desactualizadas)} "
              f"(su último precio informado tiene más de {consulta.max_dias} días; "
              f"el más reciente de esos precios es del {mas_reciente:%Y-%m-%d}).")
    if not resultado:
        print("No hay precios informados para esa combinación a esa fecha.")
        print("Sugerencia: revisar el nombre exacto con --listar-productos.")
        print(f"Rechazos guardados en: {ruta_rechazos}")
        return 0

    mostrar_tabla(resultado)
    resumen = resumir_resultado(resultado)
    print(f"\nEstaciones: {resumen['estaciones']} | mínimo: ${resumen['minimo']:.2f} "
          f"| máximo: ${resumen['maximo']:.2f} | promedio: ${resumen['promedio']:.2f} "
          f"| diferencia entre extremos: {resumen['diferencia_pct']}%")

    ruta_consulta = exportar_consulta(resultado, salida / "consulta.csv")
    print(f"\nResultado guardado en: {ruta_consulta}")
    print(f"Rechazos guardados en: {ruta_rechazos}")
    return 0


def main():
    try:
        return ejecutar()
    except (ErrorLectura, ErrorEsquema, ErrorConsulta) as e:
        # Errores esperables (archivo, columnas, parámetros): mensaje claro, sin traceback.
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ErrorResultado as e:
        # No debería ocurrir nunca: si ocurre, es un error de programación.
        print(f"Error interno: el resultado no superó la verificación ({e})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
