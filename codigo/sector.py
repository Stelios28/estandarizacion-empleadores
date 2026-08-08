# -*- coding: utf-8 -*-
"""
Fase 9 — clasificación sectorial en CIIU Rev. 4 (decisión D3).

Cascada determinística, de la evidencia más fuerte a la más débil:

  1. Gazetteer          — la entidad está identificada, el sector es un hecho.
  2. Propiedad horiz.   — `PH X` es una forma jurídica, no una palabra clave: la
                          actividad se deduce de ella y no admite discusión.
  3. Frase              — `SALON DE BELLEZA`, `CAJA DE SEGURO SOCIAL`. Gana a los
                          tokens sueltos porque el contexto desambigua.
  4. Token con peso     — `FERRETERIA` (peso 8) le gana a `SERVICIOS` (peso 1).
  5. Token aproximado   — errata o singular/plural. Evidencia real, más débil.
  6. Sin evidencia      — no se inventa un sector: el registro queda marcado para
                          la fase 7. Adivinar aquí contamina el análisis de
                          concentración de cartera, que es justo para lo que
                          Riesgo va a usar esta columna.

Los tipos que no son un empleador reciben su etiqueta fija y nunca llegan aquí.
"""
from __future__ import annotations

import reglas

def por_gazetteer(tokens: list[str]) -> tuple[str, str, str] | None:
    """(sección, división, motivo) si la entidad está en el gazetteer."""
    import canonico

    hit = canonico.buscar_gazetteer(tokens)
    if hit:
        return hit[1], hit[2], 'entidad identificada en el maestro: %s' % hit[0]
    return None


def por_propiedad_horizontal(tokens: list[str]) -> tuple[str, str, str] | None:
    """
    (sección, división, motivo) si el empleador es una propiedad horizontal.

    Va alto en la cascada porque no es una palabra clave: es la forma jurídica de la
    entidad, y la actividad se deduce de ella. La PH administra el inmueble y
    contrata al personal que lo opera — CIIU 68, gestión de bienes inmuebles.
    """
    if reglas.es_propiedad_horizontal(tokens):
        return 'L', '68', 'propiedad horizontal (Ley 31 de 2010): entidad que administra el inmueble'
    return None


def por_frase(nucleo: str) -> tuple[str, str, str] | None:
    """(sección, división, motivo) si una frase del catálogo aparece en el nombre."""
    for frase in reglas.FRASES_CIIU:
        if frase in nucleo:
            seccion, division, etiqueta, _ = reglas.REGLAS_CIIU[frase]
            return seccion, division, 'frase "%s" -> %s' % (frase, etiqueta)
    return None


def por_token(tokens: list[str]) -> tuple[str, str, str] | None:
    """
    (sección, división, motivo) por el token de mayor peso.

    Ante empate de peso gana el token que aparece primero en el nombre: en español
    el sustantivo que encabeza suele ser la actividad (`FERRETERIA LOS ANDES`).
    """
    mejor = None
    for posicion, t in enumerate(tokens):
        regla = reglas.REGLAS_CIIU.get(t)
        if not regla:
            continue
        seccion, division, etiqueta, peso = regla
        candidato = (peso, -posicion, seccion, division, etiqueta, t)
        if mejor is None or candidato > mejor:
            mejor = candidato

    if mejor is None:
        return None
    peso, _, seccion, division, etiqueta, token = mejor
    return seccion, division, 'palabra clave "%s" (peso %d) -> %s' % (token, peso, etiqueta)


# --------------------------------------------------------------------------
# Consulta aproximada al catálogo (D11)
# --------------------------------------------------------------------------
# El motor de entidades usa fuzzy pero el catálogo se consultaba solo por
# coincidencia exacta. Esa asimetría dejaba fuera `TRANPORTE`, `CONTRUCCIONES` y
# `UNVIERSIDAD` en un corpus donde la errata es la norma, no la excepción.
#
# Se abre en dos mecanismos porque tienen naturalezas distintas, y mezclarlos
# fue el primer error de diseño al medirlo:
#
#   - Morfología (`ACARREO`/`ACARREOS`): no es una errata, es un hueco del propio
#     catálogo. Determinista y sin umbral.
#   - Errata (`TRANPORTE`/`TRANSPORTE`): sí necesita distancia y guardas.

