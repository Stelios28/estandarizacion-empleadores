# -*- coding: utf-8 -*-
"""
Fase 8 — determinación de la razón social canónica.

El dataset llegó deduplicado (NOTAS_PERFILAMIENTO.MD §3), así que la heurística
habitual de entity resolution —"la variante más frecuente del clúster es el nombre
bueno"— no es aplicable: todas las variantes tienen frecuencia 1.

El canónico se determina entonces por regla lingüística y evidencia, en este orden:

  1. Coincidencia con el gazetteer de grandes empleadores  -> nombre oficial
  2. Variante más informativa del clúster                  -> reconstrucción
  3. Presentación: capitalización española y sufijo societario en forma legal
"""
from __future__ import annotations

import collections
import re

import reglas

# Siglas que deben permanecer en mayúscula al capitalizar.
ACRONIMOS: set[str] = {
    'ACP', 'CSS', 'IDAAN', 'MEDUCA', 'MINSA', 'MOP', 'MIDA', 'MIDES', 'MICI',
    'MEF', 'MIRE', 'ATTT', 'ATP', 'AMP', 'SENAN', 'SENAFRONT', 'SENADIS',
    'IFARHU', 'IPT', 'CEBG', 'UTP', 'UP', 'UDELAS', 'USMA', 'UNACHI',
    'HSBC', 'BBVA', 'BAC', 'BNP', 'HP', 'IBM', 'BMW', 'KFC', 'PH', 'ZL',
    'SA', 'SAS', 'LLC', 'LTD', 'INC', 'CORP', 'BV', 'NV', 'AG', 'DHL', 'UPS',
    'PWC', 'KPMG', 'EY', 'TV', 'FM', 'AM', 'GPS', 'IT', 'RH', 'PYME',
}

# Conectores que van en minúscula salvo al inicio del nombre.
CONECTORES: set[str] = {
    'DE', 'DEL', 'LA', 'LAS', 'EL', 'LOS', 'Y', 'E', 'EN', 'A', 'AL',
    'PARA', 'POR', 'CON', 'THE', 'OF', 'AND', 'FOR',
}

_RX_SOLO_CONSONANTES = re.compile(r'^[BCDFGHJKLMNPQRSTVWXYZ]+$')


def capitalizar(texto: str) -> str:
    """
    Capitalización en español: cada palabra en mayúscula inicial, los conectores en
    minúscula salvo al principio, y las siglas intactas.

    `MINISTERIO DE OBRAS PUBLICAS` -> `Ministerio de Obras Publicas`
    `HSBC BANK PANAMA`             -> `HSBC Bank Panama`
    `J M R SERVICIOS`              -> `J M R Servicios`
    """
    palabras = texto.split()
    salida: list[str] = []
    for i, p in enumerate(palabras):
        if p in ACRONIMOS:
            salida.append(p)
        elif len(p) <= 4 and _RX_SOLO_CONSONANTES.match(p):
            # Iniciales y siglas sin vocales: `J M R`, `FQM`, `BLM`.
            salida.append(p)
        elif p.isdigit():
            salida.append(p)
        elif i > 0 and p in CONECTORES:
            salida.append(p.lower())
        else:
            salida.append(p.capitalize())
    return ' '.join(salida)


def clave_gazetteer(tokens: list[str]) -> str:
    """Clave con la que se consulta el gazetteer: tokens significativos, en orden."""
    return ' '.join(t for t in tokens if t not in reglas.STOPWORDS)


# Índice del gazetteer por primer token, con las claves ya partidas. Evita recorrer
# las 185 entradas en cada consulta y permite exigir límite de palabra.
_INDICE_GAZETTEER: dict[str, list[tuple[list[str], tuple[str, str, str]]]] = {}
for _clave, _valor in reglas.GAZETTEER.items():
    _partes = _clave.split()
    _INDICE_GAZETTEER.setdefault(_partes[0], []).append((_partes, _valor))
# Primero las claves largas: `BANCO GENERAL` debe ganarle a `BANCO` si ambas están.
for _lista in _INDICE_GAZETTEER.values():
    _lista.sort(key=lambda par: -len(par[0]))


