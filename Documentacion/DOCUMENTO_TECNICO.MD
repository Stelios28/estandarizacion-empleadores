# Estandarización de lugar de trabajo — Documento técnico

**Prueba técnica · Ingeniería de Datos · Riesgo de Crédito**
Fecha: 2026-08-07 · Dataset: 323.001 registros · Panamá

---

## 1. Resumen ejecutivo

Se construyó un pipeline productivo que transforma 323.001 empleadores capturados
como texto libre en un maestro corporativo de **200.373 empleadores únicos**, con
razón social canónica, sector CIIU Rev. 4, score de confianza y traza completa de
cada decisión.

| Resultado | Valor |
|---|---:|
| Registros procesados | 323.001 |
| Empleadores identificados | 309.476 · **95,81 %** |
| Empleadores únicos en el maestro | 200.650 |
| Consolidación de variantes | **35,4 %** |
| Con sector CIIU asignado | 190.303 · **61,5 %** de los empleadores |
| Tiempo total de ejecución | **~2 minutos** en un portátil |
| Pares comparados vs. espacio total | 7,4 M de 30.446 M · **0,024 %** |

El corte del 60,7 % en cobertura sectorial no es una limitación del método: es el
punto exacto donde la evidencia interna se agota. Los 89.720 clústeres restantes
son marcas sin palabra descriptiva —`BRICKHAUS`, `SOLINTECSA`, `WILHELMSEN`— que
requieren conocimiento externo. La fase 7 está construida y su costo medido:
**USD 149** con Claude Opus 5, **USD 75** usando la Message Batches API.

---

## 2. Perfilamiento: cuatro hallazgos que determinaron el diseño

El detalle completo, con cifras y método, está en
[`Mantenimiento/NOTAS_PERFILAMIENTO.MD`](Mantenimiento/NOTAS_PERFILAMIENTO.MD).
Cuatro hallazgos cambiaron decisiones de arquitectura:

### 2.1 El dataset llegó deduplicado — no hay frecuencias

323.000 valores, **todos distintos**. 35.820 terminan en `" <número>"`; al retirar
ese sufijo quedan 305.676 y aparecen 13.013 grupos repetidos.

**Consecuencia de diseño:** la heurística estándar de entity resolution —"la
variante más frecuente del clúster es el nombre canónico"— **no es aplicable**.
Todas las variantes tienen frecuencia 1. Hubo que construir un criterio alternativo
(§5.2).

### 2.2 Dos truncamientos de origen: 30 y 40 caracteres

Pico en longitud 30 (18.748 contra ~8.500 esperados) y acantilado en 40→41
(1.833 → 181). Son dos sistemas fuente con campos `VARCHAR(30)` y `VARCHAR(40)`.
**20.532 registros** llegan potencialmente cortados a media palabra.

**Consecuencia de diseño:** un nombre truncado es *prefijo exacto* de su nombre
completo, no un error ortográfico. Necesita regla propia con distancia asimétrica
(§4.3), no un umbral de similitud.

### 2.3 El texto ya llegó destruido

Cero tildes, cero eñes, cero minúsculas en 323.000 registros. Solo 29 guiones y 5
puntos de puntuación en total. 312 registros contienen `PANAMEA` — la eñe fue
*eliminada*, no sustituida.

**Consecuencia de diseño:** la normalización agresiva ya ocurrió aguas arriba y es
irreversible. Se pierde información de desambiguación que no se puede recuperar. Se
documenta como pérdida y se ataca en origen (§8.1).

### 2.4 Los números finales son códigos de sucursal, no ruido

`EMPRESAS MELO SA` aparece con 019, 020, 025, 026, 027, 029, 034, 051, 053, 094 y
510. `MINI SUPER` con 07, 11, 18, 21.

**Consecuencia de diseño:** el número **no se borra**. Se separa como atributo y se
neutraliza solo en la clave de comparación. Para riesgo de crédito, todas las
sucursales de Empresas Melo son el mismo empleador — pero el número se conserva
porque identifica el punto de trabajo.

---

## 3. Arquitectura

