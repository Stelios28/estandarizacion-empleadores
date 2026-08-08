# -*- coding: utf-8 -*-
"""
Fases 2 y 3: limpieza, normalización, tipificación del registro y generación de
claves de comparación.

Principio: el `nombre_original` es evidencia y nunca se altera. Todo lo que se
construye aquí son campos derivados, cada uno con su traza.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import reglas

# --------------------------------------------------------------------------
# Constantes de limpieza
# --------------------------------------------------------------------------

PREFIJO_EXPORT = "'"

_RX_ESPACIOS = re.compile(r'\s+')
_RX_NO_PERMITIDO = re.compile(r'[^A-Z0-9 ]')
# Número suelto al final: posible código de sucursal o artefacto de unicidad.
_RX_SUFIJO_NUM = re.compile(r'^(.*?)\s+(\d{1,4})$')

# Marcas cuyo número forma parte de la identidad. No se separa.
MARCAS_CON_NUMERO: set[str] = {
    'SUPER 99', 'CANAL 13', 'CANAL 4', 'RADIO 10', 'FARMACIA 24', 'MULTI 24',
    'PIO PIO 24', 'GRUPO 5', 'TIENDA 5', 'BINGO 90',
}


# --------------------------------------------------------------------------
# Resultado de la normalización
# --------------------------------------------------------------------------

@dataclass
class Registro:
    """Un registro del dataset con todos sus campos derivados y su traza."""

    idx: int
    original: str                      # tal cual viene del Excel, con apóstrofe
    limpio: str = ''                   # sin apóstrofe, sin ruido, espacios colapsados
    sufijo_numerico: str = ''          # número final separado, si lo hubo
    sufijo_societario: str = ''        # 'S A', 'INC', ... en forma normalizada
    nucleo: str = ''                   # nombre sin sufijo societario ni número
    clave: str = ''                    # clave de comparación exacta
    tokens: tuple[str, ...] = ()       # tokens del núcleo, expandidos y corregidos
    tipo: str = 'EMPRESA'              # EMPRESA | DIRECCION | INACTIVO | ...
    truncado: bool = False
    traza: list[str] = field(default_factory=list)

    def anotar(self, mensaje: str) -> None:
        self.traza.append(mensaje)


# --------------------------------------------------------------------------
# Fase 2 — limpieza
# --------------------------------------------------------------------------

def limpiar(crudo: str) -> tuple[str, list[str]]:
    """
    Quita el apóstrofe de exportación, normaliza a mayúsculas sin acentos, elimina
    caracteres no permitidos y colapsa espacios.

    Devuelve (texto_limpio, traza).
    """
    traza: list[str] = []
    texto = crudo.strip()

    if texto.startswith(PREFIJO_EXPORT):
        texto = texto[1:].strip()
        traza.append('apostrofe_exportacion_removido')

    # El dataset ya llegó sin acentos, pero se normaliza igual: la fuente puede
    # cambiar y una tilde no debe partir un clúster.
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper().replace('Ñ', 'N')

    sin_signos = _RX_NO_PERMITIDO.sub(' ', texto)
    if sin_signos != texto:
        traza.append('caracteres_no_alfanumericos_removidos')
    texto = sin_signos

    colapsado = _RX_ESPACIOS.sub(' ', texto).strip()
    if colapsado != texto.strip():
        traza.append('espacios_colapsados')

    # Siglas que el origen escribió con las letras sueltas. Se unen antes de
    # tokenizar o quedan como dos tokens de una letra y la sigla se pierde:
    # 196 registros escriben `P H MULTIPLAZA` y 957 escriben `PH MULTIPLAZA`.
    for rx, reemplazo, marca in reglas.SIGLAS_SEPARADAS:
        nuevo = rx.sub(reemplazo, colapsado)
        if nuevo != colapsado:
            colapsado = nuevo
            traza.append(marca)

    # El origen trunca a 30 caracteres: `INDEPENDIENT`, `JUBILADS`. Se completan
    # aquí, antes de tokenizar, para que las tres capas de abajo —tipificación,
    # situación laboral y sector— lo vean ya resuelto. Una sola corrección que
    # sirve a las tres, en lugar de una lista de erratas por capa (D22).
    completos, hubo = reglas.completar_truncadas(colapsado.split())
    if hubo:
        colapsado = ' '.join(completos)
        traza.append('raiz_truncada_completada')

    # Erratas de las palabras institucionales largas: `CONTRUCTORA`, `MINSTERIO`,
    # `TRASPORTE`. Mismo criterio que arriba —se corrige una vez, arriba de todo—
    # y por eso también sirve al agrupamiento: las 47 formas de `CONSTRUCTORA`
    # dejan de ser 47 claves distintas.
    corregidos, hubo = reglas.corregir_erratas(colapsado.split())
    if hubo:
        colapsado = ' '.join(corregidos)
        traza.append('errata_corregida')

    return colapsado, traza


def separar_sufijo_numerico(texto: str) -> tuple[str, str]:
    """
    Separa un número final suelto del resto del nombre.

    Evidencia (NOTAS_PERFILAMIENTO.MD §3): estos números no son un contador
    sintético. `EMPRESAS MELO SA` aparece con 019, 020, 025, 026, 027, 029, 034,
    051, 053, 094 y 510 — son códigos de sucursal. `MINI SUPER` con 07, 11, 18, 21.

    Por eso el número **no se borra**: se separa y se conserva como atributo. Para
    riesgo de crédito, todas las sucursales de Empresas Melo son el mismo empleador,
    así que el número tampoco debe impedir la agrupación.

    Devuelve (base, sufijo_numerico). Si no procede separar, (texto, '').
    """
    if texto in MARCAS_CON_NUMERO:
        return texto, ''

    m = _RX_SUFIJO_NUM.match(texto)
    if not m:
        return texto, ''

    base, numero = m.group(1).strip(), m.group(2)

    # No dejar un núcleo inutilizable ni convertir un número en nombre.
    if len(base) < 4 or not any(c.isalpha() for c in base):
        return texto, ''
    # Si la base es un solo token muy corto, el número probablemente identifica.
    if len(base.split()) == 1 and len(base) <= 4:
        return texto, ''

    return base, numero


# --------------------------------------------------------------------------
# Fase 3 — tipificación del registro
# --------------------------------------------------------------------------

def _frase_en(texto: str, frases: set[str]) -> str | None:
    for f in frases:
        if f == texto or (' ' in f and f in texto):
            return f
    return None


_ARTICULOS_TRAS_CASA = {'DE', 'DEL', 'EL', 'LA', 'LOS', 'LAS'}

# Giros que se escriben pegados a `CASA`, sin artículo en medio. `CASA CURAL` es la
# casa del párroco —un empleador con sacristán y secretaria— y quedaba como
# dirección porque `CASA` sola cuenta como indicio de inmueble (D23).
_GIROS_TRAS_CASA = {'CURAL', 'MATRIZ', 'CENTRAL', 'FUNERARIA', 'COMERCIAL'}


def _casa_de_giro(tokens: list[str]) -> set[str]:
    """
    Devuelve `{'CASA'}` si el nombre usa el giro comercial «Casa de/del X».

    `CASA DE EMPENO`, `CASA DE FUNERALES`, `LA CASA DEL CHAPISTERO` son nombres de
    negocio. Una casa como dirección se escribe con número (`CASA 25`), no con
    artículo. Neutraliza el token para que no cuente como indicio de inmueble.
    """
    for i, t in enumerate(tokens):
        if t == 'CASA' and i + 1 < len(tokens) and (
                tokens[i + 1] in _ARTICULOS_TRAS_CASA
                or tokens[i + 1] in _GIROS_TRAS_CASA):
            return {'CASA'}
    return set()


def clasificar_tipo(texto: str, tokens: list[str],
                    sufijo_societario: str = '') -> tuple[str, str]:
    """
    Determina qué es el registro antes de intentar resolverlo como empresa.

    Orden deliberado: lo que es barato y seguro de descartar va primero, para no
    gastar fuzzy ni llamadas externas en registros que nunca serán un empleador.

    Devuelve (tipo, evidencia).
    """
    conjunto = set(tokens)
    # `tokens` llega con el sufijo societario ya separado por `normalizar()`, así que
    # aquí no se puede volver a deducir: el llamante lo pasa.
    if not sufijo_societario:
        _, sufijo_societario = reglas.separar_sufijo_societario(tokens)

    # 1. Ruido puro y nulos explícitos
    if not texto or len(texto) <= 1:
        return 'VACIO', 'cadena vacía o de un carácter'
    if reglas._RX_SOLO_RUIDO.match(texto.replace(' ', '')):
        return 'VACIO', 'solo caracteres de relleno'
    if texto in reglas.MARCADORES_NULO:
        return 'VACIO', 'marcador de nulo explícito: %s' % texto
    motivo = reglas.es_inclasificable(texto)
    if motivo:
        return 'VACIO', motivo

    # 2. Anotación operativa del sistema, no un empleador
    marca = _frase_en(texto, reglas.MARCADORES_ANOTACION)
    if marca:
        return 'ANOTACION', 'anotación del sistema de originación: %s' % marca
    prefijo, _ = reglas.prefijo_anotacion(texto)
    if prefijo:
        return 'ANOTACION', 'anotación del sistema, por prefijo: %s' % prefijo.strip()

    # 2b. A la espera de vínculo laboral: hay un empleador nombrado, pero todavía
    #     no emplea a esta persona. `ESPERANDO NOMBRAMIENTO EN EL MIN DE EDUCACION`
    #     se clasificaba como el ministerio. Ver D14.
    marca = _frase_en(texto, reglas.MARCADORES_ESPERA)
    if marca:
        return 'INACTIVO', 'a la espera de vínculo laboral: %s' % marca

    # 3. Situación laboral, no empleador
    marca = _frase_en(texto, reglas.MARCADORES_INACTIVO)
    suelto = conjunto & reglas.MARCADORES_INACTIVO
    # `ESTUDIANTE` es el único marcador suelto que aparece como nombre de negocio
    # (`ALMACEN EL ESTUDIANTE`, `LIBRERIA EL ESTUDIANTE`). Si un término de actividad
    # lo precede, manda el negocio — la misma regla de orden de D10.
    if suelto == {'ESTUDIANTE'} and not marca:
        pos_est = tokens.index('ESTUDIANTE')
        if any(reglas.REGLAS_CIIU.get(t, ('', '', '', 0))[3] >= 7
               for t in tokens[:pos_est]):
            suelto = set()
    if marca or suelto:
        return 'INACTIVO', 'situación laboral declarada: %s' % (marca or 'token')

    # 4. Trabajador por cuenta propia
    # El marcador puede venir acompañado (`INDEPENDIENTE AGRIMENSURA`), así que no
    # basta la coincidencia de frase: también se busca como token suelto.
    marca = (_frase_en(texto, reglas.MARCADORES_INDEPENDIENTE)
             or next((m for m in sorted(reglas.MARCADORES_INDEPENDIENTE)
                      if ' ' not in m and m in conjunto), None))
    if marca:
        # Todo lo que se declara independiente se agrupa como independiente: no es
        # un empleador corporativo y no entra al maestro ni a la validación externa
        # (D13). La actividad, cuando el texto la trae —`INDEPENDIENTE
        # AGRIMENSURA`—, no se pierde: la fase 12 la usa para asignar sector.
        resto = [t for t in tokens if t not in marca.split()]
        if not resto:
            return 'INDEPENDIENTE', 'declarado independiente sin actividad'
        return 'INDEPENDIENTE', 'independiente con actividad declarada: %s' % ' '.join(resto)

    # 5. Dirección. Un token fuerte basta; los débiles necesitan respaldo.
    #
    # Tres guardas, cada una nacida de un falso positivo real (ver D10):
    #
    #  a) Sufijo societario: `HOTEL PLAZA HERRERA S A` es una sociedad inscrita.
    #     Nadie le pone "S.A." a una calle. El sufijo vence a cualquier indicio.
    #  b) Quien aparece primero, manda: `MINISUPER PARQUE EL EMPALME` es un
    #     minisúper que está en un parque; `AVENIDA PRINCIPAL LA HACIENDA
    #     CARICUAO` es una avenida que pasa por una hacienda. Las dos traen
    #     token de negocio y token de dirección — lo que las separa es el orden,
    #     porque en español el nombre se encabeza con lo que la cosa *es*.
    #  c) `CASA DE|DEL|EL|LA X` es giro de nombre comercial (`CASA DE EMPENO`,
    #     `LA CASA DEL CHAPISTERO`). Una casa como dirección lleva número.
    #  d) Una propiedad horizontal encabezada por `PH` es una persona jurídica
    #     con planilla propia (Ley 31 de 2010), no un inmueble. Ver D12.
    if not sufijo_societario and not reglas.es_propiedad_horizontal(tokens):
        fuertes = conjunto & reglas.TOKENS_DIRECCION_FUERTES
        debiles = (conjunto & reglas.TOKENS_DIRECCION_DEBILES) - _casa_de_giro(tokens)

        pos_dir = min((i for i, t in enumerate(tokens) if t in fuertes | debiles),
                      default=None)
        pos_neg = min((i for i, t in enumerate(tokens)
                       if reglas.REGLAS_CIIU.get(t, ('', '', '', 0))[3] >= 7),
                      default=None)
        manda_negocio = pos_neg is not None and (pos_dir is None or pos_neg < pos_dir)

        if not manda_negocio:
            if fuertes:
                return 'DIRECCION', 'token de vía: %s' % ', '.join(sorted(fuertes))
            if debiles and (len(debiles) >= 2
                            or reglas._RX_NUMERO_DIRECCION.search(texto)
                            or conjunto & {p.split()[0] for p in reglas.LUGARES_PANAMA}):
                return 'DIRECCION', 'indicadores de inmueble: %s' % ', '.join(sorted(debiles))

    # 6. Cargo en lugar de empleador. Solo si el registro es *únicamente* el cargo.
    if conjunto and conjunto <= (reglas.MARCADORES_OCUPACION | reglas.STOPWORDS):
        return 'OCUPACION', 'el registro es un cargo, no un empleador'

    # 7. Persona natural. Empleador válido en Panamá, pero no va al maestro
    #    corporativo como sociedad.
    if 2 <= len(tokens) <= 4 and not (conjunto & set(reglas.SUFIJOS_SOCIETARIOS)):
        pila = conjunto & reglas.NOMBRES_PILA
        apellidos = conjunto & reglas.APELLIDOS
        if (pila and apellidos) or len(apellidos) >= 2:
            return 'PERSONA_NATURAL', 'antropónimo: %s' % ' '.join(sorted(pila | apellidos))

    return 'EMPRESA', ''


# --------------------------------------------------------------------------
# Fase 3 — claves de comparación
# --------------------------------------------------------------------------

def expandir_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Aplica correcciones ortográficas y expande abreviaturas. Devuelve (tokens, traza)."""
    traza: list[str] = []
    salida: list[str] = []
    for t in tokens:
        corregido = reglas.CORRECCIONES.get(t, t)
        if corregido != t:
            traza.append('correccion:%s->%s' % (t, corregido))
        expandido = reglas.ABREVIATURAS.get(corregido, corregido)
        if expandido != corregido:
            traza.append('abreviatura:%s->%s' % (corregido, expandido))
        salida.extend(expandido.split())
    return salida, traza


