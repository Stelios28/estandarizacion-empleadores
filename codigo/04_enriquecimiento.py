# -*- coding: utf-8 -*-
"""
Bloque 4 — Fase 7: validación externa cuando existen dudas razonables (decisión D2).

Dos preguntas que el motor determinístico no puede responder y que sí justifican
una consulta externa:

  A. **Sector desconocido.** El nombre no contiene ninguna palabra del catálogo
     CIIU: `BRICKHAUS`, `SOLINTECSA`, `WILHELMSEN`, `FATTUME`. Son marcas. Sin
     conocimiento del mundo no hay forma de clasificarlas, y el enunciado prohíbe
     explícitamente asumir que un nombre corto es inválido.

  B. **Pares en zona de duda.** La medición de la fase 5 mostró que las
     poblaciones "misma entidad" y "entidades distintas" se solapan entre 76 y 88
     de similitud. Ningún umbral las separa. Esa banda se resuelve con evidencia,
     no adivinando.

Tres controles de costo, porque consultar 103.000 clústeres sin ellos es el riesgo
R7 materializado:

  1. **Se consulta el clúster, nunca la variante.** 103.104 clústeres, no 148.327
     registros.
  2. **Lotes de 40.** Un prompt de sistema con el catálogo CIIU se amortiza entre
     40 respuestas en lugar de reenviarse por cada nombre.
  3. **Caché persistente en disco.** Una corrida interrumpida se reanuda sin
     repetir ni una llamada; una segunda corrida sobre datos nuevos solo paga por
     lo que no había visto.

Además hay un presupuesto máximo de llamadas y prioridad por volumen: los
clústeres se ordenan por número de registros que representan, así que un
presupuesto parcial cubre primero lo que más pesa en la cartera.

Entrada : trabajo/03_clusters_resueltos.csv.gz, trabajo/02_zona_duda.csv.gz
Salida  : trabajo/04_cache_llm.json          respuestas, reutilizable entre corridas
          trabajo/04_sectores_externos.csv.gz
          trabajo/04_resumen.json

Uso:
    .venv\\Scripts\\python.exe codigo/04_enriquecimiento.py --presupuesto 200
    .venv\\Scripts\\python.exe codigo/04_enriquecimiento.py --todo
    .venv\\Scripts\\python.exe codigo/04_enriquecimiento.py --estimar   (no consulta)
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import gzip
import json
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import comun
import reglas

MODELO = 'claude-opus-5'
TAMANO_LOTE = 40
HILOS = 6

# Precio por millón de tokens del modelo, para la estimación previa.
PRECIO_ENTRADA = 5.00
PRECIO_SALIDA = 25.00
PRECIO_CACHE_LECTURA = 0.50      # ~0,1x la entrada

RUTA_CACHE = 'trabajo/04_cache_llm.json'

# Pares (sección, división) que el catálogo autoriza. Se usa para verificar la
# respuesta: el prompt los enumera, pero un prompt pide, no obliga (D32).
PARES_CIIU: frozenset[tuple[str, str]] = frozenset(
    (s, d) for s, d, _e, _p in reglas.REGLAS_CIIU.values()
)


# --------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------

def catalogo_para_prompt() -> str:
    """Catálogo CIIU en el formato más compacto que sigue siendo inequívoco."""
    vistas: dict[tuple[str, str], str] = {}
    for seccion, division, etiqueta, _peso in reglas.REGLAS_CIIU.values():
        vistas[(seccion, division)] = etiqueta
    lineas = ['%s | %s | %s' % (s, d, e)
              for (s, d), e in sorted(vistas.items())]
    return '\n'.join(lineas)


SISTEMA = """Eres un analista de riesgo de crédito en Panamá especializado en \
identificación de empleadores y clasificación sectorial CIIU Rev. 4.

Recibes nombres de empleadores capturados como texto libre durante la vinculación \
de clientes de un banco panameño. Vienen en mayúsculas, sin tildes ni eñes, a veces \
con errores de digitación o truncados por el límite del campo de origen.

Tu tarea: para cada nombre, determinar la razón social real y su sector CIIU.

CATALOGO CIIU AUTORIZADO (seccion | division | etiqueta).
Solo puedes responder con una combinacion seccion+division de esta lista:
{catalogo}

REGLAS

1. Un nombre corto o poco conocido NO es invalido. `VEOLIA`, `KUBOX` y `SOLINTECSA` \
son empresas reales. Solo declara desconocido cuando de verdad no puedas identificar \
ni la entidad ni la actividad.