def buscar_gazetteer(tokens: list[str]) -> tuple[str, str, str] | None:
    """
    Coincidencia con el gazetteer de grandes empleadores.

    Se acepta si la clave aparece como **secuencia de tokens completos** dentro del
    nombre: `AUTORIDAD DEL CANAL DE PANAMA ESCLUSAS` sigue siendo la ACP.

    La comparación es por token y no por subcadena de caracteres, que era el
    comportamiento anterior y producía falsos positivos silenciosos: `AVIS` casaba
    dentro de `BELLAVISTA`, `DAVIS` y `BUENAVISTA`; `TIGO` dentro de `VERTIGO`;
    `GBM` dentro de `LGBM`. 128 registros de una sola clave (D15).
    """
    consulta = clave_gazetteer(tokens)
    if not consulta:
        return None
    directo = reglas.GAZETTEER.get(consulta)
    if directo:
        return directo

    partes = consulta.split()
    for i, token in enumerate(partes):
        for clave, valor in _INDICE_GAZETTEER.get(token, ()):
            if partes[i:i + len(clave)] == clave:
                return valor
    return None


def calidad_ortografica(tokens: list[str], df: dict[str, int]) -> int:
    """
    Cuán bien escrita está una variante, medido sobre el propio corpus.

    Un token bien escrito aparece en muchos registros; una errata aparece en uno.
    En el clúster de Copa Airlines, `COPA` tiene frecuencia documental alta y
    `COPAR` tiene 1 — así que el corpus mismo dice cuál grafía es la buena, sin
    diccionario externo y sin necesidad de frecuencias por cliente (que este
    dataset no tiene, ver NOTAS_PERFILAMIENTO.MD §3).

    Se toma el token *peor* soportado de la variante: una sola errata la descalifica.
    Se devuelve en escala logarítmica para que diferencias pequeñas no dominen
    sobre criterios más importantes.
    """
    significativos = [t for t in tokens if len(t) >= 4]
    if not significativos:
        return 0
    peor = min(df.get(t, 1) for t in significativos)
    return peor.bit_length()          # log2 aproximado, monótono y barato


# --- Un desempate por suma de frecuencias: probado y descartado (D30) -------
#
# `calidad_ortografica` mira el **mínimo**, y eso resuelve el caso en que una
# variante está limpia del todo. Cuando todas traen algún token raro, todas
# empatan y el desempate cae en «la más larga», que a veces premia la errata:
#
#     ADMINISTRACION DE APARTITELES    (29)  <- se descartaba
#     ADMINISTRACIONN DE APARTOTELES   (30)  <- ganaba, con dos enes
#
# Se probó sumar el respaldo de todos los tokens en lugar de tomar el peor. Movió
# 9.947 registros y el saldo fue **negativo**:
#
#   Assa Compa Ia de Seguros  -> ASSA Compañía de Seguros, S.A.   mejor
#   Cab Le Onda               -> Cable Onda, S.A.                 mejor
#   Franquicias Panameñas SA  -> Franquicias Panamena             PEOR: pierde el gazetteer
#   Tetra Pak Panamá          -> Tetra Park                       PEOR: pierde el gazetteer
#   Produccion Panamena Hielo -> Productos Panamena de Hielo       PEOR: cambia el sentido
#   American Sportswear       -> America Sportswear                PEOR
#
# **La suma de frecuencias no mide «bien escrito», mide «usa palabras comunes».**
# `PRODUCTOS` es más frecuente que `PRODUCCION` y `AMERICA` más que `AMERICAN`, así
# que la variante equivocada gana en cuanto sus palabras son más corrientes.
#
# Lo que sí es un defecto real, y queda anotado como **R14**: las mejores mejoras
# del experimento —`Compa Ia`, `Cab Le`, `Paname a`— son variantes con la palabra
# **partida por la eliminación de la Ñ** en la fase 1. Eso se arregla reparando el
# token partido, no cambiando el criterio de selección.


