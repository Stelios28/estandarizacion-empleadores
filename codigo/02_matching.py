# -*- coding: utf-8 -*-
"""
Bloque 2 — Fases 5 y 6 del Anexo A: matching difuso y resolución de entidades.

El problema es cuadrático por naturaleza: 247.386 claves distintas son 30.600
millones de pares. La solución no es un umbral más alto, es no generar el par.

Estrategia de bloqueo, en tres canales complementarios:

  1. **Token raro compartido.** Un par solo se evalúa si comparte al menos un token
     de baja frecuencia documental. Es lo que impide que `BANCO UNO` y
     `BANCO CONTINENTAL` lleguen siquiera a compararse: `BANCO` es genérico y
     `UNO`/`CONTINENTAL` no coinciden. Precisión por construcción, no por umbral.

  2. **Afijo de token raro.** Primeros y últimos 4 caracteres de cada token raro.
     Recupera los errores de digitación dentro del token distintivo
     (`ODEBRECHT` / `ODEBRETCH`), que el canal 1 se perdería.

  3. **Prefijo, para los truncados.** ~20.500 registros llegan cortados a 30 o 40
     caracteres. Un nombre truncado es prefijo exacto de su nombre completo, no un
     error ortográfico, y necesita una regla propia con distancia asimétrica.

Entrada : trabajo/01_registros.csv.gz, trabajo/01_df_tokens.json
Salida  : trabajo/02_clusters.json       clave -> id de clúster
          trabajo/02_pares.csv.gz        pares evaluados y aceptados, con score
          trabajo/02_resumen.json

Uso: .venv\\Scripts\\python.exe codigo/02_matching.py
"""
from __future__ import annotations

import collections
import itertools
import os
import sys

from rapidfuzz import fuzz, process

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import comun
import reglas

# --------------------------------------------------------------------------
# Parámetros de bloqueo y aceptación
# --------------------------------------------------------------------------

# Un token que aparece en más de este número de claves no sirve para bloquear:
# su bloque sería enorme y no discrimina.
MAX_TAMANO_BLOQUE = 120

# Tokens raros por clave que se usan para bloquear. Más de tres multiplica el costo
# sin mejorar el recall de forma apreciable.
TOKENS_BLOQUEO_POR_CLAVE = 3

# Umbral de aceptación del par.
UMBRAL_ACEPTACION = 88.0
# Con dos o más tokens raros en común se puede ser algo más permisivo: la evidencia
# de identidad ya es fuerte antes de mirar la similitud de cadena.
UMBRAL_CON_EVIDENCIA_FUERTE = 82.0
# Sin ningún token distintivo en común solo se acepta una coincidencia casi literal:
# el par llegó por el canal de afijos y toda la evidencia es la cadena misma.
UMBRAL_SIN_EVIDENCIA = 94.0

# Longitud mínima del prefijo para aceptar un match por truncamiento.
MIN_PREFIJO_TRUNCADO = 18

# Coherencia mínima entre los representantes de dos clústeres para poder fusionarlos.
#
# Sin esta guarda, Union-Find encadena: si A~B y B~C, A y C terminan juntos aunque
# no se parezcan. En la primera corrida eso metió `HOSPITAL ARNULFO ARIAS`,
# `COMPLEJO HOSPITALARIO METROPOLITANO` y `HOSPITAL MANUEL AMADOR GUERRERO` —tres
# hospitales distintos— en un mismo clúster de 131 claves.
#
# La fusión se procesa en orden descendente de score y exige que los dos
# representantes también se parezcan entre sí, no solo el par que disparó la unión.
UMBRAL_COHESION = 86.0

# Zona de duda razonable.
#
# Se midió la separación entre pares que son la misma entidad y pares que no lo son
# (evidencia en el documento técnico): las dos poblaciones se solapan entre 76 y 88.
# No existe un umbral que las separe — la similitud de cadena ya no alcanza.
#
# Esa banda no se resuelve adivinando. Se marca y pasa a la fase 7, que es
# exactamente lo que el enunciado llama "búsqueda web cuando existan dudas
# razonables". Debajo de la banda son entidades distintas y no se consulta nada.
BANDA_DUDA_MINIMA = 76.0


# --------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------

class Nodo:
    """Una clave distinta del corpus. Es la unidad que se agrupa, no el registro."""

    __slots__ = ('clave', 'nucleo', 'reducido', 'limpio', 'tokens', 'truncado',
                 'n_registros')

    def __init__(self, clave: str):
        self.clave = clave
        self.nucleo = ''
        self.reducido = ''          # sin calificadores de sucursal ni de cargo
        self.limpio = ''
        self.tokens: frozenset[str] = frozenset()
        self.truncado = False
        self.n_registros = 0


