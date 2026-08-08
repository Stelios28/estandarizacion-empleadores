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