def elegir_representante(variantes: list[dict],
                         df: dict[str, int] | None = None) -> dict:
    """
    Variante más informativa del clúster.

    Criterios, en orden de prioridad:
      1. No estar truncada — un nombre cortado nunca puede ser el canónico.
      2. Estar bien escrita, medido por frecuencia documental (ver arriba).
         Sin este criterio el canónico salía como `Copar Airlines` y
         `Comidas Rapidas Internancionales`: la variante con errata era la más
         larga, y la longitud sola premiaba el error.
      3. Tener más tokens significativos.
      4. Traer sufijo societario.
      5. Ser más larga.
      6. Orden alfabético, para que el resultado sea determinístico entre corridas.

    Se probó insertar un criterio de «respaldo ortográfico en conjunto» entre el 2
    y el 3, y se descartó con evidencia: ver la nota sobre D30 arriba.
    """
    df = df or {}

    def puntaje(v: dict) -> tuple:
        tokens = v['nucleo'].split()
        return (
            0 if v['truncado'] == '1' else 1,
            calidad_ortografica(tokens, df),
            len(tokens),
            1 if v['sufijo_societario'] else 0,
            len(v['limpio']),
            v['limpio'],
        )

    return max(variantes, key=puntaje)


# Entidades públicas y educativas: nunca llevan sufijo societario mercantil.
# Sin esta guarda el canónico salía como `Ministerio de Economia y Finanzas, S.A.`
# y `Cuerpo de Bomberos, S.A.`, porque una variante del clúster traía un `SA`
# escrito por error en el formulario.
ENCABEZADOS_SIN_SUFIJO: set[str] = {
    'MINISTERIO', 'AUTORIDAD', 'CONTRALORIA', 'TRIBUNAL', 'ORGANO', 'ASAMBLEA',
    'PROCURADURIA', 'DEFENSORIA', 'CAJA', 'CUERPO', 'POLICIA', 'MUNICIPIO',
    'ALCALDIA', 'JUNTA', 'SECRETARIA', 'DIRECCION', 'GOBERNACION', 'CORREGIDURIA',
    'UNIVERSIDAD', 'ESCUELA', 'COLEGIO', 'INSTITUTO', 'HOSPITAL', 'POLICLINICA',
    'IGLESIA', 'PARROQUIA', 'FUNDACION', 'EMBAJADA', 'CONSULADO', 'LOTERIA',
}


def decidir_sufijo(variantes: list[dict], rep: dict) -> tuple[str, str]:
    """
    ¿Lleva sufijo societario el nombre canónico? Devuelve (sufijo, motivo).

    Dos guardas, porque una sola variante mal capturada no debe convertir a un
    ministerio en sociedad anónima:

      1. La entidad no puede ser pública ni educativa.
      2. El sufijo debe aparecer en al menos la mitad de las variantes del clúster.
    """
    tokens = rep['nucleo'].split()
    if tokens and tokens[0] in ENCABEZADOS_SIN_SUFIJO:
        return '', 'sufijo societario omitido: entidad pública o institucional'

    con_sufijo = collections.Counter(v['sufijo_societario'] for v in variantes
                                     if v['sufijo_societario'])
    if not con_sufijo:
        return '', ''

    mayoritario, cuantos = con_sufijo.most_common(1)[0]
    if cuantos * 2 < len(variantes):
        return '', ('sufijo societario omitido: solo %d de %d variantes lo traen'
                    % (cuantos, len(variantes)))
    return mayoritario, ''


def construir(variantes: list[dict],
              df: dict[str, int] | None = None) -> tuple[str, str, list[str]]:
    """
    Devuelve (nombre_canonico, origen, traza) para un clúster.

    `origen` es 'gazetteer' o 'reconstruccion' y alimenta el score de confianza.
    """
    traza: list[str] = []
    rep = elegir_representante(variantes, df)

    hit = buscar_gazetteer(rep['nucleo'].split())
    if hit:
        traza.append('gazetteer: entidad reconocida')
        return hit[0], 'gazetteer', traza

    if rep['truncado'] == '1' and len(variantes) == 1:
        traza.append('nombre truncado en origen y sin variante completa en el corpus')

    nombre = capitalizar(rep['nucleo'])

    sufijo, motivo = decidir_sufijo(variantes, rep)
    if motivo:
        traza.append(motivo)
    if sufijo:
        forma = reglas.FORMA_CANONICA_SUFIJO.get(sufijo, sufijo)
        nombre = '%s, %s' % (nombre, forma)
        traza.append('sufijo societario normalizado: %s -> %s' % (sufijo, forma))

    if len(variantes) > 1:
        traza.append('representante elegido entre %d variantes del clúster' % len(variantes))

    return nombre, 'reconstruccion', traza
