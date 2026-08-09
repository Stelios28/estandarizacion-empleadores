# -*- coding: utf-8 -*-
"""
Base de conocimiento del pipeline: sufijos societarios, abreviaturas, tokens de
dirección, marcadores de no-empresa y el mapa de palabras clave a CIIU Rev. 4.

Todo el vocabulario de este módulo se derivó del dataset real, no de suposiciones.
El inventario de tokens que lo sustenta está en
`Documentacion/Mantenimiento/NOTAS_PERFILAMIENTO.MD`.

Separado del código de proceso a propósito: es la pieza que un analista de negocio
debe poder revisar y ampliar sin tocar el motor.
"""
from __future__ import annotations

import functools
import re

from rapidfuzz import fuzz, process

# ==========================================================================
# 1. Sufijos societarios
# ==========================================================================
# El dataset perdió toda la puntuación, así que "S.A." aparece como "SA" o como
# "S A". Ambas formas deben reconocerse y separarse del núcleo del nombre.
# Frecuencias observadas: SA 43.494 · S 29.292 + A 28.753 · INC 6.480 ·
# CORP 4.659 · CA 4.466 · CIA 1.285 · SAS 956 · LTD 904 · RL 487.

SUFIJOS_SOCIETARIOS: set[str] = {
    'SA', 'S A', 'SAS', 'S A S', 'SRL', 'S R L', 'RL', 'R L',
    'S DE R L', 'SDERL', 'CA', 'C A', 'CIA', 'COMPANIA', 'COMPANY', 'CO',
    'CORP', 'CORPORATION', 'CORPORACION', 'INC', 'INCORPORATED',
    'LTD', 'LTDA', 'LIMITED', 'LLC', 'LP', 'LLP', 'PLC', 'GMBH', 'BV', 'NV',
    'AG', 'SPA', 'SL', 'S L', 'EIRL', 'AB',
}

# Ordenados de más largo a más corto: al recortar el sufijo hay que intentar
# primero "S DE R L" antes que "L", o se muerde el núcleo del nombre.
_SUFIJOS_ORDENADOS: list[list[str]] = sorted(
    (s.split() for s in SUFIJOS_SOCIETARIOS), key=len, reverse=True
)

# Forma canónica con la que se reescribe el sufijo en el nombre propuesto.
FORMA_CANONICA_SUFIJO: dict[str, str] = {
    'S A': 'S.A.', 'SA': 'S.A.',
    'S A S': 'S.A.S.', 'SAS': 'S.A.S.',
    'S R L': 'S. de R.L.', 'SRL': 'S. de R.L.',
    'R L': 'S. de R.L.', 'S DE R L': 'S. de R.L.', 'SDERL': 'S. de R.L.',
    'C A': 'C.A.', 'CA': 'C.A.',
    'CIA': 'Cía.', 'COMPANIA': 'Cía.',
    'CORP': 'Corp.', 'CORPORATION': 'Corporation', 'CORPORACION': 'Corporación',
    'INC': 'Inc.', 'INCORPORATED': 'Inc.',
    'LTD': 'Ltd.', 'LTDA': 'Ltda.', 'LIMITED': 'Limited', 'LLC': 'LLC',
    'LP': 'LP', 'LLP': 'LLP', 'PLC': 'PLC', 'GMBH': 'GmbH',
    'BV': 'B.V.', 'NV': 'N.V.', 'AG': 'AG', 'SPA': 'S.p.A.',
    'S L': 'S.L.', 'SL': 'S.L.', 'EIRL': 'E.I.R.L.', 'AB': 'AB',
    'CO': 'Co.', 'COMPANY': 'Company',
}


def separar_sufijo_societario(tokens: list[str]) -> tuple[list[str], str]:
    """
    Separa el sufijo societario del final del nombre.

    Devuelve (núcleo, sufijo_normalizado). El sufijo se devuelve con espacios
    (`'S A'`) para poder consultarlo en FORMA_CANONICA_SUFIJO.

    Nunca deja el núcleo vacío: `['SA']` devuelve `(['SA'], '')`, porque un nombre
    que es solo un sufijo no es un sufijo, es un nombre que no supimos interpretar.
    """
    for patron in _SUFIJOS_ORDENADOS:
        k = len(patron)
        if len(tokens) > k and tokens[-k:] == patron:
            return tokens[:-k], ' '.join(patron)
    return tokens, ''


# ==========================================================================
# 2. Abreviaturas y variantes ortográficas
# ==========================================================================
# Expandir antes de comparar hace que "ESC NUEVO ARRAIJAN" y
# "ESCUELA NUEVO ARRAIJAN" caigan en la misma clave sin pasar por fuzzy.

# Regla de admisión: una abreviatura de 2-3 letras solo entra si no puede aparecer
# como fragmento legítimo de otro nombre. Se excluyeron a propósito `COL`
# (Colón, Colombia, "Coca Col..."), `PAN` ("Pan American") y `RP`: expandirlas
# inventaba evidencia. `COL -> COLEGIO` clasificó a Coca-Cola FEMSA en Enseñanza
# porque 2 de sus 48 variantes venían escritas `COCA COL FEMSA`.
ABREVIATURAS: dict[str, str] = {
    # Educación
    'ESC': 'ESCUELA', 'ESCU': 'ESCUELA', 'COLEG': 'COLEGIO',
    'CEBG': 'CENTRO EDUCATIVO BASICO GENERAL', 'IPT': 'INSTITUTO PROFESIONAL Y TECNICO',
    'UNIV': 'UNIVERSIDAD', 'INST': 'INSTITUTO',
    # Gobierno
    'MIN': 'MINISTERIO', 'MINIST': 'MINISTERIO', 'MRIO': 'MINISTERIO',
    'MINISTERIO': 'MINISTERIO',
    'MEDUCA': 'MINISTERIO DE EDUCACION',
    'MINSA': 'MINISTERIO DE SALUD',
    'MOP': 'MINISTERIO DE OBRAS PUBLICAS',
    'MIDA': 'MINISTERIO DE DESARROLLO AGROPECUARIO',
    'MIDES': 'MINISTERIO DE DESARROLLO SOCIAL',
    'MICI': 'MINISTERIO DE COMERCIO E INDUSTRIAS',
    'MEF': 'MINISTERIO DE ECONOMIA Y FINANZAS',
    'MITRADEL': 'MINISTERIO DE TRABAJO Y DESARROLLO LABORAL',
    'CSS': 'CAJA DE SEGURO SOCIAL',
    'ACP': 'AUTORIDAD DEL CANAL DE PANAMA',
    'AMP': 'AUTORIDAD MARITIMA DE PANAMA',
    'ATP': 'AUTORIDAD DE TURISMO DE PANAMA',
    'IDAAN': 'INSTITUTO DE ACUEDUCTOS Y ALCANTARILLADOS NACIONALES',
    'SENAFRONT': 'SERVICIO NACIONAL DE FRONTERAS',
    'SENAN': 'SERVICIO NACIONAL AERONAVAL',
    'SENADIS': 'SECRETARIA NACIONAL DE DISCAPACIDAD',
    'IFARHU': 'INSTITUTO PARA LA FORMACION Y APROVECHAMIENTO DE RECURSOS HUMANOS',
    # Empresa
    'CONST': 'CONSTRUCTORA', 'CONSTR': 'CONSTRUCTORA',
    'DISTRIB': 'DISTRIBUIDORA', 'DIST': 'DISTRIBUIDORA',
    'IMP': 'IMPORTADORA', 'EXP': 'EXPORTADORA',
    'INV': 'INVERSIONES', 'INVERS': 'INVERSIONES',
    'SERV': 'SERVICIOS', 'SERVS': 'SERVICIOS',
    'INT': 'INTERNACIONAL', 'INTL': 'INTERNACIONAL', 'INTER': 'INTERNACIONAL',
    'TRANSP': 'TRANSPORTE', 'CORP': 'CORPORACION',
    'AGROP': 'AGROPECUARIA', 'INDUST': 'INDUSTRIAS', 'IND': 'INDUSTRIAS',
    'PROD': 'PRODUCTOS', 'COMERC': 'COMERCIAL',
    'TECNOL': 'TECNOLOGIA', 'ADMIN': 'ADMINISTRACION',
    'HOSP': 'HOSPITAL', 'CLIN': 'CLINICA', 'LAB': 'LABORATORIO',
    'RESTAUR': 'RESTAURANTE', 'REST': 'RESTAURANTE',
    'SUPERM': 'SUPERMERCADO', 'MINISUPER': 'MINI SUPER',
    'PMA': 'PANAMA', 'PTY': 'PANAMA',
    'ZL': 'ZONA LIBRE', 'ZLC': 'ZONA LIBRE DE COLON',
}

# Errores ortográficos recurrentes detectados en el dataset. Se corrigen solo en la
# clave de comparación, nunca en el `nombre_original`, que es evidencia.
CORRECCIONES: dict[str, str] = {
    'PANAMEA': 'PANAMENA',      # la eñe fue eliminada, no sustituida, en el origen
    'PANAMEAS': 'PANAMENAS',
    'PANAMEO': 'PANAMENO',
    'PANAMEOS': 'PANAMENOS',
    'INVERCIONES': 'INVERSIONES',
    'CONSTRUCION': 'CONSTRUCCION',
    'CONSTRUCCIONE': 'CONSTRUCCIONES',
    'SERVISIOS': 'SERVICIOS',
    'COMPAIA': 'COMPANIA',
    'ESPAA': 'ESPANA',
    'SEORA': 'SENORA',
    'NIOS': 'NINOS',
    'DISEO': 'DISENO',
    'DISEADORA': 'DISENADORA',
    'MAANA': 'MANANA',
    'ENSEANZA': 'ENSENANZA',
}

# Palabras vacías: aportan poco a la identidad y se retiran de la clave de núcleo.
# Se conservan en el nombre propuesto.
STOPWORDS: set[str] = {
    'DE', 'DEL', 'LA', 'LAS', 'EL', 'LOS', 'Y', 'E', 'EN', 'A', 'AL',
    'THE', 'OF', 'AND', 'FOR',
}


# --------------------------------------------------------------------------
# Propiedad horizontal (D12)
# --------------------------------------------------------------------------
# En Panamá una PH no es un edificio: es una **persona jurídica** inscrita bajo la
# Ley 31 de 2010, con junta directiva, RUC y planilla propia — administrador,
# seguridad, aseo, mantenimiento. Es un empleador de pleno derecho, y aparecer
# como tal en el campo de empleador es correcto, no un error de captura.
#
# `PH` encabezando el nombre es la forma en que se escribe en Panamá.

TOKEN_PROPIEDAD_HORIZONTAL = 'PH'

# Siglas escritas con las letras separadas en el origen. Se unen en la limpieza:
# si no, `P H MULTIPLAZA` produce dos tokens de una letra, no coincide con
# `PH MULTIPLAZA` y el nombre canónico sale como «P H Multiplaza».
SIGLAS_SEPARADAS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r'\bP\s+H\b'), 'PH', 'sigla_PH_unida'),
    # `C S S` = Caja de Seguro Social. 56 registros la escriben letra por letra
    # (`C S S LOS SANTOS`, `JUB C S S`, `COMPLEJO HOSPITALARIO C S S`) y ninguno
    # coincidía con `CSS`, que sí está en el gazetteer. Mismo defecto que `P H`,
    # encontrado tres decisiones después: el patrón se repite, no era un caso
    # aislado (D22).
    (re.compile(r'\bC\s+S\s+S\b'), 'CSS', 'sigla_CSS_unida'),
    # `IN DEPENDIENTE` es `INDEPENDIENTE` partido, no un dependiente económico.
    # Va antes que cualquier regla sobre `DEPENDIENTE` para no invertir el sentido.
    (re.compile(r'\bIN\s+DEPENDIENTE\b'), 'INDEPENDIENTE', 'IN_DEPENDIENTE_unido'),
    # `M S` encabezando el nombre es «Mini Super», la tienda de barrio panameña.
    # 463 registros y el patrón no deja duda al leerlos juntos: `M S CHEN LOU`,
    # `M S SAN SEBASTIAN`, `M S RIO RITA`, `M S EL CRISOL` — apellido chino o
    # nombre de santo, que es exactamente cómo se llaman los abarroteros del país.
    # Solo al inicio: en medio del nombre `M S` puede ser iniciales de persona.
    (re.compile(r'^M\s+S\b'), 'MINISUPER', 'sigla_MS_minisuper'),
]

# --- Truncación del origen -------------------------------------------------
# El campo viene cortado a 30 caracteres, así que las palabras largas llegan sin
# final: `INDEPENDIENT`, `INDEPENDIEN`, `JUBILADS`, `JUBILADACSS`. Enumerar cada
# variante no escala —son cientos y siempre aparece una nueva—; enumerar la
# **raíz** sí, porque la truncación corta siempre por el final.
#
# Cada raíz tiene 7 caracteres o más: con menos empieza a tocar palabras ajenas
# (`ESTUDIANT` capturaría `ESTUDIANTIL`, que es un adjetivo de negocio).
# Se probó relajar la guarda de prefijo del corrector de erratas para que cubriera
# estos casos de forma genérica y salió mal: reabría `CONSULTOR -> CONSULTORIO` y
# metía 1.200 plurales inútiles (`PROYECTO -> PROYECTOS`). La truncación por prefijo
# se ataca aquí, enumerada y acotada, no aflojando una guarda que sirve (D23).
RAICES_TRUNCADAS: list[tuple[str, str]] = [
    ('INDEPENDIEN', 'INDEPENDIENTE'),
    ('JUBILAD', 'JUBILADO'),
    ('PENSIONAD', 'PENSIONADO'),
    ('DESEMPLEAD', 'DESEMPLEADO'),
    ('UNIVERSIDA', 'UNIVERSIDAD'),
    ('MINISTERI', 'MINISTERIO'),
]


def completar_truncadas(tokens: list[str]) -> tuple[list[str], bool]:
    """Devuelve los tokens con las raíces truncadas completadas, y si hubo cambio."""
    salida, cambio = [], False
    for t in tokens:
        for raiz, completa in RAICES_TRUNCADAS:
            if t != completa and t.startswith(raiz):
                salida.append(completa)
                cambio = True
                break
        else:
            salida.append(t)
    return salida, cambio

# Lo que sí convierte una PH en domicilio particular: la unidad dentro del edificio.
# `PH VERTIKAL AP 26B` es la casa de alguien; `PH Vertikal` es la entidad.
# `CASA` NO entra: `PH Casa del Mar` y `PH Casa Blanca` son nombres de edificio.
UNIDADES_INMUEBLE: set[str] = {'APTO', 'APT', 'AP', 'APARTAMENTO', 'PISO', 'LOCAL'}


def es_propiedad_horizontal(tokens: list[str]) -> bool:
    """
    La PH como entidad empleadora, no como domicilio de alguien.

    `PH` va en las dos primeras posiciones: encabezando (`PH Multiplaza`) o
    precedido por una palabra que lo refuerza. Medido sobre el corpus, los 52 casos
    en que `PH` no encabeza vienen tras `EDIFICIO`, `ADMINISTRACION`, `CONJUNTO`,
    `CONDOMINIO` o `CONSORCIO` — todas confirman la entidad en lugar de negarla.
    """
    if TOKEN_PROPIEDAD_HORIZONTAL not in tokens[:2]:
        return False
    conjunto = set(tokens)
    # Unidad concreta -> es el domicilio de alguien, no la entidad.
    # Token fuerte de vía -> es una dirección que menciona un PH de referencia.
    return not (conjunto & UNIDADES_INMUEBLE
                or conjunto & TOKENS_DIRECCION_FUERTES)


# ==========================================================================
# 3. Detección de direcciones
# ==========================================================================
# El enunciado exige la categoría `No identificable - Direcciones`.
# Precisión sobre recall: un token fuerte basta; los débiles necesitan compañía.

TOKENS_DIRECCION_FUERTES: set[str] = {
    'CALLE', 'AVENIDA', 'AVE', 'AV', 'CARRETERA', 'AUTOPISTA', 'TRANSISTMICA',
    'CORREGIMIENTO', 'BARRIADA', 'URBANIZACION', 'URB',
    'BOULEVARD', 'BULEVAR', 'CALLEJON', 'SENDERO', 'DIAGONAL',
}