def cargar_nodos() -> tuple[list[Nodo], dict[str, int]]:
    """
    Colapsa los 323.000 registros en sus claves distintas.

    Representante de cada clave: la variante más larga no truncada, porque es la
    que más información conserva. Si todas están truncadas, la más larga.
    """
    por_clave: dict[str, Nodo] = {}
    mejor_limpio: dict[str, tuple[int, int, str]] = {}
    tipos_validos = {'EMPRESA', 'INDEPENDIENTE_CON_ACTIVIDAD', 'PERSONA_NATURAL'}

    for fila in comun.leer_csv(comun.ruta_trabajo('01_registros.csv.gz')):
        if fila['tipo'] not in tipos_validos:
            continue
        clave = fila['clave']
        nodo = por_clave.get(clave)
        if nodo is None:
            nodo = por_clave[clave] = Nodo(clave)
            nodo.tokens = frozenset(fila['nucleo'].split())
        nodo.n_registros += 1

        truncado = fila['truncado'] == '1'
        nodo.truncado = nodo.truncado or truncado
        # prioridad: no truncado primero, luego más largo
        candidato = (0 if truncado else 1, len(fila['limpio']), fila['limpio'])
        if clave not in mejor_limpio or candidato > mejor_limpio[clave]:
            mejor_limpio[clave] = candidato
            nodo.nucleo = fila['nucleo']
            nodo.limpio = fila['limpio']

    for nodo in por_clave.values():
        reducido, _ = reglas.quitar_calificadores(nodo.nucleo.split())
        nodo.reducido = ' '.join(reducido)

    nodos = list(por_clave.values())
    indice = {n.clave: i for i, n in enumerate(nodos)}
    return nodos, indice


# --------------------------------------------------------------------------
# Canal 1 y 2 — bloqueo por token raro y por afijo
# --------------------------------------------------------------------------

def tokens_de_bloqueo(nodo: Nodo, df: dict[str, int]) -> list[str]:
    """Los N tokens de menor frecuencia documental del nodo: los que identifican."""
    candidatos = [t for t in nodo.tokens if len(t) >= 2 and t not in reglas.STOPWORDS]
    if not candidatos:
        candidatos = list(nodo.tokens)
    candidatos.sort(key=lambda t: (df.get(t, 1), t))
    return candidatos[:TOKENS_BLOQUEO_POR_CLAVE]


def construir_bloques(nodos: list[Nodo], df: dict[str, int]) -> dict[str, list[int]]:
    """Índice invertido: señal de bloqueo -> índices de nodo."""
    bloques: dict[str, list[int]] = collections.defaultdict(list)
    for i, nodo in enumerate(nodos):
        for t in tokens_de_bloqueo(nodo, df):
            bloques['T:' + t].append(i)
            if len(t) >= 6:                       # canal 2: tolerancia a digitación
                bloques['P:' + t[:4]].append(i)
                bloques['S:' + t[-4:]].append(i)
    return bloques


# --------------------------------------------------------------------------
# Reglas de aceptación
# --------------------------------------------------------------------------

def evidencia_compartida(a: Nodo, b: Nodo, df: dict[str, int], corte: int) -> int:
    """Cuántos tokens raros comparten los dos nodos."""
    return sum(1 for t in (a.tokens & b.tokens) if df.get(t, 1) < corte)


def es_truncado_de(corto: Nodo, largo: Nodo) -> bool:
    """
    ¿`corto` es la versión truncada de `largo`?

    Distancia asimétrica: cortar el final es barato, cambiar el inicio no lo es.
    Por eso se exige prefijo exacto y no una similitud global.
    """
    if not corto.truncado or len(corto.limpio) >= len(largo.limpio):
        return False
    if len(corto.limpio) < MIN_PREFIJO_TRUNCADO:
        return False
    if not largo.limpio.startswith(corto.limpio):
        return False
    # El corte debe caer en un límite de palabra o a media palabra, nunca dejando
    # que "BANCO GENERAL" absorba a "BANCO GENERAL DE SEGUROS" por casualidad:
    # se exige que el original estuviera efectivamente en el tope del campo.
    return len(corto.limpio) in (30, 40)


