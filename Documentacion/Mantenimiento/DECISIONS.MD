# Decisiones

Registro canónico de decisiones del proyecto. Una decisión reemplazada no se elimina:
cambia de estado y apunta a la que la sustituye.

Estados: `PROPUESTA` · `VIGENTE` · `REEMPLAZADA` · `REVOCADA`

---

## D1 — Alcance: pipeline completo ejecutable sobre 323.000 registros

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Decisión:** Construir el pipeline end-to-end ejecutable sobre el dataset completo,
  más los cinco entregables del enunciado (código, dataset resultado, documento
  técnico, presentación ejecutiva, propuesta de evolución).
- **Motivo:** Es lo que el enunciado pide literalmente. Un diseño sin ejecución deja
  "escala a millones de registros" como afirmación en vez de evidencia, y el enunciado
  exige explícitamente "código fuente" y "arquitectura escalable".
- **Alternativas consideradas:** diseño + prototipo sobre muestra de 10-20k; solo
  documento técnico y presentación.
- **Impacto:** Fija el presupuesto de cómputo y obliga a que cada fase sea
  materializable en disco y reanudable. Descarta implementaciones O(n²).
- **Evidencia:** `Prueba tecnica.docx`, sección "Requerimientos obligatorios".
- **Archivos afectados:** todo `codigo/`.

---

## D2 — Validación externa: búsqueda web y LLM sobre representantes de clúster

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Decisión:** Usar búsqueda web real y LLM únicamente para el representante de cada
  clúster que quede en duda razonable tras las fases determinísticas, con caché
  persistente en disco y presupuesto máximo de llamadas declarado.
- **Motivo:** El enunciado exige "consulta de fuentes públicas para validar
  organizaciones" y "búsqueda web cuando existan dudas razonables". Un motor solo
  offline incumple el requisito.
- **Alternativas consideradas:** solo reglas y diccionarios; offline ahora y web
  después.
- **Impacto:** Introduce dependencia de red, credenciales y costo variable. Obliga a
  que el pipeline sea determinístico y reanudable con la caché fría, y a que ninguna
  decisión crítica dependa exclusivamente de una respuesta de LLM sin traza.
- **Riesgo asociado:** R7 (costo). Mitigación: consultar el representante del clúster,
  nunca la variante; caché por clave normalizada; tope de llamadas configurable.
- **Evidencia:** `Prueba tecnica.docx`, Anexo A, fase 7.
- **Archivos afectados:** fase de enriquecimiento en `codigo/`.

---

## D3 — Taxonomía sectorial: CIIU Rev. 4

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Decisión:** Asignar `sector_propuesto` sobre CIIU Rev. 4, a nivel de sección
  (letra) y división (2 dígitos), usando la adaptación nacional publicada por la
  Contraloría General de Panamá como referencia de etiquetas.
- **Motivo:** Estándar internacional, compatible con reporte regulatorio y con
  análisis de concentración de cartera. Permite agregar hacia arriba para la
  presentación ejecutiva sin perder granularidad para Riesgo.
- **Alternativas consideradas:** segmentación interna de Riesgo (descartada: no se
  dispone del catálogo y no puede inventarse); taxonomía simple de ~15 sectores
  (descartada como taxonomía primaria, se conserva como vista agregada).
- **Impacto:** Se entrega sección y división. La vista de ~15 sectores para ejecutivos
  se deriva por agrupación de secciones, no se clasifica dos veces.
- **Evidencia:** `Prueba tecnica.docx`, "Asignación de sector económico"; contexto
  panameño confirmado en `NOTAS_PERFILAMIENTO.MD` §7.
- **Archivos afectados:** fase de clasificación sectorial, catálogo CIIU en `datos/`.

---

## D4 (propuesta) — Entorno de ejecución: versión de Python

- **Fecha:** 2026-08-07
- **Estado:** REEMPLAZADA por «D4 — Entorno: Python 3.12 en entorno virtual dedicado»
  (más abajo). Se conserva por trazabilidad: contiene la evidencia de compatibilidad
  que sustentó la decisión.
- **Decisión propuesta:** Instalar Python 3.12 (o 3.11) para este proyecto y trabajar
  en un entorno virtual dedicado.
- **Motivo:** El único intérprete instalado es **Python 3.7.9** (EOL desde junio de
  2023). Ninguna librería relevante del stack de entity resolution soporta ya 3.7:

  | Paquete | Última versión | Requiere | Última compatible con 3.7 |
  |---|---|---|---|
  | rapidfuzz | 3.14.5 | >=3.10 | ~3.4.0 |
  | scikit-learn | 1.9.0 | >=3.11 | 1.0.2 |
  | scipy | 1.18.0 | >=3.12 | 1.7.3 |
  | anthropic | 0.121.0 | >=3.9 | — no viable |
  | duckdb | 1.5.5 | >=3.10 | 1.3.2 |
  | networkx | 3.6.1 | >=3.11 | 2.6.3 |
  | pyarrow | 25.0.0 | >=3.10 | 12.0.1 |

  Instalado hoy: pandas 1.3.5, numpy 1.21.6, openpyxl, requests. **No hay** librería
  de matching difuso, ni SDK de LLM, ni clustering.

  El bloqueo duro es `anthropic` (>=3.9): D2 no es implementable sobre 3.7.
- **Alternativas consideradas:**
  1. Fijar todo a versiones legacy de 2021-2022 y renunciar al SDK de LLM (rompe D2).
  2. Implementar similitud y blocking en Python puro sobre 305.676 registros
     (inviable en tiempo, y O(n²) sin blocking vectorizado).
- **Impacto si se acepta:** desbloquea D2, permite `rapidfuzz` (C++, órdenes de
  magnitud más rápido) y blocking por TF-IDF de n-gramas con `scikit-learn`, que es
  lo que hace viable D1 a 323k.
- **Reversibilidad:** alta. Instalar 3.12 en paralelo no altera el 3.7 existente ni
  ningún otro proyecto; el entorno virtual queda aislado en la carpeta del proyecto.
- **Pendiente:** confirmación de Javier.

---

## D4 — Entorno: Python 3.12 en entorno virtual dedicado

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE (ejecutada)
- **Decisión:** Se instaló Python 3.12.10 (ARM64) y se creó `.venv` en la carpeta del proyecto.
- **Resultado:** El Python 3.7.9 preexistente queda intacto. Stack instalado: pandas 3.0.5,
  numpy 2.5.1, rapidfuzz 3.14.5, openpyxl 3.1.5, anthropic 0.121.0.
- **Reversible:** sí, borrando `.venv`.

---

## D5 — Sin scipy ni scikit-learn: bloqueo rediseñado sobre índice invertido

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Decisión:** El bloqueo de candidatos se implementa con índice invertido en
  diccionarios de Python + `rapidfuzz`, en lugar de `TfidfVectorizer` + producto de
  matrices dispersas.
- **Motivo:** App Control de Windows bloquea las DLL compiladas de `scipy.stats`, lo que
  arrastra a `scikit-learn`. **No se desactivó App Control**: Smart App Control no se puede
  volver a habilitar sin reinstalar Windows, y no es una decisión que corresponda tomar
  para desbloquear una dependencia.
- **Alternativas consideradas:** desactivar App Control (descartada, irreversible);
  implementar similitud en Python puro (descartada, O(n²) sin blocking vectorizado).
- **Impacto:** ninguno negativo medido. El resultado es **más interpretable**: cada par
  candidato se explica por el token que lo generó, cosa que un coseno de TF-IDF no permite.
  7.387.844 pares evaluados, el 0,024 % del espacio.
- **Evidencia:** `ImportError: DLL load failed while importing _stats: Una directiva de
  Control de aplicaciones bloqueó este archivo.`

---

## D6 — Precisión sobre cobertura en la asignación sectorial

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Decisión:** No se asigna sector sin evidencia del catálogo. Los clústeres sin
  coincidencia quedan con sector vacío y marcados para la fase 7, en lugar de recibir un
  sector por inferencia débil.
- **Motivo:** Riesgo va a usar esta columna para análisis de concentración de cartera.
  Una fila sin sector se ve; una fila con el sector equivocado contamina en silencio.
- **Consecuencias medidas:** cobertura sectorial de 52,8 % sobre empleadores identificados.
  Se descartaron a propósito tokens de alto volumen y sector ambiguo (`CENTRO`, `CASA`,
  `FAMILIA`, `MUNDO`, `GENERAL`) que habrían subido la cobertura sin mejorar la verdad.
- **Corolario aplicado a la banda de duda:** los 15.656 pares cuya similitud cae entre 76 y
  88 no se fusionan ni se descartan; se marcan para validación externa.

---

## D7 — Tres correcciones de calidad encontradas por inspección del maestro

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Contexto:** Tras la primera corrida completa se revisó a mano el top-22 del maestro
  corporativo. Aparecieron tres defectos que las métricas agregadas no mostraban.

| # | Defecto | Causa raíz | Corrección |
|---|---|---|---|
| 1 | `Ministerio de Economia Finanza, S.A.` | El representante elegido traía un `SA` capturado por error | Dos guardas: no se agrega sufijo a entidades institucionales, ni si menos de la mitad de las variantes lo traen |
| 2 | `Copar Airlines` como canónico | La variante con errata era la más larga, y la longitud premiaba el error | El canónico se elige por calidad ortográfica medida con frecuencia documental sobre el propio corpus |
| 3 | Coca-Cola FEMSA clasificada en Enseñanza | La abreviatura `COL -> COLEGIO` disparaba en 2 de 48 variantes | Regla de admisión de abreviaturas: una de 2-3 letras solo entra si no puede ser fragmento de otro nombre. Se excluyeron `COL`, `PAN` y `RP` |

- **Guarda probada y retirada:** se implementó un umbral de respaldo mínimo (20 % de las
  variantes) para aceptar un sector. Medido sobre el corpus rechazaba 62 clústeres y **la
  mayoría eran correctos** (`Constructora Urbana` → Construcción, `Complejo Hospitalario`
  → Salud tienen el token descriptivo en una sola variante porque las demás llegaron
  truncadas). Se retiró y el motivo quedó documentado en `codigo/sector.py` para que no se
  reintroduzca.
- **Lección:** las métricas agregadas no detectan errores de este tipo. La inspección
  manual de la cabeza de la distribución debe ser parte del ciclo, no un extra.

---

## D8 — Separar «falta información» de «pendiente de validación externa»

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Origen:** Javier revisó el dataset y preguntó por qué `Seimo de Costa Rica, S.A.`,
  `Tricom` o `Panama Canal Railways Company` aparecían como no identificables. Tenía razón:
  sí están identificadas.
- **Defecto:** `05_salida.py` escribía `No identificable - Falta informacion` en
  `sector_propuesto` para **todo** clúster sin sección CIIU. Eso mezclaba dos estados que
  no son el mismo:

  | Estado real | Qué se sabe | Etiqueta correcta |
  |---|---|---|
  | El registro no permite identificar empleador | nada | `No identificable - Falta informacion` |
  | Empleador identificado, actividad desconocida | nombre canónico, variantes, RUC potencial | `Pendiente de validación externa` |

  La fase 11 ya distinguía bien los dos casos; la fase 12 los aplanaba al escribir. Era un
  defecto de la capa de salida, no del motor.
- **Agravante:** el enunciado reserva `No identificable - Falta informacion` para «después
  de agotar validaciones». La fase 7 —la validación externa— no se ha ejecutado, así que la
  etiqueta afirmaba algo falso sobre el propio proceso.
- **Corrección:** constante `SECTOR_PENDIENTE` en `reglas.py`; `03` y `05` la comparten.
- **Efecto medido:** `No identificable - Falta informacion` cae de **148.260 a 60**
  registros — los 60 verdaderamente vacíos. Los 148.200 restantes pasan a
  `Pendiente de validación externa`, que es la cola exacta de la fase 7.