```
prueba_tecnica_ing_datos.xlsx  (solo lectura, nunca se modifica)
        │
        ▼
┌─ BLOQUE 1 ── fases 1-4 ────────────────────────────────────────────┐
│  Perfilamiento · Limpieza · Normalización · Tipificación           │
│  Diccionario incremental · Matching exacto                          │
│  323.001 registros ──▶ 242.847 claves distintas                     │
└─────────────────────────────────────────────────────────────────────┘
        ▼
┌─ BLOQUE 2 ── fases 5-6 ────────────────────────────────────────────┐
│  Bloqueo en 3 canales · Matching difuso · Clustering con cohesión   │
│  242.847 claves ──▶ 200.373 clústeres  (7,4 M pares de 30.446 M)    │
│  15.427 pares en zona de duda ──▶ propagan sector, no identidad     │
└─────────────────────────────────────────────────────────────────────┘
        ▼
┌─ BLOQUE 3 ── fases 8, 9, 11 ───────────────────────────────────────┐
│  Razón social canónica · Sector CIIU por voto ponderado             │
│  Reproceso iterativo: el clúster propaga lo aprendido               │
│  110.653 clústeres clasificados ·  89.720 pendientes                │
└─────────────────────────────────────────────────────────────────────┘
        ▼
┌─ BLOQUE 4 ── fase 7 ───────────────────────── (requiere credencial) ┐
│  Validación externa solo sobre representantes con duda razonable    │
│  Caché persistente · Lotes de 40 · Presupuesto acotado              │
└─────────────────────────────────────────────────────────────────────┘
        ▼
┌─ BLOQUE 5 ── fases 10, 12 ─────────────────────────────────────────┐
│  Score de confianza explicable · Tablas auditables · KPIs           │
└─────────────────────────────────────────────────────────────────────┘
```

Cada bloque materializa su salida en disco. El pipeline es **reanudable**: una
corrida interrumpida en el bloque 3 no repite los bloques 1 y 2.

### Restricción de entorno encontrada

La máquina es **Windows ARM64** y `scipy`/`scikit-learn` están bloqueados por App
Control de Windows. El diseño previsto usaba `TfidfVectorizer` + producto de
matrices dispersas para el bloqueo. Se rediseñó sobre **índice invertido en
diccionarios de Python + `rapidfuzz`**, sin pérdida de rendimiento —de hecho el
resultado es más interpretable, porque cada par candidato se puede explicar por el
token que lo generó, cosa que un coseno de TF-IDF no permite.

---

## 4. Estrategia de matching

### 4.1 El problema es no generar el par, no subir el umbral

242.847 claves distintas son **30.446 millones** de pares. La solución no es un
umbral más alto: es bloqueo.

### 4.2 Tres canales de bloqueo complementarios

| Canal | Señal | Qué recupera |
|---|---|---|
| **1. Token raro** | Los 3 tokens de menor frecuencia documental de cada clave | El caso general. Es lo que impide que `BANCO UNO` y `BANCO CONTINENTAL` lleguen siquiera a compararse: `BANCO` es genérico (df 1.120 > corte 807) y `UNO`/`CONTINENTAL` no coinciden. **Precisión por construcción, no por umbral.** |
| **2. Afijo de token raro** | Primeros y últimos 4 caracteres de cada token raro | Erratas *dentro* del token distintivo: `ODEBRECHT` / `ODEBRETCH` / `OLDERECHT`. El canal 1 se las perdería. |
| **3. Prefijo** | Los 30 o 40 primeros caracteres | Los 20.532 truncados de origen. |

**El corte entre token "raro" y "genérico" se mide, no se escribe a mano.** Un token
presente en ≥ 0,25 % de los registros (807 apariciones) no distingue a nadie. Con
ese criterio, 99 de 108.354 tokens resultan genéricos: `DE`, `SA`, `PANAMA`,
`GRUPO`, `INVERSIONES`, `SERVICIOS`, `CENTRO`.

**Resultado:** 7.387.844 pares evaluados — el **0,024 %** del espacio completo.

### 4.3 Aceptación del par: umbral condicionado a la evidencia

```
2+ tokens distintivos en común  →  umbral 82
1  token  distintivo en común   →  umbral 88
0  tokens distintivos en común  →  umbral 94   (el par llegó por afijo)
truncamiento: prefijo exacto en el tope del campo  →  aceptación directa
```

La distancia para truncamiento es **asimétrica**: cortar el final es barato,
cambiar el inicio no lo es. Por eso se exige prefijo exacto y no similitud global.

### 4.4 La guarda de cohesión: Union-Find encadena

En la primera corrida, Union-Find metió `HOSPITAL ARNULFO ARIAS`,
`COMPLEJO HOSPITALARIO METROPOLITANO` y `HOSPITAL MANUEL AMADOR GUERRERO` —tres
hospitales distintos— en un clúster de 131 claves. A~B y B~C, luego A y C acaban
juntos aunque no se parezcan.

**Solución:** las fusiones se procesan en **orden descendente de score**, y antes de
unir dos clústeres se exige que sus *representantes* también se parezcan
(cohesión ≥ 86). La unión más segura fija el representante; las dudosas se miden
contra él.

**Efecto:** 43.443 fusiones aplicadas, 2.340 descartadas, y el encadenamiento
desaparece. Los tres hospitales quedan en clústeres separados.

### 4.5 Calificadores de sucursal y de cargo

El campo mezcla tres cosas: el empleador, dónde queda la sede, y qué hace la
persona. Para riesgo de crédito el empleador es el mismo:

