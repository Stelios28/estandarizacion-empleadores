# -*- coding: utf-8 -*-
"""
Bloque 3 — Fases 8, 9 y 11: razón social canónica, sector CIIU y reproceso iterativo.

El reproceso (fase 11) es lo que hace que el pipeline aprenda de sí mismo: una vez
formados los clústeres, el conocimiento adquirido en una variante se propaga a todas
las demás. Dos efectos concretos:

  * Un clúster cuyo representante es una anotación del sistema arrastra a sus
    variantes tipográficas. `DEPENDEINTE ECONOMICA` no coincidía con ningún marcador
    escrito a mano; su clúster sí.
  * Un clúster con una variante clasificada y otras sin clasificar hereda el sector
    de la que sí tuvo evidencia.

Entrada : trabajo/01_registros.csv.gz, trabajo/02_clusters.json
Salida  : trabajo/03_clusters_resueltos.csv.gz   una fila por clúster
          trabajo/03_resumen.json

Uso: .venv\\Scripts\\python.exe codigo/03_canonico_sector.py
"""
from __future__ import annotations

import collections
import os
import sys

from rapidfuzz import fuzz, process

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import canonico
import comun
import reglas
import sector

# Un clúster se reclasifica como anotación o situación laboral si su representante
# se parece lo suficiente a un marcador conocido. Recupera las variantes con
# errores de digitación que la coincidencia literal no atrapa.
UMBRAL_RECLASIFICACION = 88.0

TIPOS_EMPLEADOR = {'EMPRESA', 'INDEPENDIENTE_CON_ACTIVIDAD', 'PERSONA_NATURAL'}

ETIQUETA_POR_TIPO = {
    'DIRECCION': reglas.SECTOR_DIRECCION,
    'VACIO': reglas.SECTOR_FALTA_INFO,
    'ANOTACION': reglas.SECTOR_NO_EMPLEADOR,
    'INACTIVO': reglas.SECTOR_NO_EMPLEADOR,
    'OCUPACION': reglas.SECTOR_NO_EMPLEADOR,
    'INDEPENDIENTE': reglas.SECTOR_NO_EMPLEADOR,
}

NOMBRE_POR_TIPO = {
    'DIRECCION': 'No identificable - Direcciones',
    'VACIO': 'No identificable - Falta informacion',
    'ANOTACION': 'No identificable - No es un empleador',
    'INACTIVO': 'No identificable - No es un empleador',
    'OCUPACION': 'No identificable - No es un empleador',
    'INDEPENDIENTE': 'Trabajador independiente',
}

COLUMNAS = [
    'cluster', 'n_claves', 'n_registros', 'representante', 'nombre_canonico',
    'origen_nombre', 'seccion_ciiu', 'division_ciiu', 'sector_propuesto',
    'vista_ejecutiva', 'origen_sector', 'motivo_sector', 'requiere_fase7', 'traza',
]

_MARCADORES_NO_EMPLEADOR = sorted(
    reglas.MARCADORES_ANOTACION | reglas.MARCADORES_INACTIVO
)


def reclasificar_por_similitud(representante: str) -> tuple[str, str] | None:
    """
    ¿El representante del clúster es en realidad una anotación o una situación
    laboral mal escrita? Devuelve (tipo, marcador) o None.
    """
    hit = process.extractOne(representante, _MARCADORES_NO_EMPLEADOR,
                             scorer=fuzz.token_sort_ratio,
                             score_cutoff=UMBRAL_RECLASIFICACION)
    if not hit:
        return None
    marcador = hit[0]
    tipo = 'ANOTACION' if marcador in reglas.MARCADORES_ANOTACION else 'INACTIVO'
    return tipo, marcador