TOKENS_DIRECCION_DEBILES: set[str] = {
    'EDIFICIO', 'EDIF', 'APTO', 'APT', 'AP', 'APARTAMENTO', 'PISO', 'LOCAL', 'CASA',
    'TORRE', 'PLAZA', 'ENTRADA', 'FRENTE', 'DETRAS', 'CONTIGUO', 'ALTOS',
    'RESIDENCIAL', 'BARRIO', 'VIA', 'KM', 'KILOMETRO', 'NO', 'NRO', 'NUMERO',
    'SECTOR', 'MANZANA', 'LOTE', 'PARQUE',
    # `INTERAMERICANA` bajó de fuerte a débil. Como fuerte mandaba 58 registros a
    # «no identificable», y al leerlos casi ninguno es la carretera: es la
    # Universidad Interamericana (`UNV INTERAMERICANA`, `U INTERAMERICANA`), la
    # Comisión Interamericana del Atún, `T SHIRTS INTERAMERICANA`. La vía se
    # escribe `AV INTERAMERICANA`, y ahí el `AV` fuerte ya hace el trabajo (D24).
    'INTERAMERICANA',
    # `FINCA` estaba aquí y mandaba 212 registros a «no identificable - dirección».
    # Pero `FINCA LA CEIBA` y `FINCA LOS LIMONES` no son la dirección de nadie: son
    # el lugar de trabajo, y su actividad es la agricultura. En Panamá la finca es
    # una unidad productiva, no una referencia de ubicación. Sale de aquí y se queda
    # solo como token agrícola, donde ya estaba con peso 8 (D23).
}

# Provincias y distritos de Panamá. Solos no indican dirección — hay muchas empresas
# con el nombre del lugar — pero suman evidencia junto a un token débil.
LUGARES_PANAMA: set[str] = {
    'PANAMA', 'COLON', 'CHIRIQUI', 'VERAGUAS', 'HERRERA', 'COCLE', 'DARIEN',
    'BOCAS DEL TORO', 'LOS SANTOS', 'ARRAIJAN', 'LA CHORRERA', 'SAN MIGUELITO',
    'DAVID', 'SANTIAGO', 'CHITRE', 'PENONOME', 'AGUADULCE', 'LA CONCEPCION',
    'CHANGUINOLA', 'BUGABA', 'CAPIRA', 'CHEPO', 'TOCUMEN', 'JUAN DIAZ',
    'BETHANIA', 'CALIDONIA', 'ANCON', 'CHILIBRE', 'PACORA', 'ALBROOK',
    'COSTA DEL ESTE', 'PUNTA PACIFICA', 'EL DORADO', 'VIA ESPANA',
    'MARBELLA', 'OBARRIO', 'PAITILLA', 'CLAYTON', 'AMADOR',
}

_RX_NUMERO_DIRECCION = re.compile(r'\b(NO|NRO|N|#)\s*\d+\b|\bCALLE\s+\d+|\b\d+\s*[A-Z]?\s*$')

# Lugares en forma de token suelto, para reconocerlos al final de un nombre.
LUGARES_TOKEN: set[str] = set()
for _l in LUGARES_PANAMA:
    LUGARES_TOKEN.update(_l.split())
LUGARES_TOKEN -= {'DEL', 'DE', 'LA', 'EL', 'LOS', 'SAN', 'SANTA', 'VIA', 'COSTA',
                  'PUNTA', 'VERAGUAS'}


# Vocabulario del sistema de nómina, no del empleador. `PLANILLA MAERSK` y `MAERSK`
# son el mismo empleador visto desde dos capturas distintas.
PALABRAS_ADMINISTRATIVAS: set[str] = {
    'PLANILLA', 'PLANILLAS', 'NOMINA', 'ASALARIADO', 'ASALARIADA',
}


def quitar_calificadores(tokens: list[str]) -> tuple[list[str], list[str]]:
    """
    Separa del nombre los calificadores que identifican **sucursal o cargo**, no
    empleador.

    El campo mezcla tres cosas distintas: el empleador, dónde queda la sede y qué
    hace la persona. Para riesgo de crédito el empleador es el mismo:

        IDAAN ANALISTA DE RECARGO        e  IDAAN FONTANERO III
        OPERADORA PANAMAX S A BRISAS     y  OPERADORA PANAMAX SA ALBROOK
        HOSPITAL CECILIO CASTILLERO      y  HOSPITAL CECILIO CASTILLERO CHITRE
        UNIVERSIDAD TECNOLOGICA PANAMA   y  UNIVERSIDAD TECNOLOGICA PENONOME

    Los lugares solo se retiran del **final** del nombre. `PANAMA PORTS COMPANY`
    conserva su PANAMA inicial, que sí es parte de la razón social.

    Devuelve (núcleo_reducido, calificadores_retirados). Nunca vacía el núcleo.
    """
    calificadores: list[str] = []
    nucleo = list(tokens)

    # `PLANILLA` es cómo se paga, no para quién se trabaja. El empleador viene
    # detrás: `PLANILLA MAERSK`, `PLANILLA KRAFT`, `PLANILLA LOCKHEED MARTIN`.
    # Retirarla une esos 62 registros con los que nombran la empresa a secas (D23).
    resto = [t for t in nucleo if t not in PALABRAS_ADMINISTRATIVAS]
    if resto and len(resto) < len(nucleo):
        calificadores.extend(t for t in nucleo if t in PALABRAS_ADMINISTRATIVAS)
        nucleo = resto

    # Cargos: en cualquier posición, son atributo de la persona.
    resto = [t for t in nucleo if t not in MARCADORES_OCUPACION]
    if resto and len(resto) < len(nucleo):
        calificadores.extend(t for t in nucleo if t in MARCADORES_OCUPACION)
        nucleo = resto

    # Lugares: solo como sufijo, y sin dejar el núcleo sin contenido.
    while len(nucleo) > 1 and nucleo[-1] in LUGARES_TOKEN:
        calificadores.append(nucleo.pop())

    while nucleo and nucleo[-1] in STOPWORDS:
        nucleo.pop()

    return (nucleo or list(tokens)), calificadores


# ==========================================================================
# 4. Registros que no son un empleador identificable
# ==========================================================================
# El enunciado no crea categoría para ellos, pero mezclarlos con empresas contamina
# el maestro corporativo. Se marcan aparte y la decisión queda documentada en D5.

MARCADORES_INACTIVO: set[str] = {
    'JUBILADO', 'JUBILADA', 'PENSIONADO', 'PENSIONADA', 'RETIRADO', 'RETIRADA',
    'DESEMPLEADO', 'DESEMPLEADA', 'AMA DE CASA', 'AMO DE CASA', 'ESTUDIANTE',
    'NO TRABAJA', 'SIN TRABAJO', 'SIN EMPLEO', 'CESANTE',
    # `HOGAR` a secas estaba aquí y sacaba empresas del maestro: `ALMACEN PUNTO EL
    # HOGAR` y `FINANZAS Y CREDITOS DEL HOGAR` quedaban como situación laboral
    # inactiva. El marcador tiene que ser la frase, no la palabra (D18).
    'AMA DE CASA', 'AMO DE CASA', 'AMA DE LLAVES',
    'ADMINISTRADORA DEL HOGAR', 'ADMINISTRADOR DEL HOGAR',
    'ADMINISTRADORA DE SU HOGAR', 'ADMINISTRADORA EL HOGAR',
    'ADMON DEL HOGAR', 'ADMO DEL HOGAR', 'ADMINISTRADORA DOMESTICA',
    'LABORES DEL HOGAR', 'OFICIOS DEL HOGAR', 'TAREAS DEL HOGAR',
    # Formas de «no está trabajando» que el corpus escribe con adverbio delante.
    'NO LABORA', 'NO ESTA LABORANDO', 'NO ESTA TRABAJANDO',
    'QUEDO CESANTE', 'ACABA DE QUEDAR CESANTE', 'SIN EMPLEO ACTUAL',
}

# Anotaciones operativas del sistema de originación que quedaron en el campo de
# empleador. No describen una situación laboral: describen al cliente. Se detectaron
# al revisar los clústeres más grandes de la primera corrida de la fase 5
# ("CLIENTE FALLECIDA 18 09 2003", 379 variantes; "MENOR DEPENDIENTE", 251).
MARCADORES_ANOTACION: set[str] = {
    'CLIENTE FALLECIDO', 'CLIENTE FALLECIDA', 'FALLECIDO', 'FALLECIDA',
    'DEPENDIENTE ECONOMICO', 'DEPENDIENTE ECONOMICA', 'MENOR DEPENDIENTE',
    'MENOR DE EDAD', 'DEPENDIENTE DE TERCERO', 'DEPENDIENTE DE UN TERCERO',
    'DEPENDIENTE', 'MENOR', 'CLIENTE', 'CUENTA CANCELADA', 'CUENTA CERRADA',
    'NO VERIFICADO', 'POR VERIFICAR', 'ACTUALIZAR', 'REVISAR',
}

# El dependiente económico se escribe de 184 maneras distintas —`DEPENDIENTE DE SU
# ESPOSA`, `DEPENDIENTE ECONIMICO DE UN TE`, `DEPENDIENTE ECOMONICO`, `DEPENDIENTE
# TERCERA EDAD`— y ninguna coincidía con una frase completa, así que los 184
# entraron al maestro corporativo como si fueran empresas. Lo estable no es la
# frase entera: es cómo **empieza** el registro (D22).
#
# Falso positivo conocido y aceptado: `DEPENDIENTE DE CAMBIO` (1 registro) es un
# dependiente de casa de cambio. Uno contra 184.
PREFIJOS_ANOTACION: list[tuple[str, str]] = [
    ('DEPENDIENTE ', 'Dependiente económico'),
]


def prefijo_anotacion(texto: str) -> tuple[str, str]:
    """Devuelve (prefijo, etiqueta) si el registro arranca con una anotación."""
    for prefijo, etiqueta in PREFIJOS_ANOTACION:
        if texto.startswith(prefijo):
            return prefijo, etiqueta
    return '', ''

# `ESPERANDO NOMBRAMIENTO EN EL MIN DE EDUCACION` no es el ministerio: es una
# persona sin vínculo laboral todavía. Se clasificaba como administración pública.
MARCADORES_ESPERA: set[str] = {
    'ESPERANDO NOMBRAMIENTO', 'POR NOMBRAR', 'PENDIENTE DE NOMBRAMIENTO',
    'EN TRAMITE DE NOMBRAMIENTO', 'ESPERA DE NOMBRAMIENTO',
}

MARCADORES_INDEPENDIENTE: set[str] = {
    'INDEPENDIENTE', 'CUENTA PROPIA', 'POR SU CUENTA', 'AUTONOMO', 'AUTOEMPLEADO',
    'NEGOCIO PROPIO', 'FREELANCE', 'INFORMAL', 'BUHONERO',
}

# Cargos, no empleadores. Solo aplica si el registro es *únicamente* la ocupación.
MARCADORES_OCUPACION: set[str] = {
    'TRABAJADOR', 'TRABAJADORA', 'TRABAJADORES', 'ADMINISTRADOR',
    'ADMINISTRADORA', 'ADMINISTRADORES', 'COORDINADOR', 'COORDINADORA',
    'ENTRENADOR', 'EDUCADORA', 'INSTALADOR', 'PESCADOR', 'DISENADORA',
    'ANALISTA', 'ESPECIALISTA', 'ESTILISTA', 'TAXISTA', 'EBANISTA',
    'ANALISTA', 'ASISTENTE', 'SECRETARIA', 'SECRETARIO', 'VENDEDOR', 'VENDEDORA',
    'CONDUCTOR', 'TAXISTA', 'ALBANIL', 'MECANICO', 'COCINERO', 'COCINERA',
    'GUARDIA', 'DOCENTE', 'PROFESOR', 'PROFESORA', 'MAESTRA', 'MAESTRO',
    'ENFERMERO', 'ENFERMERA', 'OBRERO', 'OBRERA', 'EMPLEADO', 'EMPLEADA',
    'OPERARIO', 'SUPERVISOR', 'GERENTE', 'CONTADOR', 'CONTADORA', 'ABOGADO',
    'ABOGADA', 'MEDICO', 'ODONTOLOGO', 'INGENIERO', 'ARQUITECTO', 'CHOFER',
    'JARDINERO', 'PINTOR', 'SOLDADOR', 'ELECTRICISTA', 'PLOMERO', 'CAJERO',
    'CAJERA', 'MENSAJERO', 'RECEPCIONISTA', 'BARBERO', 'ESTILISTA', 'NINERA',
    'DOMESTICA', 'AGRICULTOR', 'GANADERO', 'PESCADOR', 'COMERCIANTE',
}

MARCADORES_NULO: set[str] = {
    'NA', 'N A', 'NO APLICA', 'NINGUNO', 'NINGUNA', 'SIN INFORMACION',
    'SI', 'S I', 'NO SABE', 'DESCONOCIDO', 'PENDIENTE', 'NULL', 'NONE',
    'VACIO', 'SIN DATO', 'SIN DATOS', 'NO DISPONIBLE', 'NO REFIERE', 'XX',
    'ZZ', 'PRUEBA', 'TEST', 'ASDF', 'QWERTY',
}

_RX_SOLO_RUIDO = re.compile(r'^[X\-\.\_\*0]{1,}$')


def es_inclasificable(texto: str) -> str:
    """
    Motivo por el que el registro no puede identificar a ningún empleador, o ''.

    Filtro deliberadamente **estrecho**: solo cadenas donde no hay nada que buscar,
    ni para una regla ni para una búsqueda web. Su valor no es el ahorro —son ~500
    clústeres— sino no pagar por preguntar «¿a qué se dedica 00582129864593?».

    NO se filtra por longitud. Se midió: cortar en 3 caracteres perdería `3M`, `EY`,
    `ACP`, `MSC`, `SAP`, `HP`, `IBM`, `DHL`, `UPS`, `KFC`, `PWC` y `TVN`; cortar en
    7 perdería además `NESTLE`, `HAWORTH` y `CENAMEP`. El largo mide la longitud
    del nombre, no si el nombre existe.
    """
    plano = texto.replace(' ', '')
    if not plano:
        return ''
    if plano.isdigit():
        return 'el registro es solo dígitos: no nombra a nadie'
    if len(plano) >= 2 and len(set(plano)) == 1:
        return 'un solo carácter repetido: relleno de captura'
    return ''

# Nombres propios frecuentes en Panamá. Se usan solo para señalar que un registro
# probablemente es una persona natural, nunca para descartarlo: en Panamá una
# persona natural sí puede ser el empleador.
NOMBRES_PILA = {
    'JOSE', 'MARIA', 'JUAN', 'CARLOS', 'LUIS', 'ANA', 'PEDRO', 'JORGE', 'MIGUEL',
    'RICARDO', 'ROBERTO', 'FRANCISCO', 'MANUEL', 'ANTONIO', 'RAFAEL', 'DANIEL',
    'EDUARDO', 'FERNANDO', 'ALBERTO', 'JAVIER', 'ROSA', 'CARMEN', 'ELENA',
    'PATRICIA', 'MARTA', 'LAURA', 'SANDRA', 'GLORIA', 'YOLANDA', 'MARIBEL',
    'OMAR', 'ABDIEL', 'YARIELA', 'ITZEL', 'ARIEL', 'EDWIN', 'ELIECER', 'AURELIO',
    'BENIGNO', 'DEMETRIO', 'EUCLIDES', 'ROGELIO', 'VIELKA', 'MARISOL', 'NITZIA',
}

APELLIDOS = {
    'GUARDIA',   # «de la Guardia»: apellido panameño frecuente, no un vigilante
    'GONZALEZ', 'RODRIGUEZ', 'GOMEZ', 'PEREZ', 'MARTINEZ', 'SANCHEZ', 'RAMIREZ',
    'TORRES', 'FLORES', 'RIVERA', 'GOMES', 'CASTILLO', 'JIMENEZ', 'MORENO',
    'HERRERA', 'MEDINA', 'VARGAS', 'CASTRO', 'ORTEGA', 'DELGADO', 'GUERRA',
    'SANTAMARIA', 'CEDENO', 'CEDENO', 'BATISTA', 'QUINTERO', 'AROSEMENA',
    'BARRIA', 'SAMANIEGO', 'ATENCIO', 'CABALLERO', 'MENDIETA', 'SANJUR',
    'AGUILAR', 'BERNAL', 'ESPINOSA', 'MURILLO', 'PINEDA', 'SOLIS', 'VEGA',
}