def construir_clave(tokens: list[str], sufijo_numerico: str = '',
                    genericos: frozenset[str] = frozenset()) -> str:
    """
    Clave de comparación exacta: tokens significativos ordenados alfabéticamente.

    El orden alfabético hace que `PANAMA SERVICIOS` y `SERVICIOS PANAMA` colapsen.

    Tres decisiones que costaron una iteración y que sostienen la precisión:

    1. **Las iniciales se conservan.** Filtrar tokens de una letra colapsaba
       `INVERSIONES M C`, `INVERSIONES H W C` e `INVERSIONES M M` en la clave
       `INVERSIONES`: 111 empresas distintas en un solo grupo. En Panamá las
       iniciales suelen ser toda la identidad del nombre.

    2. **No se deduplican los tokens.** `M M` y `M` son nombres distintos.

    3. **Si todos los tokens del núcleo son genéricos** (`MINI SUPER`,
       `INVERSIONES`, `GRUPO`), el nombre no identifica a nadie por sí solo y el
       número final pasa a ser el discriminante: `MINI SUPER 66` y
       `MINI SUPER 889` no son la misma tienda.

    `genericos` se calcula sobre el propio corpus por frecuencia documental; no es
    una lista escrita a mano.
    """
    significativos = [t for t in tokens if t not in reglas.STOPWORDS]
    if not significativos:
        significativos = [t for t in tokens if t]

    clave = ' '.join(sorted(significativos))

    if sufijo_numerico and significativos and all(t in genericos for t in significativos):
        clave = '%s #%s' % (clave, sufijo_numerico)

    return clave


