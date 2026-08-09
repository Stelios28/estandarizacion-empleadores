# Project State

## Proyecto
Prueba técnica de Ingeniería de Datos: pipeline que estandariza empleadores capturados
como texto libre (323.001 variantes, Panamá) en nombre canónico + sector CIIU Rev. 4,
con score de confianza y explicación por registro.

Repositorio público: `https://github.com/Stelios28/estandarizacion-empleadores`
El dataset de origen **no** está versionado: es cartera de clientes de un banco.

## Estado global
Entregable completo y ejecutado. Cerrado un ciclo de revisión de calidad con Javier que
produjo **veinticinco correcciones (D8-D32)**. Solo queda la fase 7 (validación externa),
que está construida, auditada en seco y probada en su ruta de estimación, pero **nunca
ejecutada**: requiere credencial.

## Misión activa
Agotar los recursos determinísticos antes de gastar en fase 7 (instrucción de negocio).
**Estado: agotados, con tres señales medidas** — ver D28 y D29.
Criterio de cierre original: cobertura sectorial > 90 %. No se alcanza sin fase 7.

## Resultados medidos

| Métrica | Valor |
|---|---:|
| Registros procesados | 323.001 |
| Empleadores identificados | 309.553 · 95,84 % |
| Empleadores únicos (maestro) | 198.516 |
| Consolidación de variantes | 35,9 % |
| Con sector CIIU | 196.224 · 63,39 % de los empleadores |
| Confianza promedio / mediana | 54,1 / 59 |
| Pares evaluados | 7,4 M de 30.446 M (0,024 %) |

Bandas: automático 41.366 (12,8 %) · muestreo 102.750 (31,8 %) · revisión 56.638
(17,5 %) · verificación individual 122.247 (37,8 %).

## Cómo se corre

```
.venv\Scripts\python.exe codigo\01_limpieza.py
.venv\Scripts\python.exe codigo\02_matching.py
.venv\Scripts\python.exe codigo\03_canonico_sector.py
.venv\Scripts\python.exe codigo\04_enriquecimiento.py --estimar   # no gasta
.venv\Scripts\python.exe codigo\05_salida.py
```

Cualquier cambio en `reglas.py` obliga a rehacer 01→02→03→05. Toma ~4 minutos.
Si un `.xlsx` de `salidas/` está abierto en Excel, la fase 5 avisa y sigue (D25).

## Decisiones vigentes
- **D1** — Pipeline completo ejecutable sobre los 323.000 registros, con los 5 entregables
- **D2** — Validación externa con LLM, solo sobre representantes de clúster, con caché
- **D3** — Sector económico en CIIU Rev. 4 (sección + división)
- **D4** — Python 3.12 en venv dedicado (ejecutada)
- **D5** — Sin scipy/scikit-learn: bloqueados por App Control; bloqueo rediseñado sobre índice invertido + rapidfuzz
- **D6** — Precisión sobre cobertura: no se asigna sector sin evidencia
- **D7** — Tres correcciones de calidad halladas por inspección manual del maestro
- **D8** — `Pendiente de validación externa` ≠ `Falta información`: 148.260 → 60 registros
- **D9** — CSV entregables con BOM UTF-8 (Excel los abría en ANSI)
- **D10** — Tres guardas negocio/inmueble: sufijo societario, orden de aparición, giro «Casa de X»
- **D11** — Consulta aproximada al catálogo: morfología + errata, con cuatro guardas
- **D12** — `PH` = propiedad horizontal: persona jurídica con planilla, no un inmueble
- **D13** — Diccionario de empleadores ancla de Panamá; el sector lo decide la
  **actividad del lugar de trabajo, no la propiedad** (criterio INEC / Naciones Unidas)
- **D14** — Auditoría de tokens genéricos con peso de específicos
- **D15** — Reguladores del Estado a administración pública; gazetteer comparando por
  token y no por subcadena (`AVIS` casaba dentro de `BELLAVISTA`)
- **D16** — Vocabulario derivado del conteo de frecuencias sobre el residuo sin sector
- **D17** — Oficios de la cola larga por sufijo español y propagación de sector por la
  zona de duda, con guardas de evidencia fuerte y de nombre propio
- **D18** — El oficio del trabajador independiente es un sector
- **D19** — El jubilado nombra a su empleador y el estudiante a su universidad
- **D20** — Cada situación laboral es una categoría propia, no un cajón «no identificable»
- **D21** — Corrección de D20: el archivo de revisión filtraba al revés
- **D22** — Lo hallado en el bloque chico paga en el grande: corrector de erratas
  derivado del corpus (3.298 registros), sección T de la CIIU, anotaciones por prefijo