# ==========================================================================
# 5. Clasificación sectorial — CIIU Rev. 4
# ==========================================================================
# Decisión D3. Se entrega sección (letra) y división (2 dígitos).
# La vista ejecutiva de ~15 sectores se deriva agregando secciones, no se
# clasifica dos veces.

SECCIONES_CIIU: dict[str, str] = {
    'A': 'Agricultura, ganadería, silvicultura y pesca',
    'B': 'Explotación de minas y canteras',
    'C': 'Industrias manufactureras',
    'D': 'Suministro de electricidad, gas, vapor y aire acondicionado',
    'E': 'Suministro de agua, alcantarillado y gestión de desechos',
    'F': 'Construcción',
    'G': 'Comercio al por mayor y al por menor',
    'H': 'Transporte y almacenamiento',
    'I': 'Alojamiento y servicios de comida',
    'J': 'Información y comunicaciones',
    'K': 'Actividades financieras y de seguros',
    'L': 'Actividades inmobiliarias',
    'M': 'Actividades profesionales, científicas y técnicas',
    'N': 'Actividades de servicios administrativos y de apoyo',
    'O': 'Administración pública y defensa; seguridad social obligatoria',
    'P': 'Enseñanza',
    'Q': 'Salud humana y asistencia social',
    'R': 'Artes, entretenimiento y recreación',
    'S': 'Otras actividades de servicios',
    'T': 'Hogares como empleadores',
    'U': 'Organizaciones y órganos extraterritoriales',
}

# Palabra clave -> (sección, división, etiqueta de la división, peso).
# El peso rompe empates cuando un nombre dispara varias reglas: un token muy
# específico ("FERRETERIA") debe ganarle a uno genérico ("SERVICIOS").
REGLAS_CIIU: dict[str, tuple[str, str, str, int]] = {}


def _regla(claves: str, seccion: str, division: str, etiqueta: str, peso: int = 5) -> None:
    for clave in claves.split('|'):
        REGLAS_CIIU[clave.strip()] = (seccion, division, etiqueta, peso)


# --- A. Agropecuario -------------------------------------------------------
_regla('FINCA|AGROPECUARIA|AGRICOLA|GANADERA|GANADERIA|HACIENDA|CULTIVOS|'
       'PLANTACION|BANANERA|CAFETALERA|PORCINA|AVICOLA|GRANJA|VIVERO',
       'A', '01', 'Agricultura, ganadería, caza', 7)
_regla('PESCA|PESQUERA|PESQUERO|CAMARONERA|ACUICULTURA|MARISCOS',
       'A', '03', 'Pesca y acuicultura', 8)
_regla('ASERRADERO|MADERERA|REFORESTADORA|SILVICULTURA',
       'A', '02', 'Silvicultura y extracción de madera', 8)

# --- B. Minería ------------------------------------------------------------
_regla('MINERA|MINERIA|CANTERA|CANTERAS|EXTRACTORA|PETROLERA|GRAVERA|MINING|QUARRY',
       'B', '08', 'Explotación de minas y canteras', 8)

# --- C. Manufactura --------------------------------------------------------
_regla('PANADERIA|PANIFICADORA|REPOSTERIA|PASTELERIA|EMBUTIDOS|LACTEOS|'
       'PROCESADORA|ALIMENTOS|CONSERVAS|MOLINO|INGENIO|AZUCARERA|HARINERA|'
       'CARNICOS|FRIGORIFICO', 'C', '10', 'Elaboración de productos alimenticios', 8)
_regla('CERVECERIA|EMBOTELLADORA|REFRESQUERA|DESTILERIA|LICORERA',
       'C', '11', 'Elaboración de bebidas', 8)
_regla('TEXTIL|TEXTILES|CONFECCIONES|CONFECCION|HILANDERIA|UNIFORMES|BORDADOS|'
       'TEXTILE|APPAREL|GARMENTS',
       'C', '13', 'Fabricación de productos textiles', 8)
_regla('CALZADO|ZAPATERIA|CURTIEMBRE|TALABARTERIA',
       'C', '15', 'Fabricación de cuero y calzado', 8)
_regla('EBANISTERIA|CARPINTERIA|MUEBLES|MUEBLERIA',
       'C', '31', 'Fabricación de muebles', 8)
_regla('IMPRENTA|LITOGRAFIA|EDITORIAL|SERIGRAFIA|TIPOGRAFIA',
       'C', '18', 'Impresión y reproducción de grabaciones', 8)
_regla('QUIMICA|QUIMICOS|COSMETICOS|PLASTICOS|PLASTICO|PINTURAS|DETERGENTES|'
       'FARMACEUTICA|LABORATORIOS', 'C', '20', 'Fabricación de sustancias químicas', 7)
_regla('METALICA|METALICAS|METALURGICA|FUNDICION|HERRERIA|SOLDADURA|'
       'ESTRUCTURAS|ACERO|ALUMINIO', 'C', '25', 'Fabricación de productos metálicos', 7)
_regla('CEMENTO|CONCRETO|HORMIGON|BLOQUERA|LADRILLERA|VIDRIO|CERAMICA',
       'C', '23', 'Fabricación de minerales no metálicos', 8)
_regla('MANUFACTURA|MANUFACTURAS|FABRICA|INDUSTRIA|INDUSTRIAS|INDUSTRIAL|'
       'ENSAMBLADORA', 'C', '32', 'Industrias manufactureras diversas', 4)

# --- D / E. Utilities ------------------------------------------------------
_regla('ELECTRICA|ELECTRIFICADORA|ENERGIA|HIDROELECTRICA|GENERADORA|'
       'TERMOELECTRICA|SOLAR|EOLICA', 'D', '35', 'Suministro de electricidad y gas', 7)
_regla('ACUEDUCTO|ACUEDUCTOS|POTABILIZADORA|SANEAMIENTO|ASEO|RECOLECCION|'
       'RECICLADORA|RECICLAJE|DESECHOS|RESIDUOS',
       'E', '38', 'Gestión de desechos y saneamiento', 8)

# --- F. Construcción -------------------------------------------------------
_regla('CONSTRUCTORA|CONSTRUCCIONES|CONSTRUCCION|CONSTRUCTORES|EDIFICADORA|'
       'URBANIZADORA|PROMOTORA|DESARROLLADORA|OBRAS|INFRAESTRUCTURA|'
       'PAVIMENTOS|ASFALTOS|EXCAVACIONES|DEMOLICIONES',
       'F', '41', 'Construcción de edificios y obras', 8)
_regla('PLOMERIA|ELECTRICIDAD|INSTALACIONES|ACABADOS|REMODELACIONES|'
       'IMPERMEABILIZACION|AIRE ACONDICIONADO|REFRIGERACION',
       'F', '43', 'Actividades especializadas de construcción', 7)

# --- G. Comercio -----------------------------------------------------------
_regla('MINISUPER|MINI SUPER|SUPERMERCADO|SUPER|ABARROTERIA|ABARROTES|BODEGA|'
       'TIENDA|MERCADITO|MINIMARKET|COMISARIATO|DEPOSITO',
       'G', '47', 'Comercio al por menor', 8)
_regla('FERRETERIA|FERRETERA|MATERIALES|DEPOSITO DE MATERIALES',
       'G', '47', 'Comercio al por menor', 8)
_regla('FARMACIA|BOTICA|DROGUERIA|PHARMACY|DRUGSTORE', 'G', '47', 'Comercio al por menor', 8)
_regla('BOUTIQUE|ZAPATERIA|JOYERIA|LIBRERIA|PAPELERIA|MUEBLERIA|OPTICA|'
       'FLORISTERIA|VARIEDADES|BAZAR|NOVEDADES|ALMACEN|ALMACENES',
       'G', '47', 'Comercio al por menor', 7)
_regla('DISTRIBUIDORA|DISTRIBUIDOR|MAYORISTA|COMERCIALIZADORA|IMPORTADORA|'
       'EXPORTADORA|IMPORT|EXPORT|TRADING|SUMINISTROS|PROVEEDORES|'
       'REPRESENTACIONES', 'G', '46', 'Comercio al por mayor', 7)
_regla('AUTOMOTRIZ|AUTOS|VEHICULOS|CONCESIONARIO|REPUESTOS|LLANTAS|'
       'LUBRICENTRO|TALLER|TALLERES|AUTOSERVICIO|GASOLINERA|ESTACION DE SERVICIO|'
       # `SERVICENTRO` es la gasolinera panameña y no estaba. Con `AUTOREPUESTO`
       # y las marcas de combustible: 455 registros traían `ESTACION` o
       # `SERVICENTRO` y se quedaban sin sector (D24).
       'SERVICENTRO|AUTOREPUESTO|AUTOREPUESTOS|AUTOPARTES|RECTIFICADORA|'
       'TEXACO|ESSO|TERPEL|ACCEL|PETROAMERICA|SILVER STAR',
       'G', '45', 'Comercio y reparación de vehículos', 7)
# `ESTACION` sola no basta —hay estación de bus, de policía y `GRAN ESTACION`, que
# es un centro comercial— pero acompañada de la marca o de la palabra combustible
# no deja duda. Las frases se evalúan antes que los tokens.
_regla('ESTACION DE COMBUSTIBLE|ESTACION SHELL|ESTACION TEXACO|ESTACION ESSO|'
       'ESTACION PUMA|ESTACION TERPEL|ESTACION DELTA|ESTACION ACCEL|'
       'ESTACION DE GASOLINA|BOMBA DE COMBUSTIBLE',
       'G', '45', 'Comercio y reparación de vehículos', 8)
# Grúas y estacionamientos: servicio de apoyo al transporte, no transporte de
# pasajeros. 125 registros sin sector.
_regla('GRUA|GRUAS|PARKING|ESTACIONAMIENTO|ESTACIONAMIENTOS|APARCAMIENTO|'
       'REMOLQUE|REMOLQUES', 'H', '52',
       'Almacenamiento y actividades de apoyo al transporte', 7)

# Peso 3: por debajo de cualquier término que designe una actividad concreta
# (4-9). `INSTITUTO` se comportaba como específico con peso 9 y mandaba a
# Enseñanza al Instituto de Recursos Hidráulicos, al de Telecomunicaciones y al
# de Innovación Agropecuaria. Ahora pierde contra el token que sí describe qué
# se hace, y solo decide cuando no hay ninguno — que es el caso mayoritario.
_regla('INSTITUTO', 'P', '85', 'Enseñanza', 3)
# Peso 7, no 3: la frase `SUPER SERVICE` ya ataja el falso positivo que motivó
# bajarlo en D14, y con peso 3 rompía la guarda de D10 — `MINI SUPER PARQUE EL
# EMPALME` volvía a clasificarse como dirección porque `PARQUE` le ganaba.
_regla('SUPER|MINISUPER|MINISUPERMERCADO|SUPERETTE', 'G', '47',
       'Comercio al por menor', 7)
# La Zona Libre de Colón y el aeropuerto: 101 nombres distintos con `DUTY FREE`
# y ninguna palabra de actividad además de esa (`AROMAS DUTY FREE`, `DORADO DUTY
# FREE SA`). Es comercio al por menor sin ambigüedad posible (D22).
_regla('DUTY FREE|DUTYFREE|LIBRE DE IMPUESTOS', 'G', '47',
       'Comercio al por menor', 8)
_regla('GLOBAL', 'N', '82', 'Actividades de apoyo a empresas', 1)

# Ampliación del vocabulario de oficios con el tramo alfabético A-B (D20).
_regla('ARTESANO|ARTESANA|ARTESANIA|ARTESANIAS|EBANISTERIA ARTESANAL',
       'C', '32', 'Otras industrias manufactureras', 8)
_regla('ARTISTA|MUSICO|PINTOR ARTISTICO|ESCULTOR|BAILARIN|ACTOR',
       'R', '90', 'Actividades creativas y artísticas', 8)
_regla('ASEADORA|ASEADOR|LIMPIADORA|CONSERJE|SERVICIOS DE ASEO',
       'N', '81', 'Servicios a edificios y paisajismo', 8)
_regla('ASERRADOR|ASERRIO|MADERERO|LENADOR',
       'A', '02', 'Silvicultura y extracción de madera', 8)
_regla('BILLETERO|BILLETERA|VENTA DE BILLETES|LOTERO',
       'R', '92', 'Actividades de juegos de azar', 8)
_regla('BIOLOGO|BIOLOGA|QUIMICO|LABORATORISTA|INVESTIGADOR',
       'M', '72', 'Investigación científica y desarrollo', 7)
_regla('AGRONOMO|AGRONOMA|AGROEXPORTADOR|AGROGANADERA|AGROGANADERO|'
       'AGROINDUSTRIAL|AGROSERVICIO', 'A', '01',
       'Agricultura, ganadería, caza', 8)
_regla('AGROVETERINARIA|AGROVETERINARIO|VETERINARIA|VETERINARIO|CLINICA VETERINARIA',
       'M', '75', 'Actividades veterinarias', 8)
_regla('ASADOS Y FRITURAS|FRITURAS|VENTA DE COMIDAS|KIOSKO DE COMIDA',
       'I', '56', 'Servicio de comidas y bebidas', 8)
_regla('CUIDA NINOS|CUIDADORA DE NINOS|CUIDADO DE NINOS|CUIDADORA|'
       'CUIDADO DE ANCIANOS', 'Q', '87',
       'Atención en instituciones', 7)

# --- Oficio del trabajador independiente (D18) -----------------------------
# `ABOGADA INDEPENDIENTE`, `ACUICULTOR INDEPENDIENTE`, `INDEPENDIENTE AGRIMENSURA`.
# El registro no nombra una empresa —no la hay— pero **sí dice a qué se dedica la
# persona**, que es justo la columna que Riesgo necesita. El tipo sigue siendo
# INDEPENDIENTE; lo que se recupera es el sector.
#
# Solo entran oficios de actividad inequívoca. Se dejaron fuera `ADMINISTRADOR`,
# `OPERADOR`, `AYUDANTE`, `PROFESIONAL`, `CORREDOR` y `EMPRESARIO`: son cargos que
# existen en cualquier rama y no dicen en cuál.

_regla('VENDEDOR|VENDEDORA|VENDEDORES|COMERCIANTE|BUHONERO|MERCANCIA|'
       'MERCANCIAS|REVENDEDOR', 'G', '47', 'Comercio al por menor', 7)
_regla('AGRICULTOR|AGRICULTORA|GANADERO|GANADERA|CAMPESINO|AVICULTOR|'
       'APICULTOR|SEMBRADOR|FINQUERO',
       'A', '01', 'Agricultura, ganadería, caza', 8)
_regla('PESCADOR|ACUICULTOR|MARISCADOR', 'A', '03', 'Pesca y acuicultura', 8)
_regla('CONDUCTOR|CONDUCTORA|CHOFER|CHOFERES|TAXISTA|CAMIONERO|MOTORISTA|'
       'BUSERO|SELECTIVERO', 'H', '49', 'Transporte terrestre', 8)
_regla('MECANICO|MECANICA AUTOMOTRIZ|LATONERO', 'G', '45',
       'Comercio y reparación de vehículos', 8)
_regla('SOLDADOR|TORNERO|HERRERO', 'C', '25',
       'Fabricación de productos metálicos', 8)
_regla('ALBANIL|ALBANILES|PLOMERO|ELECTRICISTA|PINTOR|CONTRATISTA|'
       'CARPINTERO|TECHERO', 'F', '43',
       'Actividades especializadas de construcción', 8)
_regla('PROFESOR|PROFESORA|MAESTRO|MAESTRA|DOCENTE|INSTRUCTOR|INSTRUCTORA|'
       'TUTOR|EDUCADOR', 'P', '85', 'Enseñanza', 8)
_regla('ABOGADO|ABOGADA|ABOGADOS|NOTARIO|CONTADOR PUBLICO|AUDITOR',
       'M', '69', 'Actividades jurídicas y de contabilidad', 8)
_regla('PROGRAMADOR|PROGRAMADORA|DESARROLLADOR|INFORMATICO|WEBMASTER',
       'J', '62', 'Programación informática y consultoría', 8)
_regla('DISENADOR|DISENADORA|DECORADOR|DECORADORA|FOTOGRAFO|FOTOGRAFA|'
       'PUBLICISTA', 'M', '74', 'Otras actividades profesionales', 7)
_regla('MODISTA|COSTURERA|SASTRE', 'C', '14',
       'Confección de prendas de vestir', 8)
_regla('ESTILISTA|BARBERO|PELUQUERO|PELUQUERA|MANICURISTA|COSMETOLOGA|'
       'MASAJISTA', 'S', '96', 'Otros servicios personales', 8)