- **Huecos de catálogo encontrados en la misma revisión:** tokens ausentes que sí tenían
  sector inequívoco. `ADUANALES` (estaba el singular `ADUANAL`, no el plural),
  `RAILWAY`/`RAILWAYS`/`FERROCARRIL`, `FINANCE` (estaba `FINANCIAL`), `TRUCKING`,
  `PHARMACY`, `CLINIC`, `MINING`, `TEXTILE`, `APPAREL`, `ACADEMY`, `CUSTOMS`.
  Patrón de fondo: **el catálogo tenía sesgo hacia el español y hacia el singular.**
  Cada término admitido pasó la misma regla de admisión de D7 — se descartó `FARM` porque
  puede ser el fragmento de un `FARMACIA` truncado a 30 caracteres.
- **Efecto:** +531 registros con sector CIIU (166.233 → 166.764; 52,78 % → 52,95 % de los
  empleadores). Pequeño en volumen, pero corrige clasificaciones que estaban visiblemente
  mal en la cabeza de la distribución.
- **Lección:** la etiqueta de un dato es parte del dato. Decir «no identificable» de algo
  que sí se identificó le cuesta al analista más que dejar el campo vacío, porque cierra
  la pregunta en falso.

---

## D28 - R13 cerrado, y el metodo deterministico toca su limite

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** sexta iteracion del muestreo. Objetivo: cerrar R13, que D27 dejo abierto.

### R13 cerrado, y una correccion mia

D27 dijo que la propagacion por zona de duda mostraba «10-20 % de destinos dudosos».
Esa cifra salio de leer 40 casos sueltos y **era erronea**.

Al listar los 783 pares completos, ordenados por similitud, la via esta sana:

```
POL JJ VALLARINO         <- POLICLINICA JJ VALLARINO JUAN DIAZ   76
CAJA SEG SOC             <- CJA DE SEGURO SOCIAL                 77
HSBC USA                 <- HSBC BANK USA                        76
COL OCTAVIO CRESPO       <- COLEGIO DANIEL OCTAVIO CRESPO        76
ESTACION DON BOSCO       <- ESTACION SHELL DON BOSCO             85
J COMUNAL PLAYA LEONA    <- JUNTA COMUNAL DE PLAYA LEONA         85
```

Se midio el patron de riesgo concreto —heredar cuando lo unico compartido es un
toponimo— y salieron **3 casos de 783**, los tres correctos (`ALBROOK BOWLIN` de
`BOWLING ALBROOK MALL`, `FUETE CLAYTON` de `ARMY FUERTE CLAYTON`). El unico error
claro de toda la lista fue `PIQUERA DEL VALLE DE URRACA` heredando «enseñanza» de
una escuela del mismo valle; la piquera es la parada de taxis del barrio, y entro al
catalogo como transporte terrestre.

**Leccion sobre el propio metodo:** una muestra de 40 sirve para *encontrar*
candidatos, no para *estimar* una tasa. D27 uso la muestra para las dos cosas y la
segunda salio mal. Enumerar los 783 costo lo mismo que muestrearlos.

### El sufijo societario pegado al nombre

`AMERICAN SPORTSWEARSA`, `PP CONSTRUCCIONESSA`, `PANAMEA DE PLASTICOSSA`. El
capturista se comio el espacio y el token deja de coincidir con nada: ni con el
catalogo ni con la variante bien escrita del mismo empleador.

La guarda es estricta —**solo se separa si lo que queda es una palabra del
catalogo**— porque sin ella el corte es arbitrario. Aun asi quedan tres falsos
positivos aceptados (`FINCASA` es una financiera, no una finca) contra 52 aciertos.

Vale mas por la agrupacion que por el sector: `AMERICAN SPORTSWEARSA` vuelve a ser
el mismo empleador que `AMERICAN SPORTSWEAR S A`, que arrastra 37 registros.

### `TRADE` faltaba por una terminacion

`TRADING` estaba en el catalogo desde el principio. `TRADE` no. 191 registros por
tres letras.

### La señal que D26 anuncio, ya llego

D26 escribio: *«cuando las diez palabras mas frecuentes del residuo sean todas
`CORPORATION` y `EXPRESS`, el metodo determinista habra llegado a su limite»*.

Recontado despues de D27, esto es lo que encabeza la lista de palabras no cubiertas,
ponderada por registros:

```
CORPORATION 1.426   CENTRO 1.363   CENTER 744   EXPRESS 541
LATIN 409   COLOMBIA 366   VENEZUELA 356   FAMILIA 327
CENTRAL 309   LTDA 293   LIMITED 292   STAR 276   WORLD 270
```

**Todas son palabras de fantasia, formas societarias o toponimos. Ninguna nombra una
actividad.** La unica rescatable de las treinta primeras fue `TRADE`.

Esto no es que se acabaran las ideas: es que **el nombre de los empleadores que
quedan no contiene su actividad**. `R P CORPORATION S A` no dice a que se dedica, y
ninguna regla sobre el texto puede saberlo. Hace falta conocimiento del mundo, que es
exactamente lo que la fase 7 compra.

### Efecto medido

| | Antes (D27) | Despues |
|---|---:|---:|
| Con sector CIIU | 195.381 | **195.752** |
| Cobertura sobre empleadores | 63,12 % | **63,24 %** |
| Empleadores únicos (maestro) | 198.750 | **198.690** |

### Balance de las seis tiradas

| Tirada | Enfoque | Registros ganados |
|---|---|---:|
| D23 | Aleatorio uniforme | +1.859 |
| D24 | Aleatorio uniforme, otra semilla | +676 |
| D25 | Cabeza de la cola por volumen | +1.859 |
| D26 | Conteo ponderado de vocabulario | +3.476 |
| D27 | **Auditoria de lo clasificado** | **−933 (correccion)** |
| D28 | Cierre de R13 + residuos | +371 |

**Neto: +7.308 registros con sector y 1.085 clasificaciones falsas retiradas, sin
gastar un dolar.** La cobertura paso de 61,26 % a 63,24 % de los empleadores.

El rendimiento por tirada cayo de 1.859 a 371 en la ultima, con la señal de
vocabulario agotado confirmandolo. **Recomendacion: la siguiente ganancia real ya no
es gratis.**

---

## D27 - Auditar lo clasificado, no solo lo que falta

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** quinta iteracion del muestreo. Las cuatro anteriores buscaron **huecos**
  —registros sin sector—. Esta busco **errores**: muestreo de lo ya clasificado por
  las vias mas debiles, para ver si estaba bien puesto.

### Por que tocaba

Cuatro tiradas seguidas subiendo la cobertura crean un sesgo: se optimiza lo que se
mide, y lo que se medía era el porcentaje con sector. **Un sector equivocado es peor
que un hueco** — el hueco se ve y se manda a la fase 7; el error entra al reporte de
Riesgo como si fuera un dato.

Se muestrearon 40 nombres de cada una de las cuatro vias mas debiles.

### Lo que aparecio: 1.085 registros mal clasificados

| Regla | Registros | Que pasaba |
|---|---:|---|
| `PRODUCTOS` ~ `PRODUCTIONS` al **90 %** | **574** | `PRODUCTOS OCEANOS`, `PRODUCTOS ALIMENTICIOS PASCUAL` y `PRODUCTOS CORQUIVEN` clasificados como **productoras de cine** |
| `SOLUTION` = `SOLUTIONS` | 287 | Palabra de fantasia tratada como giro |
| `SISTEMA` = `SISTEMAS` | 209 | `PROBOILER SISTEMA DE VAPOR` es una caldera, no software |
| `BAKER` = `BAKERS` | 15 | `HAYWARD BAKER` es una constructora de cimentaciones |

**Dos de los cuatro los introduje yo en D26**, la tirada inmediatamente anterior:
`PRODUCTIONS` y `BAKERY` son reglas nuevas de esa decision, y ninguna prueba de humo
las cazo porque el dano no estaba en las palabras que anadi, sino en **lo que se
parecia a ellas**.

El caso de `PRODUCTOS` es el mas instructivo. `PRODUCTOS`(9) contra
`PRODUCTIONS`(11) puntua exactamente 90, que es el umbral. Y `PRODUCTOS` es una de
las palabras mas frecuentes del corpus español —508 registros en el conteo de D22—.
**Una palabra española corrientisima nunca debio entrar a una comparacion difusa con
vocabulario ingles.**

### El nombre del conjunto era parte del defecto

La lista que existe justamente para esto se llamaba `MORFOLOGIA_EXCLUIDA`. Pero
`por_token_aproximado` la consulta **antes de las dos rampas**, la morfologica y la
difusa. Leyendo el nombre, nadie diria que sirve para bloquear una comparacion
difusa; leyendo el codigo, si.

Ese malentendido me costo dos errores: en D26 anadi `PRODUCCION` pensando que solo
tapaba el plural morfologico, y no revise que la misma lista habria evitado el fuzzy
de `PRODUCTOS`.

Renombrada a **`EXCLUIDAS_DEL_APROXIMADO`**, que es lo que hace.

### `SOLUTIONS`, `DIGITAL` y `DATA` bajan a peso 3

No son giros: son palabras que cualquier empresa se pone en el nombre, igual que
`CORPORATION` o `EXPRESS`. Con peso 6 le ganaban a tokens de actividad real. Con 3
solo deciden cuando no hay nada mejor. `SOFTWARE` e `INFORMATICA` suben a 7, que es
donde debian estar: esas si nombran el oficio.

### Dos correcciones sueltas de la misma auditoria

**La Loteria Nacional seguia clasificada como esparcimiento.** Javier lo señalo al
revisar el documento de grandes empleadores, y quedo a medias: se corrigio el
tratamiento general pero la entrada del gazetteer siguio apuntando a R/92. La
Loteria Nacional de Beneficencia es una institucion autonoma del Estado — O/84.

**`PH CONSULTORES S A` y `PH CONTRACTOR INC` no son propiedades horizontales.** Una
PH no se inscribe como sociedad anonima; si el nombre trae sufijo societario, `PH`
son las iniciales de otra cosa.

### Y una compensacion

Sacar `PRODUCTOS` de la comparacion difusa deja sin sector a los que si informaban.
Se recuperan con frases, que se evaluan antes que los tokens: `PRODUCTOS
ALIMENTICIOS` (C/10), `PRODUCTOS QUIMICOS` (C/20), `PRODUCTOS FARMACEUTICOS` (C/21),
`PRODUCTOS DE BELLEZA` (G/47), `PRODUCTOS AGRICOLAS` (A/01). Tambien entro `CRANE`,
que en D24 se anadio solo en español.

### Efecto medido: la cobertura BAJA, y eso es la mejora

| | Antes (D26) | Despues |
|---|---:|---:|
| Con sector CIIU | 196.314 | **195.381** |
| Cobertura sobre empleadores | 63,42 % | **63,12 %** |
| Clasificaciones falsas retiradas | — | **1.085** |
| Recuperadas con las frases nuevas | — | ~152 |

**Es la primera decision del proyecto que empeora la metrica principal a proposito.**

Vale la pena dejarlo escrito: durante cuatro tiradas la cobertura subio 6.860
registros y nadie estaba comprobando que esos registros estuvieran bien. Una racha
de mejoras en una sola metrica es exactamente el momento en que conviene auditar,
no el momento de acelerar.

### Lo que queda pendiente

`propagacion_duda` (783 registros) mostro en la muestra un 10-20 % de destinos
dudosos: `BEST QUALITY CRANE` heredando «agencias de viajes», `COLGATE PALMOLIVE`
como comercio minorista en lugar de manufactura, `OFICINA PROPIA` como agricultura.
Es la via mas debil que queda y merece su propia revision — anotado como **R13**.

---

## D26 - El catalogo estaba escrito en español y media plaza trabaja en ingles

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** cuarta iteracion del muestreo. Esta vez, en lugar de leer nombres al
  azar, se conto el vocabulario del residuo **ponderado por registros arrastrados**.

### El hueco estructural

Panama es plaza de servicios internacionales y una parte grande del residuo tiene el
nombre en ingles. El catalogo CIIU de `reglas.py` se escribio casi todo en español,
asi que `CLEAN`, `DESIGN`, `BAKERY`, `NAILS` o `GRAPHICS` no clasificaban nada.

No es un olvido puntual: es un **sesgo de idioma** en la base de conocimiento, y por
eso vale mas que las correcciones anteriores. Mide 3.058 registros.

### Lo que NO entro, y por que importa

