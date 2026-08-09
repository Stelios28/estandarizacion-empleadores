# -*- coding: utf-8 -*-
"""
Bloque 1 — Fases 1 a 4 del Anexo A.

  1. Perfilamiento          -> ya cubierto por 00_perfilamiento.py
  2. Limpieza y normalización
  3. Diccionario incremental de empleadores
  4. Matching exacto sobre la clave de núcleo

Entrada : prueba_tecnica_ing_datos.xlsx (solo lectura)
Salida  : trabajo/01_registros.csv.gz   un registro por fila, con traza
          trabajo/01_claves.json        clave -> lista de índices (grupos exactos)
          trabajo/01_df_tokens.json     frecuencia documental de cada token
          trabajo/01_resumen.json       métricas de la fase

Se hacen dos pasadas de normalización a propósito: la primera mide la frecuencia
documental de cada token sobre el corpus real, la segunda usa esa medida para
decidir qué tokens son genéricos al construir la clave. Escribir esa lista a mano
habría sido una suposición; medirla es evidencia.

Uso: .venv\\Scripts\\python.exe codigo/01_limpieza.py
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import comun
import normalizacion

COLUMNAS = [
    'idx', 'nombre_original', 'limpio', 'nucleo', 'clave',
    'sufijo_societario', 'sufijo_numerico', 'tipo', 'truncado', 'traza',
]

# Un token presente en más de este porcentaje de los registros no distingue a nadie.
# 0,25 % sobre 323.000 son ~800 apariciones: deja fuera GRUPO, INVERSIONES, SERVICIOS,
# CENTRO, PANAMA y similares, y conserva las iniciales y los nombres propios.
UMBRAL_GENERICO = 0.0025


def calcular_df(registros: list) -> dict[str, int]:
    """Frecuencia documental: en cuántos registros distintos aparece cada token."""
    df: dict[str, int] = collections.Counter()
    for reg in registros:
        df.update(set(reg.tokens))
    return dict(df)


def main() -> None:
    with comun.Fase('leer fuente'):
        crudos = comun.leer_fuente()
        comun.log('  %d registros leídos' % len(crudos))

    with comun.Fase('fase 2-3 (pasada 1): normalización y medición de tokens'):
        registros = [normalizacion.normalizar(i, c) for i, c in enumerate(crudos)]
        df = calcular_df(registros)
        corte = max(2, int(len(registros) * UMBRAL_GENERICO))
        genericos = frozenset(t for t, c in df.items() if c >= corte)
        comun.log('  tokens distintos: %d | corte genérico: >=%d apariciones | genéricos: %d'
                  % (len(df), corte, len(genericos)))

    with comun.Fase('fase 2-3 (pasada 2): claves con conciencia de tokens genéricos'):
        # `df` viaja a la segunda pasada: es el diccionario con el que se
        # reconstruyen las palabras que la Ñ destruida partió en dos (D31).
        registros = [normalizacion.normalizar(i, c, genericos, df)
                     for i, c in enumerate(crudos)]

    with comun.Fase('fase 4: matching exacto sobre clave de núcleo'):
        claves: dict[str, list[int]] = collections.defaultdict(list)
        for reg in registros:
            if reg.tipo in ('EMPRESA', 'INDEPENDIENTE_CON_ACTIVIDAD', 'PERSONA_NATURAL'):
                claves[reg.clave].append(reg.idx)
        grupos = {k: v for k, v in claves.items() if len(v) > 1}
        comun.log('  claves distintas          : %d' % len(claves))
        comun.log('  claves con más de un caso : %d' % len(grupos))
        comun.log('  registros ya agrupados    : %d' % sum(len(v) for v in grupos.values()))

    with comun.Fase('escribir intermedios'):
        ruta = comun.ruta_trabajo('01_registros.csv.gz')
        comun.escribir_csv(ruta, COLUMNAS, (
            [r.idx, r.original, r.limpio, r.nucleo, r.clave,
             r.sufijo_societario, r.sufijo_numerico, r.tipo,
             int(r.truncado), '; '.join(r.traza)]
            for r in registros
        ))
        comun.escribir_json(comun.ruta_trabajo('01_claves.json'),
                            {k: v for k, v in claves.items()})
        comun.escribir_json(comun.ruta_trabajo('01_df_tokens.json'), df)

    # ---- métricas -------------------------------------------------------
    tipos = collections.Counter(r.tipo for r in registros)
    n = len(registros)
    resumen = {
        'registros': n,
        'tipos': dict(tipos),
        'con_sufijo_societario': sum(1 for r in registros if r.sufijo_societario),
        'con_sufijo_numerico': sum(1 for r in registros if r.sufijo_numerico),
        'posibles_truncados': sum(1 for r in registros if r.truncado),
        'claves_distintas': len(claves),
        'claves_con_multiples': len(grupos),
        'registros_agrupados_exacto': sum(len(v) for v in grupos.values()),
        'tokens_distintos': len(df),
        'tokens_genericos': len(genericos),
        'corte_generico': corte,
    }
    comun.escribir_json(comun.ruta_trabajo('01_resumen.json'), resumen)

    print('\n=== BLOQUE 1 — RESULTADO ===')
    print('Registros procesados        : %d' % n)
    print('\nTipificación:')
    for tipo, cuenta in tipos.most_common():
        print('  %-30s %8d  %5.2f%%' % (tipo, cuenta, 100.0 * cuenta / n))
    print('\nAtributos separados:')
    print('  Con sufijo societario       : %8d  %5.2f%%'
          % (resumen['con_sufijo_societario'], 100.0 * resumen['con_sufijo_societario'] / n))
    print('  Con sufijo numérico         : %8d  %5.2f%%'
          % (resumen['con_sufijo_numerico'], 100.0 * resumen['con_sufijo_numerico'] / n))
    print('  Posibles truncados          : %8d  %5.2f%%'
          % (resumen['posibles_truncados'], 100.0 * resumen['posibles_truncados'] / n))
    print('\nMatching exacto (fase 4):')
    print('  Claves distintas            : %8d' % len(claves))
    print('  Claves con >1 variante      : %8d' % len(grupos))
    print('  Variantes ya unificadas     : %8d' % resumen['registros_agrupados_exacto'])

    print('\nMayores grupos exactos:')
    for clave, idxs in sorted(grupos.items(), key=lambda kv: -len(kv[1]))[:12]:
        muestra = ' | '.join(registros[i].limpio for i in idxs[:3])
        print('  %3d  %-38s %s' % (len(idxs), clave[:38], muestra[:70]))


if __name__ == '__main__':
    main()
