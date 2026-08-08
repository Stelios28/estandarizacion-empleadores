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

import re

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
]

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
    'INTERAMERICANA', 'CORREGIMIENTO', 'BARRIADA', 'URBANIZACION', 'URB',
    'BOULEVARD', 'BULEVAR', 'CALLEJON', 'SENDERO', 'DIAGONAL',
}

TOKENS_DIRECCION_DEBILES: set[str] = {
    'EDIFICIO', 'EDIF', 'APTO', 'APT', 'AP', 'APARTAMENTO', 'PISO', 'LOCAL', 'CASA',
    'TORRE', 'PLAZA', 'ENTRADA', 'FRENTE', 'DETRAS', 'CONTIGUO', 'ALTOS',
    'RESIDENCIAL', 'BARRIO', 'VIA', 'KM', 'KILOMETRO', 'NO', 'NRO', 'NUMERO',
    'SECTOR', 'MANZANA', 'LOTE', 'FINCA', 'PARQUE',
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
    'NO TRABAJA', 'SIN TRABAJO', 'SIN EMPLEO', 'CESANTE', 'HOGAR',
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
       'LUBRICENTRO|TALLER|TALLERES|AUTOSERVICIO|GASOLINERA|ESTACION DE SERVICIO',
       'G', '45', 'Comercio y reparación de vehículos', 7)

# Peso 3: por debajo de cualquier término que designe una actividad concreta
# (4-9). `INSTITUTO` se comportaba como específico con peso 9 y mandaba a
# Enseñanza al Instituto de Recursos Hidráulicos, al de Telecomunicaciones y al
# de Innovación Agropecuaria. Ahora pierde contra el token que sí describe qué
# se hace, y solo decide cuando no hay ninguno — que es el caso mayoritario.
_regla('INSTITUTO', 'P', '85', 'Enseñanza', 3)
_regla('SUPER', 'G', '47', 'Comercio al por menor', 3)
_regla('GLOBAL', 'N', '82', 'Actividades de apoyo a empresas', 1)

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
       'CAFE|BAR|CANTINA|DISCOTECA|CATERING|COMIDAS|KIOSCO|REFRESQUERIA',
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
       'DIOCESIS|COMUNIDAD RELIGIOSA|HERMANAS|CAPILLA',
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
    'TOCUMEN': ('Aeropuerto Internacional de Tocumen, S.A.', 'H', '52'),
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
MORFOLOGIA_EXCLUIDA: set[str] = {'LABORATORIO', 'GUARDIA'}


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
