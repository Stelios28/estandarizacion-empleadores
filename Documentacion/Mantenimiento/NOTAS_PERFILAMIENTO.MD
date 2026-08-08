# Notas de perfilamiento — dataset de empleadores

**Fecha:** 2026-08-07
**Fuente de verdad:** `prueba_tecnica_ing_datos.xlsx`, hoja `Sheet1`, columna `nombre_original`
**Reproducible con:** `python codigo/00_perfilamiento.py`
**Alcance:** solo lectura. No se modificó el archivo fuente.

Este documento existe para que los hallazgos no queden únicamente en una conversación.
Todo lo afirmado aquí es medido, no inferido, salvo donde se marque como inferencia.

---

## 1. Volumen

| Métrica | Valor |
|---|---|
| Filas de datos | 323.001 |
| Nulos | 1 |
| Registros útiles | 323.000 |
| Columnas | 1 (`nombre_original`) |

Longitud del texto: mín 1 · p50 21 · p90 32 · p99 41 · máx 65.

---

## 2. Artefacto de exportación: apóstrofe inicial

**100,00 %** de los valores (323.000/323.000) empiezan con `'`.

Es el prefijo de texto de Excel materializado en el valor. No es parte del nombre del
empleador. **Debe eliminarse en el primer paso de limpieza**, antes de cualquier
normalización, o contamina hashes, blocking keys y comparaciones exactas.

---

## 3. El dataset fue deduplicado y uniquificado artificialmente

Hallazgo con mayor impacto en el diseño.

| Métrica | Valor |
|---|---|
| Valores distintos exactos | 323.000 de 323.000 (**100 %**) |
| Terminan en `" <número>"` | 35.820 (11,09 %) |
| Distintos al retirar ese sufijo | 305.676 |
| Grupos que colapsan (>1 ocurrencia) | 13.013 |

Sufijos más comunes: `1` (16.856 veces), luego `2`…`9` y `0` con ~1.700–2.100 cada uno.
El patrón —`1` dominante y el resto casi uniforme— es firma de un proceso de
desduplicación con contador, no de datos capturados por un digitador.

Bases que reaparecen al quitar el sufijo:

```
51  MINI SUPER              13  AUTORIDAD DEL CANAL DE PANAMA
44  CALLE                   13  CONTRALORIA MRIO
19  EMPRESAS MELO SA        12  MINISTERIO DE EDUCACION
18  EMPRESAS MELO S A       12  TRIBUNAL ELECTORAL
18  MINISUPER               12  CAJA DE SEGURO SOCIAL
17  INVERSIONES             11  CONST NORBERTO ODEBRECHT S A
```

### Implicaciones

1. **No existen frecuencias reales.** Queda inutilizable la heurística estándar de
   entity resolution "la variante más frecuente del clúster es el nombre canónico".
   El canónico debe determinarse por regla lingüística + validación externa.
2. **No se puede reportar "% de registros afectados" en términos de cartera.** Cada
   fila es una variante de escritura, no un cliente. Los KPI deben expresarse sobre
   variantes únicas y declararlo explícitamente.
3. **El sufijo numérico es ruido inyectado.** Debe removerse en limpieza — pero solo
   cuando es un entero corto separado (`ELECTRONICA SUN SA 1`), nunca cuando forma
   parte del nombre (`JOSUE 8`, `3N SA`, `WEST WIND 66`, años `2005`, código `507`).
   Requiere regla con lista de excepciones y evidencia por caso.
4. `EMPRESAS MELO SA` y `EMPRESAS MELO S A` conviviendo confirma que la separación
   del sufijo societario es un eje real de variación.

---

## 4. Dos truncamientos de origen: 30 y 40 caracteres

Histograma de longitudes:

```
26  9.256      31  4.936      36  3.666
27  8.482      32  4.518      37  2.573
28  8.139      33  4.344      38  2.667
29  9.054      34  3.967      39  2.754
30 18.748  <<  35  3.573      40  1.833  <<
                              41    181
                              42    183
```

- **Pico en 30:** 18.748 contra ~8.500 esperados por tendencia → aprox. **10.000
  registros truncados** a 30 caracteres.
- **Acantilado en 40→41:** de 1.833 a 181 (caída de 90 %) → segundo tope de campo.
  Los ~1.000 registros con longitud 41-65 provienen de una tercera vía de captura.

**Inferencia (no medible desde el archivo):** hay al menos dos sistemas fuente con
campos `VARCHAR(30)` y `VARCHAR(40)`. Confirmarlo requiere acceso al origen.

Ejemplos de truncamiento a media palabra:

```
SENADIS SECRET NACIONAL DE DIS      AUTORIDAD NACIONAL DE DESCENTR
SALA DE BELLEZA JEHOVA MI FUER      SERVICIOS FINANCIEROS INMEDIAT
HOTELERA DOMINGUEZ HOTEL ALCAL      CONDUCTOR DE TAXI INDEPENDIENT
```

**Implicación:** el truncamiento es un caso límite de primera clase, no ruido de
digitación. Exige matching por prefijo — un nombre truncado es prefijo exacto del
canónico— y penalización asimétrica en la distancia: cortar el final es barato,
cambiar el inicio no lo es. Tratarlo como error ortográfico degrada la precisión.

---

## 5. El texto ya llegó destruido desde el origen

| Métrica | Valor |
|---|---|
| Registros con tilde o `Ñ` | **0** |
| Registros con minúsculas | **0** |
| Caracteres no alfanuméricos en 323.000 registros | 29 `-` y 5 `.` únicamente |
| Registros que contienen `PANAMEA` | 312 |