_regla('ENFERMERO|ENFERMERA|ODONTOLOGO|ODONTOLOGA|FISIOTERAPEUTA|'
       'ACUPUNTURISTA|NUTRICIONISTA|PSICOLOGO|PSICOLOGA|VETERINARIO',
       'Q', '86', 'Actividades de atención de la salud humana', 8)
_regla('AGRIMENSOR|AGRIMENSURA|TOPOGRAFO|ARQUITECTO|ARQUITECTA|'
       'INGENIERO|INGENIERA', 'M', '71', 'Arquitectura e ingeniería', 8)
_regla('EMPLEADA DOMESTICA|EMPLEADO DOMESTICO|TRABAJADORA DOMESTICA|'
       'SERVICIO DOMESTICO|NINERA', 'T', '97', 'Hogares como empleadores', 8)
# `CASA DE FAMILIA MARTINELLI` sí declara un empleador: el hogar. La sección T de
# la CIIU existe justamente para eso, y estaba desaprovechada porque solo la
# alcanzaban las frases largas. 270 registros del bloque sin sector caen aquí
# (D22). `CASA` sola no entra: la ataja `_casa_de_giro` (`CASA DE EMPENO`).
_regla('CASA DE FAMILIA|CASA FAMILIAR|CASA FAMILIA|CASA DE FLIA|'
       'DOMESTICA|DOMESTICO|DOMESTICAS|SERV DOMESTICO',
       'T', '97', 'Hogares como empleadores', 7)
_regla('COCINERO|COCINERA|REPOSTERO|REPOSTERA|PANADERO|CHEF|'
       'VENTA DE COMIDA|COMIDA RAPIDA', 'I', '56',
       'Servicio de comidas y bebidas', 8)

# --- Oficios de la cola larga (D17) ----------------------------------------
# Salieron de agrupar el residuo por sufijo español de oficio: `-ERIA` (el local
# donde se ejerce), `-ADORA` (la máquina o la empresa que hace algo).
#
# La regla por sufijo NO se automatizó, y con razón: entre las palabras que
# terminan en `-ERIA` o `-ADOR` están `IBERIA`, `NIGERIA`, `ECUADOR`, `AMADOR`,
# `SALVADOR`, `EMPERADOR` y `MIRADOR`. El sufijo sugiere dónde mirar; no decide.
# Cada término de abajo se admitió a mano.

_regla('CARNICERIA|CARNICERIAS|FRUTERIA|VERDULERIA|PESCADERIA|DULCERIA|'
       'LECHERIA|PERFUMERIA|SEDERIA|PLATERIA|HIELERIA|BUHONERIA|LLANTERIA|'
       'MERCERIA|CACHARRERIA|PANIFICADORA',
       'G', '47', 'Comercio al por menor', 8)
_regla('CEVICHERIA|HELADERIA|ROSTICERIA|CHURRERIA|LUNCHERIA|TAQUERIA|'
       'POLLERIA|EMPANADERIA|SANGUCHERIA|CAFETERIAS',
       'I', '56', 'Servicio de comidas y bebidas', 8)
_regla('HOJALATERIA|CARROCERIA|CARROCERIAS|RECTIFICADORA|LLANTERA|'
       'SILENCIADORES|RADIADORES|BATERIAS|ENDEREZADO',
       'G', '45', 'Comercio y reparación de vehículos', 8)
_regla('TORNERIA|TORNO|SOLDADURA|HERRERIA|FUNDICION|METALMECANICA',
       'C', '25', 'Fabricación de productos metálicos', 8)
_regla('MENSAJERIA|COURIER|ENCOMIENDA', 'H', '53',
       'Actividades postales y de mensajería', 8)
_regla('ALBANILERIA|ELEVADORES|ASCENSORES|CLIMATIZADORA|PLOMERIA|'
       'ELECTRICIDAD|INSTALACIONES ELECTRICAS|AIRE ACONDICIONADO',
       'F', '43', 'Actividades especializadas de construcción', 8)
_regla('SASTRERIA|MODISTERIA|CONFECCION DE UNIFORMES',
       'C', '14', 'Confección de prendas de vestir', 8)
_regla('TAPICERIA|EBANISTERIA|CARPINTERIA', 'C', '31',
       'Fabricación de muebles', 8)
_regla('CERRAJERIA|RELOJERIA|REPARADORA', 'S', '95',
       'Reparación de computadores y efectos personales', 8)
_regla('FUMIGADORA|FUMIGACION|CONTROL DE PLAGAS|JARDINERIA|PAISAJISMO',
       'N', '81', 'Servicios a edificios y paisajismo', 8)
_regla('EMPACADORA|PILADORA|BENEFICIADORA|TRILLADORA', 'C', '10',
       'Elaboración de productos alimenticios', 8)
_regla('ARRENDADORA', 'N', '77', 'Alquiler y arrendamiento', 8)
_regla('CALIFICADORA DE RIESGO|CALIFICADORA DE VALORES', 'K', '66',
       'Actividades auxiliares financieras', 8)
_regla('REASEGURADORA', 'K', '65', 'Seguros y fondos de pensiones', 8)
_regla('TENERIA|CURTIDURIA', 'C', '15', 'Fabricación de cuero y calzado', 8)
_regla('REFINERIA', 'C', '19', 'Fabricación de coque y refinación de petróleo', 8)
_regla('ENFERMERIA|FISIOTERAPIA|OPTOMETRIA', 'Q', '86',
       'Actividades de atención de la salud humana', 8)
_regla('PERSONERIA|ALCALDIA MUNICIPAL', 'O', '84', 'Administración pública', 8)

# --- Vocabulario derivado del conteo de frecuencias (D16) ------------------
# Se contaron las palabras de los clústeres SIN sector, ponderadas por registros.
# Las que encabezaban la lista y tenían actividad inequívoca entraron aquí. Las
# que encabezaban pero eran ambiguas —`PANAMA`, `CENTRO`, `CASA`, `FAMILIA`,
# `MUNDO`, `ESTACION`, `STAR`, `HERMANOS`— se dejaron fuera a propósito (D6).

# Niveles del sistema educativo panameño. `PRIMER CICLO DE PARITA` y
# `CENTRO BASICO GENERAL BEATRIZ MIRANDA` son escuelas, no otra cosa.
_regla('PRIMER CICLO|SEGUNDO CICLO|CENTRO BASICO GENERAL|CENTRO EDUCATIVO BASICO|'
       'PREMEDIA|EDUCACION BASICA GENERAL|TELEBASICA',
       'P', '85', 'Enseñanza', 9)

# Empleadores del Gobierno de EE. UU.: herencia de la antigua Zona del Canal, muy
# presente en la cartera panameña. `ARMY ZONA DEL CANAL`, `TREASURY OF THE USA`.
_regla('ARMY|NAVY|US ARMY|USA ARMY|U S ARMY|AIR FORCE|US NAVY|USA NAVY|U S NAVY|'
       'ARMY PANAMA|TREASURY OF THE|US GOVERNMENT|US GOVT|USA GOVERNMENT|'
       'DEPARTMENT OF DEFENSE|SOUTHERN COMMAND|PANAMA CANAL COMMISSION|'
       'PANAMA CANAL COMISSION|VETERANS ADMINISTRATION',
       'O', '84', 'Administración pública', 9)

# `AIR LINE` separado no coincidía con el token `AIRLINES`.
_regla('AIR LINE|AIR LINES|AIRLINE|AEREAS', 'H', '51', 'Transporte aéreo', 8)

# Lavado y cuidado de vehículos.
_regla('CAR WASH|CARWASH|AUTOLAVADO|LAVA AUTOS|LAVADO DE AUTOS|CAR CARE',
       'G', '45', 'Comercio y reparación de vehículos', 8)

# Alquiler de vehículos escrito de las formas que aparecen en el corpus.
_regla('RENT A CAR|RENTA CAR|CAR RENTAL|ALQUILER DE AUTOS|ALQUILER DE VEHICULOS',
       'N', '77', 'Alquiler y arrendamiento', 8)

# Asociaciones de padres de familia de las escuelas: son asociaciones, no la
# escuela ni una firma de asociados.
_regla('ASOCIACION DE PADRES|ASOC DE PADRES|ASOC PADRES|CLUB DE PADRES',
       'S', '94', 'Actividades de asociaciones', 9)

# `X Y ASOCIADOS` es el giro de las firmas profesionales panameñas —abogados,
# contadores, consultores—. Peso 4: cualquier token que diga la especialidad
# concreta (`INGENIERIA`, `ARQUITECTOS`, `CONTADORES`) le gana.
_regla('ASOCIADOS|ASSOCIATES', 'M', '69',
       'Actividades jurídicas y de contabilidad', 4)

# Huecos español/inglés del mismo tipo que corrigió D8: el catálogo tenía la
# forma inglesa y no la española, o al revés.
_regla('SOLUCIONES', 'J', '62',
       'Programación informática y consultoría', 4)
_regla('MANAGEMENT|GERENCIAMIENTO', 'M', '70', 'Consultoría de gestión', 5)
_regla('BUSINESS', 'N', '82', 'Actividades de apoyo a empresas', 2)

# --- Desambiguación de tokens genéricos (D14) ------------------------------
# Estas reglas van por frase, y `por_frase` corre antes que `por_token`: es la
# forma de que un nombre concreto le gane a una palabra suelta.

# `INSTITUTO` solo (peso 3, más abajo) no clasifica; con estas frases sí.
_regla('INSTITUTO PROF|INSTITUTO PRACTICO|INSTITUTO POLITECNICO|'
       'INSTITUTO PROFESIONAL|INSTITUTO TECNICO|INSTITUTO COMERCIAL|'
       'INSTITUTO EDUCATIVO|INSTITUTO BILINGUE|INSTITUTO PEDAGOGICO|'
       'INSTITUTO SUPERIOR|INSTITUTO DE ENSENANZA|INSTITUTO AMERICANO|'
       'INSTITUTO PANAMERICANO|INSTITUTO NACIONAL DE PANAMA',
       'P', '85', 'Enseñanza', 9)
_regla('INSTITUTO DE INVESTIGACION|INSTITUTO DE INVESTIGACIONES|'
       'INSTITUTO DE INNOVACION|INSTITUTO CIENTIFICO|INSTITUTO DE ESTUDIOS',
       'M', '72', 'Investigación científica y desarrollo', 9)
_regla('INSTITUTO DE RECURSOS HIDRAULICOS|INSTITUTO DE ACUEDUCTOS',
       'E', '36', 'Suministro de agua', 9)
_regla('INSTITUTO DE TELECOMUNICACIONES',
       'J', '61', 'Telecomunicaciones', 9)
_regla('INSTITUTO DE SEGUROS|INSTITUTO DE SEGURIDAD SOCIAL',
       'K', '65', 'Seguros y fondos de pensiones', 9)
_regla('INSTITUTO ONCOLOGICO|INSTITUTO DE MEDICINA|INSTITUTO NACIONAL DE SALUD',
       'Q', '86', 'Actividades de atención de la salud humana', 9)

# Órganos del Estado que quedaban clasificados en el sector que regulan o al que
# pertenece el lugar donde está destacado el funcionario (D15). Van por frase,
# así que le ganan al token de actividad:
#
#   SUPERINTENDENCIA BANCARIA        -> era intermediación financiera
#   COMISION NACIONAL DE VALORES     -> era comercio al por menor
#   JUZGADO PRIMERO DE CIRCUITO CIVIL-> era arquitectura e ingeniería (por CIVIL)
#   CONTRALORIA ESCUELA IPT          -> era enseñanza (auditor destacado en la escuela)
#
# El empleador es el órgano, no el sitio donde la persona trabaja ni el sector
# que vigila. Es el mismo criterio de D13 leído al revés: la Autoridad Marítima
# regula el transporte marítimo, y por eso NO es transporte marítimo.
_regla('SUPERINTENDENCIA|COMISION NACIONAL|CONSEJO NACIONAL|SECRETARIA NACIONAL|'
       'DIRECCION NACIONAL|DIRECCION GENERAL|JUZGADO|TRIBUNAL|FISCALIA|'
       'MINISTERIO PUBLICO|DEFENSORIA|PROCURADURIA|CONTRALORIA|REGISTRO PUBLICO|'
       'MUNICIPIO DE|ALCALDIA|JUNTA COMUNAL|GOBERNACION DE|CORTE SUPREMA|'
       'ORGANO EJECUTIVO|ORGANO LEGISLATIVO|PRESIDENCIA DE LA REPUBLICA',
       'O', '84', 'Administración pública', 9)

# La Caja de Seguro Social llega con muchas erratas en la última palabra
# (`SCOIAL`, `SOCUUAL`, `SOCILA`) y el gazetteer no las alcanza; el token
# `SEGURO` la mandaba a la industria aseguradora. La seguridad social
# obligatoria es administración pública en CIIU.
_regla('CAJA DE SEGURO', 'O', '84', 'Administración pública', 9)

# El IPAT regula y promueve el turismo: no es un operador turístico (D14, R11).
_regla('INSTITUTO PANAMENO DE TURISMO|AUTORIDAD DE TURISMO',
       'O', '84', 'Administración pública', 9)

# Gremios empresariales: asociaciones, no las empresas que agrupan.
_regla('CONSEJO NACIONAL DE LA EMPRESA PRIVADA|CAMARA DE COMERCIO|'
       'SINDICATO|GREMIO|COLEGIO DE ABOGADOS|COLEGIO DE MEDICOS|'
       'ASOCIACION DE PRODUCTORES|CAMARA PANAMENA',
       'S', '94', 'Actividades de asociaciones', 9)

# `SOCIAL SECURITY` es la agencia de pensiones de EE. UU., no vigilancia privada.
# Aparecía en «Actividades de seguridad e investigación» por el token SECURITY.
_regla('INSTITUTO DE MERCADEO AGROPECUARIO|INSTITUTO MERCADEO AGROPECUARIO|'
       'INSTITUTO NACIONAL DE ESTADISTICA|INSTITUTO NACIONAL DE CULTURA|'
       'INSTITUTO NACIONAL DE DESARROLLO',
       'O', '84', 'Administración pública', 9)
_regla('SOCIAL SECURITY|SEGURO SOCIAL DE ESTADOS UNIDOS',
       'O', '84', 'Administración pública', 9)

# Bancos multilaterales: no intermedian depósitos, son organismos internacionales.
_regla('BANCO MUNDIAL|BANCO INTERAMERICANO|BANCO DE DESARROLLO DE AMERICA|'
       'FONDO MONETARIO|CORPORACION ANDINA DE FOMENTO',
       'U', '99', 'Organizaciones y órganos extraterritoriales', 9)

# `SUPER` seguido de un servicio no es un supermercado.
_regla('SUPER SERVICE|SUPER SERVICIO|SUPER TALLER',
       'N', '82', 'Actividades de apoyo a empresas', 9)

# --- H. Transporte ---------------------------------------------------------
_regla('TRANSPORTE|TRANSPORTES|TRANSPORTISTA|CARGA|MUDANZAS|ACARREOS|BUSES|'
       'TAXI|TAXIS|FERROCARRIL|FERROCARRILES|RAILWAY|RAILWAYS|TRUCKING',
       'H', '49', 'Transporte terrestre', 8)
_regla('NAVIERA|MARITIMA|MARITIMO|PORTUARIA|PUERTO|PORTS|SHIPPING|'
       'REMOLCADORES|ASTILLERO', 'H', '50', 'Transporte marítimo', 8)
_regla('AEROLINEA|AEREA|AVIACION|AIRLINES|AIRWAYS|AEROPUERTO',
       'H', '51', 'Transporte aéreo', 8)
_regla('LOGISTICA|LOGISTIC|LOGISTICS|ALMACENAJE|ALMACENADORA|COURIER|'
       'ENCOMIENDAS|ADUANAS|ADUANERA|ADUANERAS|ADUANERO|ADUANAL|ADUANALES|'
       'CARGO|FREIGHT|CUSTOMS|FORWARDING|FORWARDER|FORDWARDING',
       'H', '52', 'Almacenamiento y actividades de apoyo al transporte', 8)

# --- I. Alojamiento y comida ----------------------------------------------
_regla('HOTEL|HOTELES|HOTELERA|HOSTAL|RESORT|MOTEL|APARTHOTEL|POSADA|CABANAS',
       'I', '55', 'Alojamiento', 8)
