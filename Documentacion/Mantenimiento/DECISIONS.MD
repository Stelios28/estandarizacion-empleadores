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
