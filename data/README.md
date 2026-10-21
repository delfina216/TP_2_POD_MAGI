# Datos

## Origen
- **Dataset:** Precios en Surtidor — Resolución 314/2016, recurso **"Precios históricos"**
- **Responsable:** Secretaría de Energía de la Nación (Ministerio de Economía)
- **Página del dataset:** http://datos.energia.gob.ar/dataset/precios-en-surtidor
- **Descarga directa del CSV histórico:** http://datos.energia.gob.ar/dataset/1c181390-5045-475e-94dc-410429be4b17/resource/f8dda0d5-2a9f-4d34-b79b-4e63de3995df/download/precios-historicos.csv
- **Licencia:** Creative Commons Atribución 4.0 (CC-BY-4.0)
- **Fecha de descarga:** 2026-10-20

El archivo completo tiene 3.380.186 filas (unos 780 MB), con precios informados desde 2016 en todo el país. La fecha de vigencia viene con formato `DD/MM/AAAA HH:MM`.

## Cómo regenerar la muestra
1. Descargar el CSV histórico desde el enlace de arriba y guardarlo en esta carpeta como
   `data/precios-en-surtidor-historico.csv`.
   Ese archivo **no se sube a GitHub** porque es grande: `.gitignore` excluye `data/precios-en-surtidor*.csv`.
   Si se guarda con su nombre original (`precios-historicos.csv`), hay que renombrarlo, porque ese nombre no está excluido.
2. Desde la raíz del proyecto, ejecutar:
   ```bash
   python scripts/preparar_muestra.py data/precios-en-surtidor-historico.csv --localidades Rosario
   ```
   El script conserva las filas de las localidades indicadas y, de ellas, los últimos 6 meses de datos
   (se puede cambiar con `--meses`). También escribe un resumen en `outputs/resumen_dataset.txt`.
3. El script genera `muestra.csv` y `muestra.json`, que son **equivalentes**: mismas filas, mismos campos y mismo orden. El JSON es una lista de objetos.

Si el portal publica datos nuevos, la muestra regenerada va a cubrir otro período y los resultados del ejemplo del README van a cambiar.

## Contenido de la muestra
- **Localidad incluida:** Rosario (Santa Fe)
- **Cantidad de filas:** 662 (la consigna pide como referencia al menos 50)
- **Estaciones:** 23
- **Combustibles:** Nafta (súper) entre 92 y 95 Ron, Nafta (premium) de más de 95 Ron, Gas Oil Grado 2, Gas Oil Grado 3 y GNC
- **Período cubierto:** del 01/05/2026 al 14/10/2026 (fecha mínima y máxima de `fecha_vigencia`)
- **Filas rechazadas por la limpieza:** ninguna. Los errores de carga del archivo completo (fechas como `01/01/0001`, precios en 0) quedan fuera del período de la muestra.

## Datos de prueba
`tests/fixtures/` contiene datos **inventados a mano** con valores conocidos. Sirven solo para las pruebas y no representan precios reales. Incluyen a propósito casos que deben rechazarse (duplicados, precios contradictorios, precio no numérico, fecha inexistente, precio negativo y localidad vacía).