`PANAMEA` es `PANAMEÑA` con la eñe eliminada, no sustituida por `N`. Lo mismo aplica
a `CONSERVAS PANAMEAS SELECTAS SA`.

### Implicaciones

1. La normalización agresiva (mayúsculas, sin acentos, sin puntuación) **ya ocurrió
   aguas arriba y es irreversible**. Se pierde información de desambiguación.
2. La ausencia casi total de puntuación elimina el discriminante `S.A.` vs `SA` y
   simplifica la limpieza, pero también borra separadores útiles.
3. `PANAMEA`, `PANAMENA` y `PANAMEÑA` deben resolver a la misma entidad. El
   normalizador necesita tratar la eñe eliminada como caso explícito, no confiar en
   `unicodedata.normalize`, que no revierte una letra ya borrada.

---

## 6. Taxonomía exploratoria

Conteos por expresión regular. **Son cotas inferiores**, no la clasificación final:
detectan la presencia de un token, no la naturaleza del registro.

| Categoría | Registros | % |
|---|---|---|
| Sufijo societario al final (`SA`, `CORP`, `INC`, `LTD`, `LLC`…) | 69.972 | 21,66 % |
| Contiene dígitos | 41.129 | 12,73 % |
| Una sola palabra | 22.123 | 6,85 % |
| Educación (escuela, colegio, universidad, IPT, CEBG) | 9.392 | 2,91 % |
| Independiente / cuenta propia | 6.044 | 1,87 % |
| Gobierno (ministerios, autoridades, ACP, CSS) | 5.388 | 1,67 % |
| Inmueble (edificio, PH, local, urbanización, barriada) | 4.779 | 1,48 % |
| Salud (hospital, clínica, policlínica, farmacia) | 4.699 | 1,45 % |
| Inactivos (ama de casa, jubilado, desempleado, estudiante) | 3.573 | 1,11 % |
| Vía (calle, avenida, carretera, transístmica) | 1.207 | 0,37 % |
| Longitud ≤ 3 caracteres | 1.229 | 0,38 % |
| Ocupación en lugar de empresa | 1.123 | 0,35 % |
| Nulo explícito (`N/A`, `XXX`, `NINGUNO`) | 27 | 0,01 % |

Observaciones:

- **Direcciones ≈ 1,8 %** (unión de vía + inmueble, con solapamiento). El enunciado
  les asigna categoría propia `No identificable - Direcciones`, así que la precisión
  importa mucho más que el volumen. Resoluble con reglas explícitas.
- **Nulos explícitos: 27 registros.** La categoría residual
  `No identificable - Falta informacion` no se llenará con `N/A`; se llenará con
  cadenas cortas sin significado (`ASJDI`, `MFASD`, `TEMYM`, `DNK`), que son el
  verdadero problema y exigen agotar validación externa antes de rendirse.
- **Una sola palabra: 6,85 %.** Contiene tanto marcas reales (`VEOLIA`, `LOREAL`,
  `KUBOX`) como ruido. El enunciado prohíbe explícitamente asumir que un nombre corto
  es inválido.

---

## 7. Contexto geográfico: Panamá

Confirmado por las entidades más repetidas: Autoridad del Canal de Panamá, Caja de
Seguro Social, Tribunal Electoral, Ministerio de Educación, Banco Nacional de Panamá,
Panama Ports Company, Contraloría, Órgano Judicial, Zona Libre (`ZL`).

Fuentes públicas pertinentes para la fase de validación externa:

- Registro Público de Panamá — sociedades anónimas y su razón social exacta
- Panamá Emprende / Aviso de Operación — comercios y actividad económica declarada
- DGI — RUC
- Directorio de instituciones del Estado — entidades públicas
- Autoridad del Canal de Panamá — entidad autónoma con régimen propio

Taxonomía sectorial recomendada: **CIIU Rev. 4** (la Contraloría publica su
adaptación nacional), por compatibilidad con reportes regulatorios y con la
segmentación sectorial que ya usa Riesgo.

---

## 8. Riesgos de diseño identificados

| # | Riesgo | Mitigación propuesta |
|---|---|---|
| R1 | Sobre-agrupación por fuzzy: `BANCO UNO`, `BANCO CONTINENTAL` y `GLOBAL BANK` colapsan en un clúster | Bloqueo por token distintivo, no por token genérico. Priorizar precisión sobre recall. Umbral alto + revisión de clústeres grandes. |
| R2 | Sin frecuencias, elegir el canónico es ambiguo | Canónico por regla (nombre más largo no truncado + validación externa), no por moda |
| R3 | Truncados tratados como errores tipográficos | Regla de prefijo con distancia asimétrica |
| R4 | Ocupaciones e inactivos contaminan el maestro corporativo | Categoría propia, decisión documentada (el enunciado no la contempla) |
| R5 | Persona natural como empleador (`NOMBRE APELLIDO APELLIDO`, anonimizado) | Detector de antropónimo; no ingresa al maestro corporativo como sociedad |
| R6 | Remoción del sufijo numérico borra dígitos legítimos (`3N SA`, `JOSUE 8`) | Lista de excepciones + registro de cada remoción en la traza |
| R7 | Búsqueda web sobre 305.676 variantes es inviable en costo | Consultar solo el representante del clúster y solo bajo duda razonable; caché persistente |

---

## 9. Qué NO se puede saber desde este archivo

Declarado para evitar que se presente como hecho:

- Cuántos clientes reales hay detrás de cada nombre (no hay frecuencias)
- Fecha de captura, sistema de origen y canal
- Si el empleador está activo
- Relación de un registro con la cartera o su saldo
- Los nombres completos de los ~10.000 registros truncados

Todo esto requiere acceso al sistema de originación.
