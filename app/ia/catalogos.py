"""Catálogos y reglas de periodo del paquete 2.1 (Definición de Reglas y Catálogos Académicos)."""

CATEGORIAS = {
    "DOC": "Docencia",
    "VIN": "Vinculación",
    "INV": "Investigación",
    "GES": "Gestión",
}

TIPOS_DOCUMENTO = {
    "CER": "Certificado",
    "CON": "Constancia",
    "DIP": "Diploma",
    "REC": "Reconocimiento",
    "NOM": "Nombramiento",
    "INF": "Informe",
    "OTR": "Otro",
}

# Sufijos de periodo: 2026-1, 2026-2, 2026-5 ... ANU, MULTI y S/P van sin año.
PERIODOS = {
    "1": "Primer semestre",
    "2": "Segundo semestre",
    "5": "Primer intersemestral (verano)",
    "6": "Segundo intersemestral (invierno)",
    "ANU": "Periodo anual",
    "MULTI": "Actividad que abarca más de un periodo",
    "S/P": "Sin periodo identificable",
}

# Mes -> sufijo de periodo. Debe ajustarse al calendario académico oficial de la UABC.
MES_A_PERIODO = {1: "6", 2: "1", 3: "1", 4: "1", 5: "1", 6: "1", 7: "5",
                 8: "2", 9: "2", 10: "2", 11: "2", 12: "2"}


def periodo_de_fecha(fecha_iso: str | None) -> str | None:
    """'2026-03-15' -> '2026-1'. Devuelve None si la fecha no es válida."""
    if not fecha_iso:
        return None
    try:
        anio, mes, _ = fecha_iso[:10].split("-")
        return f"{int(anio)}-{MES_A_PERIODO[int(mes)]}"
    except (ValueError, KeyError):
        return None


def calcular_periodo(inicio: str | None, fin: str | None, emision: str | None) -> str:
    """Reglas del catálogo de periodos: se prefieren las fechas de la actividad;
    si abarca dos periodos es MULTI; sin fechas de actividad se usa la de emisión."""
    p_inicio, p_fin = periodo_de_fecha(inicio), periodo_de_fecha(fin)
    if p_inicio and p_fin:
        return p_inicio if p_inicio == p_fin else "MULTI"
    if p_inicio or p_fin:
        return p_inicio or p_fin
    return periodo_de_fecha(emision) or "S/P"
