# -*- coding: utf-8 -*-
"""
Perfilamiento del dataset de empleadores (Fase 1 del pipeline).

Fuente de verdad: prueba_tecnica_ing_datos.xlsx, hoja Sheet1, columna 'nombre_original'.
Solo lee. No escribe ni modifica el archivo fuente.

Uso:
    python codigo/00_perfilamiento.py
"""
from __future__ import unicode_literals, print_function

import collections
import os
import random
import re

import openpyxl

RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'prueba_tecnica_ing_datos.xlsx')
SEMILLA = 7

# Prefijo de exportacion: todos los valores llegan con apostrofe inicial.
PREFIJO_EXPORT = "'"
# Sufijo numerico agregado para forzar unicidad en el archivo entregado.
RX_SUFIJO_UNICIDAD = re.compile(r'\s+\d+$')

# Taxonomia exploratoria. Son cotas inferiores por regex, no la clasificacion final.
PATRONES = [
    ('DIR_via',            r'\b(CALLE|AVE|AVENIDA|VIA|CARRETERA|AUTOPISTA|TRANSISTMICA|INTERAMERICANA)\b'),
    ('DIR_inmueble',       r'\b(EDIF|EDIFICIO|PH|APTO|LOCAL|PISO|CASA|TORRE|PLAZA|URB|URBANIZACION|BARRIADA|CORREGIMIENTO|FRENTE|DETRAS)\b'),
    ('SUFIJO_SOCIETARIO',  r'(\bS ?A|\bSAS|\bCORP|\bINC|\bLTD|\bLTDA|\bLLC|\bCIA|\bSRL)$'),
    ('INDEPENDIENTE',      r'INDEPENDIENTE|CUENTA PROPIA|AUTONOMO'),
    ('INACTIVO',           r'DESEMPLEAD|AMA DE CASA|JUBILAD|PENSIONAD|ESTUDIANTE|NO TRABAJA|SIN TRABAJO|RETIRAD'),
    ('NULO_EXPLICITO',     r'^(N ?/? ?A|NO APLICA|NINGUN[OA]?|SIN INFORMACION|S ?/? ?I|X{2,}|\.+|-+|0+|NO SABE|DESCONOCIDO|PENDIENTE|NULL|NONE|VACIO)$'),
    ('GOBIERNO',           r'\b(MINISTERIO|MINIST|ALCALDIA|MUNICIPIO|AUTORIDAD|CONTRALORIA|TRIBUNAL|ORGANO JUDICIAL|CAJA DE SEGURO|ASAMBLEA|PROCURADURIA|POLICIA|SENAFRONT|MEDUCA|MINSA|ACP)\b'),
    ('EDUCACION',          r'\b(ESCUELA|ESC|COLEGIO|UNIVERSIDAD|CENTRO EDUCATIVO|CEBG|IPT|INSTITUTO)\b'),
    ('SALUD',              r'\b(HOSPITAL|CLINICA|POLICLINICA|CENTRO DE SALUD|FARMACIA)\b'),
    ('OCUPACION',          r'^(ANALISTA|ASISTENTE|SECRETARI|VENDEDOR|CONDUCTOR|TAXISTA|ALBANIL|MECANIC|COCINER|GUARDIA|DOCENTE|PROFESOR|ENFERMER|OBRERO|EMPLEAD|OPERARIO|SUPERVISOR|GERENTE|CONTADOR|ABOGAD|MEDICO)'),
    ('UNA_PALABRA',        r'^\S+$'),
    ('CON_DIGITOS',        r'\d'),
]


def cargar():
    """Devuelve (crudos, base). base = sin apostrofe de exportacion ni espacios."""
    wb = openpyxl.load_workbook(RUTA, read_only=True, data_only=True)
    filas = wb['Sheet1'].iter_rows(values_only=True)
    encabezado = next(filas)
    assert encabezado[0] == 'nombre_original', encabezado

    crudos, nulos = [], 0
    for fila in filas:
        if fila[0] is None:
            nulos += 1
            continue
        crudos.append(fila[0])

    base = []
    for s in crudos:
        s = s.strip()
        if s.startswith(PREFIJO_EXPORT):
            s = s[1:]
        base.append(s.strip())
    return crudos, base, nulos


def main():
    crudos, base, nulos = cargar()
    n = len(base)
    pct = lambda k: '%d (%.2f%%)' % (k, 100.0 * k / n)

    print('=== VOLUMEN ===')
    print('Filas de datos      :', n + nulos)
    print('Nulos               :', nulos)
    print('No vacios           :', n)

    print('\n=== ARTEFACTOS DE EXPORTACION ===')
    print('Con apostrofe inicial:', pct(sum(1 for s in crudos if s.strip().startswith(PREFIJO_EXPORT))))

    print('\n=== UNICIDAD ===')
    print('Distintos exactos                 :', len(set(base)))
    sin_sufijo = [RX_SUFIJO_UNICIDAD.sub('', s) for s in base]
    conteo = collections.Counter(sin_sufijo)
    print('Con sufijo " <numero>"            :', pct(sum(1 for s in base if RX_SUFIJO_UNICIDAD.search(s))))
    print('Distintos al quitar sufijo        :', len(conteo))
    print('Grupos con mas de una ocurrencia  :', sum(1 for v in conteo.values() if v > 1))
    print('Top 15 bases repetidas:')
    for k, v in conteo.most_common(15):
        print('   %4d  %s' % (v, k))

    print('\n=== TRUNCAMIENTO DE ORIGEN ===')
    hist = collections.Counter(len(s) for s in base)
    print('Longitud  Frecuencia   (esperado: picos en 30 y corte en 40)')
    for L in range(26, 43):
        print('   %2d      %6d' % (L, hist.get(L, 0)))

    print('\n=== PERDIDA DE CARACTERES EN ORIGEN ===')
    caracteres = collections.Counter()
    for s in base:
        caracteres.update(s)
    no_alfanum = sorted(((k, v) for k, v in caracteres.items() if not k.isalnum() and k != ' '),
                        key=lambda x: -x[1])
    print('No alfanumericos    :', no_alfanum)
    print('Con tildes o enie   :', sum(1 for s in base if re.search('[ÁÉÍÓÚÑÜáéíóúñü]', s)))
    print('Con minusculas      :', sum(1 for s in base if s != s.upper()))
    print("Contienen 'PANAMEA' :", sum(1 for s in base if 'PANAMEA' in s))

    print('\n=== TAXONOMIA EXPLORATORIA (cotas inferiores) ===')
    for nombre, patron in PATRONES:
        rx = re.compile(patron)
        print('%-20s %s' % (nombre, pct(sum(1 for s in base if rx.search(s)))))
    print('%-20s %s' % ('LEN<=3', pct(sum(1 for s in base if len(s) <= 3))))

    print('\n=== MUESTRAS ===')
    random.seed(SEMILLA)
    for etiqueta, universo, k in [
        ('Aleatoria general', base, 30),
        ('Longitud == 30 (truncados)', [s for s in base if len(s) == 30], 15),
        ('Cortos (<=6)', [s for s in base if len(s) <= 6], 20),
    ]:
        print('\n-- %s --' % etiqueta)
        for s in random.sample(universo, min(k, len(universo))):
            print('   |%s|' % s)


if __name__ == '__main__':
    main()