_PESO_MIN_APROXIMADO = 6      # solo términos que designan actividad, no forma jurídica
_LARGO_MIN_APROXIMADO = 7     # bajo esto, dos palabras distintas se parecen demasiado
_UMBRAL_APROXIMADO = 90.0

# Términos del catálogo elegibles para comparación aproximada. `EMPRESA` (peso 1)
# queda fuera a propósito: `Movistar Empresas` no es una empresa de apoyo
# empresarial, y una coincidencia aproximada sobre una palabra de relleno solo
# propaga ruido con apariencia de evidencia.
_VOCABULARIO_APROXIMADO = sorted(
    k for k, v in reglas.REGLAS_CIIU.items()
    if ' ' not in k and len(k) >= _LARGO_MIN_APROXIMADO and v[3] >= _PESO_MIN_APROXIMADO
)

# Un apellido o una provincia no son actividad económica. `HERRERA` es las dos
# cosas en Panamá y se parece a `HERRERIA` en un 93 %.
_NO_ELEGIBLES = reglas.APELLIDOS | reglas.NOMBRES_PILA | reglas.LUGARES_TOKEN


_LARGO_MIN_MORFOLOGICO = 4    # bajo esto el token puede ser el resto de un truncamiento


def _variante_morfologica(token: str) -> str | None:
    """Singular/plural del token que sí esté en el catálogo, con peso suficiente."""
    if len(token) < _LARGO_MIN_MORFOLOGICO:
        return None
    for cand in (token + 'S', token + 'ES',
                 token[:-1] if token.endswith('S') else '',
                 token[:-2] if token.endswith('ES') else ''):
        regla = reglas.REGLAS_CIIU.get(cand) if cand else None
        if regla and regla[3] >= _PESO_MIN_APROXIMADO:
            return cand
    return None


def por_token_aproximado(tokens: list[str]) -> tuple[str, str, str] | None:
    """
    (sección, división, motivo) por coincidencia aproximada con el catálogo.

    Última rampa antes de declarar el clúster pendiente de validación externa.
    """
    from rapidfuzz import fuzz, process

    for t in tokens:
        if (t in reglas.REGLAS_CIIU or t in _NO_ELEGIBLES
                or t in reglas.MORFOLOGIA_EXCLUIDA):
            continue

        cand = _variante_morfologica(t)
        if cand:
            seccion, division, etiqueta, _ = reglas.REGLAS_CIIU[cand]
            return seccion, division, ('variante morfológica "%s" = "%s" -> %s'
                                       % (t, cand, etiqueta))

        if len(t) < _LARGO_MIN_APROXIMADO:
            continue
        m = process.extractOne(t, _VOCABULARIO_APROXIMADO, scorer=fuzz.ratio,
                               score_cutoff=_UMBRAL_APROXIMADO)
        # Una errata no contiene la palabra correcta intacta: `RECONSTRUCTION`
        # contiene `CONSTRUCTION` y significa otra cosa (es un taller, no una
        # constructora). El prefijo cambia el sentido, no lo deteriora.
        if m and m[0] not in t:
            seccion, division, etiqueta, _ = reglas.REGLAS_CIIU[m[0]]
            return seccion, division, ('"%s" ~ "%s" al %.0f %% -> %s'
                                       % (t, m[0], m[1], etiqueta))
    return None