def main() -> None:
    with comun.Fase('cargar registros y clústeres'):
        asignacion = comun.leer_json(comun.ruta_trabajo('02_clusters.json'))
        df = comun.leer_json(comun.ruta_trabajo('01_df_tokens.json'))
        por_cluster: dict[int, list[dict]] = collections.defaultdict(list)
        sueltos: list[dict] = []          # tipos que no son empleador
        for fila in comun.leer_csv(comun.ruta_trabajo('01_registros.csv.gz')):
            if fila['tipo'] in TIPOS_EMPLEADOR:
                por_cluster[asignacion[fila['clave']]].append(fila)
            else:
                sueltos.append(fila)
        comun.log('  clústeres de empleador: %d | registros no empleador: %d'
                  % (len(por_cluster), len(sueltos)))

    with comun.Fase('fase 8-9: canónico y sector por clúster'):
        resueltos: list[list] = []
        reclasificados = 0
        for cid, variantes in por_cluster.items():
            rep = canonico.elegir_representante(variantes, df)
            traza: list[str] = []

            # Fase 11: propagar el conocimiento del clúster a todas sus variantes.
            n_claves = len({v['clave'] for v in variantes})

            recl = reclasificar_por_similitud(rep['limpio'])
            if recl:
                tipo, marcador = recl
                reclasificados += 1
                resueltos.append([
                    cid, n_claves, len(variantes), rep['limpio'],
                    NOMBRE_POR_TIPO[tipo], 'reclasificacion_cluster', '', '',
                    ETIQUETA_POR_TIPO[tipo], 'No aplica', 'reclasificacion',
                    'el clúster coincide con el marcador "%s"' % marcador, 0,
                    'reclasificado en fase 11 por similitud con un marcador conocido',
                ])
                continue

            nombre, origen_nombre, traza_nom = canonico.construir(variantes, df)
            traza.extend(traza_nom)

            # Fase 11: el sector se decide por voto ponderado entre todas las
            # variantes del clúster, no por el primer acierto.
            seccion, division, origen_sec, motivo_sec = sector.clasificar_cluster(
                sorted({v['nucleo'] for v in variantes}))

            requiere_f7 = int(origen_sec == 'sin_evidencia')
            etiqueta_sec = (sector.etiqueta(seccion, division) if seccion
                            else reglas.SECTOR_PENDIENTE)

            resueltos.append([
                cid, n_claves, len(variantes), rep['limpio'], nombre,
                origen_nombre, seccion, division, etiqueta_sec,
                sector.vista_ejecutiva(seccion) if seccion else 'Sin clasificar',
                origen_sec, motivo_sec, requiere_f7, '; '.join(traza),
            ])

        comun.log('  clústeres resueltos: %d | reclasificados en fase 11: %d'
                  % (len(resueltos), reclasificados))

    with comun.Fase('escribir intermedios'):
        comun.escribir_csv(comun.ruta_trabajo('03_clusters_resueltos.csv.gz'),
                           COLUMNAS, resueltos)

    # ---- métricas -------------------------------------------------------
    origen_sec = collections.Counter(r[10] for r in resueltos)
    origen_nom = collections.Counter(r[5] for r in resueltos)
    secciones = collections.Counter(r[6] for r in resueltos if r[6])
    pendientes = sum(1 for r in resueltos if r[12])
    n = len(resueltos)

    resumen = {
        'clusters': n,
        'registros_no_empleador': len(sueltos),
        'reclasificados_fase11': reclasificados,
        'origen_nombre': dict(origen_nom),
        'origen_sector': dict(origen_sec),
        'clusters_pendientes_fase7': pendientes,
        'secciones_ciiu': dict(secciones),
    }
    comun.escribir_json(comun.ruta_trabajo('03_resumen.json'), resumen)

    print('\n=== BLOQUE 3 — RESULTADO ===')
    print('Clústeres de empleador        : %8d' % n)
    print('Reclasificados en fase 11     : %8d' % reclasificados)
    print('\nOrigen del nombre canónico:')
    for k, v in origen_nom.most_common():
        print('  %-26s %8d  %5.1f%%' % (k, v, 100.0 * v / n))
    print('\nOrigen del sector:')
    for k, v in origen_sec.most_common():
        print('  %-26s %8d  %5.1f%%' % (k, v, 100.0 * v / n))
    reg_total = sum(int(r[2]) for r in resueltos)
    reg_pend = sum(int(r[2]) for r in resueltos if r[12])
    print('\nCobertura sectorial:')
    print('  clústeres clasificados      : %8d  %5.1f%%'
          % (n - pendientes, 100.0 * (n - pendientes) / n))
    print('  registros clasificados      : %8d  %5.1f%%'
          % (reg_total - reg_pend, 100.0 * (reg_total - reg_pend) / reg_total))
    print('  pendientes para fase 7      : %8d clústeres / %d registros'
          % (pendientes, reg_pend))
    print('\nDistribución por sección CIIU (clústeres clasificados):')
    total_clas = sum(secciones.values())
    for s, v in secciones.most_common():
        print('  %s  %-58s %7d  %5.1f%%'
              % (s, reglas.SECCIONES_CIIU.get(s, '')[:58], v, 100.0 * v / total_clas))


if __name__ == '__main__':
    main()