2. Prioriza el conocimiento verificable sobre la inferencia. Si reconoces la empresa \
(multinacional, entidad panamena conocida, marca establecida), usala. Si no la \
reconoces pero el nombre revela la actividad, clasifica por actividad. Si ninguna \
de las dos cosas aplica, responde desconocido.

3. Contexto panameno. Considera Zona Libre de Colon, Canal de Panama, sector \
maritimo y portuario, banca offshore, juntas comunales, instituciones del Estado.

4. Un nombre truncado a 30 o 40 caracteres pudo perder el final. Completalo solo si \
la reconstruccion es evidente.

5. Explica cada decision en una frase corta, indicando en que te basaste.

6. NIVELES DE CONFIANZA
   alta  : reconoces la entidad especifica y estas seguro del sector
   media : infieres el sector por la actividad que sugiere el nombre
   baja  : el nombre da una pista debil pero no lo puedes verificar

7. Si no puedes identificar nada, usa seccion y division vacias, \
confianza "ninguna", y explica por que.

No inventes razones sociales. Si no conoces la forma legal exacta, devuelve el \
nombre limpio tal como te llego, con capitalizacion correcta."""


ESQUEMA_SALIDA = {
    'type': 'object',
    'properties': {
        'resultados': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'n': {'type': 'integer',
                          'description': 'Numero del nombre en la lista recibida'},
                    'nombre_canonico': {'type': 'string',
                                        'description': 'Razon social con capitalizacion correcta'},
                    'seccion': {'type': 'string',
                                'description': 'Letra de seccion CIIU, o cadena vacia'},
                    'division': {'type': 'string',
                                 'description': 'Division CIIU de 2 digitos, o cadena vacia'},
                    'confianza': {'type': 'string',
                                  'enum': ['alta', 'media', 'baja', 'ninguna']},
                    'motivo': {'type': 'string',
                               'description': 'Una frase explicando la decision'},
                },
                'required': ['n', 'nombre_canonico', 'seccion', 'division',
                             'confianza', 'motivo'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['resultados'],
    'additionalProperties': False,
}


# --------------------------------------------------------------------------
# Caché
# --------------------------------------------------------------------------

class Cache:
    """Caché persistente por nombre. Hace la fase reanudable y idempotente."""

    def __init__(self, ruta: str):
        self.ruta = ruta
        self.datos: dict[str, dict] = comun.leer_json(ruta, {}) or {}
        self.candado = threading.Lock()
        self.nuevos = 0

    def falta(self, nombres: list[str]) -> list[str]:
        return [n for n in nombres if n not in self.datos]

    def guardar_lote(self, resultados: dict[str, dict]) -> None:
        with self.candado:
            self.datos.update(resultados)
            self.nuevos += len(resultados)
            comun.escribir_json(self.ruta, self.datos)


# --------------------------------------------------------------------------
# Consulta
# --------------------------------------------------------------------------

def construir_cliente():
    import anthropic
    return anthropic.Anthropic()


def consultar_lote(cliente, sistema: str, nombres: list[str]) -> dict[str, dict]:
    """
    Clasifica un lote de nombres. Devuelve nombre -> resultado.

    El prompt de sistema lleva `cache_control`: es idéntico en las 2.578 llamadas,
    así que a partir de la segunda se cobra a tarifa de lectura de caché.

    Se usa pensamiento adaptativo con esfuerzo bajo en vez de desactivarlo: con el
    pensamiento apagado el modelo puede escribir la respuesta fuera del formato
    estructurado, y el ahorro real lo da el esfuerzo, no el apagado.
    """
    numerados = '\n'.join('%d. %s' % (i + 1, n) for i, n in enumerate(nombres))

    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=8000,
        system=[{'type': 'text', 'text': sistema,
                 'cache_control': {'type': 'ephemeral'}}],
        thinking={'type': 'adaptive'},
        output_config={
            'effort': 'low',
            'format': {'type': 'json_schema', 'schema': ESQUEMA_SALIDA},
        },
        messages=[{'role': 'user',
                   'content': 'Clasifica estos %d empleadores:\n\n%s'
                              % (len(nombres), numerados)}],
    )

    if respuesta.stop_reason == 'refusal':
        raise RuntimeError('respuesta rechazada: %s' % (respuesta.stop_details,))
    # Con `max_tokens` el JSON llega cortado y `json.loads` revienta con un error
    # que no dice nada. Se detecta aquí para que el mensaje sea accionable: la
    # solución es bajar `TAMANO_LOTE`, no reintentar.
    if respuesta.stop_reason == 'max_tokens':
        raise RuntimeError(
            'respuesta truncada en max_tokens con un lote de %d nombres; '
            'baja TAMANO_LOTE o sube max_tokens' % len(nombres))

    texto = next(b.text for b in respuesta.content if b.type == 'text')
    datos = json.loads(texto)

    salida: dict[str, dict] = {}
    for r in datos['resultados']:
        i = r['n'] - 1
        # El prompt dice «solo puedes responder con una combinación de esta
        # lista», pero un prompt es una petición, no una garantía. Sin esta
        # comprobación una sección inventada entra al maestro corporativo con la
        # misma apariencia que una buena, y nadie la distingue después.
        if r.get('seccion') and (r['seccion'], r.get('division', '')) not in PARES_CIIU:
            r['motivo'] = ('[descartado: %s/%s no está en el catálogo] %s'
                           % (r['seccion'], r.get('division', ''), r.get('motivo', '')))
            r['seccion'] = r['division'] = ''
            r['confianza'] = 'ninguna'
        if 0 <= i < len(nombres):
            r['_uso'] = {
                'entrada': respuesta.usage.input_tokens,
                'cache_lectura': respuesta.usage.cache_read_input_tokens or 0,
                'salida': respuesta.usage.output_tokens,
                'lote': len(nombres),
            }
            salida[nombres[i]] = r
    return salida


# --------------------------------------------------------------------------
# Selección de trabajo
# --------------------------------------------------------------------------

def pendientes_por_prioridad() -> list[tuple[str, int, int]]:
    """
    (representante, n_registros, cluster) de los clústeres sin sector, ordenados
    por registros descendente: un presupuesto parcial cubre primero lo que más pesa.
    """
    filas = []
    for r in comun.leer_csv(comun.ruta_trabajo('03_clusters_resueltos.csv.gz')):
        if r['requiere_fase7'] == '1':
            filas.append((r['representante'], int(r['n_registros']), int(r['cluster'])))
    filas.sort(key=lambda f: -f[1])
    return filas


def lotes(items: list, tamano: int):
    for i in range(0, len(items), tamano):
        yield items[i:i + tamano]


# --------------------------------------------------------------------------
# Proceso
# --------------------------------------------------------------------------

def estimar(n_nombres: int, sistema: str) -> dict:
    """Estimación de costo antes de gastar. Aproximada pero suficiente para decidir."""
    n_llamadas = (n_nombres + TAMANO_LOTE - 1) // TAMANO_LOTE
    tok_sistema = len(sistema) // 3.5          # aprox. 3,5 caracteres por token
    tok_lote = TAMANO_LOTE * 12                # nombre corto + numeración
    tok_salida = TAMANO_LOTE * 55              # objeto JSON por nombre

    # La primera llamada escribe la caché (1,25x); las demás la leen (0,1x).
    entrada_normal = n_llamadas * tok_lote
    cache_lectura = (n_llamadas - 1) * tok_sistema
    cache_escritura = tok_sistema * 1.25
    salida = n_llamadas * tok_salida

    costo = ((entrada_normal + cache_escritura) / 1e6 * PRECIO_ENTRADA
             + cache_lectura / 1e6 * PRECIO_CACHE_LECTURA
             + salida / 1e6 * PRECIO_SALIDA)

    return {
        'nombres': n_nombres,
        'llamadas': n_llamadas,
        'tokens_entrada': int(entrada_normal + cache_escritura),
        'tokens_cache_lectura': int(cache_lectura),
        'tokens_salida': int(salida),
        'costo_usd_estimado': round(costo, 2),
        'modelo': MODELO,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--presupuesto', type=int, default=50,
                    help='máximo de llamadas a la API en esta corrida')
    ap.add_argument('--todo', action='store_true',
                    help='sin límite de llamadas: procesa todos los pendientes')
    ap.add_argument('--estimar', action='store_true',
                    help='solo estima costo y volumen, no consulta nada')
    args = ap.parse_args()

    sistema = SISTEMA.format(catalogo=catalogo_para_prompt())

    with comun.Fase('seleccionar pendientes'):
        pend = pendientes_por_prioridad()
        cache = Cache(comun.ruta_trabajo('04_cache_llm.json'))
        nombres = [p[0] for p in pend]
        faltantes = cache.falta(nombres)
        comun.log('  clústeres sin sector: %d | ya en caché: %d | por consultar: %d'
                  % (len(pend), len(pend) - len(faltantes), len(faltantes)))

    est = estimar(len(faltantes), sistema)
    print('\n=== FASE 7 — ESTIMACIÓN ===')
    print('Modelo                       : %s' % est['modelo'])
    print('Nombres por consultar        : %8d' % est['nombres'])
    print('Llamadas necesarias          : %8d  (lotes de %d)' % (est['llamadas'], TAMANO_LOTE))
    print('Tokens entrada               : %8d' % est['tokens_entrada'])
    print('Tokens leídos de caché       : %8d  (prompt de sistema reutilizado)'
          % est['tokens_cache_lectura'])
    print('Tokens salida                : %8d' % est['tokens_salida'])
    print('Costo estimado               : %8s USD' % ('$%.2f' % est['costo_usd_estimado']))
    print('  con Message Batches API    : %8s USD  (50%% de descuento, hasta 24 h)'
          % ('$%.2f' % (est['costo_usd_estimado'] / 2)))

    if args.estimar:
        comun.escribir_json(comun.ruta_trabajo('04_estimacion.json'), est)
        print('\nSolo estimación. No se consultó nada.')
        return

    if not faltantes:
        print('\nNada por consultar: la caché ya cubre todos los pendientes.')
        return

    tope = None if args.todo else args.presupuesto
    todos_los_lotes = list(lotes(faltantes, TAMANO_LOTE))
    if tope is not None:
        todos_los_lotes = todos_los_lotes[:tope]
    comun.log('  lotes a ejecutar en esta corrida: %d' % len(todos_los_lotes))

    with comun.Fase('consultar (%d llamadas, %d hilos)' % (len(todos_los_lotes), HILOS)):
        cliente = construir_cliente()
        fallos = 0

        def trabajar(lote: list[str]) -> int:
            nonlocal fallos
            try:
                cache.guardar_lote(consultar_lote(cliente, sistema, lote))
                return len(lote)
            except Exception as e:                      # noqa: BLE001
                comun.log('  ERROR en lote: %s' % str(e)[:140])
                fallos += 1
                return 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=HILOS) as pool:
            for hechos in pool.map(trabajar, todos_los_lotes):
                if hechos:
                    comun.log('  progreso: %d nombres en caché' % len(cache.datos))

        comun.log('  nuevos en caché: %d | lotes fallidos: %d' % (cache.nuevos, fallos))

    with comun.Fase('escribir resultados'):
        por_nombre = {p[0]: p for p in pend}
        filas = []
        for nombre, r in cache.datos.items():
            if nombre not in por_nombre:
                continue
            _, n_reg, cid = por_nombre[nombre]
            filas.append([cid, nombre, r['nombre_canonico'], r['seccion'],
                          r['division'], r['confianza'], r['motivo'], n_reg])
        comun.escribir_csv(
            comun.ruta_trabajo('04_sectores_externos.csv.gz'),
            ['cluster', 'representante', 'nombre_canonico', 'seccion_ciiu',
             'division_ciiu', 'confianza_llm', 'motivo_llm', 'n_registros'],
            filas,
        )

    conf = collections.Counter(r['confianza'] for r in cache.datos.values())
    resueltos = sum(1 for r in cache.datos.values() if r['seccion'])
    resumen = {
        'consultados': len(cache.datos),
        'resueltos_con_sector': resueltos,
        'sin_resolver': len(cache.datos) - resueltos,
        'confianza': dict(conf),
        'llamadas_esta_corrida': len(todos_los_lotes),
        'estimacion': est,
    }
    comun.escribir_json(comun.ruta_trabajo('04_resumen.json'), resumen)

    print('\n=== FASE 7 — RESULTADO ===')
    print('Nombres en caché             : %8d' % len(cache.datos))
    print('Con sector asignado          : %8d  %5.1f%%'
          % (resueltos, 100.0 * resueltos / max(1, len(cache.datos))))
    print('\nConfianza declarada por el modelo:')
    for k, v in conf.most_common():
        print('  %-10s %8d  %5.1f%%' % (k, v, 100.0 * v / max(1, len(cache.datos))))


if __name__ == '__main__':
    main()