El vocabulario ingles mas frecuente del residuo no dice actividad:

```
CORPORATION  1.445    CENTER  788    EXPRESS  557    STAR  289
WORLD          284    STUDIO  243    PLUS     184    LAND  161
```

Son palabras de fantasia, como `PANAMA` o `INTERNATIONAL`. Meterlas habria inflado
la cobertura con clasificaciones falsas. **La medicion mas util de esta tirada fue
descubrir cuanto del residuo es intrinsecamente inclasificable por reglas**: la
cabeza de la lista de frecuencias no contiene giros, contiene marcas.

Solo entro lo que nombra un oficio:

| Regla | Registros | Sección |
|---|---:|---|
| `DESIGN` / `DESING` / `DISENO` | 397 | M/74 |
| `PRODUCCIONES` / `PRODUCTIONS` | 336 | J/59 |
| `STUDIO` | 260 | M/74, peso 4 |
| `NAILS` / `MANICURE` | 251 | S/96 |
| `METALES` / `SOLDADURA` | 219 | C/25 |
| `GRAPHICS` / `PRINTING` | 194 | C/18 |
| `IMPORTACIONES` / `EXPORTACIONES` | 192 | G/46 |
| `EVENTOS` / `EVENTS` | 191 | N/82 |
| `CLEAN` / `CLEANING` / `JANITORIAL` | 156 | N/81 |
| `HEALTH` / `CHIROPRACTIC` | 156 | Q/86 |
| `COFFEE HOUSE` vs `COFFEE ROASTERS` | 136 | I/56 vs C/10 |
| `CARS` / `RENT A CAR` | 130 | G/45 |
| `BAKERY` / `PASTRY` | 84 | C/10 |
| `ADVISORS` / `ADVISORY` | 68 | M/70 |
| `DAY CARE` / `GUARDERIA` | 21 | P/85 |

`LABORATORIO` a secas se dejo fuera otra vez: `LABORATORIO DE INYECCION DIESEL` es
un taller, `LABORATORIO CLINICO` es salud y `LABORATORIOS X` suele ser farmaceutica.
Entran solo las formas que desambiguan.

### Tres errores que la prueba de humo atajo

Se probaron 28 casos antes de correr el pipeline. Tres fallaron:

**1. `PRODUCCION PANAMENA DE HIELO` clasificada como cine.** La regla nueva era
`PRODUCCIONES` en plural —que es como se llama una productora audiovisual— y
deliberadamente dejaba fuera el singular. Pero el **rescate morfologico** de D11 lo
devolvia por detras: para esa capa, singular y plural son la misma palabra.

Es el defecto mas instructivo de la tanda. **Una exclusion deliberada en el catalogo
hay que repetirla en `MORFOLOGIA_EXCLUIDA`, o la capa de abajo la deshace.** Ya habia
pasado con `LABORATORIO` en D11; volvio a pasar quince decisiones despues porque la
relacion entre las dos listas no es evidente al leer ninguna de las dos.

**2. `PANAMONTE INN AND SPA` clasificado como salon de belleza.** `SPA` y el
alojamiento pesaban igual y gano el que se evaluo primero. Un hotel con spa es un
hotel: lo resuelve la frase, que se evalua antes que los tokens.

**3. `PANAMA METAL RECYCLING` como metalmecanica.** El reciclaje de chatarra es
gestion de desechos (E/38), no fabricacion de productos de metal.

### Efecto medido

| | Antes (D25) | Despues |
|---|---:|---:|
| Con sector CIIU | 192.838 | **196.314** |
| Cobertura sobre empleadores | 62,30 % | **63,42 %** |
| Empleador sin sector | 122.694 | **119.299** |
| Clusteres en la cola de la fase 7 | 87.162 | **84.437** |

Es el mayor salto de las cuatro tiradas: **+3.476 registros**.

### Lo que llevan las cuatro tiradas

| | Antes de D23 | Ahora |
|---|---:|---:|
| Con sector CIIU | 189.454 | **196.314** |
| Cobertura sobre empleadores | 61,26 % | **63,42 %** |
| No identificable | 2.074 | **1.774** |
| Clusteres a consultar | 89.9xx | **84.437** |

**+6.860 registros con sector, sin gastar un dolar.** Y 2.725 clusteres menos en la
cola de la fase 7, que son consultas que ya no se pagan.

### Lo que dice sobre cuando parar

Las cuatro tiradas rindieron 1.859, 676, 1.859 y 3.476 registros. No hay señal de
agotamiento todavia, pero el conteo ponderado de esta tirada da el aviso: la cabeza
de la lista de palabras no cubiertas ya son marcas, no giros. Cuando las diez
palabras mas frecuentes del residuo sean todas `CORPORATION` y `EXPRESS`, el metodo
determinista habra llegado a su limite y lo que quede sera, por definicion, trabajo
para la fase 7.

---

## D25 - Mirar la cabeza de la cola, no el residuo entero

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** tercera iteracion del muestreo aleatorio, reenfocada tras medir la cola
  de la fase 7 para responder una pregunta de Javier sobre el costo.

### El cambio de foco

Las dos tiradas anteriores muestrearon **uniformemente** sobre nombres distintos. Al
medir la cola de la fase 7 para estimar el costo salio un dato que cambia el metodo:

| Tamaño del cluster | Clusteres | Registros | Acumulado |
|---|---:|---:|---:|
| 21+ registros | 33 | 846 | 0,7 % |
| 6-20 | 957 | 7.859 | 7,0 % |
| 3-5 | 6.652 | 22.799 | 25,3 % |
| 2 | 13.342 | 26.684 | **46,8 %** |
| 1 | 66.178 | 66.178 | 100 % |

El muestreo uniforme cae casi siempre en la ultima fila: 66.178 de 87.162 clusteres
son de un solo registro. Se estaba mirando el 53 % que menos importa.

Ordenando los clusteres **por registros que arrastran** aparece otro mundo. No hay
marcas raras de un registro: hay empresas grandes cuya actividad el catalogo no
nombraba.

### Lo que estaba en la cabeza de la cola

```
41  FRANQUICIAS PANAMENAS      37  AMERICAN SPORTSWEAR      35  STAR CONTACT
32  MAERSK LINE CENTRAL AM     29  ADIDAS LATIN AMERICA     29  AXA ASSISTANCE
27  H T TZANETATOS             24  VARELA HERMANOS          23  ERNST AND YOUNG
23  MOSSACK FONSECA            22  ALEMAN CORDERO Y GALINDO LEE
21  ICAZA GONZALEZ RUIZ Y ALEMAN                19  PATTON MORENO Y ASVAT
```

Tres familias, todas medidas contra el residuo antes de escribir una linea:

**1. Multinacionales que faltaban en el gazetteer** (~500 registros). `MAERSK` solo
aparece en 38 clusteres distintos con 163 registros, escrito de todas las formas
posibles: `MAERSK LINE`, `MAERKS`, `SEALAND MAERKS`, `DAMCO MAERSK`.

**2. Casas comerciales y familias empresarias panameñas** (~230 registros). Varela
Hermanos, Felipe Motta, Tagaropulos, Cochez, Cardoze y Lindo, H. Tzanetatos, Editora
El Panama America. Son nombres propios: sin conocimiento del pais no hay forma de
saber que Varela Hermanos hace ron y Cochez vende ferreteria.

**3. Bufetes de abogados** (~150 registros). Panama es plaza de servicios legales y
sus firmas se nombran con los apellidos de los socios —`ALEMAN CORDERO Y GALINDO
LEE`, `ICAZA GONZALEZ RUIZ Y ALEMAN`, `PATTON MORENO Y ASVAT`— **sin ninguna palabra
que diga a que se dedican**. Por eso ninguno tenia sector.

Se resistio la tentacion de escribir una regla del tipo «dos apellidos unidos por Y
es un bufete»: `CARDOZE Y LINDO` distribuye alimentos, `COCHEZ Y CIA` vende
ferreteria y `VARELA HERMANOS` hace ron. El patron existe pero no discrimina. Cada
bufete entra por nombre, y siempre con **dos** apellidos: `ALEMAN` o `ARIAS` sueltos
son apellidos corrientes en Panama (la leccion de D15).

### Vocabulario que el catalogo no tenia

| Regla | Registros | Nota |
|---|---:|---|
| `EDITORA` / `IMPRESORA` / `LITOGRAFIA` | 183 | Edicion (J/58) e impresion (C/18) |
| `CALL CENTER` / `TELEMARKETING` / `BPO` | 140 | Panama es plaza de call centers |
| `SPORTSWEAR` / `T SHIRTS` / `MAQUILA` | 90 | Confeccion (C/14) |
| `HELADOS` / `HELADERIA` | 67 | |
| `EMPAQUES` / `ENVASES` | 66 | |
| `EMPENO` | 49 | Credito prendario (K/64), no comercio |
| `STEAMSHIP` | 37 | |
| `RAMA JUDICIAL` / `PALACIO LEGISLATIVO` / `CONTRALORIA` | 32 | Organos del Estado que no son ministerio |
| `MOLINO` / `HARINAS` | 27 | |
| `MONTACARGAS` / `FORKLIFT` | 27 | |

### Un fallo de robustez que ya iba por la tercera vez

La corrida murio con `PermissionError` al escribir `dataset_resultado.xlsx`, que
estaba abierto en Excel. Y murio **despues** de haber hecho todo el trabajo: los CSV
ya escritos, los KPIs sin escribir y el resumen sin imprimir.

Habia pasado tres veces durante el ciclo de revision, siempre por la misma razon —
tener el entregable abierto para mirarlo, que es exactamente lo que se espera que
haga quien revisa.

Un archivo bloqueado es un **aviso**, no un fallo del pipeline. `guardar_excel()`
captura el error, lo registra y sigue; al final el resumen dice cuales quedaron sin
regenerar y que los CSV si estan al dia.

### Efecto medido

| | Antes (D24) | Despues |
|---|---:|---:|
| Con sector CIIU | 190.979 | **192.838** |
| Cobertura sobre empleadores | 61,70 % | **62,30 %** |
| Empleador sin sector | 124.546 | **122.694** |
| Empleadores identificados | 309.551 | **309.552** |

### La leccion del metodo

Ordenar por volumen no es lo mismo que muestrear al azar, y ninguna de las dos
sustituye a la otra:

| Vista | Encuentra | Coste de encontrarlo |
|---|---|---|
| Aleatoria uniforme | El patron sin palabra (`M S`, `REFRICAR`) | Cae en la cola larga: mucho ruido |
| **Cabeza de la cola** | **La empresa grande que nadie nombro** | **Directa: 90 lineas cubren 1.859 registros** |

Y hay un argumento economico: la cabeza de la cola es exactamente lo que la fase 7
consultaria primero, porque el presupuesto se ordena por registros. Cada empresa
resuelta aqui es una consulta que no se paga.

---

## D24 - Segunda tirada aleatoria: el giro pegado al nombre

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** segunda iteracion del muestreo aleatorio que estreno D23, con semilla
  distinta sobre el residuo ya reprocesado.

### Una hipotesis propia, descartada por la evidencia

La idea de entrada era: **si el gazetteer reconoce la entidad, el gazetteer deberia
vencer a la tipificacion de direccion.** `BANISTMO AVE PERU` es el banco con su
sucursal, no una avenida.

Al medirla, 36 registros tipificados como direccion contenian una clave del gazetteer.
Y al leerlos, la mitad eran falsos positivos **del gazetteer**, no de la direccion:

```
VIA TOCUMEN                      -> Aeropuerto Internacional de Tocumen
PLAZA TOCUMEN                    -> Aeropuerto Internacional de Tocumen
BOULEVARD DE ACCESO AEROPUERTO   -> Aeropuerto Internacional de Tocumen
```

Tocumen es a la vez el aeropuerto, un corregimiento y una via principal. Aplicar la
regla tal cual habria empeorado el resultado.

`TOCUMEN` sale del gazetteer como clave suelta —queda `AEROPUERTO TOCUMEN`— por el
mismo motivo por el que salieron `ARROCHA` y `RICARDO PEREZ` en D15: **el toponimo o
el apellido solo no identifican a la entidad**. Con eso hecho, la guarda si se pudo
activar, y ahora `BANISTMO AVE PERU`, `RIBA SMITH TRANSISTMICA`, `CAJA DE AHORROS VIA
ESPANA` y `CREDICORP BANK CALLE 50` son empleadores.