```
IDAAN ANALISTA DE RECARGO        ≡  IDAAN FONTANERO III
OPERADORA PANAMAX S A BRISAS     ≡  OPERADORA PANAMAX SA ALBROOK
HOSPITAL CECILIO CASTILLERO      ≡  HOSPITAL CECILIO CASTILLERO CHITRE
```

La cohesión se mide sobre el núcleo completo **y** sobre el núcleo sin
calificadores, tomando la mayor. Los lugares se retiran solo del **final** del
nombre: `PANAMA PORTS COMPANY` conserva su `PANAMA` inicial, que sí es parte de la
razón social.

### 4.6 La zona de duda razonable — el hallazgo central del matching

Se midió la separación entre pares que *son* la misma entidad y pares que no lo son:

| Misma entidad | Score | | Entidades distintas | Score |
|---|---:|---|---|---:|
| `AUTORIDAD DE TRANSPORTE TERRESTRE` / `AUTORIDAD DE TRANSITO Y TRANSPORTE` | 75,4 | | `FABRICA DE BLOQUES TECNO SA` / `FABRICA DE BLOQUES MARLON SA` | 76,4 |
| `BEATRIZ MIRANDA DE CAVAL` / `COLEGIO BEATRIZ MIRANDA DE CABAL` | 82,1 | | `LINEA 3 DEL METRO` / `LINEA DOS DEL METRO` | 80,0 |
| `CHINA HARBIUR ENGINEERING` / `CHINA HARBOUR ENGINEERING` | 83,1 | | `UTP PANAMA` / `UTP PENONOME` | 84,5 |
| `PROGRAMA DE LAS NAC UNIDAS` / `PROGRAMA DE LAS NACIONES UNIDAS` | 86,1 | | `AVANT GARDE IMPORT CORP` / `AVANT GARDE IMPORT EXPORT` | 87,5 |
| `HOSPITAL CECILIO A CASTILLERO` / `HOSPITAL CECILIO CASTILLERO CHITRE` | 88,6 | | | |

**Las dos poblaciones se solapan entre 76 y 88. Ningún umbral las separa.**

Esto no es un umbral mal calibrado: es el límite de lo que la similitud de cadena
puede decidir. Es exactamente lo que el enunciado llama "duda razonable". Esa banda
—**15.427 pares**— no se resuelve adivinando: se marca, propaga sector sin fusionar identidades (D17) y pasa a la fase 7. Debajo de
76 son entidades distintas y no se consulta nada.

---

## 5. Razón social canónica

### 5.1 Por qué la heurística estándar no sirve aquí

Sin frecuencias (§2.1), no se puede votar por la variante más común. El canónico se
determina en cascada: **gazetteer → variante más informativa → presentación**.

### 5.2 Elegir la variante correcta usando el propio corpus

Un token bien escrito aparece en muchos registros; una errata aparece en uno. El
corpus mismo dice cuál grafía es la buena:

```
COPA   → frecuencia documental alta
COPAR  → frecuencia documental 1
```

Se toma el token **peor soportado** de cada variante (una sola errata la
descalifica) y se prefiere la variante con mejor soporte. Sin este criterio, el
canónico salía como `Copar Airlines` y `Comidas Rapidas Internancionales`: la
variante con errata era la más larga, y la longitud sola premiaba el error.

**Antes / después, sobre el maestro real:**

| Antes | Después |
|---|---|
| Copar Airlines, S.A. | **Copa Airlines, S.A.** |
| Crisa Comidas Rapidas Internancionales | **Comidas Internacionales** |
| Cocoa Cola Femsa de Panama, S.A. | **Coca-Cola FEMSA de Panamá, S.A.** |
| Ministerio de Economia Finanza, S.A. | **Ministerio de Economía y Finanzas** |
| Cuerpo de Bomberos, S.A. | **Cuerpo de Bomberos de Panamá** |

### 5.3 Dos guardas sobre el sufijo societario

Un ministerio no es una sociedad anónima. El sufijo solo se agrega si:

1. La entidad no encabeza con un token institucional (`MINISTERIO`, `AUTORIDAD`,
   `CUERPO`, `UNIVERSIDAD`, `HOSPITAL`, `FUNDACION`…), **y**
2. Al menos la mitad de las variantes del clúster lo traen.

Sin esto, una sola variante mal capturada convertía a un ministerio en S.A.

---

## 6. Clasificación sectorial — CIIU Rev. 4

Cascada determinística de la evidencia más fuerte a la más débil:

