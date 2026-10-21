"""
modelo.py — Clase del dominio (Paso 4: "al menos una clase significativa").

ConsultaPrecio representa LO QUE PIDE EL USUARIO: una localidad, un combustible,
un tipo de horario y una fecha de referencia. Reúne:
  - atributos: los parámetros de la consulta, ya validados y normalizados;
  - comportamiento: decidir si un registro le corresponde (coincide) y
    ordenar los resultados (aplicar).

No se crea una clase por cada fila del CSV: la consigna aclara que también se
puede modelar una consulta, que es el concepto central de esta aplicación.
"""

from validaciones import ErrorValidacion, normalizar_texto, parsear_fecha_consulta


class ErrorConsulta(ValueError):
    """Los parámetros de la consulta no son válidos."""


class ConsultaPrecio:
    """Consulta de precios vigentes para una localidad, combustible y fecha."""

    HORARIOS_VALIDOS = ("DIURNO", "NOCTURNO")
    MAX_DIAS_POR_DEFECTO = 90

    def __init__(self, localidad, producto, fecha, horario="DIURNO",
                 max_dias=MAX_DIAS_POR_DEFECTO):
        self.localidad = self._requerido(localidad, "localidad")
        self.producto = self._requerido(producto, "producto")
        self.horario = self._requerido(horario, "horario")
        if self.horario not in self.HORARIOS_VALIDOS:
            raise ErrorConsulta(
                f"Horario '{horario}' inválido. Opciones: "
                f"{', '.join(h.title() for h in self.HORARIOS_VALIDOS)}."
            )
        try:
            self.fecha = parsear_fecha_consulta(fecha)
        except ErrorValidacion as e:
            raise ErrorConsulta(str(e)) from None
        self.max_dias = self._validar_max_dias(max_dias)

    @staticmethod
    def _validar_max_dias(valor):
        try:
            dias = int(str(valor).strip())
        except ValueError:
            raise ErrorConsulta(
                f"La antigüedad máxima '{valor}' debe ser un número entero de días."
            ) from None
        if dias < 1:
            raise ErrorConsulta(f"La antigüedad máxima debe ser de al menos 1 día (se indicó {dias}).")
        return dias

    @staticmethod
    def _requerido(valor, nombre):
        normalizado = normalizar_texto(valor)
        if not normalizado:
            raise ErrorConsulta(f"Falta indicar {nombre}.")
        return normalizado

    def coincide(self, registro):
        """True si el registro es de la localidad, producto y horario pedidos."""
        return (
            registro["localidad"] == self.localidad
            and registro["producto"] == self.producto
            and registro["horario"] == self.horario
        )

    def antiguedad(self, registro):
        return (self.fecha - registro["fecha_vigencia"].date()).days

    def es_reciente(self, registro):
        return self.antiguedad(registro) <= self.max_dias

    def aplicar(self, vigentes):
        """Filtra los registros vigentes y los ordena del más barato al más caro.

        Desempate documentado: a igual precio, orden alfabético por empresa y
        luego por identificador de estación, para que el resultado sea siempre
        el mismo (reproducible).
        """
        seleccion = [r for r in vigentes if self.coincide(r) and self.es_reciente(r)]
        return sorted(seleccion, key=lambda r: (r["precio"], r["empresa"], r["estacion_id"]))

    def desactualizados(self, vigentes):
        return [r for r in vigentes if self.coincide(r) and not self.es_reciente(r)]

    def describir(self):
        return (
            f"{self.producto} en {self.localidad.title()} "
            f"(horario {self.horario.lower()}) vigente al {self.fecha.isoformat()}, "
            f"con precios de hasta {self.max_dias} días de antigüedad"
        )

    def __repr__(self):
        return (
            f"ConsultaPrecio(localidad={self.localidad!r}, producto={self.producto!r}, "
            f"fecha={self.fecha.isoformat()!r}, horario={self.horario!r}, "
            f"max_dias={self.max_dias!r})"
        )
