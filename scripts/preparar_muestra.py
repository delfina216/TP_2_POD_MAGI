"""
preparar_muestra.py — Genera la muestra del repositorio a partir del archivo
oficial descargado (Paso 2: "conservar una muestra pequeña").

El archivo histórico completo pesa cientos de MB, así que no se sube a GitHub.
Este script lo recorre UNA vez, fila por fila (sin cargarlo entero en memoria),
y conserva solo:
  - las filas de las localidades elegidas;
  - los últimos N meses de datos de esas localidades (por defecto 6).

Escribe DOS archivos equivalentes (mismas filas, mismos campos, mismo orden):
    data/muestra.csv
    data/muestra.json   (lista de objetos)

y un resumen del dataset en outputs/resumen_dataset.txt (no se versiona).

Uso (desde la raíz del proyecto):
    python scripts/preparar_muestra.py data/precios-en-surtidor-historico.csv --localidades Rosario
"""

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from validaciones import normalizar_texto  # noqa: E402


def abrir(ruta):
    """Abre el CSV en UTF-8; si no lo es, lo reintenta en Latin-1 (común en datos públicos)."""
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            with open(ruta, encoding=codificacion, newline="") as f:
                f.read(1_000_000)  # prueba la codificación con el primer MB
            return codificacion
        except UnicodeDecodeError:
            continue
    sys.exit("Error: no se pudo determinar la codificación del archivo.")


def buscar_columna(columnas, nombre):
    for c in columnas:
        if c.strip().lower() == nombre:
            return c
    return None


def fecha_iso(texto):
    t = (texto or "").strip()[:10]
    if len(t) == 10 and t[2] == "/" and t[5] == "/":
        return f"{t[6:]}-{t[3:5]}-{t[:2]}"
    return t


def restar_meses(fecha, meses):
    total = fecha.year * 12 + (fecha.month - 1) - meses
    return date(total // 12, total % 12 + 1, 1)


def main():
    parser = argparse.ArgumentParser(description="Recorta el dataset oficial a una muestra.")
    parser.add_argument("origen", help="CSV completo descargado del portal oficial.")
    parser.add_argument("--localidades", nargs="+", required=True)
    parser.add_argument("--meses", type=int, default=6,
                        help="Meses a conservar, contados hacia atrás desde el último dato (por defecto 6).")
    parser.add_argument("--destino", default="data")
    args = parser.parse_args()

    codificacion = abrir(args.origen)
    elegidas = {normalizar_texto(l) for l in args.localidades}
    total = 0
    filas = []
    fecha_min_total, fecha_max_total = None, None

    with open(args.origen, encoding=codificacion, newline="") as f:
        lector = csv.DictReader(f)
        columnas = lector.fieldnames or []
        col_loc = buscar_columna(columnas, "localidad")
        col_fecha = buscar_columna(columnas, "fecha_vigencia")
        if not col_loc or not col_fecha:
            sys.exit(f"Error: faltan las columnas 'localidad' o 'fecha_vigencia'. Columnas: {columnas}")
        for fila in lector:
            total += 1
            fecha = fecha_iso(fila[col_fecha])
            if fecha:
                fecha_min_total = min(fecha_min_total or fecha, fecha)
                fecha_max_total = max(fecha_max_total or fecha, fecha)
            if normalizar_texto(fila[col_loc]) in elegidas:
                filas.append(fila)

    if not filas:
        sys.exit("Error: ninguna fila coincide con esas localidades.")

    # Ventana de los últimos N meses respecto del último dato de esas localidades.
    fechas = sorted(fecha_iso(f[col_fecha]) for f in filas if f[col_fecha])
    ultima = date.fromisoformat(fechas[-1])
    desde = restar_meses(ultima, args.meses - 1).isoformat()
    muestra = [f for f in filas if fecha_iso(f[col_fecha]) >= desde]
    muestra.sort(key=lambda f: (fecha_iso(f[col_fecha]), f[col_fecha][11:],
                                f.get("idempresa", ""), f.get("producto", "")))

    destino = Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)
    with open(destino / "muestra.csv", "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(muestra)
    with open(destino / "muestra.json", "w", encoding="utf-8") as f:
        json.dump(muestra, f, ensure_ascii=False, indent=1)

    resumen = [
        f"Archivo de origen: {args.origen}",
        f"Codificación detectada: {codificacion}",
        f"Columnas: {', '.join(columnas)}",
        f"Filas totales del archivo: {total}",
        f"Período total del archivo: {fecha_min_total} a {fecha_max_total}",
        f"Filas de {', '.join(args.localidades)}: {len(filas)}",
        f"Ventana conservada: {desde} a {ultima.isoformat()} ({args.meses} meses)",
        f"Filas en la muestra: {len(muestra)}",
    ]
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/resumen_dataset.txt").write_text("\n".join(resumen) + "\n", encoding="utf-8")
    print("\n".join(resumen))
    print(f"\nMuestra escrita en {destino / 'muestra.csv'} y {destino / 'muestra.json'}")


if __name__ == "__main__":
    main()
