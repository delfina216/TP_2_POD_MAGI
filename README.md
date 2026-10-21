# Buscador de precios vigentes de combustibles

**Autora:** Delfina Magi

**Materia:** Programación Orientada a Datos — Licenciatura en Ciencia de Datos, UCA, 2026

**Trabajo:** TP2

---

## 1. Problema, usuario y solución

### Problema

En Argentina, las estaciones de servicio informan cada cambio de precio a la Secretaría de Energía, que publica esos datos en formato abierto. El archivo reúne muchas actualizaciones de distintas fechas, varios combustibles y dos tipos de horario (diurno y nocturno). Si alguien compara directamente las filas del archivo, puede terminar comparando un precio de hace meses con uno de ayer, o una nafta con un gasoil, y llegar a una conclusión equivocada sobre qué estación es más barata.

### Usuario

* Una persona que quiere saber dónde cargar combustible más barato en su localidad.
* Una persona que necesita reconstruir cuál era el precio de cada estación en una fecha pasada (por ejemplo, para controlar un gasto o un reintegro).

### Solución propuesta

Una aplicación de consola que recibe **localidad, combustible, fecha de referencia y horario**, selecciona para cada estación el **precio vigente a esa fecha** y devuelve las estaciones **ordenadas de la más barata a la más cara**.