def decidir(a: Nodo, b: Nodo, df: dict[str, int], corte: int) -> tuple[bool, float, str]:
    """
    ¿Son la misma entidad? Devuelve (acepta, score, motivo).

    El motivo es obligatorio: el enunciado exige explicar cada decisión.
    """
    if es_truncado_de(a, b):
        return True, 100.0, 'truncamiento: "%s" es prefijo exacto de "%s" en el tope de %d caracteres' % (
            a.limpio, b.limpio, len(a.limpio))
    if es_truncado_de(b, a):
        return True, 100.0, 'truncamiento: "%s" es prefijo exacto de "%s" en el tope de %d caracteres' % (
            b.limpio, a.limpio, len(b.limpio))

    raros = evidencia_compartida(a, b, df, corte)
    score = fuzz.token_sort_ratio(a.nucleo, b.nucleo)
    if raros >= 2:
        umbral = UMBRAL_CON_EVIDENCIA_FUERTE
    elif raros == 1:
        umbral = UMBRAL_ACEPTACION
    else:
        umbral = UMBRAL_SIN_EVIDENCIA

    if score >= umbral:
        compartidos = sorted(t for t in (a.tokens & b.tokens) if df.get(t, 1) < corte)
        return True, score, 'similitud %.1f >= %.0f con %d token(s) distintivo(s) en común: %s' % (
            score, umbral, raros, ', '.join(compartidos[:4]) or 'ninguno')

    return False, score, 'similitud %.1f < %.0f' % (score, umbral)


def cohesion(a: Nodo, b: Nodo) -> float:
    """
    Similitud entre los representantes de dos clústeres que se quieren fusionar.

    Se mide sobre el núcleo completo y sobre el núcleo sin calificadores de
    sucursal o cargo, y se toma la mayor: `IDAAN ANALISTA DE RECARGO` e
    `IDAAN FONTANERO III` son el mismo empleador aunque las cadenas se parezcan poco.

    Un prefijo exacto vale 100: es la relación de truncamiento, no un parecido.
    """
    if a.limpio and b.limpio:
        corto, largo = sorted((a.limpio, b.limpio), key=len)
        if len(corto) >= MIN_PREFIJO_TRUNCADO and largo.startswith(corto):
            return 100.0
    return max(fuzz.token_sort_ratio(a.nucleo, b.nucleo),
               fuzz.token_sort_ratio(a.reducido, b.reducido))


# --------------------------------------------------------------------------
# Proceso
# --------------------------------------------------------------------------