| # | Fuente | Clústeres | % |
|---|---|---:|---:|
| 1 | Gazetteer — 185 empleadores ancla de Panamá | 3.573 | 1,8 % |
| 2 | Propiedad horizontal (forma jurídica, no palabra clave) | 871 | 0,4 % |
| 3 | Frase del catálogo (`SALON DE BELLEZA`, `CAJA DE SEGURO`) | 7.163 | 3,6 % |
| 4 | Token con peso (`FERRETERIA` p8 > `SERVICIOS` p1) | 90.306 | 45,1 % |
| 5 | Token aproximado (errata o singular/plural) | 8.029 | 4,0 % |
| 6 | Propagación por zona de duda | 441 | 0,2 % |
| 7 | Reclasificación (no es un empleador) | 270 | 0,1 % |
| — | **Sin evidencia interna → fase 7** | **89.720** | **44,8 %** |

Los niveles 2, 5 y 6 no estaban en el diseño original: salieron del ciclo de revisión
(D11, D12, D17) y aportan 9.341 clústeres que antes quedaban sin sector. El nivel 1
creció de ~60 a 185 anclas con investigación de dominio aportada por negocio (D13).

### 6.1 Voto ponderado, no primer acierto

Tomar el primer acierto dejaba que una sola variante desviara al clúster entero.
Ahora cada variante vota con el peso de su regla y gana el sector con más respaldo
acumulado.

### 6.2 Dos correcciones que valen como lección de diseño

**Una abreviatura ambigua es peor que ninguna.** `COL → COLEGIO` clasificó a
Coca-Cola FEMSA en *Enseñanza*: 2 de sus 48 variantes venían escritas
`COCA COL FEMSA`. Se estableció una regla de admisión: una abreviatura de 2-3
letras solo entra si no puede aparecer como fragmento legítimo de otro nombre. Se
excluyeron `COL` (Colón, Colombia), `PAN` (Pan American) y `RP`.

**Una guarda estructural que se midió y se retiró.** Se probó exigir que el sector
ganador tuviera respaldo de al menos el 20 % de las variantes. Medida sobre el
corpus, rechazaba 62 clústeres y **la mayoría eran correctos**: `Constructora
Urbana` → Construcción y `Complejo Hospitalario` → Salud tienen el token
descriptivo en una sola variante porque las demás llegaron truncadas. Se retiró. La
decisión y su evidencia quedan en el código, para que nadie la vuelva a introducir.

### 6.3 No se inventa sector

Se descartaron a propósito tokens de alto volumen pero sector ambiguo: `CENTRO`,
`CASA`, `FAMILIA`, `MUNDO`, `STAR`, `WORLD`, `GENERAL`. Clasificarlos habría subido
la cobertura y ensuciado el análisis de concentración de cartera, que es justo para
lo que Riesgo va a usar esta columna.

**Una fila sin sector se ve. Una fila con el sector equivocado contamina en
silencio.**

---

## 7. Score de confianza

El enunciado pide "puntaje de confianza y explicación de cada decisión". Un número
sin desglose no es auditable, así que el score se compone de factores nombrados y
cada registro sale con la lista de los que lo movieron.

```
confianza = 100 × factor_identidad × factor_sector − penalizaciones
```

| Banda | Score | Registros | % | Uso operativo |
|---|---|---:|---:|---|
| Automático | ≥ 85 | 37.478 | 11,6 % | Utilizable sin revisión |
| Muestreo | 70-84 | 91.197 | 28,2 % | Utilizable con control por muestra |
| Revisión | 50-69 | 62.559 | 19,4 % | Revisar antes de usar en concentración |
| Verificación individual | < 50 | 131.767 | 40,8 % | No usar sin verificar |

**El 40,8 % en la banda baja es, casi en su totalidad, el efecto de no tener
sector.** Ejecutar la fase 7 mueve esa masa hacia arriba: el factor sector pasa de
0,25 a 0,50-0,90 según la confianza que declare el modelo.

Ejemplo de traza real de un registro:

```
identidad gazetteer (x1.00) | sector gazetteer (x1.00)
+6 agrupa 19 variantes coherentes
→ confianza 100, banda automatico
```

---

## 8. Preguntas estratégicas

### 8.1 ¿Cómo evitaría que el problema se genere nuevamente?

El problema no se arregla aguas abajo. Cinco intervenciones, ordenadas por impacto
sobre esfuerzo:

| # | Intervención | Impacto | Esfuerzo |
|---|---|---|---|
| 1 | **Autocompletado contra el maestro** en el formulario de vinculación. El asesor escribe 3 letras y elige de una lista; el sistema guarda el `id_empleador`, no el texto. | Elimina el 80-90 % del problema en origen | Medio |
| 2 | **Ampliar los campos a `VARCHAR(200)`** en los dos sistemas fuente. Los truncamientos a 30 y 40 caracteres son pura pérdida de información, irrecuperable. | Elimina 20.532 casos límite | Bajo |
| 3 | **Preservar tildes y eñes** (`UTF-8` extremo a extremo). La normalización destructiva actual borra información de desambiguación. | Mejora precisión de matching | Bajo |
| 4 | **Campos separados** para empleador, sucursal y cargo. Hoy los tres viven en una sola casilla y hay que separarlos por heurística. | Elimina una capa completa del pipeline | Medio |
| 5 | **Validación en línea** que rechace direcciones y anotaciones operativas en el campo de empleador. | 1.928 direcciones + 899 anotaciones | Bajo |