- **D23** — Muestreo aleatorio como tercera vista: `M S` = Mini Super (463),
  `FINCA` deja de ser dirección (212), `PLANILLA` es nómina y no empleador (62)
- **D24** — El giro pegado al nombre (`REFRICAR`): nivel nuevo de prefijos comerciales
- **D25** — Mirar la cabeza de la cola: multinacionales, casas comerciales panameñas y
  bufetes (1.859 registros). Un `.xlsx` abierto ya no mata la corrida
- **D26** — Sesgo de idioma: el catálogo estaba en español y media plaza trabaja
  en inglés (`CLEAN`, `DESIGN`, `BAKERY`, `NAILS`) — 3.476 registros
- **D27** — Auditar lo clasificado, no solo lo que falta: 1.085 clasificaciones
  falsas retiradas. La cobertura baja a propósito, por primera vez
- **D28** — R13 cerrado (la propagación estaba sana) y el vocabulario del residuo se
  agota: lo que queda no nombra su actividad
- **D29** — Auditado el último bloque (situación laboral): rinde 3 %
- **D30** — Auditada la columna `nombre_propuesto`: la Ñ destruida partía palabras
  (`COMPA IA`, `PANAME A`) y duplicaba 141 empleadores en el maestro
- **D31** — La misma reconstrucción derivada del corpus en vez de enumerada:
  `NU EZ`→`NUNEZ`, `ORDO EZ`→`ORDONEZ`. Regla que no envejece, no lista
- **D32** — Auditada la fase 7 en seco, antes de gastar: el prompt enumera el catálogo
  pero el código no verificaba la respuesta contra él

## Pendientes prioritarios
- **Bloqueante** — `ANTHROPIC_API_KEY` para ejecutar la fase 7
- **Alta** — Decidir modelo. Propuesto a Javier un A/B de **USD 0,70**: los mismos 400
  nombres con Haiku 4.5 y con Opus 5, comparando (a) cuántos declara desconocidos cada
  uno, (b) en cuántos coinciden, (c) los que difieren los juzga él. Sin respuesta aún
- **Alta** — Correr la fase 7 acotada a los **20.152 clústeres de 2+ registros**, que
  cubren el 46,1 % de los registros sin sector: **≈ USD 6 con Haiku 4.5** (USD 3 con
  Batches). El resto son 64.324 clústeres de una sola aparición, que negocio ya declaró
  irrelevantes para el análisis de concentración
- **Baja** — Ampliar `reglas.py` con vocabulario local aportado por negocio
- **Baja** — Migrar intermedios a Parquet si el proyecto sale de Windows ARM64

## Riesgos o bloqueos
- **R0 Entorno** — resuelto con D4/D5. scipy y sklearn siguen bloqueados por App Control
  (**no se desactivó: es irreversible sin reinstalar Windows**)
- **R1 Sobre-agrupación** — mitigado con guarda de cohesión; 2.340 fusiones descartadas
- **R2 Sin frecuencias** — mitigado: el canónico se elige por calidad ortográfica
- **R3 Truncamiento** — mitigado: 20.532 registros con regla de prefijo asimétrica
- **R7 Costo fase 7** — acotado: caché persistente, lotes de 40, presupuesto por corrida,
  prioridad por volumen, y desde D32 verificación de la respuesta contra el catálogo
- **R8 Cobertura sectorial 63,4 %** — abierto. Se cierra solo con la fase 7
- **R10 Vocabulario de negocio** — abierto por diseño: hay reglas de dominio que no se
  infieren del corpus, se cierran preguntando. `reglas.py` está separado del motor
- **R12 Asociaciones de padres de familia** — abierto, 11 registros
- **R13 Propagación por zona de duda** — **cerrado con D28**: se enumeraron los 783 pares
  y solo 3 se apoyan en un topónimo, los tres correctos
- **R14 La Ñ destruida aguas arriba** — abierto y **no resoluble desde aquí**. Medido en
  D30: 2.280 ocurrencias y al menos 141 empleadores duplicados. D30 y D31 tapan los casos
  frecuentes; la solución de fondo es pedir el campo sin esa transformación
- **R9 / R11** — cerrados con D8 y D15

## Archivos actualmente afectados
- `prueba_tecnica_ing_datos.xlsx` — fuente de verdad, **solo lectura, nunca modificada**
- `codigo/` — 6 orquestadores + 6 módulos (reglas, normalización, canónico, sector, confianza, común)
- `salidas/` — 6 entregables + `revision_pendiente.xlsx` (archivo de trabajo, 2 hojas)
- `Documentacion/DOCUMENTO_TECNICO.MD` — las 5 preguntas estratégicas
- `Documentacion/PROPUESTA_EVOLUCION.MD` — evolución del producto analítico
- `Documentacion/Mantenimiento/DECISIONS.MD` — D1-D32, cada una con motivo y evidencia