_regla('RESTAURANTE|RESTAURANT|CAFETERIA|FONDA|PIZZERIA|MARISQUERIA|PARRILLADA|'
       'CAFE|BAR|CANTINA|DISCOTECA|CATERING|COMIDAS|KIOSCO|REFRESQUERIA|'
       # El corpus escribe `KIOSKO` con K —104 registros— y la regla solo tenía la
       # forma con C. `MESON` y `RINCONCITO` son los otros dos nombres con que se
       # bautiza una fonda en Panamá (D23).
       'KIOSKO|MESON|RINCONCITO|REFRESQUERIA|SODA',
       'I', '56', 'Servicio de comidas y bebidas', 8)

# --- J. Información y comunicaciones --------------------------------------
_regla('SOFTWARE|SISTEMAS|INFORMATICA|TECNOLOGIA|TECNOLOGIAS|COMPUTO|'
       'COMPUTADORAS|DATA|DIGITAL|SOLUTIONS|IT|CIBER',
       'J', '62', 'Programación informática y consultoría', 6)
_regla('TELECOMUNICACIONES|TELEFONIA|CABLE|TELECOM|COMUNICACIONES|INTERNET|'
       'SATELITAL', 'J', '61', 'Telecomunicaciones', 8)
_regla('TELEVISION|RADIO|PRODUCTORA|MEDIOS|PERIODICO|PRENSA|NOTICIAS|'
       'PUBLICIDAD MEDIOS', 'J', '60', 'Programación y transmisión', 7)

# --- K. Financiero ---------------------------------------------------------
_regla('BANCO|BANK|BANCARIA|BANCARIO|FINANCIERA|FINANCIERO|FINANCIAL|FINANCE|'
       'CREDITOS|PRESTAMOS|COOPERATIVA|CASA DE EMPENO|FIDUCIARIA|CAMBIO',
       'K', '64', 'Intermediación financiera', 8)
_regla('SEGUROS|SEGURO|ASEGURADORA|REASEGUROS|INSURANCE|CORREDORES DE SEGUROS',
       'K', '65', 'Seguros y fondos de pensiones', 8)
_regla('CASA DE VALORES|PUESTO DE BOLSA|BOLSA|INVESTMENT|CAPITAL|ASSET|'
       'FONDO|FONDOS|HOLDING', 'K', '66', 'Actividades auxiliares financieras', 5)

# --- L. Inmobiliario -------------------------------------------------------
_regla('INMOBILIARIA|INMOBILIARIO|BIENES RAICES|REAL ESTATE|PROPERTIES|'
       'PROPIEDADES|ARRENDAMIENTOS|ALQUILERES|ADMINISTRADORA DE PH',
       'L', '68', 'Actividades inmobiliarias', 8)

# --- M. Profesionales ------------------------------------------------------
_regla('ABOGADOS|BUFETE|JURIDICO|JURIDICA|LEGAL|NOTARIA|LEGALES',
       'M', '69', 'Actividades jurídicas y de contabilidad', 8)
_regla('CONTABILIDAD|CONTADORES|AUDITORES|AUDITORIA|CONTABLE|FISCAL',
       'M', '69', 'Actividades jurídicas y de contabilidad', 8)
_regla('CONSULTORES|CONSULTORIA|CONSULTING|ASESORES|ASESORIA|ASESORAMIENTO',
       'M', '70', 'Consultoría de gestión', 6)
_regla('INGENIERIA|INGENIEROS|ARQUITECTURA|ARQUITECTOS|DISENO|TOPOGRAFIA|'
       'GEOTECNIA|PROYECTOS', 'M', '71', 'Arquitectura e ingeniería', 7)
_regla('PUBLICIDAD|MERCADEO|MARKETING|AGENCIA DE PUBLICIDAD|BTL',
       'M', '73', 'Publicidad y estudios de mercado', 8)
_regla('VETERINARIA|VETERINARIO', 'M', '75', 'Actividades veterinarias', 9)

# --- N. Servicios administrativos y de apoyo ------------------------------
_regla('SEGURIDAD|VIGILANCIA|PROTECCION|GUARDIAS|SECURITY|CUSTODIA',
       'N', '80', 'Actividades de seguridad e investigación', 8)
_regla('LIMPIEZA|ASEO INDUSTRIAL|MANTENIMIENTO|JARDINERIA|FUMIGACION|'
       'CLEANERS|CLEANING|SANITIZACION',
       'N', '81', 'Servicios a edificios y paisajismo', 8)
_regla('AGENCIA DE EMPLEO|OUTSOURCING|RECURSOS HUMANOS|TEMPORALES|STAFFING|'
       'CALL CENTER|CONTACT CENTER|BPO',
       'N', '78', 'Actividades de empleo y tercerización', 8)
_regla('AGENCIA DE VIAJES|VIAJES|TOURS|TURISMO|TRAVEL|OPERADORA TURISTICA',
       'N', '79', 'Agencias de viajes y operadores turísticos', 8)
_regla('RENT A CAR|RENTAL|ALQUILER DE EQUIPO|ARRENDADORA DE EQUIPO',
       'N', '77', 'Alquiler y arrendamiento', 7)

# --- O. Administración pública --------------------------------------------
_regla('MINISTERIO|ALCALDIA|MUNICIPIO|MUNICIPAL|AUTORIDAD|CONTRALORIA|'
       'TRIBUNAL|ORGANO JUDICIAL|ASAMBLEA|PROCURADURIA|DEFENSORIA|'
       'REGISTRO PUBLICO|SECRETARIA NACIONAL|INSTITUTO NACIONAL|'
       'DIRECCION GENERAL|GOBERNACION|CORREGIDURIA',
       'O', '84', 'Administración pública', 9)
_regla('POLICIA|BOMBEROS|SENAFRONT|SENAN|MIGRACION|ADUANA NACIONAL|'
       'FUERZA PUBLICA|PROTECCION CIVIL|SINAPROC',
       'O', '84', 'Administración pública, defensa y orden público', 9)
_regla('CAJA DE SEGURO SOCIAL|SEGURO SOCIAL',
       'O', '84', 'Seguridad social obligatoria', 9)

# --- P. Enseñanza ----------------------------------------------------------
_regla('ESCUELA|COLEGIO|UNIVERSIDAD|CENTRO EDUCATIVO|EDUCATIVO|'
       'EDUCACION|ACADEMIA|PREESCOLAR|GUARDERIA|KINDER|BILINGUE|SCHOOL|'
       'COLLEGE|UNIVERSITY|CAPACITACION|ENSENANZA|LICEO|SEMINARIO|ACADEMY',
       'P', '85', 'Enseñanza', 9)

# --- Q. Salud --------------------------------------------------------------
_regla('HOSPITAL|CLINICA|POLICLINICA|CENTRO DE SALUD|CENTRO MEDICO|MEDICO|'
       'MEDICA|CONSULTORIO|ODONTOLOGICA|DENTAL|OFTALMOLOGICO|CARDIOLOGICO|'
       'PEDIATRICO|MATERNIDAD|IMAGENOLOGIA|RADIOLOGIA|CLINIC',
       'Q', '86', 'Actividades de atención de la salud humana', 9)
_regla('LABORATORIO CLINICO|ANALISIS CLINICOS|PATOLOGIA',
       'Q', '86', 'Actividades de atención de la salud humana', 9)
_regla('ASILO|HOGAR DE ANCIANOS|GERIATRICO|ALBERGUE|ORFANATO|'
       'CENTRO DE REHABILITACION', 'Q', '87', 'Atención en instituciones', 8)

# --- R. Artes y recreación -------------------------------------------------
_regla('GIMNASIO|GYM|DEPORTIVO|DEPORTES|CLUB|ESTADIO|CANCHA|RECREATIVO|'
       'PARQUE ACUATICO|CASINO|APUESTAS|LOTERIA|HIPODROMO|CINE|TEATRO|MUSEO',
       'R', '93', 'Actividades deportivas y de esparcimiento', 7)

# --- S. Otros servicios ----------------------------------------------------
_regla('SALON DE BELLEZA|BELLEZA|BARBERIA|PELUQUERIA|SPA|ESTETICA|BARBER|'
       'SALON', 'S', '96', 'Otros servicios personales', 8)
_regla('LAVANDERIA|TINTORERIA|LAVAMATIC', 'S', '96', 'Otros servicios personales', 8)
_regla('FUNERARIA|CREMATORIO|CEMENTERIO|SERVICIOS FUNERARIOS',
       'S', '96', 'Otros servicios personales', 9)
_regla('IGLESIA|PARROQUIA|MINISTERIO RELIGIOSO|TEMPLO|CONGREGACION|MISION|'
       'DIOCESIS|COMUNIDAD RELIGIOSA|HERMANAS|CAPILLA|'
       # La sede del obispo y la casa del párroco son empleadores reales —tienen
       # sacristán, secretaria, personal de mantenimiento— y quedaban sin sector
       # o, peor, como dirección (`CASA CURAL SAN JUAN BAUTISTA`). D23.
       'OBISPADO|CASA CURAL|CURIA|VICARIA|SANTUARIO',
       'S', '94', 'Actividades de asociaciones', 8)
_regla('FUNDACION|ASOCIACION|ONG|SINDICATO|GREMIO|CAMARA DE COMERCIO|'
       'COOPERATIVA DE SERVICIOS|PATRONATO',
       'S', '94', 'Actividades de asociaciones', 6)
_regla('REPARACION|REPARACIONES|SERVICE CENTER|TECNICO',
       'S', '95', 'Reparación de computadores y efectos personales', 5)

# --- U. Extraterritoriales -------------------------------------------------
_regla('EMBAJADA|CONSULADO|NACIONES UNIDAS|ONU|UNICEF|OEA|BID|PNUD|'
       'CRUZ ROJA INTERNACIONAL|ORGANISMO INTERNACIONAL',
       'U', '99', 'Organizaciones extraterritoriales', 9)

# --------------------------------------------------------------------------
# Ampliación derivada de los clústeres que quedaron sin clasificar en la primera
# corrida de la fase 9. Se priorizaron los tokens por número de registros que
# desbloquean, y se incorporaron **solo** los que tienen sector inequívoco.
#
# Se descartaron a propósito CENTRO, CASA, FAMILIA, MUNDO, STAR, WORLD, GENERAL y
# similares: cubren mucho volumen pero no determinan actividad. Clasificarlos
# habría subido la cobertura y ensuciado el análisis de concentración de cartera,
# que es justo para lo que Riesgo va a usar esta columna.
# --------------------------------------------------------------------------

# Zona Libre de Colón: la mayor zona franca del hemisferio y un empleador masivo en
# el dataset. Es comercio al por mayor por definición.
_regla('ZONA LIBRE|ZONA LIBRE DE COLON|ZONA FRANCA|FREE ZONE',
       'G', '46', 'Comercio al por mayor (Zona Libre)', 9)

# Juntas comunales: gobierno local panameño.
_regla('JUNTA COMUNAL|JUNTA LOCAL|JUNTA DE DESARROLLO',
       'O', '84', 'Administración pública local', 9)

# Comercio
_regla('SHOP|STORE|MARKET|MALL|OUTLET|MINIMARKET|TIENDAS|COMERCIALES',
       'G', '47', 'Comercio al por menor', 7)
_regla('VENTAS|VENTA|MERCADO|COMERCIANTE|SUPPLY|SUPPLIES|EQUIPOS|AGENCIAS|AGENCIA',
       'G', '46', 'Comercio al por mayor', 5)
_regla('MOTORS|PARTES|AUTOPARTES|MOTOR', 'G', '45', 'Comercio y reparación de vehículos', 7)

# Tecnología
_regla('TECHNOLOGY|TECHNOLOGIES|TECH|SYSTEMS|SYSTEM|ELECTRONICS|ELECTRONICA|'
       'COMPUTERS|NETWORKS', 'J', '62', 'Programación informática y consultoría', 7)

# Construcción e ingeniería
_regla('CONSTRUCTION|CONTRATISTA|CONTRATISTAS|CONSORCIO|CONTRACTORS',
       'F', '41', 'Construcción de edificios y obras', 7)
_regla('ENGINEERING|ENGINEERS|CIVIL', 'M', '71', 'Arquitectura e ingeniería', 6)

# Salud y alimentos
_regla('MEDICAL|HEALTHCARE|SALUD', 'Q', '86', 'Actividades de atención de la salud humana', 6)
_regla('FOOD|FOODS|PIZZA|BURGER|GRILL|SUSHI|COMIDA', 'I', '56', 'Servicio de comidas y bebidas', 7)

# Marítimo y energía
_regla('MARINE|MARITIME|OCEAN|SHIPPING LINE|TERMINAL|TERMINALS|PORT',
       'H', '50', 'Transporte marítimo y actividades portuarias', 7)
_regla('POWER|ENERGY|ELECTRIC', 'D', '35', 'Suministro de electricidad y gas', 6)

# Financiero e inmobiliario
_regla('INVESTMENTS|HOLDINGS|HOLDING', 'K', '66', 'Actividades auxiliares financieras', 5)
_regla('REALTY|PROPERTY|BIENES Y RAICES', 'L', '68', 'Actividades inmobiliarias', 7)

# Servicios personales y de apoyo
_regla('BEAUTY|SPA Y BELLEZA', 'S', '96', 'Otros servicios personales', 7)
_regla('ADMINISTRADORA|ADMINISTRACION|MULTISERVICIOS|OUTSOURCING SERVICIOS',
       'N', '82', 'Actividades de apoyo a empresas', 3)
_regla('GOBIERNO|MUNICIPIO DE|ALCALDIA DE', 'O', '84', 'Administración pública', 8)
_regla('COOPERATIVA DE AHORRO|COOP', 'K', '64', 'Intermediación financiera', 6)

# Ropa y deporte
_regla('FASHION|MODA|ROPA|CONFECCIONES Y ROPA', 'G', '47', 'Comercio al por menor', 6)
_regla('SPORT|SPORTS|DEPORTIVA', 'R', '93', 'Actividades deportivas y de esparcimiento', 6)

# Chapistería y reparación automotriz
_regla('CHAPISTERIA|LATONERIA|DETAILING|LAVADO DE AUTOS|AUTOLAVADO',
       'G', '45', 'Comercio y reparación de vehículos', 8)

# Reglas genéricas de bajo peso: solo aplican si nada más disparó.
_regla('SERVICIOS|SERVICE|SERVICES|GROUP|GRUPO|CORPORACION|EMPRESA|COMPANIA|'
       'INVERSIONES|INVERSION|ENTERPRISE|ENTERPRISES|GLOBAL|INTERNACIONAL',
       'N', '82', 'Actividades de apoyo a empresas', 1)

# Frases multipalabra: se buscan sobre el nombre completo, antes que los tokens.
# --- Vocabulario de la cabeza de la cola de la fase 7 (D25) ----------------
# Salió de mirar los clústeres sin sector **ordenados por registros que
# arrastran**, que es distinto de mirarlos al azar: aquí no hay marcas raras de
# un solo registro, hay empresas grandes cuya actividad el catálogo no nombraba.
# Cada línea se midió contra el residuo antes de escribirla.
_regla('CALL CENTER|CONTACT CENTER|TELEMARKETING|TELEMERCADEO|BPO|'
       'CENTRO DE LLAMADAS', 'N', '82',
       'Actividades administrativas y de apoyo de oficina', 8)   # 140 registros
_regla('EDITORA|EDITORIAL|EDITORES|PERIODICO|DIARIO', 'J', '58',
       'Actividades de edición', 8)
_regla('IMPRESORA|IMPRESORES|IMPRENTA|LITOGRAFIA|SERIGRAFIA|TIPOGRAFIA|'
       'ARTES GRAFICAS', 'C', '18',
       'Impresión y reproducción de grabaciones', 8)             # 183 con las de arriba
_regla('SPORTSWEAR|T SHIRTS|TSHIRTS|CAMISERIA|SASTRERIA|MAQUILA|'
       'CONFECCIONES', 'C', '14', 'Confección de prendas de vestir', 8)
_regla('STEAMSHIP|STEAM SHIP|LINE COMPANY', 'H', '50',
       'Transporte marítimo', 8)
_regla('EMPAQUES|EMPAQUE|ENVASES|EMBALAJE|EMBALAJES', 'C', '22',
       'Fabricación de productos de caucho y plástico', 7)
# La casa de empeño es crédito prendario: presta con garantía, no vende.
_regla('EMPENO|EMPENOS|CASA DE EMPENO|PRENDARIO|MONTEPIO', 'K', '64',
       'Actividades de servicios financieros', 8)