**Regla de gobierno:** ninguna captura nueva debe poder crear un empleador que no
exista en el maestro sin pasar por una excepción registrada. Un dato que solo se
puede limpiar después es un dato que se seguirá ensuciando.

### 8.2 ¿Cómo construiría un maestro corporativo empresarial?

El maestro que produce este pipeline (`salidas/maestro_corporativo.csv`) es el
punto de partida, no el destino. Un maestro corporativo de banco necesita cuatro
capas:

**Capa 1 — Identidad.** `id_empleador` estable y opaco, nunca derivado del nombre
(un nombre cambia; el identificador no). Razón social canónica, nombre comercial,
RUC/RUC-DV cuando exista, forma societaria, estado de vigencia.

**Capa 2 — Estructura.** Relación matriz-subsidiaria-sucursal. Es lo que convierte
"323.000 nombres" en "un grupo económico con exposición consolidada". Los códigos de
sucursal que ya detectamos (§2.4) son la semilla natural.

**Capa 3 — Atributos de riesgo.** Sector CIIU, tamaño (nómina estimada por número
de clientes vinculados), antigüedad, formalidad (¿tiene Aviso de Operación?),
concentración geográfica.

**Capa 4 — Gobierno.** Dueño de datos designado, proceso de altas con aprobación,
versionado de cada cambio, log de quién modificó qué y cuándo, y **reconciliación
periódica** contra el Registro Público.

**Cómo se construye, en orden:**

1. Cargar el maestro generado por este pipeline como base (200.373 entidades).
2. Enriquecer la cabeza de la distribución —los 5.000 empleadores que concentran el
   grueso de la cartera— contra Registro Público y Panamá Emprende. Cubre la mayor
   parte de la exposición con esfuerzo acotado.
3. Publicar el servicio de búsqueda que alimenta el autocompletado (§8.1).
4. Definir el proceso de altas: todo empleador nuevo entra por ahí, no por captura
   libre.
5. Reconciliar mensualmente contra las fuentes públicas; los cambios de razón social
   y las disoluciones son señales de riesgo por sí mismas.

### 8.3 ¿Qué fuentes externas agregaría?

| Fuente | Qué aporta | Prioridad |
|---|---|---|
| **Registro Público de Panamá** | Razón social exacta, forma societaria, vigencia, directores, disoluciones | **Alta** |
| **Panamá Emprende / Aviso de Operación** | Actividad económica declarada, ubicación, formalidad del comercio | **Alta** |
| **DGI — RUC** | Identificador fiscal, el ancla más fuerte para deduplicar | **Alta** |
| **Caja de Seguro Social** | Tamaño real de nómina — el mejor proxy de estabilidad del empleador | Alta (requiere convenio) |
| **Directorio de instituciones del Estado** | Cierra el sector público, que es empleador masivo en Panamá | Media |
| **Superintendencia de Bancos / SMV** | Entidades reguladas y su estado | Media |
| **ACP y autoridades autónomas** | Régimen laboral propio, empleadores de alta estabilidad | Media |
| **LinkedIn / sitios corporativos** | Tamaño, sector y presencia para empresas medianas | Baja |
| **Listas de sanciones (OFAC, ONU, UE)** | Riesgo reputacional y de cumplimiento | Alta para compliance |

**Orden de aplicación:** RUC (determinístico) → Registro Público (razón social) →
Panamá Emprende (actividad) → resto. Cada fuente debe registrar *cuándo* se
consultó: un dato externo sin fecha de vigencia es una suposición.

### 8.4 ¿Qué KPIs de calidad de datos monitorearía?

**Tablero operativo — se mide en cada carga:**

| KPI | Definición | Valor hoy | Meta |
|---|---|---:|---:|
| Tasa de identificación | Registros con empleador identificable | 96,26 % | > 98 % |
| Cobertura sectorial | Registros con CIIU asignado | 51,47 % | > 90 % |
| Tasa de consolidación | 1 − (empleadores únicos / registros) | 35,5 % | Estable ±3 pp |
| Confianza automática | Registros en banda ≥ 85 | 11,6 % | > 60 % |
| Tasa de truncamiento | Registros en el tope del campo | 6,36 % | **0 %** |
| Direcciones en el campo | Registros clasificados como dirección | 0,60 % | < 0,1 % |
| Anotaciones operativas | `CLIENTE FALLECIDO`, `MENOR DEPENDIENTE` | 0,28 % | 0 % |
| Registros vacíos o ruido | Cadenas sin significado | 0,02 % | 0 % |

