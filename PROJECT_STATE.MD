# Project State

## Proyecto
Prueba técnica de Ingeniería de Datos: pipeline que estandariza empleadores capturados
como texto libre (323.001 variantes, Panamá) en nombre canónico + sector CIIU Rev. 4,
con score de confianza y explicación por registro.

## Estado global
Entregable completo y ejecutado. Cerrado un ciclo de revisión de calidad con Javier que
produjo diez correcciones (D8-D17). Solo queda la fase 7 (validación externa), que está
construida y probada en su ruta de estimación pero no ejecutada: requiere credencial.

## Misión activa
Agotar los recursos determinísticos antes de gastar en fase 7 (instrucción de negocio).
Cola actual: 93.501 clústeres; 22.801 de ellos aparecen 2+ veces.
Criterio de cierre: cobertura sectorial > 90 % y banda de confianza automática > 50 %.

## Resultados medidos

| Métrica | Valor |
|---|---:|
| Registros procesados | 323.001 |
| Empleadores identificados | 310.684 · 96,19 % |
| Empleadores únicos (maestro) | 200.377 |
| Consolidación de variantes | 35,4 % |
| Con sector CIIU | 185.230 · 59,64 % de los empleadores |
| Confianza promedio / mediana | 49,8 / 53 |
| Pares evaluados | 7,4 M de 30.446 M (0,024 %) |

Bandas: automático 30.453 (9,4 %) · muestreo 92.007 (28,5 %) · revisión 58.624 (18,2 %) ·
verificación individual 141.917 (43,9 %).

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
- **D13** — Diccionario de 185 empleadores ancla de Panamá; el sector lo decide la
  **actividad del lugar de trabajo, no la propiedad** (criterio INEC / Naciones Unidas)
- **D14** — Auditoría de tokens genéricos con peso de específicos: `INSTITUTO`, `SUPER`,
  `GLOBAL`, `SOCIAL SECURITY`, bancos multilaterales, DHL, «esperando nombramiento»
- **D15** — Reguladores del Estado a administración pública; gazetteer comparando por
  token y no por subcadena (`AVIS` casaba dentro de `BELLAVISTA`)
- **D16** — Vocabulario derivado del conteo de frecuencias sobre el residuo sin sector
- **D17** — Oficios de la cola larga por sufijo español (curados a mano) y propagación
  de sector por la zona de duda, con guardas de evidencia fuerte y de nombre propio

## Pendientes prioritarios
- **Alta** — Decidido por negocio: los clústeres de una sola aparición no aportan al
  análisis de concentración. La fase 7 debe correr sobre los de 2+ registros (21.604
  clústeres): ~USD 7 con Haiku 4.5. Los recursos determinísticos están agotados
- **Bloqueante** — API key de Anthropic para ejecutar la fase 7 (`ANTHROPIC_API_KEY`)
- **Media** — Decidir modelo de fase 7: Opus 5 (~USD 140) o Haiku 4.5 (~USD 28); con Batches API, la mitad
- **Baja** — Ampliar `reglas.py` con más vocabulario local de Panamá aportado por negocio
- **Baja** — Migrar intermedios a Parquet si el proyecto sale de Windows ARM64

## Riesgos o bloqueos
- **R0 Entorno** — resuelto con D4/D5. scipy y sklearn siguen bloqueados por App Control (no se desactivó: es irreversible)
- **R1 Sobre-agrupación** — mitigado con guarda de cohesión entre representantes; 2.340 fusiones descartadas
- **R2 Sin frecuencias** — mitigado: el canónico se elige por calidad ortográfica medida sobre el corpus
- **R3 Truncamiento** — mitigado: 20.532 registros tratados con regla de prefijo asimétrica
- **R7 Costo fase 7** — acotado: caché persistente, lotes de 40, presupuesto por corrida, prioridad por volumen
- **R8 Cobertura sectorial 57,6 %** — abierto. Se cierra solo con la fase 7
- **R11 IPAT en agencias de viajes** — cerrado con D15: pasó a administración pública
- **R12 Asociaciones de padres de familia** — abierto, 11 registros. Caen en Enseñanza
  porque la frase de la escuela es más larga; no se fuerza por volumen
- **R9 Etiquetado de estados** — cerrado con D8
- **R10 Vocabulario de negocio** — abierto por diseño. D12 mostró que hay reglas de dominio
  que no se infieren del corpus; se cierran preguntando, y `reglas.py` está separado del
  motor para que se puedan aportar sin tocar código

## Archivos actualmente afectados
- `prueba_tecnica_ing_datos.xlsx` — fuente de verdad, **solo lectura, nunca modificada**
- `codigo/` — 6 orquestadores + 6 módulos (reglas, normalización, canónico, sector, confianza, común)
- `salidas/` — 6 entregables generados
- `Documentacion/DOCUMENTO_TECNICO.MD` — documento técnico con las 5 preguntas estratégicas
- `Documentacion/PROPUESTA_EVOLUCION.MD` — evolución del producto analítico
- `Documentacion/Mantenimiento/` — perfilamiento y decisiones

## Última validación
- Pipeline completo sobre 323.001 registros — 96,19 % identificación, 200.456 empleadores únicos, 57,6 % cobertura sectorial — 2026-08-08
- Diccionario ancla: 275 anclas activas sobre 9.308 registros — 2026-08-08
- 25 casos de tipificación dirección/negocio, revisados uno a uno — 25/25 — 2026-08-07
- 9 casos de propiedad horizontal (entidad vs domicilio), revisados uno a uno — 9/9 — 2026-08-07
- 5 casos de control del matching aproximado (falsos positivos esperados), rechazados — 5/5 — 2026-08-07
- Estimación de fase 7 contra la API real de precios — USD 149 / USD 75 por lotes — 2026-08-07

## Lección transversal del ciclo de revisión
D8-D11 comparten causa: **dos categorías que comparten vocabulario, y un ganador elegido
implícitamente.** Ninguna aparecía en las métricas agregadas — todas salieron de mirar
filas concretas.

D12 y D13 son de otra clase y de mayor rendimiento: **conocimiento de dominio que no está
en el dato.** `PH` como figura jurídica y el criterio actividad-sobre-propiedad no se
infieren del corpus por mucho que se lo analice. Se aportan. Por eso `reglas.py` está
separado del motor, y por eso integrar 125 entidades nuevas fue editar un diccionario y no
rediseñar nada.

## Próxima mejor acción
Exportar `ANTHROPIC_API_KEY` y correr la fase 7 acotada a los clústeres de 2+ registros
(~USD 7 con Haiku 4.5), luego `codigo/05_salida.py`. Antes de eso, seguir agotando reglas
determinísticas con vocabulario aportado por negocio: es gratis y rinde más.
