# -*- coding: utf-8 -*-
"""
Fase 10 — score de confianza explicable.

El enunciado pide "puntaje de confianza y explicación de cada decisión". Un número
sin desglose no es auditable, así que el score se compone de factores nombrados y
cada registro sale con la lista de factores que lo movieron.

El score responde una pregunta operativa concreta: **¿un analista de riesgo puede
usar esta fila sin revisarla?** No mide qué tan parecidas son dos cadenas.

    confianza = 100
                × factor_identidad      (¿sabemos quién es?)
                × factor_sector         (¿sabemos qué hace?)
                − penalizaciones        (truncamiento, nombre pobre, clúster grande)

Bandas de uso:

    >= 85   Automático. Utilizable sin revisión.
    70-84   Utilizable con muestreo de control.
    50-69   Requiere revisión antes de usarse en análisis de concentración.
    < 50    No usar sin verificación individual.
"""
from __future__ import annotations

# Qué tan seguros estamos de la identidad, según de dónde salió el nombre.
FACTOR_IDENTIDAD = {
    'gazetteer': 1.00,             # entidad reconocida en el maestro
    'llm_alta': 0.92,              # el modelo identificó la entidad específica
    'reconstruccion': 0.85,        # nombre reconstruido de las variantes del clúster
    'llm_media': 0.75,
    'llm_baja': 0.55,
    'reclasificacion_cluster': 1.00,   # no es un empleador; la etiqueta es certera
}

# Qué tan seguros estamos del sector, según la evidencia que lo asignó.
FACTOR_SECTOR = {
    'gazetteer': 1.00,             # sector conocido de la entidad identificada
    'propiedad_horizontal': 0.94,  # forma jurídica, no palabra clave: la actividad se deduce de ella
    'frase': 0.92,                 # frase completa del catálogo: el contexto desambigua
    'token': 0.80,                 # una palabra clave; se ajusta por peso más abajo
    'token_aproximado': 0.62,      # errata o variante morfológica: evidencia real, más débil
    'llm_alta': 0.90,
    'llm_media': 0.72,
    'llm_baja': 0.50,
    'reclasificacion': 1.00,
    'sin_evidencia': 0.25,         # queda sin sector; la fila igual sirve para el maestro
}

PENALIZACIONES = {
    'truncado_sin_variante_completa': 12,
    'nombre_de_una_palabra': 6,
    'solo_iniciales': 10,
    'clave_generica_con_sufijo_numerico': 8,
    'cluster_grande_sin_ancla': 10,
}

UMBRAL_AUTOMATICO = 85
UMBRAL_MUESTREO = 70
UMBRAL_REVISION = 50


def banda(score: float) -> str:
    if score >= UMBRAL_AUTOMATICO:
        return 'automatico'
    if score >= UMBRAL_MUESTREO:
        return 'muestreo'
    if score >= UMBRAL_REVISION:
        return 'revision'
    return 'verificacion_individual'


def calcular(origen_nombre: str, origen_sector: str, *,
             truncado: bool, n_claves: int, tokens_nucleo: list[str],
             peso_token: int = 5, sufijo_numerico: bool = False,
             clave_generica: bool = False) -> tuple[int, list[str]]:
    """
    Devuelve (score 0-100, factores). `factores` es la explicación legible.
    """
    factores: list[str] = []

    f_id = FACTOR_IDENTIDAD.get(origen_nombre, 0.70)
    factores.append('identidad %s (x%.2f)' % (origen_nombre, f_id))

    f_sec = FACTOR_SECTOR.get(origen_sector, 0.50)
    if origen_sector == 'token':
        # Un token muy específico ("FERRETERIA", peso 8-9) es mejor evidencia que
        # uno genérico ("SERVICIOS", peso 1). El peso ya lo mide; se traslada.
        f_sec = 0.55 + 0.05 * min(peso_token, 9)
    factores.append('sector %s (x%.2f)' % (origen_sector, f_sec))

    score = 100.0 * f_id * f_sec

    if truncado and n_claves == 1:
        score -= PENALIZACIONES['truncado_sin_variante_completa']
        factores.append('-%d truncado en origen y sin variante completa en el corpus'
                        % PENALIZACIONES['truncado_sin_variante_completa'])

    if len(tokens_nucleo) == 1:
        score -= PENALIZACIONES['nombre_de_una_palabra']
        factores.append('-%d el nombre es una sola palabra'
                        % PENALIZACIONES['nombre_de_una_palabra'])

    if tokens_nucleo and all(len(t) <= 2 for t in tokens_nucleo):
        score -= PENALIZACIONES['solo_iniciales']
        factores.append('-%d el nombre son solo iniciales'
                        % PENALIZACIONES['solo_iniciales'])

    if clave_generica and sufijo_numerico:
        score -= PENALIZACIONES['clave_generica_con_sufijo_numerico']
        factores.append('-%d nombre genérico distinguido solo por un número'
                        % PENALIZACIONES['clave_generica_con_sufijo_numerico'])

    # Un clúster grande sin ancla en el maestro concentra riesgo de sobre-agrupación.
    if n_claves >= 12 and origen_nombre not in ('gazetteer', 'reclasificacion_cluster'):
        score -= PENALIZACIONES['cluster_grande_sin_ancla']
        factores.append('-%d clúster de %d variantes sin ancla en el maestro'
                        % (PENALIZACIONES['cluster_grande_sin_ancla'], n_claves))

    # Agrupar variantes es evidencia positiva: varias escrituras coinciden.
    if 2 <= n_claves <= 11:
        bono = min(6, n_claves)
        score += bono
        factores.append('+%d agrupa %d variantes coherentes' % (bono, n_claves))

    score = max(0.0, min(100.0, score))
    return int(round(score)), factores