**Tablero de deriva — se compara contra la carga anterior:**

- **Empleadores nuevos por carga.** Un salto indica que el autocompletado se
  desactivó o que entró una fuente nueva sin normalizar.
- **Variantes nuevas de empleadores existentes.** Debería tender a cero si el
  autocompletado funciona. Es el KPI que mide si el problema se está volviendo a
  generar.
- **Distribución sectorial vs. período anterior.** Un desplazamiento brusco es señal
  de cambio en las reglas, no en la economía.
- **Longitud media del nombre.** Cae cuando alguien reduce un campo.
- **Tasa de reingreso a fase 7.** Cuánto del corpus sigue necesitando validación
  externa; debería bajar en cada corrida a medida que el maestro crece.

**Alertas, no reportes.** Un KPI que solo se ve en un tablero mensual no previene
nada. Los cinco de deriva deben disparar alerta automática ante desviación > 2σ.

### 8.5 ¿Qué variables de riesgo derivaría?

**Del empleador, directamente:**

| Variable | Construcción | Uso |
|---|---|---|
| `sector_ciiu` | Este pipeline | Segmentación, concentración, stress testing sectorial |
| `tamano_empleador` | Nº de clientes del banco vinculados al mismo `id_empleador` | Proxy de estabilidad; empleadores grandes → menor rotación |
| `es_sector_publico` | Sección CIIU = O | Estabilidad laboral marcadamente distinta en Panamá |
| `antiguedad_empleador` | Fecha de constitución (Registro Público) | Empleadores jóvenes concentran más riesgo |
| `formalidad` | ¿Aviso de Operación vigente? ¿RUC activo? | Discriminante fuerte en el segmento PyME |
| `estabilidad_empleador` | Rotación observada de clientes que declaran ese empleador | Predictor directo de continuidad de ingreso |

**De la cartera, agregando:**

| Variable | Construcción | Uso |
|---|---|---|
| `concentracion_empleador` | Exposición del banco a un solo empleador | **Riesgo correlacionado.** Si una empresa despide, todos sus empleados fallan juntos |
| `concentracion_sectorial` | Exposición por sección CIIU | Insumo directo de stress testing e ICAAP |
| `HHI_sectorial` | Índice de Herfindahl sobre la distribución sectorial | Métrica única de diversificación para comité |
| `sensibilidad_ciclica` | Sector ponderado por su beta al PIB | Proyección de PD bajo escenarios macro |

**Para modelos de originación y comportamiento:**

- **`pd_sectorial`** — tasa de incumplimiento observada del sector como variable
  explicativa. Es la aplicación más inmediata y probablemente la de mayor lift.
- **`cambio_de_empleador`** — detectado al comparar cargas. Un cambio de empleador
  es un evento de riesgo observable que hoy es invisible.
- **`match_empleador_ingreso`** — coherencia entre el ingreso declarado y el rango
  típico del sector. Detector de sobreestimación de ingresos en originación.
- **`calidad_del_dato`** — el score de confianza de este pipeline entra como
  variable. Un cliente cuyo empleador no se pudo identificar es, en sí mismo, una
  señal: o el dato se capturó mal, o el empleador es informal.

**La variable con mayor valor esperado es `concentracion_empleador`.** Hoy el banco
no puede responder "¿cuánta exposición tengo a los empleados de un solo empleador?"
porque el mismo empleador aparece con 60 grafías distintas. Este pipeline convierte
esa pregunta en una consulta de una línea. Es riesgo correlacionado no medido, que
es el tipo de riesgo que sorprende a los comités.

---

## 9. Casos límite y cómo se tratan