**El orden importaba: la regla nueva era correcta, pero no se podia activar sin
arreglar antes el dato que consultaba.**

### `INTERAMERICANA` era token *fuerte* de direccion

58 registros iban a «no identificable» por esa palabra. Al leerlos, casi ninguno es la
carretera:

```
UNV INTERAMERICANA          UNIVERCUDAD INTERAMERICANA 5      U INTERAMERICANA 6
T SHIRTS INTERAMERICANA     COMISION INTERAMERICANA DE ATUN TROPICAL
SOC INTERAMERICANA DE AGUAS AUTO CENTRO INTERAMERICANA
```

Es la Universidad Interamericana, la comision del atun y un puñado de empresas. La via
se escribe `AV INTERAMERICANA`, y ahi el `AV` fuerte ya hace el trabajo. Baja a debil.

Tercera vez que aparece el mismo patron de D10: una palabra que dos categorias se
disputan, con el ganador elegido implicitamente y mal.

### El giro pegado al nombre: un mecanismo nuevo

El comercio panameño bautiza los negocios pegando el giro delante del nombre:

```
REFRICAR   REFRIAIRE   REFRIHOGAR   REFRITODO   REFRIPARTES
REFRICENTRO   REFRIAUTO   REFRITEC   REFRIGAS   REFRIVIALCA
```

136 registros sin sector, y ninguno coincide con un token del catalogo porque **el giro
no llega a ser una palabra**: es una silaba pegada a otra cosa. Ni el token exacto ni
el parecido ortografico lo alcanzan — `REFRICAR` no se parece a `REFRIGERACION`.

Se añadio `PREFIJOS_CIIU` y un nivel nuevo en la cascada, `por_prefijo_comercial`,
entre el token exacto y el aproximado. Vota con peso 4: mas que un parecido
ortografico, menos que una palabra del catalogo. El prefijo esta escrito bien; lo que
le falta es ser una palabra suelta.

Solo entran prefijos **inequivocos**. `REFRI` unicamente puede ser refrigeracion.
`SERVI`, `MULTI` y `DISTRI` se dejaron fuera a proposito: `SERVIPAR` es un
estacionamiento y `MULTIBANK` es un banco — el prefijo no dice de que van.

Y va a F/43, no a S/95, porque `REFRIGERACION` ya estaba en el catalogo como
instalacion especializada. Partir la familia en dos secciones habria sido incoherente
con la regla que ya existia.

### Vocabulario: la gasolinera panameña

455 registros traian `ESTACION` o `SERVICENTRO` y se quedaban sin sector.
`SERVICENTRO` —que es como se llama la gasolinera en Panama— no estaba en el catalogo.

`ESTACION` sola no basta: hay estacion de bus, de policia, y `GRAN ESTACION` es un
centro comercial. Se resolvio con frases (`ESTACION TEXACO`, `ESTACION SHELL`,
`ESTACION DE COMBUSTIBLE`) mas las marcas sueltas, que se evaluan antes que los tokens.

Tambien entraron `GRUAS`, `PARKING` y `ESTACIONAMIENTO` (125 registros, H/52) y
`AUTOREPUESTO` (G/45).

### Efecto medido

| | Antes (D23) | Despues |
|---|---:|---:|
| Con sector CIIU | 190.303 | **190.979** |
| Cobertura sobre empleadores | 61,49 % | **61,70 %** |
| No identificable | 1.849 | **1.774** |
| Empleador sin sector | 125.140 | **124.546** |
| Empleadores identificados | 309.476 | **309.551** |

### Lo que llevan dos tiradas aleatorias

D23 y D24 juntas: **+1.525 registros con sector, −300 no identificables**, y dos
mecanismos nuevos que no existian (siglas partidas al inicio, prefijos comerciales).

El muestreo aleatorio encuentra lo que no se puede buscar porque no se sabe que existe.
`M S` son dos letras sueltas; `REFRICAR` no se parece a ninguna palabra del catalogo.
Ningun conteo de frecuencias ni ninguna lectura alfabetica los habria sacado.

---

## D23 - Muestreo aleatorio: lo que el conteo por frecuencia no ensena

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** *«busca aleatoriamente nombres que puedan dar informacion y mejorar
  nuestro trabajo, agotemos todos los recursos antes de empezar a generar costos»*.

### Una tercera forma de mirar el residuo

Hasta aqui el residuo se habia revisado de dos maneras: **por volumen** (D5-D17), que
muestra los errores caros, y **alfabeticamente** (D18-D22), que agrupa las familias.
El muestreo aleatorio es la tercera, y encuentra lo que las otras dos no pueden:
patrones frecuentes que ninguna palabra delata y que estan repartidos por todo el
alfabeto.

220 nombres al azar -160 del bloque sin sector, 60 del no identificable- produjeron
seis hipotesis. Las seis se verificaron contra el corpus antes de escribir una linea.

### 1. `M S` al inicio es «Mini Super» — 463 registros

El hallazgo grande, y ninguna de las dos vistas anteriores lo habria encontrado: `M S`
son dos tokens de una letra, invisibles en cualquier conteo de palabras. Leidos juntos
no dejan duda:

```
M S CHEN LOU 7      M S SAN SEBASTIAN     M S RIO RITA
M S QUING LEE       M S EL CRISOL         M S AGUA BENDITA
```

Apellido chino o nombre de santo: es exactamente como se llama la abarroteria de barrio
en Panama. Entra a `SIGLAS_SEPARADAS` junto a `P H` y `C S S`, y solo al inicio del
nombre — en medio, `M S` puede ser las iniciales de una persona.

Es la **tercera** sigla partida que aparece. El origen escribe las siglas con las
letras sueltas y eso ya no es una anecdota: es una caracteristica del campo.

### 2. `FINCA` no es una direccion — 212 registros

`FINCA` estaba en los tokens debiles de direccion y mandaba a «no identificable» cosas
como `FINCA LA CEIBA`, `FINCA LOS LIMONES`, `FINCA EL MACHO`. Pero en Panama la finca
no es una referencia de ubicacion: es la unidad productiva, y su actividad es la
agricultura. Sale de los tokens de direccion y se queda solo como token agricola,
donde ya estaba con peso 8.

Es otra vez el patron de D10: una palabra que dos categorias se disputan, con el
ganador elegido implicitamente y mal.

### 3. `PLANILLA` es como se paga, no para quien se trabaja — 62 registros

`PLANILLA MAERSK`, `PLANILLA KRAFT`, `PLANILLA LOCKHEED MARTIN`. La planilla es la
nomina; el empleador viene detras. Entra a un conjunto nuevo, `PALABRAS_ADMINISTRATIVAS`,
que `quitar_calificadores` retira igual que retira los cargos. Beneficio secundario:
esos 62 registros se unen con los que nombran la empresa a secas.

### 4, 5 y 6. Vocabulario que faltaba

- **`KIOSKO` con K** — la regla solo tenia `KIOSCO` con C, y el corpus escribe la otra.
  Con `MESON` y `RINCONCITO`, 104 registros de comida.
- **`OBISPADO` y `CASA CURAL`** — la sede del obispo y la casa del parroco son
  empleadores reales. `CASA CURAL` ademas caia como direccion, porque `CASA` cuenta
  como indicio de inmueble; se anadio `_GIROS_TRAS_CASA` para los giros que se
  escriben sin articulo en medio.
- **`UNIVERSIDA` y `MINISTERI`** truncados, a `RAICES_TRUNCADAS`.

### Un experimento que salio mal, y por que se revirtio

`UNIVERSIDA` y `MINISTERI` son truncaciones que el corrector de erratas de D22 no
coge, porque su guarda rechaza que un token sea prefijo del otro. La tentacion era
relajarla: aceptar el prefijo cuando el token es el **mas corto**, que es la forma que
tiene una truncacion.

Se probo en seco. El resultado:

| | Antes | Con la guarda relajada |
|---|---:|---:|
| Sustituciones | 2.266 | 3.000+ |
| `CONSULTOR -> CONSULTORIO` | bloqueada | **reabierta, 128 registros** |
| `PROYECTO -> PROYECTOS` | bloqueada | reabierta, 296 |
| `REPUESTO -> REPUESTOS` | bloqueada | reabierta, 223 |

Ganaba 52 registros y perdia mas de 1.200 en ruido, con un error de sector de por
medio. Revertido.

**La leccion: una guarda que funciona no se afloja para cubrir un caso que se puede
enumerar.** `RAICES_TRUNCADAS` tiene ahora seis entradas y resuelve el problema sin
tocar nada que ya estuviera bien.

### Efecto medido

| | Antes (D22) | Despues |
|---|---:|---:|
| Con sector CIIU | 189.454 | **190.303** |
| Cobertura sobre empleadores | 61,26 % | **61,49 %** |
| No identificable | 2.074 | **1.849** |
| Empleador sin sector | 125.758 | **125.140** |
| Empleadores identificados | 309.251 | **309.476** |

### Lo que esto dice del metodo

Tres vistas del mismo residuo, tres tipos de hallazgo distintos:

| Vista | Encuentra | Ejemplo |
|---|---|---|
| Por volumen | El error caro | `INSTITUTO` con peso 9 (D14) |
| Alfabetica | La familia | `AMA DE CASA*`, `ABOGAD*` (D18-D20) |
| **Aleatoria** | **El patron sin palabra** | **`M S` = Mini Super** |

Un ciclo de mantenimiento serio deberia usar las tres. La aleatoria es la unica que
encuentra lo que no se puede buscar porque no se sabe que existe.

---

## D22 - Lo que se encuentra en el bloque chico casi siempre paga en el grande

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** *«lo que quiero ver es que aun en eso que declaras como no identificable
  yo logro identificar algo que tambien se aplique a lo que categorizas como validacion
  externa pendiente»*.

### La hipotesis, y como se midio

Javier venia revisando 2.074 registros «no identificables» y sospechaba que lo que
encontrara ahi valia tambien para los 125.758 sin sector. Se midio cruzando el
vocabulario de los tres bloques sin resolver. Tenia razon, y por un margen grande:

| Familia | Sin sector | No identif. | Sit. laboral |
|---|---:|---:|---:|
| `CASA DE FAMILIA` / `DOMESTICA` | 270 | 1 | 5 |
| `JUBILAD*` / `PENSION*` truncado | 213 | 0 | 2.333 |
| `DEPENDIENTE DE ...` | 184 | 0 | 331 |
| `AUTORIDAD DEL CANAL` y erratas | 107 | 0 | 53 |
| `DUTY FREE` | 78 | 0 | 0 |
| `C S S` con las letras sueltas | 58 | 1 | 192 |

Cada una se veia primero en el bloque de 2.000 -donde se lee entero en una tarde- y
vivia despues en el de 125.000, donde nadie la habria encontrado leyendo.

**El bloque chico no es el problema: es el microscopio.**

### Cinco correcciones

**1. `C S S` -> `CSS`.** Caja de Seguro Social escrita letra por letra, 56 registros.
Es exactamente el defecto de `P H` que corrigio D12 - el mismo patron, diez decisiones
despues. `IN DEPENDIENTE` entro a la misma lista: es `INDEPENDIENTE` partido, no un
dependiente economico, y el orden de las reglas importa para no invertirlo.

**2. Seccion T de la CIIU, que estaba desaprovechada.** `CASA DE FAMILIA MARTINELLI`
si declara un empleador: el hogar. La CIIU tiene la seccion T justamente para eso y
solo la alcanzaban las frases largas (`EMPLEADA DOMESTICA`). Con `CASA DE FAMILIA`,
`CASA FAMILIAR` y `DOMESTICA` sueltos pasa de 37 a 298 registros.

**3. `DUTY FREE` -> comercio al por menor.** 101 nombres distintos de la Zona Libre y
el aeropuerto, ninguno con otra palabra de actividad.