El **precio vigente** de una estación es el informado con la fecha más reciente que **no sea posterior** al día consultado y que **no tenga más de 90 días de antigüedad** (ver [Decisiones de limpieza y de análisis](#5-decisiones-de-limpieza-y-de-análisis)).

> Ejemplo: una estación informó $1.200 el 01/08, $1.290 el 10/09 y $1.350 el 05/10.
> Si se consulta al 30/09, el precio vigente es **$1.290**. El del 05/10 todavía no existía y el del 01/08 ya había sido reemplazado.

### Operaciones

1. Consultar el ranking de precios vigentes (localidad + combustible + fecha + horario).
2. Listar los combustibles disponibles en una localidad.
3. Guardar el resultado en un archivo CSV, con la fecha desde la que rige cada precio.
4. Guardar las filas descartadas en un archivo aparte, con el motivo de cada una.
5. Mostrar un resumen: cantidad de estaciones, precio mínimo, máximo, promedio y diferencia porcentual entre extremos.
6. Informar cuántas estaciones quedaron fuera del ranking por tener un precio desactualizado.

### Alcance de la primera versión

**Incluye:** una consulta por ejecución, un combustible y un horario por consulta, lectura de CSV y JSON.

**Queda fuera:** mapas o cálculo de distancias, evolución de precios en el tiempo, comparación entre provincias, interfaz gráfica o web, descarga automática de datos desde internet.

---

## 2. Datos

|Aspecto|Detalle|
|-|-|
|Fuente|Secretaría de Energía de la Nación. Dataset "Precios en Surtidor – Resolución 314/2016", recurso **"Precios históricos"**|
|URL|http://datos.energia.gob.ar/dataset/precios-en-surtidor|
|Responsable|Secretaría de Energía — Ministerio de Economía de la Nación|
|Licencia|Creative Commons Atribución 4.0 (CC-BY-4.0)|
|Fecha de consulta|2026-10-20|

Se usa el recurso **histórico** y no el de precios vigentes: el de vigentes trae un solo precio por estación, y entonces no habría nada que seleccionar a una fecha dada.

**Unidad de análisis:** cada fila es **un precio informado por una estación de servicio, para un combustible y un tipo de horario, con una fecha de vigencia**.

### Variables utilizadas

|Columna original|Descripción|Tipo|
|-|-|-|
|`idempresa`|Identificador de la estación (boca de expendio)|texto|
|`empresa`|Razón social de quien opera la estación|texto|
|`empresabandera`|Marca de la estación (YPF, Shell, Axion, etc.)|texto|
|`direccion`|Dirección de la estación|texto|
|`localidad`|Localidad|texto|
|`provincia`|Provincia|texto|
|`producto`|Combustible|texto|
|`tipohorario`|Diurno o Nocturno|texto|
|`precio`|Precio en pesos por unidad (litro; m³ para GNC)|número|
|`fecha_vigencia`|Fecha y hora desde la que rige el precio, con formato `DD/MM/AAAA HH:MM`|fecha y hora|

El archivo trae otras columnas (`idproducto`, `idtipohorario`, `idempresabandera`, `latitud`, `longitud`, `geojson`, `anio`, `mes`) que la aplicación no usa y descarta al leer.

### Archivo completo y muestra

El archivo completo tiene **3.380.186 filas** (unos 780 MB), así que **no se sube al repositorio** (está excluido en `.gitignore`). En el repositorio se conserva una muestra:

|Archivo|Contenido|
|-|-|
|`data/muestra.csv`|662 filas de **Rosario (Santa Fe)**, 23 estaciones, del 01/05/2026 al 14/10/2026|
|`data/muestra.json`|las mismas 662 filas en JSON (lista de objetos), equivalente al CSV|

La muestra se genera con `scripts/preparar_muestra.py`, que conserva los últimos 6 meses de datos de las localidades elegidas. Las instrucciones para descargar el archivo y regenerarla están en [`data/README.md`](data/README.md).

### Limitaciones y sesgos

* Los precios los **declaran las propias estaciones**. Puede haber demoras en la carga, errores de tipeo o estaciones que no actualizan.
* Que una estación no aparezca **no significa que no exista**: puede no haber informado precios para ese combustible.
* **GNC se expresa por m³ y los líquidos por litro.** La aplicación nunca mezcla combustibles en una misma consulta.
* La Resolución 314/2016 fue abrogada por la Resolución 717/2025 del Ministerio de Economía (B.O. 02/06/2025). Desde mediados de 2025 la cantidad de actualizaciones cae mucho: en Rosario se pasa de unas 900 filas por mes a principios de 2025 a menos de 200 por mes en 2026. Por eso, las consultas de 2026 devuelven menos estaciones que las de años anteriores.
* Los datos descargados (20/10/2026) llegan hasta el **14/10/2026** para Rosario.
* El portal describe el recurso histórico como "precios anteriores": el precio que una estación tiene cargado en este momento se publica en el recurso de precios vigentes. Por eso, en una consulta a una fecha muy cercana a la descarga, una estación puede aparecer con su precio anterior o no aparecer. Para fechas pasadas no hay diferencia.
* El archivo nacional tiene fechas mal cargadas (por ejemplo, años 0001 o 9920) y algunos precios en cero. La aplicación los rechaza y los registra (ver sección 5).
* Los nombres de localidad y de producto se escriben de forma no uniforme en el original y se normalizan antes de comparar.

---

## 3. Instalación y uso

### Requisitos

* Python 3.10 o superior (probado con Python 3.14).
* No hace falta instalar nada: el proyecto usa solo la biblioteca estándar (`csv`, `json`, `re`, `datetime`, `unicodedata`, `argparse`, `abc`, `statistics`, `unittest`). Por eso `requirements.txt` no lista dependencias.

```bash
git clone https://github.com/delfina216/TP_2_POD_MAGI.git
cd TP_2_POD_MAGI
```

### Ejecutar una consulta

Todos los comandos se ejecutan desde la carpeta raíz del proyecto.

```bash
python src/main.py --datos data/muestra.csv --localidad Rosario --producto "Nafta (súper) entre 92 y 95 Ron" --fecha 2026-09-30
```

|Argumento|Obligatorio|Descripción|
|-|-|-|
|`--datos`|sí|Archivo `.csv` o `.json` con los precios.|
|`--localidad`|sí|Localidad a consultar. No distingue mayúsculas, tildes ni espacios extra.|
|`--producto`|sí|Combustible, tal como figura en los datos (ver `--listar-productos`).|
|`--fecha`|sí|Fecha de referencia con formato `AAAA-MM-DD`.|
|`--horario`|no|`Diurno` (por defecto) o `Nocturno`.|
|`--max-dias`|no|Antigüedad máxima de un precio, en días (por defecto 90).|
|`--salida`|no|Carpeta donde se guardan los resultados (por defecto `outputs/`).|

La misma consulta con el archivo JSON da el mismo resultado:

```bash
python src/main.py --datos data/muestra.json --localidad Rosario --producto "Nafta (súper) entre 92 y 95 Ron" --fecha 2026-09-30
```

### Listar los combustibles de una localidad

```bash
python src/main.py --datos data/muestra.csv --localidad Rosario --listar-productos
```

### Archivos que genera

|Archivo|Contenido|
|-|-|
|`outputs/consulta.csv`|El ranking: posición, empresa, bandera, dirección, producto, horario, precio, fecha desde la que rige (`vigente_desde`) e identificador de la estación.|
|`outputs/rechazos.csv`|Cada fila descartada, con su número de fila en el archivo original y el motivo.|

La carpeta `outputs/` no se versiona: se regenera con los comandos anteriores.

### Ejecutar las pruebas

```bash
python -m unittest discover -s tests -v
```

---

## 4. Ejemplo de resultado

Consulta de nafta súper en Rosario al 30/09/2026, con la muestra del repositorio:

```text
Registros leídos: 662 | válidos: 662 | rechazados: 0

Consulta: NAFTA (SUPER) ENTRE 92 Y 95 RON en Rosario (horario diurno) vigente al 2026-09-30, con precios de hasta 90 días de antigüedad
Estaciones excluidas por precio desactualizado: 1 (su último precio informado tiene más de 90 días; el más reciente de esos precios es del 2026-05-20).
  #      Precio  Vigente desde     Estación
------------------------------------------------------------------------------
  1     2129.00  2026-09-25 14:00  MADEGAS SA (GULF) - AV. PTE PERON 6575
  2     2149.00  2026-09-24 00:00  CIRCUNVALACION SERVICIOS S.A. (DAPSA S.A.) - BAIGORRIA 2630
  3     2212.00  2026-09-22 09:17  BRIBAL AGRO SRL (PUMA) - PUEYRREDON 1089
  ...
 16     2294.00  2026-07-03 10:12  AYACUCHO SERVICENTRO (BLANCA) - AYACUCHO 6331

Estaciones: 16 | mínimo: $2129.00 | máximo: $2294.00 | promedio: $2231.50 | diferencia entre extremos: 7.75%
```

### Cómo se interpreta

* Cada fila es una estación y su precio **vigente al 30/09/2026**. La columna "Vigente desde" indica cuándo empezó a regir ese precio.
* La estación más barata (MADEGAS, $2.129 por litro) cobra un **7,75 % menos** que la más cara de la lista ($2.294).
* Una estación quedó fuera porque su último precio informado era del 20/05/2026, más de 90 días antes de la consulta. No se puede saber si ese precio sigue vigente.
* El resultado no dice nada de las estaciones que no informaron precios: el ranking solo incluye las que sí lo hicieron.

---

## 5. Decisiones de limpieza y de análisis

Las filas se validan una por una. Las que no cumplen una regla **no se descartan en silencio**: se guardan en `outputs/rechazos.csv` con el número de fila y el motivo. En todos los casos se cumple: filas leídas = filas válidas + filas rechazadas.

|Situación|Decisión|Motivo|
|-|-|-|
|Campo de texto obligatorio vacío (estación, empresa, dirección, localidad, provincia, producto, horario)|Se rechaza la fila.|Sin esos datos no se puede ubicar ni comparar el precio.|
|Fecha con formato inválido|Se rechaza.|Se aceptan `DD/MM/AAAA HH:MM` (formato del archivo oficial) y `AAAA-MM-DD` (ISO). Lo controla una expresión regular.|
|Fecha con formato correcto pero inexistente (por ejemplo, `30/02/2026`)|Se rechaza.|La expresión regular solo controla la forma; `datetime` controla que la fecha exista en el calendario.|
|Fecha anterior a 2016|Se rechaza.|El sistema de la Resolución 314/2016 empezó ese año; fechas como `01/01/0001` son errores de carga.|
|Precio faltante, no numérico, menor o igual a 0 o mayor a $100.000|Se rechaza.|No es un precio plausible. El límite superior es una cota de sentido común contra errores de tipeo.|
|Duplicado exacto (misma estación, producto, horario, fecha y precio)|Se conserva uno y las copias se rechazan como "duplicado exacto".|Es el mismo dato repetido.|
|Registros contradictorios (misma estación, producto, horario y fecha, con **precios distintos**)|Se rechazan todas las versiones.|No hay un criterio objetivo para elegir una.|
|Texto con mayúsculas, tildes o espacios distintos (`rosario `, `Rosario`, `ROSARIO`)|Se normaliza: mayúsculas, sin tildes, sin espacios repetidos.|Para que la misma localidad o producto se reconozca igual.|

Decisiones del análisis:

* **Precio vigente:** para cada estación, producto y horario se toma el precio con la fecha más reciente que no sea posterior al día consultado. Un precio informado ese mismo día, a cualquier hora, se incluye.
* **Antigüedad máxima de 90 días:** si el precio vigente de una estación tiene más de 90 días, la estación queda fuera del ranking y se informa cuántas quedaron afuera. Sin este límite, las estaciones que dejaron de informar aparecían primeras con precios viejos: en el archivo completo de Rosario, una consulta al 30/09/2026 mostraba arriba de todo precios de 2017 ($23,63) y el primer precio de 2026 recién aparecía en el puesto 90. Se eligió 90 días porque a principios de 2025, con datos completos, casi todas las estaciones activas de Rosario actualizaron dentro de ese plazo (79 de 106). El valor se puede cambiar con `--max-dias`.
* **Horario:** cada consulta usa un solo horario (diurno por defecto), porque la misma estación puede informar precios distintos de día y de noche.
* **Un solo combustible por consulta:** nunca se comparan productos distintos ni unidades distintas (litro y m³).
* **Desempate:** a igual precio, se ordena por nombre de la empresa y luego por identificador de estación, para que el resultado sea siempre el mismo.
* **Verificación del resultado:** antes de mostrarlo, el programa comprueba que ningún precio sea posterior a la consulta ni más viejo que el límite, que no haya estaciones repetidas y que el ranking esté ordenado. Si algo falla, avisa con un error en lugar de dar una respuesta incorrecta.

---

## 6. Organización del código

```text
TP_2_POD_MAGI/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── main.py           # punto de entrada: lee argumentos, coordina el flujo y muestra el resultado
│   ├── fuentes.py        # lectura: FuenteDatos (abstracta), FuenteCSV y FuenteJSON
│   ├── validaciones.py   # expresiones regulares, fechas, precios y normalización de texto
│   ├── pipeline.py       # esquema, limpieza, selección de vigentes, verificación y exportación
│   └── modelo.py         # ConsultaPrecio: la clase del dominio
├── scripts/
│   └── preparar_muestra.py   # genera data/muestra.csv y data/muestra.json desde el archivo oficial
├── tests/
│   ├── test_aplicacion.py    # pruebas con unittest
│   └── fixtures/             # datos de prueba inventados, con resultados conocidos
└── data/
    ├── README.md
    ├── muestra.csv
    └── muestra.json
```

Flujo de procesamiento:

```text
leer (fuentes.py) → normalizar campos → validar esquema → limpiar, con registro de rechazos
  → seleccionar vigentes → filtrar y ordenar (ConsultaPrecio) → verificar → exportar
```

### Conceptos aplicados

* **Abstracción de las fuentes de datos:** `FuenteDatos` es una clase base abstracta con el método `cargar(ruta)`. `FuenteCSV` y `FuenteJSON` implementan solo la lectura de su formato y las dos devuelven lo mismo: una lista de diccionarios con valores en texto. Así, el resto del programa no depende del formato de origen. Para leer otro formato alcanza con agregar otra subclase.
* **Clase del dominio:** `ConsultaPrecio` guarda los parámetros de la consulta (localidad, producto, fecha, horario y antigüedad máxima), los valida al crearse y sabe decidir qué registros le corresponden y cómo ordenarlos.
* **Funciones con una responsabilidad cada una:** `limpiar_datos()` convierte tipos y separa válidos de rechazados (cumple el papel de `normalizar_precios()` de la consigna), `seleccionar_vigentes()` elige el precio vigente, `buscar_estaciones()` aplica la consulta, `verificar_resultado()` controla el resultado y `exportar_consulta()` guarda el CSV.
* **Expresiones regulares:** validan el formato de las fechas del archivo (`DD/MM/AAAA HH:MM` o ISO) y de la fecha de consulta (`^\d{4}-\d{2}-\d{2}$`). Se complementan con `datetime`, porque una regex acepta `2026-02-30` aunque esa fecha no exista.
* **Errores con mensajes claros:** los errores esperables (archivo inexistente, columnas faltantes, parámetros inválidos) se muestran como un mensaje, por ejemplo `Error: La fecha de consulta '2026-02-30' no existe en el calendario.`, en lugar de un traceback.

### Pruebas

`tests/test_aplicacion.py` usa datos inventados (`tests/fixtures/`) con resultados conocidos de antemano, en CSV y en JSON equivalentes. Cubre:

* **Casos normales:** una estación con varias actualizaciones devuelve la vigente, el ranking sale completo y ordenado, y un precio informado el mismo día de la consulta se incluye.
* **Entradas inválidas y casos límite:** localidad sin resultados, fecha mal escrita o inexistente, horario inválido, antigüedad máxima inválida, archivo inexistente, formato no soportado, JSON mal estructurado y columnas faltantes.
* **Propiedades del resultado:** CSV y JSON dan el mismo resultado, ninguna fila se pierde (leídas = válidas + rechazadas), ningún precio es posterior a la consulta ni más viejo que el límite, y hay una sola fila por estación.
* **Muestra real:** con `data/muestra.csv` y `data/muestra.json`, todas las filas son válidas y las dos versiones dan el mismo ranking. Así se comprueba que la aplicación lee el formato del archivo oficial y no solo el de los datos inventados.

---

## 7. Versión entregada

La versión evaluada es la que tiene la etiqueta **`v1.0`** en el repositorio:

```bash
git checkout v1.0
```
