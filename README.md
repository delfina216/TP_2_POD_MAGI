# Buscador de precios vigentes de combustibles

**Autora:** Delfina Magi

**Materia:** Programación Orientada a Datos — Licenciatura en Ciencia de Datos, UCA, 2026

**Trabajo:** TP2



## 1\. Problema, usuario y solución

### Problema

En Argentina, las estaciones de servicio informan cada cambio de precio a la Secretaría de Energía, que publica esos datos en formato abierto. El archivo reúne muchas actualizaciones de distintas fechas, varios combustibles y dos tipos de horario (diurno y nocturno). Si alguien compara directamente las filas del archivo, puede terminar comparando un precio de hace meses con uno de ayer, o una nafta con un gasoil, y llegar a una conclusión equivocada sobre qué estación es más barata.

### Usuario

* Una persona que quiere saber dónde cargar combustible más barato en su localidad.
* Una persona que necesita reconstruir cuál era el precio de cada estación en una fecha pasada (por ejemplo, para controlar un gasto o un reintegro).

### Solución propuesta

Una aplicación de consola que recibe **localidad, combustible, fecha de referencia y horario**, selecciona para cada estación el **precio vigente a esa fecha** y devuelve las estaciones **ordenadas de la más barata a la más cara**.

El **precio vigente** de una estación es el informado con la fecha más reciente que **no sea posterior** al día consultado.

> Ejemplo: una estación informó $1.200 el 01/08, $1.290 el 10/09 y $1.350 el 05/10.
> Si se consulta al 30/09, el precio vigente es \*\*$1.290\*\*. El del 05/10 todavía no existía y el del 01/08 ya había sido reemplazado.

### Operaciones

1. Consultar el ranking de precios vigentes (localidad + combustible + fecha + horario).
2. Listar los combustibles disponibles en una localidad.
3. Guardar el resultado en un archivo CSV, con la fecha desde la que rige cada precio.
4. Guardar las filas descartadas en un archivo aparte, con el motivo de cada una.
5. Mostrar un resumen: cantidad de estaciones, precio mínimo, máximo, promedio y diferencia porcentual entre extremos.

### Alcance de la primera versión

**Incluye:** una consulta por ejecución, un combustible y un horario por consulta, lectura de CSV y JSON.

**Queda fuera:** mapas o cálculo de distancias, evolución de precios en el tiempo, comparación entre provincias, interfaz gráfica o web, descarga automática de datos desde internet.

\---

## 2\. Datos

|Aspecto|Detalle|
|-|-|
|Fuente|Secretaría de Energía de la Nación. Dataset "Precios en surtidor" (Resolución 314/2016), portal de datos abiertos de Energía|
|URL|\[COMPLETAR: URL exacta de la página del dataset]|
|Responsable|Secretaría de Energía — Ministerio de Economía de la Nación|
|Licencia|\[COMPLETAR: la que figure en la página del dataset]|
|Fecha de consulta|\[COMPLETAR: AAAA-MM-DD]|

**Unidad de análisis:** cada fila es **un precio informado por una estación de servicio, para un combustible y un tipo de horario, con una fecha de vigencia**.

### Variables que se van a utilizar

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
|`fecha\_vigencia`|Fecha y hora desde la que rige el precio|fecha y hora|

### Muestra

El archivo completo es grande, así que no se sube al repositorio. Se va a conservar una muestra de una o dos localidades (al menos 50 filas) en CSV y en JSON equivalente, junto con las instrucciones para regenerarla a partir del archivo oficial.

### Limitaciones y sesgos

* Los precios los **declaran las propias estaciones**. Puede haber demoras en la carga, errores de tipeo o estaciones que no actualizan.
* Que una estación no aparezca **no significa que no exista**: puede no haber informado precios para ese combustible.
* **GNC se expresa por m³ y los líquidos por litro.** La aplicación nunca va a mezclar combustibles en una misma consulta.
* La Resolución 314/2016 fue abrogada por la Resolución 717/2025 del Ministerio de Economía (B.O. 02/06/2025). \[COMPLETAR: indicar hasta qué fecha llegan los datos descargados.]
* Los nombres de localidad se escriben de forma no uniforme en el original y hay que normalizarlos.