_regla('MOLINO|MOLINOS|HARINAS|HARINERA|ARROCERA|TRILLADORA', 'C', '10',
       'Elaboración de productos alimenticios', 8)
_regla('HELADOS|HELADERIA|PALETERIA|SORBETERIA', 'C', '10',
       'Elaboración de productos alimenticios', 7)
_regla('MONTACARGAS|FORKLIFT|GRUAS HORQUILLA', 'G', '46',
       'Comercio al por mayor', 7)
_regla('FERTILIZANTES|FERTILIZANTE|AGROQUIMICOS|AGROQUIMICA|PLAGUICIDAS|'
       'INSECTICIDAS', 'C', '20', 'Fabricación de sustancias químicas', 8)
# Órganos del Estado que el catálogo no nombraba y que no son un ministerio.
_regla('RAMA JUDICIAL|PALACIO LEGISLATIVO|ASAMBLEA NACIONAL|CONSEJO PROVINCIAL|'
       'CONSEJO MUNICIPAL|CONTRALORIA|PROCURADURIA|DEFENSORIA DEL PUEBLO|'
       'TRIBUNAL ELECTORAL|REGISTRO PUBLICO', 'O', '84',
       'Administración pública y defensa', 9)

# --- Vocabulario de actividad en inglés (D26) ------------------------------
# Panamá es plaza de servicios internacionales y una parte grande del residuo
# tiene el nombre en inglés. El catálogo estaba escrito casi todo en español, así
# que `CLEAN`, `DESIGN`, `BAKERY` o `NAILS` no clasificaban nada.
#
# Importante: la mayoría del vocabulario inglés frecuente del residuo **no dice
# actividad** —`CORPORATION` (1.445 registros), `CENTER` (788), `EXPRESS` (557),
# `STAR`, `WORLD`, `PLUS`— y se dejó fuera por la misma razón que `PANAMA`: es
# palabra de fantasía, no de giro. Solo entra lo que nombra un oficio.
_regla('DESIGN|DESIGNS|DESING|DISENO|DISENOS|GRAPHIC DESIGN|INTERIOR DESIGN',
       'M', '74', 'Otras actividades profesionales', 6)      # 397 registros
_regla('PRODUCCIONES|PRODUCTIONS|PRODUCTORA AUDIOVISUAL', 'J', '59',
       'Actividades cinematográficas y de producción', 7)    # 336
# `PRODUCCION` en singular queda fuera a propósito: `PRODUCCION PANAMENA DE
# HIELO` es una fábrica, no una productora audiovisual.
_regla('NAILS|MANICURE|PEDICURE|SALON DE UNAS', 'S', '96',
       'Otros servicios personales', 8)                      # 251 con SPA ya existente
_regla('METALES|METALICA|METALMECANICA|SOLDADURA|SOLDADURAS|HERRERIA METALICA|'
       'SCRAP METAL', 'C', '25',
       'Fabricación de productos elaborados de metal', 6)    # 219
_regla('GRAPHICS|PRINTING|PRINT SHOP|VISUAL PRINT', 'C', '18',
       'Impresión y reproducción de grabaciones', 7)         # 194
_regla('IMPORTACIONES|EXPORTACIONES|IMPORTACION|EXPORTACION|IMPORTS|EXPORTS',
       'G', '46', 'Comercio al por mayor', 7)                # 192
_regla('EVENTOS|EVENTS|BANQUETES|ORGANIZACION DE EVENTOS', 'N', '82',
       'Actividades administrativas y de apoyo de oficina', 7)  # 191
_regla('CLEAN|CLEANING|JANITORIAL|LIMPIEZA|ASEO INDUSTRIAL', 'N', '81',
       'Actividades de servicios a edificios y paisajismo', 6)  # 156
_regla('HEALTH|HEALTHCARE|MEDICAL CENTER|WELLNESS|CHIROPRACTIC', 'Q', '86',
       'Actividades de atención de la salud humana', 6)      # 156
# `LABORATORIO` a secas NO entra: `LABORATORIO DE INYECCION DIESEL` es un taller,
# `LABORATORIO CLINICO` es salud y `LABORATORIOS X` suele ser farmacéutica. Es
# genuinamente ambiguo — por eso está en MORFOLOGIA_EXCLUIDA desde D11. Entran
# solo las formas que sí desambiguan.
_regla('LABORATORIO CLINICO|LABORATORIO DE ANALISIS|ANALISIS CLINICOS',
       'Q', '86', 'Actividades de atención de la salud humana', 8)
_regla('LABORATORIOS FARMACEUTICOS|LABORATORIO FARMACEUTICO', 'C', '21',
       'Fabricación de productos farmacéuticos', 8)
_regla('CARS|CAR WASH|AUTOLAVADO|RENT A CAR|CAR RENTAL|RENTA CAR', 'G', '45',
       'Comercio y reparación de vehículos', 7)              # 130
_regla('COFFEE HOUSE|COFFEE SHOP|CASA DE CAFE', 'I', '56',
       'Servicio de comidas y bebidas', 8)
_regla('COFFEE ROASTERS|COFFEE ESTATES|TOSTADORA DE CAFE|BENEFICIO DE CAFE',
       'C', '10', 'Elaboración de productos alimenticios', 8)  # 136 entre las dos
_regla('BAKERY|PASTRY|PASTELERIA|BAKERS', 'C', '10',
       'Elaboración de productos alimenticios', 8)           # 84
_regla('ADVISORS|ADVISORY|CONSULTING GROUP', 'M', '70',
       'Actividades de consultoría de gestión', 7)           # 68
_regla('EQUIPMENT|SUPPLIES|EQUIPOS Y SUMINISTROS', 'G', '46',
       'Comercio al por mayor', 6)                           # 63
_regla('DAY CARE|DAYCARE|GUARDERIA|CUIDADO INFANTIL|PREESCOLAR|KINDER',
       'P', '85', 'Enseñanza', 8)                            # 21
# `STUDIO` es lo más ambiguo del lote —fotografía, diseño, grabación, yoga— así
# que va con peso 4: suma cuando no hay nada mejor y pierde contra cualquier
# palabra de oficio concreta.
_regla('STUDIO|STUDIOS|ESTUDIO FOTOGRAFICO|PHOTO STUDIO|FOTOGRAFIA',
       'M', '74', 'Otras actividades profesionales', 4)      # 260
# Un hotel con spa es un hotel. `PANAMONTE INN AND SPA` caía en «otros servicios
# personales» porque `SPA` y el alojamiento pesaban igual; la frase decide.
_regla('INN AND SPA|HOTEL AND SPA|HOTEL Y SPA|RESORT AND SPA|INN', 'I', '55',
       'Alojamiento', 8)
# Reciclaje de chatarra es gestión de desechos, no metalmecánica.
_regla('RECYCLING|RECICLAJE|RECICLADORA|RECICLADORES|CHATARRA|CHATARRERIA',
       'E', '38', 'Recogida, tratamiento y eliminación de desechos', 8)

FRASES_CIIU: list[str] = sorted(
    (k for k in REGLAS_CIIU if ' ' in k), key=len, reverse=True
)


# ==========================================================================
# 6. Gazetteer de grandes empleadores de Panamá
# ==========================================================================
# Ancla el nombre canónico y el sector sin consumir llamadas externas. Cubre las
# entidades que más se repiten en el dataset (ver NOTAS_PERFILAMIENTO.MD §3).
# Formato: clave normalizada -> (nombre canónico, sección, división).