## Cómo se revisa (ciclo establecido con Javier)
`salidas/revision_pendiente.xlsx` tiene dos hojas:
- **`por revisar`** — todo lo no resuelto, alfabético, con columna `bloque` para filtrar:
  Empleador sin sector · Situación laboral · No identificable
- **`vocabulario`** — cada palabra contada en los tres bloques, para saber cuánto arrastra
  un hallazgo en el bloque grande antes de escribir la regla

Cuatro vistas del residuo, y cada una encuentra cosas distintas:

| Vista | Encuentra | Ejemplo |
|---|---|---|
| Por volumen | El error caro | `INSTITUTO` con peso 9 (D14) |
| Alfabética | La familia | `AMA DE CASA*` (D18-D20) |
| Aleatoria | El patrón sin palabra | `M S` = Mini Super (D23) |
| Cabeza de la cola | La empresa grande que nadie nombró | Maersk, bufetes (D25) |

## Lección transversal del ciclo de revisión
**Familia 1 — categorías que comparten vocabulario, con un ganador elegido
implícitamente** (D8, D10, D11, D14, D15, D24). «Plaza» es dirección y es hotel; `PH` es
edificio y es persona jurídica; `INTERAMERICANA` es carretera y es universidad. Ninguna
aparecía en las métricas agregadas: todas salieron de mirar filas concretas.

**Familia 2 — conocimiento de dominio que no está en el dato** (D12, D13, D16, D25). Que
`PH` sea una figura jurídica con planilla, que el sector lo decida la actividad y no la
propiedad, o que Varela Hermanos haga ron, no se infieren del corpus. Se aportan. Es la
familia de mayor rendimiento por esfuerzo, y la razón de que `reglas.py` esté separado.

**Familia 3 — evidencia disponible sin usar** (D17, D31). Los 15.427 pares de la zona de
duda llevaban todo el proyecto esperando; el vocabulario del propio corpus servía de
diccionario para reconstruir la Ñ.

**Familia 4 — mirar exactamente lo que mira la persona** (D20, D21). Tres iteraciones
mejorando el sector mientras la columna que Javier leía no cambiaba.

**Familia 5 — la métrica que sube sin que nadie compruebe lo que hay debajo** (D27).
Cuatro tiradas subiendo cobertura, y dos de los cuatro defectos más graves los había
introducido la tirada inmediatamente anterior.

## Experimentos probados y descartados
Documentados en el código con su evidencia, para que no se vuelvan a intentar:
- **Aflojar la guarda de prefijo del corrector de erratas** (D23) — ganaba 52 registros y
  perdía 1.200, reabriendo `CONSULTOR → CONSULTORIO`
- **El gazetteer venciendo a la tipificación de dirección, sin más** (D24) — la mitad de
  los casos eran falsos positivos del propio gazetteer (`VIA TOCUMEN` → aeropuerto)
- **Sumar el respaldo ortográfico en vez de tomar el peor token** (D30) — movía 9.947
  registros y perdía entradas del gazetteer. La suma mide «usa palabras comunes», no
  «está bien escrito»

## Última validación
- Pipeline completo sobre 323.001 registros — 95,84 % identificación, 198.516 empleadores
  únicos, 63,39 % cobertura sectorial — 2026-08-08
- Fase 7 auditada en seco: prompt, catálogo (67 pares, sin secciones huérfanas ni
  divisiones ambiguas) y parseo con respuesta simulada — 2026-08-08
- Propagación por zona de duda: los 783 pares enumerados, no muestreados — 2026-08-08
- Reconstrucción de la Ñ derivada del corpus: 17 pares, 98 registros, 100 % correctos — 2026-08-08
- Estimación de fase 7 contra los precios reales — USD 122,67 / USD 61,34 con Batches — 2026-08-08

## Próxima mejor acción
**Los recursos determinísticos están agotados**, con tres señales medidas (D28, D29):
las trece palabras más frecuentes del residuo ya no nombran actividades, el rendimiento
por tirada cayó de 1.859 a 19 registros, y el último bloque sin auditar rindió 3 %.

Lo que queda son nombres genuinamente opacos (`R P CORPORATION S A`, `Tricom`, `Cbtelsa`):
**el texto no contiene la actividad**, así que ninguna regla puede derivarla.

1. Exportar `ANTHROPIC_API_KEY`.
2. Correr el A/B de USD 0,70 (400 nombres con cada modelo) y decidir con datos.
3. Correr la fase 7 sobre los 20.152 clústeres de 2+ registros con el modelo elegido.
4. Volver a correr `codigo/05_salida.py` y actualizar las cifras de los MD.