def main() -> None:
    with comun.Fase('cargar claves distintas'):
        nodos, indice = cargar_nodos()
        df = comun.leer_json(comun.ruta_trabajo('01_df_tokens.json'))
        resumen_1 = comun.leer_json(comun.ruta_trabajo('01_resumen.json'))
        corte = resumen_1['corte_generico']
        comun.log('  %d claves distintas | corte de token genérico: %d' % (len(nodos), corte))

    with comun.Fase('construir bloques'):
        bloques = construir_bloques(nodos, df)
        utiles = {k: v for k, v in bloques.items() if 2 <= len(v) <= MAX_TAMANO_BLOQUE}
        descartados = sum(1 for v in bloques.values() if len(v) > MAX_TAMANO_BLOQUE)
        pares_teoricos = sum(len(v) * (len(v) - 1) // 2 for v in utiles.values())
        comun.log('  señales: %d | bloques útiles: %d | demasiado grandes: %d'
                  % (len(bloques), len(utiles), descartados))
        comun.log('  pares candidatos (con repetición): %d' % pares_teoricos)

    with comun.Fase('evaluar pares candidatos'):
        vistos: set[tuple[int, int]] = set()
        aceptados: list[tuple[int, int, float, str]] = []
        evaluados = 0

        for señal, miembros in utiles.items():
            for i, j in itertools.combinations(sorted(miembros), 2):
                if (i, j) in vistos:
                    continue
                vistos.add((i, j))
                evaluados += 1
                acepta, score, motivo = decidir(nodos[i], nodos[j], df, corte)
                if acepta:
                    aceptados.append((i, j, score, motivo))

        comun.log('  pares únicos evaluados: %d | aceptados: %d' % (evaluados, len(aceptados)))

    with comun.Fase('fusión ordenada con guarda de cohesión'):
        # Orden descendente de score: las uniones más seguras se consolidan primero
        # y fijan el representante del clúster; las dudosas se miden contra él.
        aceptados.sort(key=lambda p: -p[2])
        uf = comun.UnionFind(len(nodos))
        representante = {i: i for i in range(len(nodos))}
        fusiones = 0
        bloqueadas: list[tuple[str, str, float]] = []
        dudas: list[tuple[str, str, float, int]] = []

        for i, j, score, motivo in aceptados:
            ri, rj = uf.buscar(i), uf.buscar(j)
            if ri == rj:
                continue
            a, b = nodos[representante[ri]], nodos[representante[rj]]
            coh = cohesion(a, b)
            if coh < UMBRAL_COHESION:
                if coh >= BANDA_DUDA_MINIMA:
                    dudas.append((a.limpio, b.limpio, coh,
                                  evidencia_compartida(a, b, df, corte)))
                else:
                    bloqueadas.append((a.limpio, b.limpio, coh))
                continue
            uf.unir(i, j)
            nueva = uf.buscar(i)
            # Representante del clúster fusionado: el nombre más completo.
            representante[nueva] = max(
                (representante[ri], representante[rj]),
                key=lambda k: (not nodos[k].truncado, len(nodos[k].limpio)),
            )
            fusiones += 1

        comun.log('  fusiones aplicadas: %d | en zona de duda: %d | descartadas: %d'
                  % (fusiones, len(dudas), len(bloqueadas)))

    with comun.Fase('formar clústeres'):
        grupos = uf.grupos()
        asignacion = {}
        for cid, (raiz, miembros) in enumerate(sorted(grupos.items(), key=lambda kv: -len(kv[1]))):
            for m in miembros:
                asignacion[nodos[m].clave] = cid
        multi = [g for g in grupos.values() if len(g) > 1]
        comun.log('  clústeres: %d | con más de una clave: %d' % (len(grupos), len(multi)))

    with comun.Fase('escribir intermedios'):
        comun.escribir_json(comun.ruta_trabajo('02_clusters.json'), asignacion)
        comun.escribir_csv(
            comun.ruta_trabajo('02_pares.csv.gz'),
            ['clave_a', 'clave_b', 'score', 'motivo'],
            ((nodos[i].limpio, nodos[j].limpio, round(s, 1), m) for i, j, s, m in aceptados),
        )
        comun.escribir_csv(
            comun.ruta_trabajo('02_fusiones_descartadas.csv.gz'),
            ['representante_a', 'representante_b', 'cohesion'],
            ((a, b, round(c, 1)) for a, b, c in bloqueadas),
        )
        # Entrada de la fase 7: los pares que la similitud de cadena no puede
        # resolver y que sí justifican una consulta externa.
        comun.escribir_csv(
            comun.ruta_trabajo('02_zona_duda.csv.gz'),
            ['representante_a', 'representante_b', 'cohesion', 'tokens_distintivos'],
            ((a, b, round(c, 1), r) for a, b, c, r in
             sorted(dudas, key=lambda d: (-d[3], -d[2]))),
        )

    registros_en_multi = sum(nodos[m].n_registros for g in multi for m in g)
    resumen = {
        'claves': len(nodos),
        'senales_bloqueo': len(bloques),
        'bloques_utiles': len(utiles),
        'bloques_descartados_por_tamano': descartados,
        'pares_evaluados': evaluados,
        'pares_aceptados': len(aceptados),
        'fusiones_aplicadas': fusiones,
        'pares_en_zona_duda': len(dudas),
        'fusiones_descartadas': len(bloqueadas),
        'clusters': len(grupos),
        'clusters_multiples': len(multi),
        'registros_en_clusters_multiples': registros_en_multi,
    }
    comun.escribir_json(comun.ruta_trabajo('02_resumen.json'), resumen)

    print('\n=== BLOQUE 2 — RESULTADO ===')
    print('Claves de entrada             : %8d' % len(nodos))
    print('Pares evaluados               : %8d  (de %d posibles sin bloqueo)'
          % (evaluados, len(nodos) * (len(nodos) - 1) // 2))
    print('Reducción por bloqueo         : %11.6f%% del espacio'
          % (100.0 * evaluados / (len(nodos) * (len(nodos) - 1) / 2)))
    print('Pares aceptados               : %8d' % len(aceptados))
    print('  fusiones aplicadas          : %8d' % fusiones)
    print('  en zona de duda razonable   : %8d  (van a fase 7)' % len(dudas))
    print('  descartadas                 : %8d  (entidades distintas)' % len(bloqueadas))
    print('Clústeres resultantes         : %8d' % len(grupos))
    print('  con más de una clave        : %8d' % len(multi))
    print('  registros que unifican      : %8d' % registros_en_multi)

    print('\nMayores clústeres formados por fuzzy:')
    for raiz, miembros in sorted(grupos.items(), key=lambda kv: -len(kv[1]))[:10]:
        if len(miembros) < 2:
            break
        print('  [%d claves] %s' % (len(miembros),
                                    ' | '.join(nodos[m].limpio for m in miembros[:4])[:110]))


if __name__ == '__main__':
    main()
