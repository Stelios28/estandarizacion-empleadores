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
| Empleadores identificados | 310.579 · 96,15 % |
| Empleadores únicos (maestro) | 200.373 |
| Consolidación de variantes | 35,5 % |
| Con sector CIIU | 185.230 · 59,64 % de los empleadores |
| Confianza promedio / mediana | 51,8 / 53 |
| Pares evaluados | 7,4 M de 30.446 M (0,024 %) |

Bandas: automático 37.478 (11,6 %) · muestreo 91.197 (28,2 %) · revisión 62.559 (19,4 %) ·
verificación individual 131.767 (40,8 %).

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
- **R8 Cobertura sectorial 59,6 %** — abierto. Se cierra solo con la fase 7
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
- Pipeline completo sobre 323.001 registros — 96,15 % identificación, 200.373 empleadores únicos, 59,6 % cobertura sectorial — 2026-08-08
- 18 casos de desambiguación de tokens genéricos, revisados uno a uno — 18/18 — 2026-08-08
- Propagación por zona de duda: 441 clústeres, muestra revisada con origen y destino juntos — 2026-08-08
- Diccionario ancla: 275 anclas activas sobre 9.308 registros — 2026-08-08
- 25 casos de tipificación dirección/negocio, revisados uno a uno — 25/25 — 2026-08-07
- 9 casos de propiedad horizontal (entidad vs domicilio), revisados uno a uno — 9/9 — 2026-08-07
- 5 casos de control del matching aproximado (falsos positivos esperados), rechazados — 5/5 — 2026-08-07
- Estimación de fase 7 contra la API real de precios — USD 149 / USD 75 por lotes — 2026-08-07

## Lección transversal del ciclo de revisión
**Familia 1 — categorías que comparten vocabulario, con un ganador elegido
implícitamente** (D8, D10, D11, D14, D15). «Plaza» es dirección y es hotel; `PH` es
edificio y es persona jurídica; `AVIS` está dentro de `BELLAVISTA`. Ninguna aparecía en
las métricas agregadas: todas salieron de mirar filas concretas.

**Familia 2 — conocimiento de dominio que no está en el dato** (D12, D13, D16). Que `PH`
sea una figura jurídica con planilla, que el sector lo decida la actividad y no la
propiedad, o que `Primer Ciclo` sea un nivel del sistema educativo panameño, no se
infieren del corpus. Se aportan. Es la familia de mayor rendimiento por esfuerzo, y la
razón de que `reglas.py` esté separado del motor.

**Familia 3 — evidencia disponible sin usar** (D17). Los 15.427 pares de la zona de duda
llevaban todo el proyecto esperando la fase 7 sin aportar nada más.

## Próxima mejor acción
**Los recursos determinísticos están agotados.** Lo que queda en la cola son nombres
genuinamente opacos (`Tricom`, `Cbtelsa`, `Damax Marbella`): el texto no contiene la
actividad, así que ninguna regla puede derivarla.

Exportar `ANTHROPIC_API_KEY` y correr la fase 7 acotada a los 21.604 clústeres de 2+
registros (~USD 7 con Haiku 4.5), luego `codigo/05_salida.py`. Conviene probar antes con
`--presupuesto 20` (~USD 1, 800 nombres) para juzgar la calidad de las respuestas.