| Caso | Volumen | Tratamiento |
|---|---:|---|
| Nombre truncado en el tope del campo | 20.532 | Regla de prefijo con distancia asimétrica; penalización en confianza si no hay variante completa |
| Direcciones en lugar de empleador | 1.829 | `No identificable - Direcciones`. Token fuerte de vía basta; los débiles necesitan respaldo. Tres guardas evitan confundir negocio con inmueble: sufijo societario, orden de aparición y el giro «Casa de X» (D10) |
| Situación laboral, no empleador | 3.630 | `AMA DE CASA`, `JUBILADO`, `DESEMPLEADO` → categoría propia |
| Anotaciones del sistema de originación | 899 | `CLIENTE FALLECIDO`, `MENOR DEPENDIENTE`. **No estaban previstos en el enunciado**; se descubrieron al revisar los clústeres más grandes |
| Persona natural como empleador | 452 | Empleador válido en Panamá; se marca aparte para no contaminar el maestro corporativo como sociedad |
| Cargo en lugar de empleador | 114 | Solo si el registro es *únicamente* el cargo |
| Cadena vacía o de relleno | 60 | `No identificable - Falta informacion` |
| Nombre de una sola palabra | 22.123 | **No se descarta.** El enunciado lo prohíbe explícitamente. `VEOLIA`, `LOREAL`, `KUBOX` son reales |
| Marca con número propio | — | Lista de excepciones: `SUPER 99`, `CANAL 13`, `MULTI 24` |
| Empresa con iniciales | — | Las iniciales se conservan en la clave. Filtrarlas colapsaba 111 empresas distintas en `INVERSIONES` |
| Propiedad horizontal (`PH X`) | 1.378 | **Es un empleador, no un inmueble.** Persona jurídica bajo la Ley 31 de 2010, con RUC y planilla. Se excluye si hay indicador de unidad (`APTO`, `AP`) o token fuerte de vía (D12) |
| Sigla escrita con letras sueltas | 196 | `P H MULTIPLAZA` se une antes de tokenizar, o no coincide con las 957 que la escriben junta |

---

## 9.1 El ciclo de revisión: cinco defectos que las métricas no mostraban

Tras la primera entrega completa, una revisión de resultados sobre filas concretas
—no sobre agregados— produjo cinco correcciones. Se documentan porque el patrón es más
útil que los casos.

| # | Defecto | Cómo se veía | Registros |
|---|---|---|---:|
| D9 | CSV sin BOM UTF-8 | Excel mostraba `ConstrucciÃ³n` | los 6 entregables |
| D8 | «No identificable» dicho de algo identificado | `Seimo de Costa Rica, S.A.` marcada como no identificable | 148.200 |
| D10 | La dirección ganaba los empates contra el negocio | `Hotel Plaza Herrera S.A.` clasificado como dirección | 1.079 |
| D11 | Fuzzy para identidades, exacto para vocabulario | `Tranporte Conrad` sin sector pese a ser evidente | 20.707 |
| D12 | `PH` tratado como «edificio» | 1.040 propiedades horizontales mal categorizadas | 1.378 |
| D13 | Diccionario ancla ausente; criterio propiedad vs actividad sin declarar | La Lotería y las policlínicas en la categoría discutida | 9.308 |
| D14 | Tokens genéricos con peso de específicos | `Instituto de Recursos Hidráulicos` en Enseñanza | ~900 |
| D15 | Gazetteer comparando subcadenas, no tokens | `Corporación Bellavista` clasificada como alquiler de autos (`AVIS`) | 252 |
| D16 | Huecos de catálogo visibles solo en el residuo | `Primer Ciclo de Parita` sin sector | ~4.000 |
| D17 | Zona de duda sin explotar | 15.427 pares esperando la fase 7 sin usarse | 441 |
| D18 | «Sin empleador corporativo» tratado como «sin información» | `Abogada independiente` sin sector | 1.677 |
| D19 | Lo mismo, sin generalizar a los inactivos | `Jubilado de la Caja del Seguro Social` sin sector | 1.377 |
| D20 | Todas las situaciones laborales en un solo cajón «no identificable» | `Ama de casa` indistinguible de `Cliente fallecido` | 4.346 |
| D21 | El archivo de revisión filtraba el bloque contrario al revisado | Herramienta inútil para el problema real | — |

**D8-D11 y D14-D15 comparten causa: dos categorías que comparten vocabulario, y un ganador
elegido implícitamente.** «Plaza» es dirección y es hotel; `PH` es edificio y es persona
jurídica; el fuzzy servía para identidades y no para vocabulario, sin razón de diseño.
En cada caso había una decisión tomada por el orden del código en lugar de por un criterio
escrito.

Tres consecuencias que quedan incorporadas al método:

1. **Ninguno aparecía en las métricas agregadas.** La cobertura sectorial subía o bajaba
   un punto; nada señalaba que 148.200 filas llevaran una etiqueta falsa. Solo se ven
   leyendo filas.
2. **Una de las cinco no era derivable del dato.** `PH` es una sigla local con estatuto
   jurídico. Sin ese contexto, «edificio, luego dirección» era la lectura razonable y
   equivocada. El vocabulario de negocio no se infiere del corpus: se pregunta. Es el
   motivo por el que `reglas.py` está separado del motor.
3. **Cada guarda nueva se midió antes de escribirse.** El matching aproximado se probó
   primero sin guardas, se midieron sus falsos positivos (`Movistar Empresas`,
   `Reconstruction Car Center`, `Arqmarcela Herrera`) y cada guarda existe porque uno de
   ellos la exigió. Están registradas en `DECISIONS.MD` con el caso que las motivó, para
   que nadie las retire por parecer arbitrarias.