**4. Anotaciones por prefijo.** El dependiente economico se escribe de 184 formas
(`DEPENDIENTE DE SU ESPOSA`, `DEPENDIENTE ECONIMICO DE UN TE`, `DEPENDIENTE ECOMONICO`)
y ninguna coincidia con una frase completa, asi que los 184 entraban al maestro como
empresas. Lo estable no es la frase entera: es como **empieza** el registro.

**5. La truncacion del origen, atacada por la raiz.** El campo viene cortado a 30
caracteres, asi que las palabras largas llegan sin final: `INDEPENDIENT`, `JUBILADS`,
`JUBILADACSS`. Enumerar variantes no escala; enumerar la **raiz** si, porque la
truncacion corta siempre por el mismo lado.

### El corrector de erratas, que es lo que de verdad cambio las cifras

Midiendo la distancia entre tokens raros y palabras institucionales frecuentes
aparecieron **1.022 variantes mal escritas de 19 palabras, en 3.298 registros**:

```
CONSTRUCTURA - COSNTRUCTORA - CONSTRUTORA - COSTRUCTORA - CONTRUCTOR
MINSTERIO - MINITERIO - MINISTERI - MINSITERIO - MINISTERO
INDEPENDIETE - IDEPENDIENTE - INDEPNDIENTE - INDENDIENTE - INDEPENDINETE
```

Enumerarlas seria una lista muerta: la 1.023 llega con el proximo lote. Lo que se
enumera es el **destino**, y ni siquiera a mano - las dianas salen de la base de
conocimiento que ya existia (tokens CIIU de peso >=7 y marcadores de situacion). No
hay lista de erratas en ninguna parte del codigo.

Se aplica en la limpieza, arriba de todo, para que las tres capas de abajo
-tipificacion, situacion laboral y sector- lo vean ya resuelto. Efecto secundario
mas valioso que el buscado: las 47 formas de `CONSTRUCTORA` dejan de ser 47 claves
distintas y el maestro se consolida.

### Cuatro guardas, dos de ellas obligatorias

La primera version se probo **en seco** contra el corpus antes de tocar el pipeline.
Menos mal:

| Sustitucion propuesta | Registros | Por que esta mal |
|---|---:|---|
| `DEPENDIENTE` -> `INDEPENDIENTE` | 531 | Son **opuestos**. El que vive de otro convertido en trabajador por cuenta propia |
| `CONSULTOR` -> `CONSULTORIO` | 128 | El consultor asesora empresas (M/70); el consultorio atiende pacientes (Q/86) |
| `CASTILLERO` -> `ASTILLERO` | 42 | Castillero es un apellido panameno corriente |
| `COMERCIAL` -> `COMERCIALES` | 1.045 | Un plural no es una errata |

Las guardas que quedaron: token de 8+ caracteres, token que ninguna regla reconozca ya,
umbral 90 -a 85 entra `DEPEDIENTE -> INDEPENDIENTE`-, y **ninguno de los dos puede ser
prefijo ni sufijo del otro**. Esa ultima sola evita 2.100 sustituciones.

**La leccion: una correccion difusa se prueba en seco y se lee la cola, no la cabeza.**
Los 40 casos mas frecuentes se veian todos bien. Los cuatro errores estaban entre ellos
y en la muestra aleatoria de la cola larga.

### Una hoja nueva en el archivo de revision

`revision_pendiente.xlsx` estrena la hoja **`vocabulario`**: cada palabra con su conteo
en los tres bloques, lado a lado. Revisar alfabeticamente encuentra las familias pero
no dice cuanto pesa cada hallazgo; esta hoja lo dice antes de escribir la regla.

### Efecto medido

| | Antes | Despues |
|---|---:|---:|
| Con sector CIIU | 188.951 | **189.454** |
| Cobertura sobre empleadores | 60,76 % | **61,26 %** |
| Empleadores unicos (maestro) | 200.613 | **198.687** |
| Consolidacion | 35,5 % | **35,8 %** |
| Seccion T (hogares empleadores) | 37 | **298** |

Y una cifra que **baja**: empleadores identificados, de 310.999 a 309.251. No es una
regresion, es lo contrario: 1.748 registros que se contaban como empresas eran
dependientes economicos, jubilados e independientes con la palabra truncada. La tasa
de identificacion baja de 96,28 % a 95,74 % porque antes estaba inflada.

---

## D21 — Corrección de D20: el archivo de revisión filtraba al revés

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** *«yo no estaba revisando "pendiente validación externa", estaba revisando lo
  que quedó como no identificable, y leía el campo nombre original»*.

### El error

`revision_sin_sector.xlsx` filtraba `tipo in TIPOS_EMPLEADOR and not seccion_ciiu`: es
decir, **exactamente el bloque contrario** al que Javier estaba revisando. Le entregué una
herramienta para un problema que no era el suyo, en la misma iteración en la que escribí
que había que mirar lo que la persona está mirando.

Sustituido por `salidas/revision_pendiente.xlsx`, que trae **todo lo no resuelto** con una
columna `bloque` para filtrar:

| Bloque | Filas | Qué es |
|---|---:|---|
| Empleador sin sector | 127.188 | Identificado, falta la actividad → fase 7 |
| Situación laboral | 9.076 | Independiente, jubilado, ama de casa, estudiante |
| No identificable | 3.013 | Direcciones, cadenas vacías, anotaciones |

Un registro se considera resuelto solo si es un empleador identificado **y** tiene sector.
Todo lo demás entra al archivo. Ordenado alfabéticamente por `nombre_original`.

### Categorías para las anotaciones del sistema

D20 dio etiqueta a las situaciones laborales pero dejó las anotaciones en el cajón
genérico. Se completaron: `Cliente fallecido` (559), `Dependiente económico` (195),
`Menor de edad` (90), `Cuenta cerrada o cancelada`.

**«No identificable - No es un empleador» pasó de 1.260 a 3 registros.**

### Una regresión que yo mismo causé

`MINISUPER PARQUE EL EMPALME` había vuelto a clasificarse como dirección.

La causa: en D14 bajé el peso de `SUPER` de 8 a 3 por el falso positivo `SUPER SERVICE`.
Pero la guarda de D10 —«manda el token que aparece primero, si es de actividad y pesa 7 o
más»— dejó de reconocer a `SUPER` como token de actividad, y `PARQUE` volvió a ganar.

`SUPER` vuelve a peso 7. El falso positivo que motivó bajarlo ya lo ataja la frase
`SUPER SERVICE`, que se evalúa antes que los tokens. Se añadieron además `MINISUPER`,
`MINISUPERMERCADO` y `SUPERETTE` explícitamente.

**Es literalmente la lección que escribí en D14** —«bajar un peso libera las disputas que
ese token venía ganando»— y no la apliqué a las guardas de tipificación, solo a las de
sector. Una regla de peso no vive solo en el clasificador sectorial: otras partes del
motor la consultan como umbral.

### Estado tras la corrección

| | Antes de D20 | Ahora |
|---|---:|---:|
| Categorías distintas para no-empleadores | 2 | **11** |
| «No identificable - No es un empleador» | 4.346 | **3** |
| Direcciones | 1.916 | 1.829 |
| Con sector CIIU | 188.300 | **188.951 · 60,76 %** |

---

## D20 — Cada situación laboral es una categoría, no «no identificable»

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** Javier revisó de nuevo el tramo A-B y dijo: *«veo los mismos de antes sin
  identificar; independiente y ama de casa siguen quedando por fuera»*. Tenía razón, y el
  problema no era el que yo había estado arreglando.

### El defecto real

D18 y D19 recuperaron el **sector** de estos registros. Pero el `nombre_propuesto` —la
columna que se lee al revisar— seguía siendo la misma para todos:

```
4.346 registros  ->  «No identificable - No es un empleador»
```

Ama de casa, jubilado, estudiante, desempleado y anotaciones del sistema, todos en el mismo
cajón. Al ordenar el archivo por `nombre_original` la lista se veía **exactamente igual que
antes de empezar**, porque la columna de resultado no distinguía nada.

**Es el error de D8 otra vez, y a mayor escala:** llamar «no identificable» a algo que está
perfectamente identificado. Un ama de casa no es un dato ilegible; es una situación laboral
concreta que el texto declara sin ambigüedad.

### La corrección

Cada situación tiene su etiqueta canónica, resuelta por `reglas.categoria_situacion()`:

| Categoría | Registros | Ejemplos de entrada |
|---|---:|---|
| Trabajador independiente | 5.577 | `ABOGADA INDEPENDIENTE`, `ADCOAST INDEPENDIENTE` |
| Jubilado o pensionado | 2.386 | `CSS JUBILADO`, `ABOGADA RETIRADA`, `ACP JUBILADO` |
| Estudiante | 496 | `ESTUDIANTE DE UNIVERSIDAD INTERAMERICANA` |
| Ama de casa | 285 | `AMA DE CASA`, `ADMON DEL HOGAR`, `LABORES DEL HOGAR` |
| Desempleado | 203 | `ACTUALMENTE NO LABORA`, `QUEDO CESANTE` |
| Ocupación declarada sin empleador | 129 | `ASISTENTE`, `ADMINISTRADOR` |
| No identificable - No es un empleador | 847 | anotaciones del sistema sin situación declarada |

El orden de evaluación importa: `AMA DE CASA ACTUALMENTE NO TRABAJA` es un ama de casa, no
una desempleada. Lo más específico se evalúa primero.

Además `OCUPACION` entró a `SECTOR_RECUPERABLE`: `AGRICULTOR` a secas es tipo ocupación,
pero su sector es agricultura y no había razón para perderlo.

### Vocabulario nuevo del tramo A-B

`ARTESANO`, `ARTISTA`, `ASEADORA`, `ASERRADOR`, `BILLETERO`, `BIOLOGO`, `AGRONOMO`,
`AGROVETERINARIA`, `AGROEXPORTADOR`, `CUIDA NINOS`, `ASADOS Y FRITURAS`. Estrenan tres
secciones que no se usaban: **R/90 actividades creativas**, **M/75 veterinarias** y
**Q/87 atención en instituciones**.

### Un archivo para el ciclo de revisión

Se añadió `salidas/revision_sin_sector.xlsx`: los registros sin sector, **ordenados
alfabéticamente**, con filtros y encabezado fijo. Es la vista que produjo D18, D19 y D20.

Ordenar por volumen muestra los errores caros; ordenar alfabéticamente agrupa las
**familias** —`ABOGAD*`, `ADMINISTRADOR*`, `AMA DE CASA*`— y ahí se ve el patrón que la
frecuencia esconde. El ciclo de mantenimiento debería usar las dos vistas.

### Lección

Estuve tres iteraciones mejorando el **sector** de estos registros mientras la columna que
Javier estaba leyendo no cambiaba. La métrica subía y la experiencia de revisión seguía
idéntica.

**Cuando alguien dice «esto sigue igual» después de un cambio medido, la respuesta correcta
no es mostrarle la métrica: es mirar exactamente lo que está mirando.**

---

## D19 — El jubilado nombra a su empleador, y el estudiante a su universidad

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** segundo tramo alfabético revisado por Javier. La letra A bastó para
  encontrar dos familias más.

### La generalización de D18

D18 recuperó el sector del trabajador independiente a partir de su oficio. La revisión
mostró que el mismo razonamiento aplica a los inactivos, y que estaba sin aplicar:

```
PANAMA CANAL COMMISSION JUBILADO        -> sin sector
JUBILADO DE LA CAJA DEL SEGURO SOCIAL   -> sin sector
ALMACEN WONG CHANG JUBILADO             -> sin sector
ESTUDIANTE DE UNIVERSIDAD INTERAMERICANA-> sin sector
REFRESCOS NACIONALES SA YA NO LABORA    -> sin sector
```

**El tipo dice que no hay vínculo laboral corporativo vigente. No dice que no haya
información.** El texto nombra al empleador del que la persona se jubiló, o la
universidad donde estudia: es la actividad económica de la que vive, que es exactamente
la columna que Riesgo necesita.

El tipo no cambia —siguen siendo `INACTIVO`, no entran al maestro corporativo— pero
conservan el sector. Se generalizó con un conjunto `SECTOR_RECUPERABLE = {INDEPENDIENTE,
INACTIVO}` en lugar de un caso especial, para que la próxima familia no requiera tocar el
motor.