GAZETTEER: dict[str, tuple[str, str, str]] = {
    'AUTORIDAD CANAL PANAMA': ('Autoridad del Canal de Panamá', 'H', '52'),
    'CAJA SEGURO SOCIAL': ('Caja de Seguro Social', 'O', '84'),
    'MINISTERIO EDUCACION': ('Ministerio de Educación', 'O', '84'),
    'MINISTERIO SALUD': ('Ministerio de Salud', 'O', '84'),
    'MINISTERIO OBRAS PUBLICAS': ('Ministerio de Obras Públicas', 'O', '84'),
    'MINISTERIO SEGURIDAD PUBLICA': ('Ministerio de Seguridad Pública', 'O', '84'),
    'MINISTERIO DESARROLLO SOCIAL': ('Ministerio de Desarrollo Social', 'O', '84'),
    'TRIBUNAL ELECTORAL': ('Tribunal Electoral', 'O', '84'),
    'ORGANO JUDICIAL': ('Órgano Judicial', 'O', '84'),
    'CONTRALORIA GENERAL REPUBLICA': ('Contraloría General de la República', 'O', '84'),
    'POLICIA NACIONAL': ('Policía Nacional de Panamá', 'O', '84'),
    'UNIVERSIDAD PANAMA': ('Universidad de Panamá', 'P', '85'),
    'UNIVERSIDAD TECNOLOGICA PANAMA': ('Universidad Tecnológica de Panamá', 'P', '85'),
    'HOSPITAL SANTO TOMAS': ('Hospital Santo Tomás', 'Q', '86'),
    'HOSPITAL NINO': ('Hospital del Niño', 'Q', '86'),
    'BANCO NACIONAL PANAMA': ('Banco Nacional de Panamá', 'K', '64'),
    'BANCO GENERAL': ('Banco General, S.A.', 'K', '64'),
    'BANCO CONTINENTAL': ('Banco Continental de Panamá, S.A.', 'K', '64'),
    'BANCO UNO': ('Banco Uno, S.A.', 'K', '64'),
    'GLOBAL BANK': ('Global Bank Corporation', 'K', '64'),
    'BANISTMO': ('Banistmo, S.A.', 'K', '64'),
    'CITIBANK PANAMA': ('Citibank, N.A. Sucursal Panamá', 'K', '64'),
    'CAJA AHORROS': ('Caja de Ahorros', 'K', '64'),
    'PANAMA PORTS COMPANY': ('Panama Ports Company, S.A.', 'H', '52'),
    'PANAMA CANAL RAILWAY COMPANY': ('Panama Canal Railway Company', 'H', '49'),
    'EMPRESAS MELO': ('Empresas Melo, S.A.', 'C', '10'),
    'CERVECERIA NACIONAL': ('Cervecería Nacional, S.A.', 'C', '11'),
    'INDUSTRIAS LACTEAS': ('Industrias Lácteas, S.A.', 'C', '10'),
    'CONSTRUCTORA NORBERTO ODEBRECHT': ('Constructora Norberto Odebrecht, S.A.', 'F', '41'),
    'GRUPO ODINSA': ('Grupo Odinsa, S.A.', 'F', '41'),
    'CABLE ONDA': ('Cable Onda, S.A.', 'J', '61'),
    'COPA AIRLINES': ('Copa Airlines', 'H', '51'),
    'SUPER 99': ('Super 99', 'G', '47'),
    'GRUPO REY': ('Grupo Rey, S.A.', 'G', '47'),
    'EULEN PANAMA': ('Eulen Panamá, S.A.', 'N', '80'),
    'DELL PANAMA': ('Dell Panamá', 'J', '62'),
    'VEOLIA': ('Veolia', 'E', '38'),

    # Ampliación derivada del maestro corporativo: las entidades con más registros
    # tras la primera corrida completa. Anclar la cabeza de la distribución es
    # barato y sube la confianza justo donde más pesa en la cartera.
    'COCA COLA FEMSA': ('Coca-Cola FEMSA de Panamá, S.A.', 'C', '11'),
    'COCA COLA PANAMA': ('Coca-Cola FEMSA de Panamá, S.A.', 'C', '11'),
    'CABLE WIRELESS': ('Cable & Wireless Panamá, S.A.', 'J', '61'),
    'COPA AIRLINES': ('Copa Airlines, S.A.', 'H', '51'),
    'MANZANILLO INTERNATIONAL TERMINAL': ('Manzanillo International Terminal Panamá, S.A.', 'H', '52'),
    'PAYLESS': ('Payless ShoeSource Panamá, S.A.', 'G', '47'),
    'LOTERIA NACIONAL BENEFICENCIA': ('Lotería Nacional de Beneficencia', 'R', '92'),
    'CUERPO BOMBEROS': ('Cuerpo de Bomberos de Panamá', 'O', '84'),
    'MINISTERIO ECONOMIA FINANZAS': ('Ministerio de Economía y Finanzas', 'O', '84'),
    'MINISTERIO RELACIONES EXTERIORES': ('Ministerio de Relaciones Exteriores', 'O', '84'),
    'MINISTERIO GOBIERNO JUSTICIA': ('Ministerio de Gobierno y Justicia', 'O', '84'),
    'MINISTERIO SEGURIDAD': ('Ministerio de Seguridad Pública', 'O', '84'),
    'SMITHSONIAN': ('Smithsonian Tropical Research Institute', 'M', '72'),
    'MOTTA INTERNACIONAL': ('Motta Internacional, S.A.', 'G', '46'),
    'PRICESMART': ('PriceSmart Panamá, S.A.', 'G', '47'),
    'HOTEL VENETO': ('Veneto Hotel & Casino', 'I', '55'),
    'HSBC BANK PANAMA': ('HSBC Bank Panamá, S.A.', 'K', '64'),
    'INTEROCEANIC SUPPLY': ('Interoceanic Supply Services, S.A.', 'G', '46'),
    'CONCILIO GENERAL ASAMBLEAS DIOS': ('Concilio General de las Asambleas de Dios', 'S', '94'),
    'TRIBUNAL ELECTORAL': ('Tribunal Electoral', 'O', '84'),
    'IDAAN': ('Instituto de Acueductos y Alcantarillados Nacionales', 'E', '36'),
    'ORGANO JUDICIAL': ('Órgano Judicial', 'O', '84'),

    # ----------------------------------------------------------------------
    # Diccionario de empleadores ancla de Panamá (D13)
    # ----------------------------------------------------------------------
    # Fuente: investigación aportada por negocio, apoyada en la planilla del
    # sector público de la Contraloría a diciembre de 2025, reguladores
    # sectoriales y Merco Empresas Panamá 2025.
    #
    # Criterio: **actividad del lugar de trabajo, no propiedad**. Es la regla
    # del INEC (CINU Rev. 4.1) y de Naciones Unidas: el estatus legal de la
    # entidad no determina por sí mismo su clasificación. Por eso un banco
    # estatal va a financiero, una universidad pública a enseñanza, MiBus a
    # transporte y la Lotería a juegos de azar. Solo ministerios, tribunales,
    # Asamblea, policía y reguladores son administración pública.

    # --- Estado: administración pública propiamente dicha ------------------
    'PROCURADURIA GENERAL NACION': ('Procuraduría General de la Nación', 'O', '84'),
    'PROCURADURIA GENERAL': ('Procuraduría General de la Nación', 'O', '84'),
    'ASAMBLEA NACIONAL': ('Asamblea Nacional', 'O', '84'),
    'CONTRALORIA GENERAL': ('Contraloría General de la República', 'O', '84'),
    'MINISTERIO DESARROLLO AGROPECUARIO': ('Ministerio de Desarrollo Agropecuario', 'O', '84'),
    'MINISTERIO COMERCIO INDUSTRIAS': ('Ministerio de Comercio e Industrias', 'O', '84'),
    'MINISTERIO TRABAJO DESARROLLO LABORAL': ('Ministerio de Trabajo y Desarrollo Laboral', 'O', '84'),
    'MINISTERIO VIVIENDA': ('Ministerio de Vivienda y Ordenamiento Territorial', 'O', '84'),
    'MINISTERIO AMBIENTE': ('Ministerio de Ambiente', 'O', '84'),
    'MINISTERIO CULTURA': ('Ministerio de Cultura', 'O', '84'),
    'AUTORIDAD MARITIMA PANAMA': ('Autoridad Marítima de Panamá', 'O', '84'),
    'AUTORIDAD NACIONAL ADUANAS': ('Autoridad Nacional de Aduanas', 'O', '84'),
    'AUTORIDAD TRANSITO TRANSPORTE': ('Autoridad del Tránsito y Transporte Terrestre', 'O', '84'),
    'SUPERINTENDENCIA BANCOS': ('Superintendencia de Bancos de Panamá', 'O', '84'),
    'SUPERINTENDENCIA MERCADO VALORES': ('Superintendencia del Mercado de Valores', 'O', '84'),
    'SUPERINTENDENCIA SEGUROS': ('Superintendencia de Seguros y Reaseguros', 'O', '84'),
    'AUTORIDAD NACIONAL SERVICIOS PUBLICOS': ('Autoridad Nacional de los Servicios Públicos', 'O', '84'),
    'DIRECCION GENERAL INGRESOS': ('Dirección General de Ingresos', 'O', '84'),
    'DEFENSORIA PUEBLO': ('Defensoría del Pueblo', 'O', '84'),
    'AUTORIDAD TURISMO PANAMA': ('Autoridad de Turismo de Panamá', 'O', '84'),

    # --- Estado, pero clasificado por su actividad -------------------------
    'MIBUS': ('MiBus - Transporte Masivo de Panamá, S.A.', 'H', '49'),
    'TRANSPORTE MASIVO PANAMA': ('MiBus - Transporte Masivo de Panamá, S.A.', 'H', '49'),
    'METRO PANAMA': ('Metro de Panamá, S.A.', 'H', '49'),
    'BANCO NACIONAL PANAMA': ('Banco Nacional de Panamá', 'K', '64'),
    'CAJA AHORROS': ('Caja de Ahorros', 'K', '64'),
    'ETESA': ('Empresa de Transmisión Eléctrica, S.A.', 'D', '35'),
    'EMPRESA TRANSMISION ELECTRICA': ('Empresa de Transmisión Eléctrica, S.A.', 'D', '35'),
    'AUTORIDAD ASEO URBANO DOMICILIARIO': ('Autoridad de Aseo Urbano y Domiciliario', 'E', '38'),
    'AAUD': ('Autoridad de Aseo Urbano y Domiciliario', 'E', '38'),
    # `TOCUMEN` a secas salió del gazetteer: es también un corregimiento y una vía
    # principal, y hacía que `VIA TOCUMEN`, `PLAZA TOCUMEN` y `NUEVO TOCUMEN`
    # —direcciones— se leyeran como el aeropuerto. Mismo motivo por el que salieron
    # `ARROCHA` y `RICARDO PEREZ`: el apellido o el topónimo solo no basta (D24).
    'AEROPUERTO TOCUMEN': ('Aeropuerto Internacional de Tocumen, S.A.', 'H', '52'),
    'AEROPUERTO INTERNACIONAL TOCUMEN': (
        'Aeropuerto Internacional de Tocumen, S.A.', 'H', '52'),
    'INSTITUTO CONMEMORATIVO GORGAS': ('Instituto Conmemorativo Gorgas', 'M', '72'),
    'SERTV': ('Sistema Estatal de Radio y Televisión', 'J', '60'),
    'UNIVERSIDAD AUTONOMA CHIRIQUI': ('Universidad Autónoma de Chiriquí', 'P', '85'),
    'UNACHI': ('Universidad Autónoma de Chiriquí', 'P', '85'),
    'UDELAS': ('Universidad Especializada de las Américas', 'P', '85'),
    'UNIVERSIDAD ESPECIALIZADA AMERICAS': ('Universidad Especializada de las Américas', 'P', '85'),
    'UNIVERSIDAD MARITIMA INTERNACIONAL': ('Universidad Marítima Internacional de Panamá', 'P', '85'),
    'IPHE': ('Instituto Panameño de Habilitación Especial', 'P', '85'),
    'INSTITUTO PANAMENO HABILITACION ESPECIAL': ('Instituto Panameño de Habilitación Especial', 'P', '85'),
    'UNIVERSIDAD LATINA': ('Universidad Latina de Panamá', 'P', '85'),

    # --- Financiero --------------------------------------------------------
    'BANCO GENERAL': ('Banco General, S.A.', 'K', '64'),
    'BANISTMO': ('Banistmo, S.A.', 'K', '64'),
    'BAC INTERNATIONAL BANK': ('BAC International Bank, Inc.', 'K', '64'),
    'GLOBAL BANK': ('Global Bank Corporation', 'K', '64'),
    'MULTIBANK': ('Multibank, Inc.', 'K', '64'),
    'BANCO ALIADO': ('Banco Aliado, S.A.', 'K', '64'),
    'CREDICORP BANK': ('Credicorp Bank, S.A.', 'K', '64'),
    'TELERED': ('Telered, S.A.', 'K', '66'),
    'LATINEX': ('Latinex Holdings, Inc.', 'K', '66'),
    'LATINCLEAR': ('Central Latinoamericana de Valores', 'K', '66'),
    'ASSA COMPANIA SEGUROS': ('ASSA Compañía de Seguros, S.A.', 'K', '65'),
    'INTERNACIONAL SEGUROS': ('Internacional de Seguros, S.A.', 'K', '65'),
    'MAPFRE': ('MAPFRE Panamá, S.A.', 'K', '65'),
    'PAN AMERICAN LIFE': ('Pan-American Life Insurance de Panamá', 'K', '65'),

    # --- Comercio ----------------------------------------------------------
    'GRUPO REY': ('Grupo Rey, S.A.', 'G', '47'),
    'SUPERMERCADO REY': ('Supermercados Rey', 'G', '47'),
    'SUPERMERCADOS REY': ('Supermercados Rey', 'G', '47'),
    'RIBA SMITH': ('Supermercados Riba Smith, S.A.', 'G', '47'),
    'FARMACIAS ARROCHA': ('Farmacias Arrocha', 'G', '47'),
    'DROGUERIAS ARROCHA': ('Farmacias Arrocha', 'G', '47'),
    'RICARDO PEREZ TOYOTA': ('Ricardo Pérez, S.A.', 'G', '45'),
    'AUTOS RICARDO PEREZ': ('Ricardo Pérez, S.A.', 'G', '45'),
    'NOVEY': ('Do It Center - Novey', 'G', '47'),
    'PANAFOTO': ('Panafoto, S.A.', 'G', '47'),
    'FELIX MADURO': ('Félix B. Maduro, S.A.', 'G', '47'),
    'MR PRECIO': ('Mr. Precio', 'G', '47'),
    'MACHETAZO': ('El Machetazo', 'G', '47'),
    'DICARINA': ('Dicarina, S.A.', 'G', '46'),
    'MAYS ZONA LIBRE': ('Mays Zona Libre, S.A.', 'G', '46'),
    'GRUPO FELIPE RODRIGUEZ': ('Grupo Felipe Rodríguez', 'G', '45'),

    # --- Manufactura y alimentos -------------------------------------------
    'CERVECERIA NACIONAL': ('Cervecería Nacional, S.A.', 'C', '11'),
    'NESTLE': ('Nestlé Panamá, S.A.', 'C', '10'),

    # --- Cabeza de la cola de la fase 7 (D25) -----------------------------
    # Empresas que arrastran 15-40 registros cada una y que la fase 7 habría
    # pagado por resolver. Cada entrada se midió contra el residuo: entre todas
    # cubren 1.779 registros que iban a la consulta externa.
    'MAERSK': ('Maersk Panamá, S.A.', 'H', '50'),
    'MAERKS': ('Maersk Panamá, S.A.', 'H', '50'),
    'SEALAND': ('Sealand - A Maersk Company', 'H', '50'),
    'ADIDAS': ('Adidas Latin America, S.A.', 'G', '46'),
    'AXA ASSISTANCE': ('AXA Assistance Panamá, S.A.', 'K', '65'),
    'ERNST AND YOUNG': ('Ernst & Young Panamá', 'M', '69'),
    'PRICE WATER HOUSE': ('PricewaterhouseCoopers Panamá', 'M', '69'),
    'PRICEWATERHOUSE': ('PricewaterhouseCoopers Panamá', 'M', '69'),
    'PROCTER AND GAMBLE': ('Procter & Gamble Panamá', 'G', '46'),
    'TETRA PACK': ('Tetra Pak Panamá', 'C', '22'),
    'TETRA PAK': ('Tetra Pak Panamá', 'C', '22'),
    'SANOFI': ('Sanofi Aventis de Panamá, S.A.', 'C', '21'),
    'GLAXO': ('GlaxoSmithKline Panamá, S.A.', 'C', '21'),
    'GLAXO SMITHKLINE': ('GlaxoSmithKline Panamá, S.A.', 'C', '21'),
    'ESTEE LAUDER': ('Estée Lauder Panamá', 'G', '46'),
    'RED BULL': ('Red Bull de Panamá', 'G', '46'),
    'BRINKS': ('Brink’s de Panamá, S.A.', 'N', '80'),
    'CANON PANAMA': ('Canon de Panamá, S.A.', 'G', '46'),
    'KUEHNE': ('Kuehne + Nagel Panamá', 'H', '52'),
    'ASSICURAZIONI GENERALI': ('Assicurazioni Generali, S.p.A.', 'K', '65'),

    # Casas comerciales y familias empresarias panameñas
    'VARELA HERMANOS': ('Varela Hermanos, S.A.', 'C', '11'),
    'FELIPE MOTTA': ('Felipe Motta, S.A.', 'G', '46'),
    'TAGAROPULOS': ('Tagaropulos, S.A.', 'G', '46'),
    'COCHEZ': ('Cochez y Compañía, S.A.', 'G', '47'),
    # `Y` y `AND` son stopwords: el núcleo llega sin ellas, pero la tipificación
    # consulta el gazetteer sobre el texto limpio, que sí las trae. Las dos formas.
    'CARDOZE LINDO': ('Cardoze y Lindo, S.A.', 'G', '46'),
    'CARDOZE Y LINDO': ('Cardoze y Lindo, S.A.', 'G', '46'),
    'MORGAN MORGAN': ('Morgan & Morgan', 'M', '69'),
    'TZANETATOS': ('H. Tzanetatos, Inc.', 'G', '46'),
    'PANAMA AMERICA': ('Editora El Panamá América, S.A.', 'J', '58'),
    'FRANQUICIAS PANAMENAS': ('Franquicias Panameñas, S.A.', 'I', '56'),

    # Firmas de abogados. Panamá es plaza de servicios legales y sus bufetes se
    # nombran con los apellidos de los socios, sin ninguna palabra que diga a qué
    # se dedican — por eso ninguno tenía sector. Entran con dos apellidos, nunca
    # con uno: `ALEMAN` o `ARIAS` sueltos son apellidos corrientes (ver D15).
    'MOSSACK FONSECA': ('Mossack Fonseca & Co.', 'M', '69'),
    'ALEMAN CORDERO': ('Alemán, Cordero, Galindo & Lee', 'M', '69'),
    'GALINDO LEE': ('Alemán, Cordero, Galindo & Lee', 'M', '69'),
    'ICAZA GONZALEZ': ('Icaza, González-Ruiz & Alemán', 'M', '69'),
    'ICAZA GONZALES': ('Icaza, González-Ruiz & Alemán', 'M', '69'),
    'PATTON MORENO': ('Patton, Moreno & Asvat', 'M', '69'),
    'ALFARO FERRER': ('Alfaro, Ferrer & Ramírez', 'M', '69'),
    'MORGAN AND MORGAN': ('Morgan & Morgan', 'M', '69'),
    'MORGAN Y MORGAN': ('Morgan & Morgan', 'M', '69'),
    'ARIAS FABREGA': ('Arias, Fábrega & Fábrega', 'M', '69'),
    'GALINDO ARIAS': ('Galindo, Arias & López', 'M', '69'),
    'SUCRE ARIAS': ('Sucre, Arias & Reyes', 'M', '69'),
    'SUCRES ARIAS': ('Sucre, Arias & Reyes', 'M', '69'),
    'RIVERA BOLIVAR': ('Rivera, Bolívar y Castañeda', 'M', '69'),
    'TAPIA LINARES': ('Tapia, Linares y Alfaro', 'M', '69'),
    'FABREGA MOLINO': ('Fábrega Molino', 'M', '69'),
    'EMPRESA PANAMENA ALIMENTOS': ('Empresa Panameña de Alimentos', 'C', '10'),
    'GRUPO MELO': ('Grupo Melo, S.A.', 'C', '10'),
    'EMPRESAS MELO': ('Empresas Melo, S.A.', 'C', '10'),
    'CEMENTOS ARGOS': ('Cementos Argos Panamá', 'C', '23'),
    'CEMEX PANAMA': ('Cemex Panamá, S.A.', 'C', '23'),
    'GRUPO ESTRELLA': ('Grupo Estrella Azul', 'C', '23'),
    'FORMETAL': ('Formetal, S.A.', 'C', '25'),
    'GRUPO HOPSA': ('Grupo Hopsa', 'C', '25'),
    'PRODUCTOS QUIMICOS PANAMERICANOS': ('Productos Químicos Panamericanos, S.A.', 'C', '20'),
    'CONFECCIONES DICAR': ('Confecciones Dicar, S.A.', 'C', '13'),
    'DECOLOSAL': ('Decolosal, S.A.', 'C', '31'),
    'EMPRESAS CARBONE': ('Empresas Carbone, S.A.', 'C', '32'),

    # --- Servicios a empresas, seguridad y facilities ----------------------
    'FOUNDEVER': ('Foundever Panamá', 'N', '82'),
    'ALORICA': ('Alorica Panamá', 'N', '82'),
    'EULEN': ('Grupo Eulen Panamá, S.A.', 'N', '81'),
    'PROSEGUR': ('Prosegur Panamá, S.A.', 'N', '80'),
    'MANPOWER': ('ManpowerGroup Panamá', 'N', '78'),
    'MANPOWERGROUP': ('ManpowerGroup Panamá', 'N', '78'),
    'COSUSA': ('Cosusa, S.A.', 'N', '78'),
    'BUDGET': ('Budget Rent a Car Panamá', 'N', '77'),
    'AVIS': ('Avis Panamá', 'N', '77'),
    'HERTZ': ('Hertz Panamá', 'N', '77'),
    'AVENTURAS 2000': ('Aventuras 2000, S.A.', 'N', '79'),
    'GRAY LINE': ('Gray Line Panamá', 'N', '79'),

    # --- Profesionales -----------------------------------------------------
    'DELOITTE': ('Deloitte Panamá', 'M', '70'),
    'MORGAN MORGAN': ('Morgan & Morgan', 'M', '69'),
    'KANTAR MERCAPLAN': ('Kantar Mercaplan', 'M', '73'),
    'DICHTER NEIRA': ('Dichter & Neira', 'M', '73'),
    'TYPSA': ('Typsa Panamá', 'M', '71'),
    'LOUIS BERGER': ('WSP - Louis Berger Panamá', 'M', '71'),

    # --- Tecnología y telecomunicaciones -----------------------------------
    'GBM': ('GBM de Panamá, S.A.', 'J', '62'),
    'MINSAIT': ('Minsait - Indra Panamá', 'J', '62'),
    'DELL': ('Dell Technologies Panamá', 'J', '62'),
    'TIGO': ('Tigo Panamá, S.A.', 'J', '61'),
    'TVN MEDIA': ('TVN Media, S.A.', 'J', '60'),

    # --- Transporte, logística y puertos -----------------------------------
    'PSA PANAMA INTERNATIONAL TERMINAL': ('PSA Panama International Terminal, S.A.', 'H', '52'),
    'PANAMA PORTS': ('Panama Ports Company, S.A.', 'H', '52'),
    'COLON CONTAINER TERMINAL': ('Colon Container Terminal, S.A.', 'H', '52'),

    # --- Salud, alojamiento y construcción ---------------------------------
    'HOSPITAL NACIONAL': ('Hospital Nacional, S.A.', 'Q', '86'),
    'HOSPITAL SAN FERNANDO': ('Hospital San Fernando, S.A.', 'Q', '86'),
    'PACIFICA SALUD': ('Pacífica Salud Hospital Punta Pacífica', 'Q', '86'),
    'HOSPITAL PUNTA PACIFICA': ('Pacífica Salud Hospital Punta Pacífica', 'Q', '86'),
    'MARRIOTT': ('Marriott Panamá', 'I', '55'),
    'SHERATON': ('Sheraton Grand Panamá', 'I', '55'),
    'RIU PLAZA': ('Riu Plaza Panamá', 'I', '55'),
    'GRUPO LOS PUEBLOS': ('Grupo Los Pueblos - GLP Properties', 'L', '68'),
    'GLP PROPERTIES': ('Grupo Los Pueblos - GLP Properties', 'L', '68'),
    'CONSTRUCTORA MECO': ('Constructora Meco, S.A.', 'F', '41'),
    'CONSTRUCTORA URBANA': ('Constructora Urbana, S.A.', 'F', '41'),
    'ARCOS DORADOS': ("Arcos Dorados - McDonald's Panamá", 'I', '56'),
    'MCDONALDS': ("McDonald's Panamá", 'I', '56'),
    'GRUPO MAITO': ('Grupo Maito', 'I', '56'),

    # --- Energía, minería, agro y organismos internacionales ---------------
    'AES PANAMA': ('AES Panamá, S.R.L.', 'D', '35'),
    'EDEMET': ('Edemet - Naturgy Panamá', 'D', '35'),
    'ELEKTRA NORESTE': ('Elektra Noreste, S.A.', 'D', '35'),
    'EDECHI': ('Edechi - Naturgy Panamá', 'D', '35'),
    'MINERA PANAMA': ('Minera Panamá, S.A. - Cobre Panamá', 'B', '07'),
    'COBRE PANAMA': ('Minera Panamá, S.A. - Cobre Panamá', 'B', '07'),
    'OPEN BLUE': ('Open Blue Sea Farms Panamá', 'A', '03'),
    'FUTURO FORESTAL': ('Futuro Forestal, S.A.', 'A', '02'),
    'CAMARA COMERCIO INDUSTRIAS AGRICULTURA': ('Cámara de Comercio, Industrias y Agricultura de Panamá', 'S', '94'),
    'CAPAC': ('Cámara Panameña de la Construcción', 'S', '94'),
    'PNUD': ('Programa de las Naciones Unidas para el Desarrollo', 'U', '99'),
    'UNICEF': ('UNICEF Oficina Regional para América Latina y el Caribe', 'U', '99'),
    'UNOPS': ('UNOPS Panamá', 'U', '99'),
    'NACIONES UNIDAS': ('Organización de las Naciones Unidas', 'U', '99'),
    'DHL': ('DHL Panamá, S.A.', 'H', '52'),
    'FEDEX': ('FedEx Panamá', 'H', '52'),
    'UPS': ('UPS Panamá', 'H', '52'),

    # --- Formas ya expandidas por ABREVIATURAS -----------------------------
    # `expandir_tokens` corre antes de consultar el gazetteer, así que las siglas
    # que están en ABREVIATURAS llegan aquí desplegadas. Sin estas claves, `IDAAN`
    # se convertía en `INSTITUTO DE ACUEDUCTOS...` y caía en Enseñanza por el token
    # `INSTITUTO`.
    'INSTITUTO ACUEDUCTOS ALCANTARILLADOS NACIONALES': (
        'Instituto de Acueductos y Alcantarillados Nacionales', 'E', '36'),
    'AUTORIDAD CANAL PANAMA': ('Autoridad del Canal de Panamá', 'H', '52'),
    'AUTORIDAD MARITIMA PANAMA': ('Autoridad Marítima de Panamá', 'O', '84'),
    'AUTORIDAD TURISMO PANAMA': ('Autoridad de Turismo de Panamá', 'O', '84'),
    'INSTITUTO FORMACION APROVECHAMIENTO RECURSOS HUMANOS': (
        'Instituto para la Formación y Aprovechamiento de Recursos Humanos', 'O', '84'),
    'SERVICIO NACIONAL FRONTERAS': ('Servicio Nacional de Fronteras', 'O', '84'),
    'SERVICIO NACIONAL AERONAVAL': ('Servicio Nacional Aeronaval', 'O', '84'),
    'SECRETARIA NACIONAL DISCAPACIDAD': ('Secretaría Nacional de Discapacidad', 'O', '84'),
}