**D12, D13 y D16 son de otra clase y de mayor rendimiento: conocimiento de dominio que no
está en el dato.** Que `PH` sea una figura jurídica con planilla propia, que el sector lo
decida la actividad y no la propiedad, o que `Primer Ciclo` sea un nivel del sistema
educativo panameño, no se infieren del corpus por mucho que se lo analice. Se aportan. Es
la justificación de que `reglas.py` esté separado del motor: integrar 125 entidades nuevas
fue editar un diccionario, no rediseñar nada.

Efecto acumulado: cobertura sectorial 52,8 % → **60,7 %**; confianza en banda automática
10,5 % → **11,5 %**; `No identificable - Falta informacion` de 148.260 a **250** registros;
cola de validación externa de 103.139 a **89.148** clústeres.

---

## 10. Escalabilidad a millones de registros

| Aspecto | Hoy (323 K) | A 10 M |
|---|---|---|
| Complejidad del bloqueo | O(n · k), k = tamaño medio de bloque | Igual. El tope de bloque (120) acota el crecimiento |
| Tiempo bloque 1 | 30 s | ~15 min · paralelizable por partición |
| Tiempo bloque 2 | 45 s | ~40 min con `rapidfuzz` multi-hilo |
| Memoria | 1,2 GB | Requiere procesamiento por lotes o Spark |
| Fase 7 | Solo sobre clústeres dudosos | Crece *sublinealmente*: el maestro absorbe cada vez más casos |

**Lo que hay que cambiar para producción a escala:**

1. **Almacenamiento columnar** (Parquet o Delta) en lugar de CSV. Se usó CSV porque
   `pyarrow` no tiene wheel para Windows ARM64 — es una restricción del entorno de
   desarrollo, no del diseño.
2. **Bloqueo distribuido**: el índice invertido particiona naturalmente por token.
3. **Procesamiento incremental**: solo los registros nuevos entran al pipeline; los
   existentes se resuelven contra el maestro con una consulta.
4. **Message Batches API** para la fase 7: 50 % del costo, hasta 100.000 solicitudes
   por lote.
5. **El maestro es el activo que se acumula.** Cada corrida lo enriquece, y cada
   enriquecimiento reduce el trabajo de la siguiente. En régimen, la fase 7 solo ve
   empleadores genuinamente nuevos.

---

## 11. Reproducibilidad

```bash
# Entorno (Python 3.12, aislado)
python -m venv .venv
.venv\Scripts\python.exe -m pip install pandas numpy rapidfuzz openpyxl anthropic

# Pipeline completo — ~2 minutos
.venv\Scripts\python.exe codigo/00_perfilamiento.py       # evidencia del diagnóstico
.venv\Scripts\python.exe codigo/01_limpieza.py            # fases 1-4
.venv\Scripts\python.exe codigo/02_matching.py            # fases 5-6
.venv\Scripts\python.exe codigo/03_canonico_sector.py     # fases 8, 9, 11
.venv\Scripts\python.exe codigo/04_enriquecimiento.py --estimar   # fase 7: costo
.venv\Scripts\python.exe codigo/04_enriquecimiento.py --todo      # fase 7: ejecutar
.venv\Scripts\python.exe codigo/05_salida.py              # fases 10, 12
```

Todos los pasos son idempotentes. El archivo fuente nunca se modifica.

### Estructura del código

| Módulo | Responsabilidad |
|---|---|
| `comun.py` | Rutas, entrada/salida, Union-Find, cronometraje |
| `reglas.py` | **Base de conocimiento.** Separada del motor a propósito: es la pieza que un analista de negocio debe poder revisar y ampliar sin tocar código |
| `normalizacion.py` | Limpieza, tipificación, claves de comparación |
| `canonico.py` | Razón social canónica |
| `sector.py` | Clasificación CIIU |
| `confianza.py` | Score explicable |
| `00`-`05_*.py` | Orquestadores por bloque |

---

## 12. Limitaciones declaradas

Lo que este pipeline **no** puede saber, y por qué:

1. **Cuántos clientes reales hay detrás de cada empleador.** El dataset llegó
   deduplicado; no hay frecuencias. Todos los porcentajes están sobre variantes
   únicas, no sobre cartera.
2. **Los nombres completos de los 20.532 registros truncados.** La información se
   perdió en el sistema de origen y no es recuperable desde este archivo.
3. **Si el empleador está activo.** Requiere Registro Público.
4. **El sector real de los 89.720 clústeres sin evidencia interna.** Requiere la
   fase 7 o una fuente externa.
5. **Tildes y eñes.** Destruidas aguas arriba de forma irreversible.

Cada una de estas limitaciones tiene una acción asociada en §8.1 o §8.3. Ninguna se
resuelve con más procesamiento sobre el mismo archivo.