# --------------------------------------------------------------------------
# Orquestación por registro
# --------------------------------------------------------------------------

def normalizar(idx: int, crudo: str,
               genericos: frozenset[str] = frozenset()) -> Registro:
    """
    Aplica el pipeline de limpieza y tipificación a un único registro.

    `genericos` solo afecta la construcción de la clave. Se pasa vacío en la
    primera pasada (cuando aún se está midiendo la frecuencia documental) y con
    contenido en la segunda.
    """
    reg = Registro(idx=idx, original=crudo)

    reg.limpio, traza = limpiar(crudo)
    for t in traza:
        reg.anotar(t)

    # Truncamiento de origen: dos topes de campo detectados (30 y 40 caracteres).
    if len(reg.limpio) in (30, 40):
        reg.truncado = True
        reg.anotar('posible_truncado_en_%d_caracteres' % len(reg.limpio))

    base, numero = separar_sufijo_numerico(reg.limpio)
    if numero:
        reg.sufijo_numerico = numero
        reg.anotar('sufijo_numerico_separado:%s' % numero)

    tokens_base = base.split()
    nucleo_tokens, sufijo = reglas.separar_sufijo_societario(tokens_base)
    if sufijo:
        reg.sufijo_societario = sufijo
        reg.anotar('sufijo_societario:%s' % sufijo)

    expandidos, traza_exp = expandir_tokens(nucleo_tokens)
    for t in traza_exp:
        reg.anotar(t)

    reg.tokens = tuple(expandidos)
    reg.nucleo = ' '.join(expandidos)
    reg.clave = construir_clave(expandidos, reg.sufijo_numerico, genericos)

    reg.tipo, evidencia = clasificar_tipo(base, list(expandidos), reg.sufijo_societario)
    if evidencia:
        reg.anotar('tipo=%s (%s)' % (reg.tipo, evidencia))

    return reg
