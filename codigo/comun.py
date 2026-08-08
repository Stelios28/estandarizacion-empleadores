# -*- coding: utf-8 -*-
"""
Utilidades compartidas: rutas, entrada/salida y registro de ejecución.

No contiene lógica de negocio. Toda regla vive en `reglas.py`.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import sys
import time
from typing import Any, Iterable, Iterator

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FUENTE_XLSX = os.path.join(RAIZ, 'prueba_tecnica_ing_datos.xlsx')
HOJA_FUENTE = 'Sheet1'
COLUMNA_FUENTE = 'nombre_original'

DIR_DATOS = os.path.join(RAIZ, 'datos')          # catálogos versionados a mano
DIR_TRABAJO = os.path.join(RAIZ, 'trabajo')      # intermedios reanudables
DIR_SALIDAS = os.path.join(RAIZ, 'salidas')      # entregables

for _d in (DIR_DATOS, DIR_TRABAJO, DIR_SALIDAS):
    os.makedirs(_d, exist_ok=True)


# --------------------------------------------------------------------------
# Registro de ejecución
# --------------------------------------------------------------------------

_t0 = time.time()


def log(mensaje: str) -> None:
    """Traza a stderr con marca de tiempo relativa, para no ensuciar stdout."""
    transcurrido = time.time() - _t0
    sys.stderr.write('[%7.1fs] %s\n' % (transcurrido, mensaje))
    sys.stderr.flush()


class Fase:
    """Contexto que cronometra una fase y reporta su volumen de salida."""

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.inicio = 0.0

    def __enter__(self) -> 'Fase':
        self.inicio = time.time()
        log('INICIO  %s' % self.nombre)
        return self

    def __exit__(self, *exc: Any) -> None:
        if exc[0] is None:
            log('FIN     %s  (%.1fs)' % (self.nombre, time.time() - self.inicio))


# --------------------------------------------------------------------------
# Lectura de la fuente
# --------------------------------------------------------------------------

def leer_fuente() -> list[str]:
    """
    Devuelve los valores crudos de `nombre_original`, tal cual están en el Excel,
    incluido el apóstrofe de exportación. La limpieza es responsabilidad de la fase 2.

    El archivo fuente es de solo lectura y nunca se modifica.
    """
    import openpyxl

    wb = openpyxl.load_workbook(FUENTE_XLSX, read_only=True, data_only=True)
    filas = wb[HOJA_FUENTE].iter_rows(values_only=True)
    encabezado = next(filas)
    if encabezado[0] != COLUMNA_FUENTE:
        raise ValueError('Encabezado inesperado: %r' % (encabezado,))

    valores: list[str] = []
    for fila in filas:
        if fila[0] is None:
            valores.append('')
        else:
            valores.append(str(fila[0]))
    wb.close()
    return valores


# --------------------------------------------------------------------------
# Intermedios: CSV comprimido (pyarrow no tiene wheel para Windows ARM64)
# --------------------------------------------------------------------------

def ruta_trabajo(nombre: str) -> str:
    return os.path.join(DIR_TRABAJO, nombre)


def escribir_csv(ruta: str, columnas: list[str], filas: Iterable[Iterable[Any]]) -> int:
    """Escribe CSV UTF-8 (gzip si la ruta termina en .gz). Devuelve filas escritas.

    Los CSV sin comprimir son entregables que se abren en Excel, y Excel en Windows
    interpreta .csv con la página de códigos ANSI salvo que el archivo empiece con
    BOM: sin él, 'Construcción' se ve 'ConstrucciÃ³n'. Se escriben con utf-8-sig.
    Los intermedios .gz no los abre nadie a mano y se dejan en utf-8 puro.
    """
    abrir = gzip.open if ruta.endswith('.gz') else open
    codificacion = 'utf-8' if ruta.endswith('.gz') else 'utf-8-sig'
    n = 0
    with abrir(ruta, 'wt', encoding=codificacion, newline='') as fh:
        w = csv.writer(fh)
        w.writerow(columnas)
        for fila in filas:
            w.writerow(fila)
            n += 1
    return n


def leer_csv(ruta: str) -> Iterator[dict[str, str]]:
    # utf-8-sig consume el BOM si está y no molesta si no está: sirve para ambos.
    abrir = gzip.open if ruta.endswith('.gz') else open
    with abrir(ruta, 'rt', encoding='utf-8-sig', newline='') as fh:
        for registro in csv.DictReader(fh):
            yield registro


def escribir_json(ruta: str, obj: Any) -> None:
    with open(ruta, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=True)


def leer_json(ruta: str, por_defecto: Any = None) -> Any:
    if not os.path.exists(ruta):
        return por_defecto
    with open(ruta, 'r', encoding='utf-8') as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Union-Find: clustering de variantes sin dependencias externas
# --------------------------------------------------------------------------

class UnionFind:
    """Conjuntos disjuntos con compresión de caminos y unión por rango."""

    def __init__(self, n: int):
        self.padre = list(range(n))
        self.rango = [0] * n

    def buscar(self, x: int) -> int:
        raiz = x
        while self.padre[raiz] != raiz:
            raiz = self.padre[raiz]
        while self.padre[x] != raiz:          # compresión de caminos
            self.padre[x], x = raiz, self.padre[x]
        return raiz

    def unir(self, a: int, b: int) -> bool:
        ra, rb = self.buscar(a), self.buscar(b)
        if ra == rb:
            return False
        if self.rango[ra] < self.rango[rb]:
            ra, rb = rb, ra
        self.padre[rb] = ra
        if self.rango[ra] == self.rango[rb]:
            self.rango[ra] += 1
        return True

    def grupos(self) -> dict[int, list[int]]:
        salida: dict[int, list[int]] = {}
        for i in range(len(self.padre)):
            salida.setdefault(self.buscar(i), []).append(i)
        return salida