**1.377 registros inactivos** recuperaron sector, además de los 3.610 independientes.

### Tercer marcador demasiado corto

`ESTUDIANTE` estaba como marcador suelto de inactividad, igual que `HOGAR` en D18:

```
ALMACEN EL ESTUDIANTE      -> era «no es un empleador»,  es una tienda
LIBRERIA EL ESTUDIANTE     -> era «no es un empleador»,  es una librería
```

Se aplicó la **regla de orden de D10**: si un término de actividad de peso alto precede al
marcador, manda el negocio. `ALMACEN EL ESTUDIANTE` → comercio; `ESTUDIANTE DE
UNIVERSIDAD` → inactivo.

`ESTUDIANTE` fue el único marcador suelto que lo necesitaba: los demás —`JUBILADO`,
`PENSIONADO`, `DESEMPLEADO`, `CESANTE`— no aparecen en nombres de negocio, y de hecho
`ALMACEN WONG CHANG JUBILADO` **debe** seguir siendo inactivo: es un jubilado de ese
almacén, no el almacén.

### Efecto medido

| | Antes | Ahora |
|---|---:|---:|
| Con sector CIIU | 186.907 · 60,12 % | **188.300 · 60,56 %** |
| Cobertura sobre el total de registros | 57,86 % | **58,30 %** |
| Inactivos con sector recuperado | 0 | 1.377 |

### El método que encontró esto

Dos tramos alfabéticos, solo la letra A, produjeron D18 y D19: **~4.500 registros**.
El conteo por volumen, que ya está exprimido, no habría encontrado ninguno de los dos —
son familias de baja frecuencia individual y alta frecuencia agregada.

**Ordenar por volumen muestra los errores caros. Ordenar alfabéticamente muestra las
familias.** Las dos vistas encuentran cosas distintas y el ciclo de mantenimiento debería
incluir ambas.

---

## D18 — El oficio del trabajador independiente es un sector

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** Javier revisó la lista alfabética de lo no identificable y señaló que ahí
  había cosas identificables: `ABOGADA INDEPENDIENTE`, `ACUICULTOR INDEPENDIENTE`,
  `ACUPUNTURISTA INDEPENDIENTE`.

### El razonamiento que faltaba

Un registro como `ABOGADA INDEPENDIENTE` **no nombra ninguna empresa, y nunca la nombrará**
—no hay empresa que nombrar—. Pero sí dice a qué se dedica la persona, y esa es
exactamente la columna que Riesgo necesita para analizar concentración.

Estábamos tratando «no hay empleador corporativo» como si fuera «no hay información». Son
cosas distintas. El tipo sigue siendo `INDEPENDIENTE`; lo que se recupera es el sector.

Se admitieron 17 familias de oficios inequívocos: `VENDEDOR`, `AGRICULTOR`, `GANADERO`,
`PESCADOR`, `ACUICULTOR`, `CONDUCTOR`, `TAXISTA`, `MECANICO`, `SOLDADOR`, `ALBANIL`,
`PLOMERO`, `ELECTRICISTA`, `PROFESOR`, `ABOGADO`, `PROGRAMADOR`, `DISENADOR`, `MODISTA`,
`ESTILISTA`, `ENFERMERO`, `ODONTOLOGO`, `ACUPUNTURISTA`, `AGRIMENSOR`, `ARQUITECTO`,
`COCINERO`, `EMPLEADA DOMESTICA`.

**Quedaron fuera a propósito:** `ADMINISTRADOR`, `OPERADOR`, `AYUDANTE`, `PROFESIONAL`,
`CORREDOR`, `EMPRESARIO`. Son cargos que existen en cualquier rama y no dicen en cuál.

Nota: `EMPLEADA DOMESTICA` estrena la sección **T — Hogares como empleadores**, que hasta
ahora no se usaba y es la clasificación correcta en CIIU para el trabajo doméstico
remunerado.

### Un defecto encontrado en la misma revisión

`HOGAR` estaba como marcador suelto de situación laboral inactiva, para capturar «ama de
casa». Sacaba empresas del maestro:

```
ALMACEN PUNTO EL HOGAR          -> era «no es un empleador»,  es un almacén
FINANZAS Y CREDITOS DEL HOGAR   -> era «no es un empleador»,  es una financiera
PATRONATO DEL HOGAR LEONISTICO  -> era «no es un empleador»,  es un asilo
```

**Un marcador tiene que ser tan específico como el concepto que marca.** «Ama de casa» es
una frase; `HOGAR` es una palabra que aparece en el nombre de cualquier negocio dirigido al
hogar. Se reemplazó por las 13 frases reales del corpus: `AMA DE CASA`,
`ADMINISTRADORA DEL HOGAR`, `ADMON DEL HOGAR`, `ADMO DEL HOGAR`, `LABORES DEL HOGAR`…

De paso se añadieron las formas de «no está trabajando» que el corpus escribe con adverbio
delante y que no casaban: `ACTUALMENTE NO LABORA`, `NO ESTA LABORANDO`, `QUEDO CESANTE`.

### Efecto medido

| | Antes | Ahora |
|---|---:|---:|
| Con sector CIIU | 185.230 · 59,64 % | **186.907 · 60,12 %** |
| Identificación | 96,15 % | **96,25 %** |
| Cola de fase 7 | 89.720 clústeres | **89.149** |
| Marcados como inactivos | 3.632 | 3.333 (299 empresas rescatadas) |

**Lección:** la revisión que encontró esto fue leer la lista **en orden alfabético**, no
por volumen. Ordenar por volumen muestra los errores caros; ordenar alfabéticamente muestra
las **familias** de registros —todos los `ABOGAD*` juntos, todos los `ADMINISTRADOR*`
juntos— y ahí se ve el patrón que el volumen esconde. Las dos vistas encuentran cosas
distintas y conviene usar ambas.

---

## D17 — Oficios de la cola larga y propagación de sector por la zona de duda

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** instrucción de agotar todo lo determinístico antes de gastar en la fase 7.

### 1. Oficios de la cola larga, por sufijo español

El residuo se agrupó por sufijo de oficio: `-ERIA` (el local donde se ejerce) y
`-ADORA` (la máquina o la empresa que hace algo). 1.873 registros en 320 palabras
distintas.

**La regla por sufijo no se automatizó**, y la lista explica por qué: entre las palabras
que terminan en `-ERIA` o `-ADOR` están `IBERIA`, `NIGERIA`, `ECUADOR`, `AMADOR`,
`SALVADOR`, `EMPERADOR` y `MIRADOR`. **El sufijo dice dónde mirar; no decide.** Se
admitieron a mano ~70 términos: `CARNICERIA`, `TORNERIA`, `MENSAJERIA`, `HOJALATERIA`,
`CEVICHERIA`, `ALBANILERIA`, `SASTRERIA`, `TAPICERIA`, `CERRAJERIA`, `FUMIGADORA`,
`EMPACADORA`, `PILADORA`, `ARRENDADORA`, `RECTIFICADORA`, `REASEGURADORA`, `TENERIA`.

De paso, las palabras en `-ADOR` que son **ocupación y no empresa** —`TRABAJADOR`,
`ADMINISTRADOR`, `COORDINADOR`, `ENTRENADOR`, `INSTALADOR`— pasaron a
`MARCADORES_OCUPACION`, que solo dispara cuando el registro es únicamente el cargo.
`CONTADORA` se dejó fuera: es también la isla de Contadora.

### 2. Propagación de sector por la zona de duda

Los 15.418 pares con similitud entre 76 y 88 estaban esperando la fase 7 sin usarse para
nada más. **No se fusionan —eso no cambia—, pero afirmar «hacen lo mismo» es una
afirmación mucho más débil que «son la misma empresa»**, y a esa distancia acierta casi
siempre:

```
LABORATORIO BIOMEDICA S C      <- LABORATORIO CLINICO BIOMEDICA     85,7 %
SECUNDARIO DE ASERRIO          <- COLEGIO SECUNDARIO DE ASERRIO     84,2 %
PANAMA CUARTO PUENTE SOBRE EL  <- CONSORCIO CUARTO PUENTE SOBRE EL  79,1 %
FELIPE RODRIGUEZ SA 9          <- GRUPO FELIPE RODRIGUEZ            86,0 %
```

Incluso cuando son entidades distintas —`UTP Panamá` y `UTP Penonomé`— el sector coincide.
Por eso se propaga la actividad y no la identidad.

**Dos guardas, ambas nacidas de un falso positivo medido:**

| Guarda | Caso que la motivó |
|---|---|
| Solo se hereda de evidencia fuerte (gazetteer, frase, forma jurídica o token de peso 7-9) | `BMW Latin America` heredaba «apoyo a empresas» de un vecino clasificado por `CORPORACION`, peso 1. Propagar una inferencia débil la convierte en dos |
| Si lo único que comparten es un nombre propio, no se hereda | `Esotérica San Miguel Arcángel` heredaba «enseñanza» de `Escuela San Miguel Arcángel`. Comparten el santo, no el oficio |

Resultado: **441 clústeres**, con origen `propagacion_duda` y factor de confianza 0,58 —
por debajo del token exacto (0,80) y del aproximado (0,62). Es evidencia plausible, no
probada, y el score lo dice.

### Un error de lectura mío, registrado

Al ver la primera muestra sin las entidades de origen juzgué que la precisión era
insuficiente y estuve a punto de descartar la técnica. Al listar **origen y destino
juntos** quedó claro que la mayoría eran la misma entidad escrita distinto. La lección es
sobre el método de revisión, no sobre el algoritmo: **una muestra sin su contexto de
decisión no permite evaluar la decisión.** La vista correcta es siempre «qué se decidió,
a partir de qué».

### Un defecto de suposición

La primera versión de la guarda de nombre propio leía la columna `tokens_distintivos` de
la zona de duda como si fuera una lista de palabras. Es un **conteo**. La guarda no
disparaba nunca y el número de propagaciones no se movía — que fue justamente la señal.
Ahora los tokens compartidos se calculan de los dos representantes.

### Efecto acumulado de la sesión

| | Al empezar el día | Ahora |
|---|---:|---:|
| Con sector CIIU | 177.955 · 56,2 % | **185.230 · 59,6 %** |
| Cola de fase 7 | 95.745 clústeres | **89.720** |
| Cola de 2+ apariciones | 22.801 | **21.604** |

---

## D16 — Vocabulario derivado del conteo de frecuencias sobre lo no clasificado

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** propuesta de Javier — separar todo en palabras, contar las más frecuentes y
  mirar cuáles permiten agrupar más. Se aplicó **solo sobre los clústeres sin sector** y
  ponderando por registros, que es lo que convierte un conteo en una lista de prioridades.

### Por qué esta vista funciona

Contar palabras sobre el corpus entero devuelve `PANAMA`, `SA`, `SERVICIOS` — nada
accionable. Contarlas **sobre lo que quedó sin clasificar** devuelve exactamente los huecos
del catálogo, ordenados por lo que cuesta no tenerlos.

### Reglas admitidas

| Patrón | Sector | Registros | Por qué es inequívoco |
|---|---|---:|---|
| `PRIMER CICLO`, `CENTRO BASICO GENERAL`, `PREMEDIA` | Enseñanza | ~500 | Son niveles del sistema educativo panameño |
| `ARMY`, `NAVY`, `AIR FORCE`, `TREASURY OF THE`, `PANAMA CANAL COMMISSION` | Administración pública | ~300 | Herencia de la antigua Zona del Canal, muy presente en la cartera |
| `AIR LINE`, `AIR LINES` | Transporte aéreo | 265 | El catálogo tenía `AIRLINES` junto, no separado |
| `Y ASOCIADOS`, `ASSOCIATES` | Jurídicas y contabilidad (peso 4) | 1.955 | Giro de las firmas profesionales panameñas |
| `SOLUCIONES` | Programación y consultoría (peso 4) | 510 | Estaba `SOLUTIONS` en inglés y no la forma española |
| `MANAGEMENT` | Consultoría de gestión (peso 5) | 548 | — |
| `CAR WASH`, `AUTOLAVADO` | Reparación de vehículos | ~120 | — |
| `RENT A CAR`, `CAR RENTAL` | Alquiler y arrendamiento | ~90 | — |
| `PTY` → `PANAMA` (abreviatura) | — | 449 | `LOS ESPECIALISTAS PTY` y `... PANAMA` caían en clústeres distintos |