def clasificar_cluster(variantes: list[str]) -> tuple[str, str, str, str]:
    """
    Sector de un clúster completo, por voto ponderado entre sus variantes.

    Tomar el primer acierto —el comportamiento anterior— dejaba que una sola
    variante desviara al clúster entero: `Coca Cola Femsa de Panamá` terminó
    clasificada en Enseñanza porque una de sus variantes contenía un token
    educativo. Ahora cada variante vota con el peso de su regla y gana el sector
    con más respaldo acumulado.

    Devuelve (sección, división, origen, motivo).
    """
    votos: dict[tuple[str, str], int] = {}
    votantes: dict[tuple[str, str], int] = {}
    origenes: dict[tuple[str, str], str] = {}
    motivos: dict[tuple[str, str], str] = {}

    for nucleo in variantes:
        tokens = nucleo.split()
        for fn, origen, peso_base in (
            (lambda: por_gazetteer(tokens), 'gazetteer', 20),
            (lambda: por_propiedad_horizontal(tokens), 'propiedad_horizontal', 15),
            (lambda: por_frase(nucleo), 'frase', 10),
            (lambda: por_token(tokens), 'token', 0),
            # Vota con peso 3: menos que cualquier token exacto (4-9), más que
            # nada. Una coincidencia aproximada nunca debe ganarle a una exacta
            # dentro del mismo clúster.
            (lambda: por_token_aproximado(tokens), 'token_aproximado', 3),
        ):
            resultado = fn()
            if not resultado:
                continue
            seccion, division, motivo = resultado
            clave = (seccion, division)
            peso = peso_base
            if origen == 'token':
                regla = next((reglas.REGLAS_CIIU[t] for t in tokens
                              if t in reglas.REGLAS_CIIU), None)
                peso = regla[3] if regla else 1
            votos[clave] = votos.get(clave, 0) + peso
            votantes[clave] = votantes.get(clave, 0) + 1
            # Se conserva el origen y el motivo de la evidencia más fuerte.
            if clave not in origenes or peso_base > 0:
                origenes[clave] = origen
                motivos[clave] = motivo
            break

    if not votos:
        return '', '', 'sin_evidencia', \
               'ninguna variante del clúster coincide con el catálogo CIIU'

    ganador = max(votos.items(), key=lambda kv: (kv[1], kv[0]))[0]
    seccion, division = ganador
    apoyo = votantes[ganador]

    # Se probó una guarda adicional que exigía respaldo mínimo del 20 % de las
    # variantes, pensando que un sector con poco apoyo sería una errata coincidente.
    # Medida sobre el corpus, rechazaba 62 clústeres y la mayoría eran correctos:
    # `Constructora Urbana` -> Construcción y `Complejo Hospitalario` -> Salud
    # tienen el token descriptivo en una sola variante porque las demás llegaron
    # truncadas. Se retiró. El caso que la motivó —Coca-Cola FEMSA clasificada en
    # Enseñanza— resultó ser una abreviatura ambigua (`COL`), y se corrigió ahí.
    detalle = motivos[ganador]
    if len(votos) > 1:
        detalle += ' (voto %d de %d puntos, %d de %d variantes, %d sectores candidatos)' % (
            votos[ganador], sum(votos.values()), apoyo, len(variantes), len(votos))
    return seccion, division, origenes[ganador], detalle


def clasificar(nucleo: str, tokens: list[str]) -> tuple[str, str, str, str]:
    """
    Devuelve (sección, división, origen, motivo).

    Si no hay evidencia, devuelve ('', '', 'sin_evidencia', motivo) y el registro
    queda pendiente para la fase 7. No se asigna un sector por defecto.
    """
    for fn, origen in ((lambda: por_gazetteer(tokens), 'gazetteer'),
                       (lambda: por_propiedad_horizontal(tokens), 'propiedad_horizontal'),
                       (lambda: por_frase(nucleo), 'frase'),
                       (lambda: por_token(tokens), 'token'),
                       (lambda: por_token_aproximado(tokens), 'token_aproximado')):
        resultado = fn()
        if resultado:
            seccion, division, motivo = resultado
            return seccion, division, origen, motivo

    return '', '', 'sin_evidencia', 'ninguna palabra clave del catálogo CIIU coincide'


def etiqueta(seccion: str, division: str) -> str:
    """Etiqueta legible de la división; si no se conoce, la de la sección."""
    for (s, d, e, _p) in reglas.REGLAS_CIIU.values():
        if s == seccion and d == division:
            return e
    return reglas.SECCIONES_CIIU.get(seccion, '')


def vista_ejecutiva(seccion: str) -> str:
    """Agregación de secciones CIIU para la presentación ejecutiva."""
    return reglas.AGREGADO_EJECUTIVO.get(seccion, 'Sin clasificar')
