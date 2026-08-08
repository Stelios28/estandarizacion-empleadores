# -*- coding: utf-8 -*-
"""
Bloque 5 — Fases 10 y 12: score de confianza y tablas auditables.

Genera los entregables:

  salidas/dataset_resultado.csv      nombre_original, nombre_propuesto, sector_propuesto
  salidas/dataset_resultado.xlsx     el mismo dataset, para abrir sin fricción
  salidas/tabla_auditoria.csv.gz     una fila por registro con toda la traza
  salidas/maestro_corporativo.csv    una fila por empleador único
  salidas/kpis_calidad.json          métricas de calidad de datos
  salidas/concentracion_sectorial.csv  vista para riesgo de cartera

Si la fase 7 ya corrió, sus resultados se incorporan automáticamente.

Uso: .venv\\Scripts\\python.exe codigo/05_salida.py
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import comun
import confianza
import reglas
import sector as sector_mod

TIPOS_EMPLEADOR = {'EMPRESA', 'PERSONA_NATURAL'}

# Tipos que no son un empleador corporativo pero cuyo texto sí puede nombrar la
# actividad de la que vive la persona: el oficio del independiente, el empleador
# del que se jubiló, la universidad donde estudia. Conservan el sector aunque el
# nombre propuesto sea la etiqueta genérica del tipo.
SECTOR_RECUPERABLE = {'INDEPENDIENTE', 'INACTIVO'}

ETIQUETA_POR_TIPO = {
    'DIRECCION': (reglas.SECTOR_DIRECCION, reglas.SECTOR_DIRECCION),
    'VACIO': (reglas.SECTOR_FALTA_INFO, reglas.SECTOR_FALTA_INFO),
    'ANOTACION': ('No identificable - No es un empleador', reglas.SECTOR_NO_EMPLEADOR),
    'INACTIVO': ('No identificable - No es un empleador', reglas.SECTOR_NO_EMPLEADOR),
    'OCUPACION': ('No identificable - No es un empleador', reglas.SECTOR_NO_EMPLEADOR),
    'INDEPENDIENTE': ('Trabajador independiente', reglas.SECTOR_NO_EMPLEADOR),
}

# Un tipo no-empleador ya está resuelto con certeza: la etiqueta es la respuesta.
CONFIANZA_TIPO = {
    'DIRECCION': 92, 'VACIO': 95, 'ANOTACION': 90,
    'INACTIVO': 92, 'OCUPACION': 85, 'INDEPENDIENTE': 90,
}


def cargar_externos() -> dict[int, dict]:
    """Resultados de la fase 7, si existe la corrida."""
    ruta = comun.ruta_trabajo('04_sectores_externos.csv.gz')
    if not os.path.exists(ruta):
        return {}
    return {int(r['cluster']): r for r in comun.leer_csv(ruta)}


def main() -> None:
    with comun.Fase('cargar resultados de los bloques anteriores'):
        asignacion = comun.leer_json(comun.ruta_trabajo('02_clusters.json'))
        clusters = {int(r['cluster']): r for r in
                    comun.leer_csv(comun.ruta_trabajo('03_clusters_resueltos.csv.gz'))}
        externos = cargar_externos()
        df = comun.leer_json(comun.ruta_trabajo('01_df_tokens.json'))
        corte = comun.leer_json(comun.ruta_trabajo('01_resumen.json'))['corte_generico']
        comun.log('  clústeres: %d | enriquecidos en fase 7: %d'
                  % (len(clusters), len(externos)))

    with comun.Fase('fase 10-12: resolver cada registro, puntuar y explicar'):
        dataset: list[tuple[str, str, str]] = []
        auditoria: list[list] = []
        maestro: dict[int, list] = {}
        bandas = collections.Counter()
        scores: list[int] = []

        for fila in comun.leer_csv(comun.ruta_trabajo('01_registros.csv.gz')):
            original = fila['nombre_original']
            tipo = fila['tipo']

            # ---- registros que no son un empleador -------------------------
            if tipo not in TIPOS_EMPLEADOR:
                nombre, sec = ETIQUETA_POR_TIPO[tipo]
                score = CONFIANZA_TIPO[tipo]
                seccion = division = ''
                vista = 'No aplica'
                # El tipo dice que no hay vínculo laboral corporativo vigente; no dice
                # que no haya información. `INDEPENDIENTE AGRIMENSURA` declara su
                # oficio y `PANAMA CANAL COMMISSION JUBILADO` declara de dónde viene
                # su pensión. Ambos son la actividad económica de la que vive esa
                # persona, que es la columna que Riesgo necesita (D18, D19).
                if tipo in SECTOR_RECUPERABLE and fila['nucleo']:
                    s_, d_, origen_, _ = sector_mod.clasificar(
                        fila['nucleo'], fila['nucleo'].split())
                    if s_:
                        seccion, division = s_, d_
                        sec = sector_mod.etiqueta(s_, d_)
                        vista = sector_mod.vista_ejecutiva(s_)
                dataset.append((original, nombre, sec))
                auditoria.append([
                    original, fila['limpio'], nombre, sec, seccion, division, vista,
                    score, confianza.banda(score), tipo, '', '',
                    fila['traza'],
                ])
                bandas[confianza.banda(score)] += 1
                scores.append(score)
                continue

            # ---- empleadores ------------------------------------------------
            cid = asignacion[fila['clave']]
            c = clusters[cid]
            ext = externos.get(cid)

            nombre = c['nombre_canonico']
            seccion, division = c['seccion_ciiu'], c['division_ciiu']
            sec_etiqueta = c['sector_propuesto']
            origen_nombre = c['origen_nombre']
            origen_sector = c['origen_sector']

            # La fase 7 solo se aplica donde el motor determinístico no llegó.
            if ext and origen_sector == 'sin_evidencia' and ext['seccion_ciiu']:
                seccion, division = ext['seccion_ciiu'], ext['division_ciiu']
                sec_etiqueta = sector_mod.etiqueta(seccion, division)
                origen_sector = 'llm_%s' % ext['confianza_llm']
                if ext['nombre_canonico']:
                    nombre = ext['nombre_canonico']
                    origen_nombre = 'llm_%s' % ext['confianza_llm']

            tokens = fila['nucleo'].split()
            peso = 5
            if origen_sector == 'token':
                regla = reglas.REGLAS_CIIU.get(
                    next((t for t in tokens if t in reglas.REGLAS_CIIU), ''))
                peso = regla[3] if regla else 5

            score, factores = confianza.calcular(
                origen_nombre, origen_sector,
                truncado=fila['truncado'] == '1',
                n_claves=int(c['n_claves']),
                tokens_nucleo=tokens,
                peso_token=peso,
                sufijo_numerico=bool(fila['sufijo_numerico']),
                clave_generica=all(df.get(t, 0) >= corte for t in tokens) if tokens else False,
            )

            # Llegar aquí significa que el empleador SÍ quedó identificado y con
            # nombre canónico; lo que falta es la actividad. Etiquetarlo
            # 'Falta informacion' sería doblemente falso: hay información, y las
            # validaciones no están agotadas — falta la fase 7. Ver D8.
            if not seccion:
                sec_etiqueta = reglas.SECTOR_PENDIENTE

            dataset.append((original, nombre, sec_etiqueta))
            auditoria.append([
                original, fila['limpio'], nombre, sec_etiqueta, seccion, division,
                sector_mod.vista_ejecutiva(seccion) if seccion else 'Sin clasificar',
                score, confianza.banda(score), tipo, origen_nombre, origen_sector,
                '%s | %s | %s' % (fila['traza'], c['motivo_sector'], '; '.join(factores)),
            ])
            bandas[confianza.banda(score)] += 1
            scores.append(score)

            if cid not in maestro:
                maestro[cid] = [cid, nombre, seccion, division, sec_etiqueta,
                                sector_mod.vista_ejecutiva(seccion) if seccion else 'Sin clasificar',
                                c['n_claves'], c['n_registros'], score,
                                confianza.banda(score), origen_nombre, origen_sector]

    with comun.Fase('escribir entregables'):
        comun.escribir_csv(
            os.path.join(comun.DIR_SALIDAS, 'dataset_resultado.csv'),
            ['nombre_original', 'nombre_propuesto', 'sector_propuesto'],
            dataset,
        )
        comun.escribir_csv(
            os.path.join(comun.DIR_SALIDAS, 'tabla_auditoria.csv.gz'),
            ['nombre_original', 'nombre_limpio', 'nombre_propuesto', 'sector_propuesto',
             'seccion_ciiu', 'division_ciiu', 'vista_ejecutiva', 'confianza',
             'banda_confianza', 'tipo_registro', 'origen_nombre', 'origen_sector',
             'traza'],
            auditoria,
        )
        comun.escribir_csv(
            os.path.join(comun.DIR_SALIDAS, 'maestro_corporativo.csv'),
            ['id_empleador', 'nombre_canonico', 'seccion_ciiu', 'division_ciiu',
             'sector', 'vista_ejecutiva', 'variantes', 'registros', 'confianza',
             'banda_confianza', 'origen_nombre', 'origen_sector'],
            sorted(maestro.values(), key=lambda m: -int(m[7])),
        )

    with comun.Fase('escribir dataset en Excel'):
        import openpyxl
        wb = openpyxl.Workbook(write_only=True)
        ws = wb.create_sheet('resultado')
        ws.append(['nombre_original', 'nombre_propuesto', 'sector_propuesto'])
        for fila in dataset:
            ws.append(list(fila))
        wb.save(os.path.join(comun.DIR_SALIDAS, 'dataset_resultado.xlsx'))

    # ---- KPIs de calidad de datos ---------------------------------------
    n = len(dataset)
    tipos = collections.Counter(a[9] for a in auditoria)
    secciones = collections.Counter(a[4] for a in auditoria if a[4])
    ejecutivo = collections.Counter(a[6] for a in auditoria if a[4])
    identificados = sum(1 for a in auditoria if a[9] in TIPOS_EMPLEADOR)
    con_sector = sum(1 for a in auditoria if a[4])

    kpis = {
        'registros': n,
        'empleadores_identificados': identificados,
        'tasa_identificacion': round(100.0 * identificados / n, 2),
        'con_sector_ciiu': con_sector,
        'cobertura_sectorial': round(100.0 * con_sector / n, 2),
        'cobertura_sectorial_sobre_empleadores': round(100.0 * con_sector / identificados, 2),
        'empleadores_unicos': len(maestro),
        'tasa_consolidacion': round(100.0 * (1 - len(maestro) / max(1, identificados)), 2),
        'confianza_promedio': round(sum(scores) / len(scores), 1),
        'confianza_mediana': sorted(scores)[len(scores) // 2],
        'bandas': dict(bandas),
        'tipos_registro': dict(tipos),
        'secciones_ciiu': dict(secciones),
        'vista_ejecutiva': dict(ejecutivo),
        'fase7_aplicada': bool(externos),
    }
    comun.escribir_json(os.path.join(comun.DIR_SALIDAS, 'kpis_calidad.json'), kpis)

    total_ej = sum(ejecutivo.values())
    comun.escribir_csv(
        os.path.join(comun.DIR_SALIDAS, 'concentracion_sectorial.csv'),
        ['sector_ejecutivo', 'registros', 'porcentaje'],
        sorted(([k, v, round(100.0 * v / total_ej, 2)] for k, v in ejecutivo.items()),
               key=lambda r: -r[1]),
    )

    # ---- reporte ---------------------------------------------------------
    print('\n=== RESULTADO FINAL ===')
    print('Registros procesados         : %8d' % n)
    print('Empleadores identificados    : %8d  %5.2f%%' % (identificados, kpis['tasa_identificacion']))
    print('Empleadores únicos (maestro) : %8d  (consolidación %.1f%%)'
          % (len(maestro), kpis['tasa_consolidacion']))
    print('Con sector CIIU              : %8d  %5.2f%% del total | %5.2f%% de los empleadores'
          % (con_sector, kpis['cobertura_sectorial'], kpis['cobertura_sectorial_sobre_empleadores']))
    print('Confianza promedio           : %8.1f  (mediana %d)'
          % (kpis['confianza_promedio'], kpis['confianza_mediana']))

    print('\nBandas de confianza:')
    for k in ('automatico', 'muestreo', 'revision', 'verificacion_individual'):
        v = bandas.get(k, 0)
        print('  %-24s %8d  %5.1f%%' % (k, v, 100.0 * v / n))

    print('\nConcentración sectorial (vista ejecutiva):')
    for k, v in ejecutivo.most_common(12):
        print('  %-34s %8d  %5.1f%%' % (k, v, 100.0 * v / total_ej))

    print('\nEntregables en salidas/:')
    for f in sorted(os.listdir(comun.DIR_SALIDAS)):
        ruta = os.path.join(comun.DIR_SALIDAS, f)
        print('  %-32s %8.1f KB' % (f, os.path.getsize(ruta) / 1024))


if __name__ == '__main__':
    main()