### Palabras frecuentes que se dejaron fuera a propósito

`PANAMA` (11.764 registros), `CENTRO` (1.475), `CASA` (1.385), `FAMILIA` (609),
`MUNDO`, `ESTACION`, `STAR`, `HERMANOS`, `PRODUCTOS`, `DESARROLLO`.

Son las más frecuentes de todas y **ninguna dice a qué se dedica la empresa**. Clasificarlas
subiría la cobertura varios puntos y metería miles de errores silenciosos. Es D6 aplicado
donde más tienta romperlo: justo en la cabeza de la lista.

### Efecto medido

Cobertura 57,63 % → **58,93 %**. Cola de fase 7: 93.501 → **91.014** clústeres.

**Lección:** el conteo de frecuencias sobre el residuo es la herramienta más barata de todo
el proyecto para encontrar trabajo pendiente. Debería ser parte del ciclo de mantenimiento,
no un ejercicio único: cada vez que entra una carga nueva, las palabras que encabezan el
residuo son la lista de tareas.

---

## D15 — Órganos del Estado y coincidencia por token en el gazetteer

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** al mover el IPAT a administración pública (pendiente R11 de D14) se buscaron
  sistemáticamente todos los organismos públicos clasificados fuera de administración
  pública. Aparecieron dos familias de defectos, una de datos y una de código.

### Defecto 1 — El regulador clasificado en el sector que regula

| Registro | Estaba en | Causa |
|---|---|---|
| `SUPERINTENDENCIA BANCARIA` | Intermediación financiera | token `BANCARIA` |
| `COMISION NACIONAL DE VALORES` | Comercio al por menor | token `VALORES` |
| `JUZGADO PRIMERO DE CIRCUITO CIVIL` | Arquitectura e ingeniería | token `CIVIL` |
| `COMISION NACIONAL DEL MEDIO AMBIENTE` | Programación y transmisión | token `MEDIO` |
| `DIRECCION NACIONAL DE SEGURIDAD` | Seguridad privada | token `SEGURIDAD` |
| `CONTRALORIA ESCUELA IPT` | Enseñanza | el auditor está destacado en la escuela |
| `CAJA DE SEGURO SCOIAL` | Seguros y pensiones | la errata en `SOCIAL` impedía el gazetteer |

Es **D13 leído al revés**: si la Autoridad Marítima no es transporte marítimo porque lo
regula, la Superintendencia de Bancos tampoco es intermediación financiera. Se añadió una
regla de frase para los encabezados inequívocos de órgano estatal, que gana al token de
actividad.

### Defecto 2 — El gazetteer comparaba subcadenas, no tokens

`buscar_gazetteer` aceptaba la coincidencia con `clave in consulta`, comparación de
**caracteres**. Con claves cortas eso produce falsos positivos invisibles:

```
AVIS  dentro de  BELLAVISTA, DAVIS, CAVIS, BUENAVISTA   -> 128 registros
TIGO  dentro de  VERTIGO                                ->  86 registros
GBM   dentro de  LGBM                                   ->  38 registros
```

`CORPORACION BELLAVISTA DE FINANZAS, S.A.` quedaba clasificada como alquiler de vehículos.
Ahora la comparación es por **secuencia de tokens completos**, con índice por primer token
y preferencia por la clave más larga.

**Este defecto existía desde el principio**, pero era inofensivo mientras el gazetteer solo
tenía claves largas. Lo activó D13 al añadir siglas de tres y cuatro letras. Un cambio de
datos despertó un defecto de código que llevaba semanas dormido.

### Defecto 3 — Claves de gazetteer que son apellidos

`ARROCHA` mandaba `Clínica Dental Arrocha` y `Hospital Dionisio Arrocha` a comercio
minorista; `RICARDO PEREZ` es además un nombre de persona corriente en Panamá. Se
retiraron como claves sueltas y solo entran acompañadas del giro: `FARMACIAS ARROCHA`,
`DROGUERIAS ARROCHA`, `RICARDO PEREZ TOYOTA`.

Es la misma regla de admisión de D7, ahora aplicada al gazetteer: **una clave corta solo
entra si no puede ser fragmento o apellido de otro nombre.**

### Pendiente menor anotado

`ASOC PADRES DE FAMILIA CEBG` cae en Enseñanza porque la frase de la escuela es más larga
que la de la asociación y `por_frase` prefiere la más específica por longitud. Son 11
registros; no se fuerza.

---

## D14 — Auditoría de tokens genéricos que se comportaban como específicos

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** tras corregir `INSTITUTO` en D13, Javier preguntó si habría más casos del
  mismo tipo. Los había. Se auditó el catálogo entero: para cada palabra clave se listaron
  los nombres que realmente clasificó, ordenados por volumen.

### El patrón

Una palabra puede ser **genérica** (aparece en muchos sectores) y aun así tener peso alto,
con lo que gana todas las disputas y arrastra al sector equivocado a cientos de registros.
`INSTITUTO` con peso 9 mandaba a Enseñanza al Instituto de Recursos Hidráulicos, al de
Telecomunicaciones, al de Innovación Agropecuaria y al Oncológico.

**La corrección no es quitar el token: es bajarle el peso.** Con peso 3, `INSTITUTO` pierde
contra cualquier término que describa una actividad concreta (4-9) y solo decide cuando no
hay ninguno — que sigue siendo el caso mayoritario y correcto (`Instituto Justo Arosemena`).

### Hallazgos y correcciones

| Token | Diagnóstico | Corrección | Registros |
|---|---|---|---:|
| `INSTITUTO` (peso 9) | Genérico disfrazado de específico | Peso 3 + 8 reglas de frase | 1.352 revisados, 431 reasignados |
| `SOCIAL SECURITY` | La agencia de pensiones de EE. UU. clasificada como vigilancia privada por el token `SECURITY` | Frase → Administración pública | 78 |
| `BANCO MUNDIAL`, `BANCO INTERAMERICANO` | Bancos multilaterales en intermediación financiera; no captan depósitos | Frase → Organismos extraterritoriales | 29 |
| `DHL` | `DHL Global Forwarding` caía en «apoyo a empresas» por el token `GLOBAL` | Al gazetteer → apoyo al transporte; se añadieron `FORWARDING`, `FEDEX`, `UPS` | 121 |
| `SUPER` (peso 8) | `Super Service` no es un supermercado; `SUPER` significa «grande» | Peso 3 + frase `SUPER SERVICE` | 1.203 revisados |
| `GLOBAL` | Palabra de relleno con peso de actividad | Peso 1 | 1.132 revisados |
| `ESPERANDO NOMBRAMIENTO` | «Esperando nombramiento en el Min. de Educación» se clasificaba **como el ministerio**. No hay vínculo laboral todavía | `MARCADORES_ESPERA` → tipo INACTIVO | 266 |

### Un error introducido y detectado en la misma sesión

Bajar `INSTITUTO` a peso 3 hizo que `INSTITUTO PROF TECNICO` cayera en «Reparación de
computadores»: el token `TECNICO` (peso 5, reparación) le ganaba, y la frase escrita —
`INSTITUTO PROFESIONAL`— no casaba con la forma abreviada `PROF`. Son escuelas
vocacionales. Se añadieron `INSTITUTO PROF`, `INSTITUTO PRACTICO` e
`INSTITUTO POLITECNICO`.

**Vale la pena registrarlo:** bajar un peso no es una operación neutra. Libera las disputas
que ese token venía ganando, y hay que mirar quién las gana ahora. La verificación no
termina con el caso que motivó el cambio.

### Reasignaciones de `INSTITUTO`, verificadas una a una

| Destino nuevo | Ejemplo real | ¿Correcto? |
|---|---|---|
| Salud humana | Instituto Oncológico, Instituto de Medicina Legal | Sí |
| Administración pública | Instituto Nacional de Estadística, INADEH | Sí |
| Investigación científica | Instituto de Innovación Agropecuaria | Sí |
| Suministro de agua | Instituto de Acueductos (IDAAN) | Sí |
| Otros servicios personales | Instituto de Belleza, Instituto de Estética | Sí |
| Actividades deportivas | Instituto Nacional de Deportes (Pandeportes) | Sí |
| Agencias de viajes | Instituto Panameño de Turismo (IPAT) | Discutible: es el regulador del sector, no un operador. Por el criterio de D13 debería ser administración pública. Queda anotado |
| Enseñanza (se mantiene) | Instituto Justo Arosemena, IPT | Sí — 828 registros |

### Efecto medido

Cobertura 57,61 % → **57,63 %**. El número casi no se mueve, y ese es justamente el punto:
**este trabajo no aumenta la cobertura, aumenta la verdad.** 431 registros de `INSTITUTO`,
121 de DHL, 78 de Social Security, 29 de bancos multilaterales y 266 de espera de
nombramiento estaban en el sector equivocado y ahora no lo están.

**Lección:** la auditoría que encuentra esto no es mirar métricas agregadas ni muestrear al
azar. Es listar, para cada regla, qué clasificó realmente, ordenado por volumen. Un error
sistemático se ve de inmediato en esa vista y es invisible en cualquier otra.

---

## D13 — Diccionario de empleadores ancla y criterio actividad-sobre-propiedad

- **Fecha:** 2026-08-08
- **Estado:** VIGENTE
- **Origen:** Javier aportó una investigación propia sobre los mayores empleadores e
  instituciones de Panamá, apoyada en la planilla del sector público de la Contraloría a
  diciembre de 2025, reguladores sectoriales y Merco Empresas Panamá 2025.

### La decisión de fondo: ¿el sector lo decide el dueño o la actividad?

La instrucción verbal («Lotería Nacional es gobierno», «toda policlínica es CSS, por tanto
gobierno») contradecía el documento aportado, que recomienda lo contrario citando la
metodología del INEC (CINU Rev. 4.1) y de Naciones Unidas: *el estatus legal o
institucional de la entidad no determina por sí mismo su clasificación*.

Se planteó la contradicción y **Javier decidió: clasificar por actividad.** Consecuencias:

| Entidad | Por propiedad sería | Por actividad es |
|---|---|---|
| Policlínica / hospital de la CSS | Administración pública | Salud humana |
| Lotería Nacional | Administración pública | Artes, entretenimiento y recreación |
| MiBus, Metro de Panamá | Administración pública | Transporte terrestre |
| Banco Nacional, Caja de Ahorros | Administración pública | Intermediación financiera |
| Universidad de Panamá, UTP, UNACHI | Administración pública | Enseñanza |
| IDAAN | Administración pública | Suministro de agua |
| ETESA | Administración pública | Suministro de electricidad |
| Autoridad del Canal | Administración pública | Apoyo al transporte |

Administración pública queda reservada a ministerios, tribunales, Asamblea, policía,
reguladores y administradores de programas del Estado. Es el criterio que ya aplicaba el
pipeline; ahora es explícito y está documentado.

**Por qué importa para Riesgo:** con el criterio de propiedad, el sector público se comería
sectores enteros y el análisis de concentración de cartera perdería resolución justo donde
más la necesita. Una escuela y un ministerio no tienen el mismo perfil de riesgo laboral.

### Diccionario ancla

El gazetteer pasó de 60 a **185 entradas**, organizadas por bloque: Estado como
administración pública, Estado clasificado por actividad, financiero, comercio,
manufactura, servicios a empresas, profesionales, tecnología, transporte y puertos, salud,
alojamiento, construcción, energía, minería, agro y organismos internacionales.

- **275 anclas dispararon** sobre 9.308 registros (antes 5.268).
- Mayor impacto: Caja de Seguro Social (1.177), Ministerio de Educación (515), Ministerio
  de Salud (366), Tocumen (277), Policía Nacional (242), Universidad de Panamá (209).

### Dos defectos encontrados al integrarlo