# ==========================================================================
# 7. Etiquetas de salida
# ==========================================================================

# Singulares que NO son sinónimo de su plural en el catálogo. La regla morfológica
# (D11) no debe cruzarlos:
#   LABORATORIO  — en Panamá, un «Laboratorio X» suele ser clínico o de inyección
#                  diesel; «Laboratorios X» en plural sí suele ser farmacéutica.
#                  El plural es el que lleva el sentido industrial.
#   GUARDIA      — apellido y provincia, además de vigilante.
# `PRODUCCION` entró en D26: la regla nueva es `PRODUCCIONES` en plural, que es
# como se llama una productora audiovisual, y deliberadamente dejaba fuera el
# singular. Pero el rescate morfológico lo devolvía por detrás —singular y plural
# son la misma palabra para él— y `PRODUCCION PANAMENA DE HIELO`, que es una
# fábrica, terminaba clasificada como cine. Una exclusión deliberada en el
# catálogo hay que repetirla aquí, o esta capa la deshace.
MORFOLOGIA_EXCLUIDA: set[str] = {'LABORATORIO', 'GUARDIA', 'PRODUCCION'}


# ==========================================================================
# Categorías de situación laboral (D20)
# ==========================================================================
# Todos los registros que no son un empleador compartían una sola etiqueta:
# «No identificable - No es un empleador». 4.346 registros en un cajón, cuando
# el texto dice con precisión qué es cada uno.
#
# Es el mismo error que corrigió D8 a mayor escala: llamar «no identificable» a
# algo que está perfectamente identificado. Un ama de casa no es un dato que no
# se pudo leer; es una situación laboral concreta, y agruparla con los jubilados
# y los fallecidos pierde información que el texto sí traía.

_GRUPOS_SITUACION: list[tuple[str, set[str]]] = [
    # El orden importa: `AMA DE CASA ACTUALMENTE NO TRABAJA` es ama de casa, no
    # una desempleada. Lo más específico se evalúa primero.
    ('Ama de casa', {
        'AMA DE CASA', 'AMO DE CASA', 'AMA DE LLAVES',
        'ADMINISTRADORA DEL HOGAR', 'ADMINISTRADOR DEL HOGAR',
        'ADMINISTRADORA DE SU HOGAR', 'ADMINISTRADORA EL HOGAR',
        'ADMON DEL HOGAR', 'ADMO DEL HOGAR', 'ADMINISTRADORA DOMESTICA',
        'LABORES DEL HOGAR', 'OFICIOS DEL HOGAR', 'TAREAS DEL HOGAR',
    }),
    ('Jubilado o pensionado', {
        'JUBILADO', 'JUBILADA', 'PENSIONADO', 'PENSIONADA',
        'RETIRADO', 'RETIRADA',
    }),
    ('Estudiante', {'ESTUDIANTE'}),
    ('Desempleado', {
        'DESEMPLEADO', 'DESEMPLEADA', 'CESANTE', 'NO TRABAJA', 'SIN TRABAJO',
        'SIN EMPLEO', 'NO LABORA', 'NO ESTA LABORANDO', 'NO ESTA TRABAJANDO',
        'QUEDO CESANTE', 'ACABA DE QUEDAR CESANTE', 'SIN EMPLEO ACTUAL',
    }),
    # Anotaciones del sistema de originación. Tampoco son «no identificables»:
    # dicen con precisión por qué el campo de empleador vino sin empleador.
    ('Cliente fallecido', {
        'CLIENTE FALLECIDO', 'CLIENTE FALLECIDA', 'FALLECIDO', 'FALLECIDA',
    }),
    ('Menor de edad', {
        'MENOR DE EDAD', 'MENOR DEPENDIENTE', 'MENOR',
    }),
    ('Dependiente económico', {
        'DEPENDIENTE ECONOMICO', 'DEPENDIENTE ECONOMICA', 'DEPENDIENTE',
        'DEPENDIENTE DE TERCERO', 'DEPENDIENTE DE UN TERCERO',
    }),
    ('Cuenta cerrada o cancelada', {
        'CUENTA CANCELADA', 'CUENTA CERRADA',
    }),
]

ETIQUETA_SITUACION: dict[str, str] = {
    marcador: etiqueta
    for etiqueta, marcadores in _GRUPOS_SITUACION
    for marcador in marcadores
}


def categoria_situacion(texto: str, tokens: list[str]) -> str:
    """
    Etiqueta canónica de la situación laboral declarada, o '' si no aplica.

    Se consulta en el orden de `_GRUPOS_SITUACION`: primero la frase completa,
    después el token suelto.
    """
    conjunto = set(tokens)
    for etiqueta, marcadores in _GRUPOS_SITUACION:
        for m in marcadores:
            if ' ' in m and m in texto:
                return etiqueta
        if conjunto & marcadores:
            return etiqueta
    # Las anotaciones por prefijo se resuelven después de los grupos: `AMA DE CASA
    # DEPENDIENTE DE SU ESPOSO` es un ama de casa, no un dependiente.
    _, etiqueta = prefijo_anotacion(texto)
    return etiqueta


SECTOR_DIRECCION = 'No identificable - Direcciones'
SECTOR_FALTA_INFO = 'No identificable - Falta informacion'
SECTOR_NO_EMPLEADOR = 'No identificable - No es un empleador'

# El empleador SÍ quedó identificado, pero su nombre no revela la actividad
# ('Tricom', 'Damax Marbella'). No es lo mismo que falta de información: el
# enunciado reserva esa etiqueta para cuando se agotaron las validaciones, y la
# validación externa (fase 7) es precisamente la que aún no se ha agotado.
SECTOR_PENDIENTE = 'Pendiente de validación externa'

# Vista ejecutiva: agregación de secciones CIIU para la presentación.
AGREGADO_EJECUTIVO: dict[str, str] = {
    'A': 'Agropecuario y pesca',
    'B': 'Minería',
    'C': 'Manufactura',
    'D': 'Energía y servicios públicos',
    'E': 'Energía y servicios públicos',
    'F': 'Construcción',
    'G': 'Comercio',
    'H': 'Transporte y logística',
    'I': 'Hotelería y restaurantes',
    'J': 'Tecnología y comunicaciones',
    'K': 'Financiero y seguros',
    'L': 'Inmobiliario',
    'M': 'Servicios profesionales',
    'N': 'Servicios de apoyo empresarial',
    'O': 'Sector público',
    'P': 'Educación',
    'Q': 'Salud',
    'R': 'Entretenimiento y recreación',
    'S': 'Otros servicios',
    'T': 'Hogares empleadores',
    'U': 'Organismos internacionales',
}


# ==========================================================================
# 12. Erratas de las palabras institucionales (D22)
# ==========================================================================
# El origen es captura libre de un ejecutivo de cuenta escribiendo a mano, y las
# palabras largas son las que más se equivocan. Medido sobre el corpus: 1.022
# variantes mal escritas de 19 palabras frecuentes, en **3.298 registros**.
#
#   CONSTRUCTURA · COSNTRUCTORA · CONSTRUTORA · COSTRUCTORA · CONTRUCTOR
#   MINSTERIO · MINITERIO · MINISTERI · MINSITERIO · MINISTERO
#   INDEPENDIETE · IDEPENDIENTE · INDEPNDIENTE · INDENDIENTE · INDEPENDINETE
#
# Enumerarlas sería una lista muerta: la 1.023ª aparece con el próximo lote. Lo
# que se enumera es el **destino** —y ni siquiera eso a mano: las dianas salen de
# la base de conocimiento que ya existe (tokens CIIU de peso alto y marcadores de
# situación). El corrector es genérico; la lista de erratas no existe.
#
# Cuatro guardas, todas necesarias:
#   a) Solo tokens de 8+ caracteres. Con menos, dos palabras legítimas distan un
#      carácter (`MAR`/`MAS`, `SUR`/`SUB`) y la corrección inventa datos.
#   b) Solo tokens que ninguna regla reconoce. Si el token ya clasifica, está bien
#      escrito por definición y tocarlo solo puede empeorar.
#   c) Umbral 90 y no 85. A 85 entra `DEPEDIENTE -> INDEPENDIENTE`, que invierte
#      el sentido del registro: el dependiente es lo contrario del independiente.
#   d) Diferencia de largo <= 2. `CONSTRUCT` y `CONSTRUCTORA` puntúan alto y no
#      son la misma palabra.

_dianas_errata: list[str] = []


def _dianas() -> list[str]:
    """Palabras diana, derivadas de la base de conocimiento ya declarada."""
    global _dianas_errata
    if not _dianas_errata:
        _dianas_errata = sorted(
            {t for t, r in REGLAS_CIIU.items()
             if ' ' not in t and len(t) >= 8 and r[3] >= 7}
            | {m for m in (MARCADORES_INACTIVO | MARCADORES_INDEPENDIENTE
                           | MARCADORES_OCUPACION)
               if ' ' not in m and len(m) >= 8}
        )
    return _dianas_errata


_vocabulario_conocido: set[str] = set()


def _conocido(token: str) -> bool:
    """Un token que alguna regla ya reconoce está bien escrito por definición."""
    global _vocabulario_conocido
    if not _vocabulario_conocido:
        _vocabulario_conocido = (
            set(REGLAS_CIIU) | STOPWORDS | set(ABREVIATURAS) | set(ABREVIATURAS.values())
            | MARCADORES_INACTIVO | MARCADORES_INDEPENDIENTE | MARCADORES_OCUPACION
            | MARCADORES_ANOTACION | TOKENS_DIRECCION_FUERTES | TOKENS_DIRECCION_DEBILES
            | {t for clave in GAZETTEER for t in clave.split()}
        )
    return token in _vocabulario_conocido


@functools.lru_cache(maxsize=None)
def _corregir_token(token: str) -> str:
    if len(token) < 8 or _conocido(token):
        return token
    m = process.extractOne(token, _dianas(), scorer=fuzz.ratio, score_cutoff=90)
    if not m:
        return token
    diana = m[0]
    if abs(len(diana) - len(token)) > 2:
        return token
    # Uno es prefijo del otro: es un plural o una derivación, no una errata.
    # `CONSULTOR` no es `CONSULTORIO` mal escrito —el consultor asesora empresas
    # (M/70) y el consultorio atiende pacientes (Q/86)— y `COMERCIAL` no es
    # `COMERCIALES`. Medido en seco: esta guarda sola evita 2.100 sustituciones,
    # todas innecesarias y algunas equivocadas.
    if diana.startswith(token) or token.startswith(diana):
        return token
    # Y uno contenido en el final del otro es otra palabra con un prefijo delante,
    # no una errata. Dos casos reales que esta guarda ataja:
    #
    #   DEPENDIENTE  -> INDEPENDIENTE   531 registros, y son **opuestos**: el que
    #                                   vive de otro convertido en cuenta propia.
    #   CASTILLERO   -> ASTILLERO        42 registros. Castillero es un apellido
    #                                   panameño corriente, no un varadero.
    if diana.endswith(token) or token.endswith(diana):
        return token
    return diana


def corregir_erratas(tokens: list[str]) -> tuple[list[str], bool]:
    """Devuelve los tokens con las erratas corregidas, y si hubo cambio."""
    salida = [_corregir_token(t) for t in tokens]
    return salida, salida != tokens


# ==========================================================================
# 13. Prefijos comerciales (D24)
# ==========================================================================
# El comercio panameño bautiza los negocios pegando el giro delante del nombre:
# `REFRICAR`, `REFRIAIRE`, `REFRIHOGAR`, `REFRITODO`, `REFRIPARTES`, `REFRICENTRO`.
# Son 136 registros sin sector y ninguno coincide con un token del catálogo, porque
# el giro no llega a ser una palabra: es una sílaba pegada a otra cosa.
#
# Solo entran prefijos **inequívocos**: `REFRI` únicamente puede ser refrigeración.
# `SERVI`, `MULTI` y `DISTRI` se dejaron fuera a propósito — `SERVIPAR` es
# estacionamiento y `MULTIBANK` es un banco; el prefijo no dice de qué van.
#
# El largo mínimo evita que el prefijo se coma la palabra entera: `REFRI` a secas
# no dispara, `REFRICAR` sí.
PREFIJOS_CIIU: list[tuple[str, str, str, str, int]] = [
    # F/43 y no S/95: `REFRIGERACION` ya está en el catálogo como instalación
    # especializada, y `REFRICAR` es la misma familia escrita pegada. Partirlas
    # en dos secciones sería incoherente con la regla que ya existe.
    ('REFRI', 'F', '43', 'Actividades especializadas de construcción', 6),
    ('AGROVET', 'M', '75', 'Actividades veterinarias', 7),
    ('AUTOREPUEST', 'G', '45', 'Comercio y reparación de vehículos', 7),
]

_LARGO_MIN_PREFIJO = 2   # caracteres que el token debe tener *además* del prefijo


def por_prefijo_comercial(token: str) -> tuple[str, str, str, int] | None:
    """Sección, división, etiqueta y peso si el token arranca con un giro pegado."""
    if token in REGLAS_CIIU:
        return None
    for prefijo, seccion, division, etiqueta, peso in PREFIJOS_CIIU:
        if (token.startswith(prefijo)
                and len(token) >= len(prefijo) + _LARGO_MIN_PREFIJO):
            return seccion, division, etiqueta, peso
    return None