1. **`IDAAN` caía en Enseñanza.** `expandir_tokens` corre **antes** de consultar el
   gazetteer, así que la sigla llegaba desplegada como `INSTITUTO DE ACUEDUCTOS...` y el
   token `INSTITUTO` (peso 9) disparaba enseñanza. Se añadieron las claves en su forma ya
   expandida para `IDAAN`, `ACP`, `AMP`, `ATP`, `IFARHU`, `SENAFRONT`, `SENAN` y `SENADIS`.
   Lección: un gazetteer que se consulta después de una transformación tiene que estar
   escrito en el idioma de la salida de esa transformación, no en el de la entrada.
2. **`INDEPENDIENTE AGRIMENSURA` no se detectaba.** El marcador se buscaba como frase
   completa, así que solo casaba si el registro era exactamente `INDEPENDIENTE`. Ahora se
   busca también como token suelto.

### Independientes

Por instrucción de negocio, **todo lo que se declara independiente se agrupa como
independiente**: no es un empleador corporativo, no entra al maestro y no consume
validación externa. 5.583 registros (antes 136).

Se conserva sin embargo el sector cuando el texto declara el oficio
(`INDEPENDIENTE AGRIMENSURA` → arquitectura e ingeniería): agrupar por nombre no obliga a
tirar la actividad, y el dato sale gratis.

### Efecto medido

| | Antes | Ahora |
|---|---:|---:|
| Con sector CIIU | 177.955 · 56,2 % | **178.979 · 57,6 %** |
| Registros por gazetteer | 5.268 | **9.308** |
| Anclas distintas activas | ~60 | **275** |
| Cola de fase 7 | 95.745 clústeres | **93.501** |
| Independientes agrupados | 136 | 5.583 |

La tasa de identificación baja de 97,96 % a 96,19 %, y es correcto: los 5.583
independientes dejaron de contarse como empleadores corporativos porque no lo son.

**Lección:** este fue el aporte de mayor rendimiento por unidad de esfuerzo de todo el
proyecto, y no vino del dato ni del código, sino de investigación de dominio. Confirma D12
a mayor escala: el vocabulario de negocio no se infiere del corpus, se aporta. La
arquitectura ya lo permitía —`reglas.py` separado del motor— y por eso integrar 125
entidades nuevas fue una edición de diccionario, no un cambio de diseño.

---

## D12 — La propiedad horizontal es un empleador, no un inmueble

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Origen:** Javier señaló que `PH` significa propiedad horizontal y pidió revisar si se
  podían rescatar. Conocimiento de dominio que yo no tenía: `PH` estaba en la lista de
  tokens débiles de dirección, es decir, tratado como sinónimo de «edificio».
- **Por qué importa:** en Panamá una PH **no es un edificio**. Es una persona jurídica
  inscrita bajo la Ley 31 de 2010, con junta directiva, RUC y planilla propia:
  administrador, seguridad, aseo, mantenimiento. Que un cliente declare `PH Multiplaza`
  como empleador es **correcto**, no un error de captura.
- **Estado antes:** 1.040 registros con token `PH` — 368 clasificados como dirección,
  548 sin sector. Ninguno reconocido como lo que era.
- **Regla:** `PH` en las dos primeras posiciones identifica a la entidad. Dos excepciones,
  ambas medidas sobre el corpus:

| Excepción | Ejemplo | Por qué |
|---|---|---|
| Indicador de unidad (`APTO`, `AP`, `PISO`, `LOCAL`) | `PH Vertikal AP 26B` | Es el domicilio de alguien, no la entidad |
| Token fuerte de vía | `Boulevard PH Costa del Este` | Es una dirección que menciona un PH de referencia |

  `CASA` **no** entra como indicador de unidad: `PH Casa del Mar` y `PH Casa Blanca` son
  nombres de edificio, no domicilios. Se verificó caso por caso.
- **Posición 0 o 1:** los 52 registros donde `PH` no encabeza vienen tras `EDIFICIO`,
  `EDIF`, `ADMINISTRACION`, `CONJUNTO`, `CONDOMINIO`, `ADMINISTRADOR` o `CONSORCIO`.
  Todos **confirman** la entidad en lugar de negarla, así que la ventana se abrió a dos.
- **Sector: CIIU L/68.** La PH administra el inmueble y contrata al personal que lo opera.
  Entra alto en la cascada —después del gazetteer, antes de las frases— porque no es una
  palabra clave sino una **forma jurídica**: la actividad se deduce de ella y no admite
  discusión. Factor de confianza 0,94.
- **Hallazgo lateral:** 196 registros escriben `P H MULTIPLAZA` con las letras sueltas.
  Al tokenizar producían dos tokens de una letra, no coincidían con los 957 que escriben
  `PH` junto, y el nombre canónico salía «P H Multiplaza». Se añadió `SIGLAS_SEPARADAS`,
  aplicada en la limpieza.
- **Efecto medido:** 1.196 registros en Actividades inmobiliarias (antes 7). Direcciones
  2.233 → **1.868**. Identificación 97,85 % → **97,96 %**. Cobertura sectorial → 56,24 %.
- **Lección:** esta no era una regla que yo pudiera derivar del dato. `PH` es una sigla
  local con estatuto jurídico, y sin ese contexto la lectura por defecto —«edificio, luego
  dirección»— era razonable y equivocada. **El vocabulario de negocio no se infiere del
  corpus; se pregunta.** Es el argumento más fuerte a favor de mantener `reglas.py`
  separado del motor: quien tiene este conocimiento debe poder aportarlo sin tocar código.

---

## D11 — Consulta aproximada al catálogo CIIU

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Origen:** Javier preguntó por qué `Interglobal Distributos` o `Todotoyota CA` quedaban
  pendientes. Al investigarlo apareció una asimetría de diseño que no había visto.
- **Defecto:** el motor de entidades usa `rapidfuzz`, pero el **catálogo sectorial se
  consultaba solo por coincidencia exacta**. En un corpus donde la errata es la norma, eso
  dejaba fuera `TRANPORTE`, `CONTRUCCIONES` y `UNVIERSIDAD` — palabras cuyo sector es
  obvio para cualquier lector.
- **Dos mecanismos, no uno.** Mezclarlos fue el primer error al medirlo:

| Mecanismo | Naturaleza | Umbral |
|---|---|---|
| Morfología (`ACARREO`/`ACARREOS`) | No es errata: es un hueco del propio catálogo | Determinista |
| Errata (`TRANPORTE`/`TRANSPORTE`) | Ruido de captura | ratio ≥ 90 |

- **Cuatro guardas, cada una motivada por un falso positivo medido:**

| Guarda | Falso positivo que evita |
|---|---|
| Solo términos de peso ≥ 6 | `Movistar Empresas` → «apoyo empresarial». Una coincidencia sobre palabra de relleno propaga ruido con apariencia de evidencia |
| Excluye apellidos, nombres y topónimos | `Arqmarcela Herrera` → «herrería» al 93 %. `Herrera` es apellido y provincia |
| La errata no contiene la palabra correcta intacta | `Reconstruction Car Center` → «Construcción». El prefijo `RE-` cambia el sentido, no lo deteriora: es un taller |
| Pares singular/plural no sinónimos (`MORFOLOGIA_EXCLUIDA`) | `Laboratorio de Inyección Diesel` → «sustancias químicas». En Panamá el singular suele ser clínico o mecánico; el plural sí es farmacéutico |

- **Peso en la votación de clúster: 3.** Menos que cualquier token exacto (4-9). Una
  coincidencia aproximada nunca debe ganarle a una exacta dentro del mismo clúster.
- **Factor de confianza: 0,62** frente a 0,80 del token exacto. Es evidencia real, más
  débil, y el score lo dice.
- **Efecto medido:** 21.156 registros clasificados por esta vía. Cobertura sectorial
  52,96 % → **54,80 %** del total.
- **Casos que deliberadamente NO resuelve**, con su causa:

| Caso | Causa | Por qué no se fuerza |
|---|---|---|
| `Interglobal Distributos` | `DISTRIBUTOS` ~ `DISTRIBUIDORA` da 75 % | Bajar el umbral a 75 abre la puerta a cientos de falsos positivos |
| `Todotoyota CA` | Token concatenado sin separador | Buscar subcadenas dentro de tokens es otra clase de problema; hacerlo mal genera más ruido del que resuelve |
| `Planeta Pasta`, `EMS Soluciones`, `Evergreen ATM` | Genuinamente ambiguos | ¿Fábrica de pasta o restaurante? El nombre no lo dice. D6 aplica |
| `Cbtelsa` | Acrónimo opaco | Ninguna regla puede saberlo. Es el caso de uso exacto de la fase 7 |

- **Lección:** vale la pena revisar si una técnica que ya se usa en una parte del sistema
  debería usarse en otra. El fuzzy llevaba todo el proyecto resolviendo identidades y
  ninguno resolviendo vocabulario, sin razón de diseño — solo porque nadie lo preguntó.

---

## D10 — Tres guardas para no confundir un negocio con un inmueble

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Origen:** Javier revisó los registros marcados `No identificable - Direcciones` y notó
  que *«algunas sí lo son, otras no»*. Correcto: había 1.079 falsos positivos.
- **Defecto:** la tipificación de dirección corría antes de cualquier señal de negocio y
  se quedaba con el primer indicio que encontraba. `HOTEL PLAZA HERRERA S A` caía por
  `PLAZA`; `MINISUPER PARQUE EL EMPALME` por `PARQUE`; `TRANSPORTE RAMON DE LA TORRE`
  por `TORRE`.
- **Guardas añadidas**, cada una medida sobre el corpus antes de escribirla:

| # | Guarda | Evidencia | Alcance |
|---|---|---|---|
| a | Un sufijo societario veta la clasificación como dirección | Nadie inscribe una calle como `S.A.` | 284 registros |
| b | **Manda quien aparece primero** entre token de negocio y token de dirección | En español el nombre se encabeza con lo que la cosa *es* | ~700 registros |
| c | `CASA DE\|DEL\|EL\|LA X` es giro comercial, no inmueble | `CASA DE EMPENO`, `LA CASA DEL CHAPISTERO`. Una casa como dirección lleva número | 405 registros |

- **La guarda (b) es la interesante.** Los dos casos difíciles traen *ambas* señales:

  ```
  MINISUPER PARQUE EL EMPALME       → un minisúper que está en un parque   → EMPRESA
  AVENIDA PRINCIPAL LA HACIENDA …   → una avenida que pasa por una hacienda → DIRECCION
  ```

  No hay diccionario que los separe, porque el vocabulario es el mismo. Lo que los separa
  es el **orden**. La regla se explica en una frase y se sostiene en los 25 casos de prueba.
- **Efecto medido:** direcciones 3.312 → **2.233**. Identificación 97,51 % → **97,85 %**.
  Empleadores únicos 203.494 → 204.181. Con sector CIIU 166.764 → 167.388.
- **Defecto de acoplamiento encontrado de paso:** `clasificar_tipo` recibía los tokens con
  el sufijo societario **ya separado** por `normalizar()`, así que al recalcularlo nunca lo
  encontraba y la guarda (a) no disparaba en el pipeline aunque sí en las pruebas
  unitarias. Ahora el sufijo se pasa como parámetro. Recordatorio de que una función que
  rededuce lo que su llamante ya sabe es una función que puede desincronizarse en silencio.
- **Lección:** el orden de las reglas es una decisión de diseño, no un detalle de
  implementación. Poner la detección de direcciones antes de la de negocio equivalía a
  decidir, sin decirlo, que la dirección gana los empates.

---

## D9 — CSV entregables con BOM UTF-8

- **Fecha:** 2026-08-07
- **Estado:** VIGENTE
- **Decisión:** Los CSV de `salidas/` se escriben en `utf-8-sig`; los intermedios `.gz`
  siguen en `utf-8` puro. La lectura usa `utf-8-sig` siempre, que tolera ambos.
- **Motivo:** Excel en Windows abre `.csv` con la página de códigos ANSI salvo que el
  archivo empiece con BOM. Sin él, `Construcción` se muestra `ConstrucciÃ³n`. Los bytes
  siempre fueron UTF-8 correcto: el defecto era de entrega, no de contenido.
- **Nota:** es un detalle de un byte que decide si el entregable se ve profesional o roto
  al abrirlo. El XLSX nunca tuvo el problema.
