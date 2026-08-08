# Project State

## Proyecto
Prueba técnica de Ingeniería de Datos: pipeline que estandariza empleadores capturados
como texto libre (323.001 variantes, Panamá) en nombre canónico + sector CIIU Rev. 4,
con score de confianza y explicación por registro.

## Estado global
Entregable completo y ejecutado. Cerrado un ciclo de revisión de calidad con Javier que
produjo cinco correcciones (D8-D12). Solo queda la fase 7 (validación externa), que está
construida y probada en su ruta de estimación pero no ejecutada: requiere credencial.

## Misión activa
Ejecutar la fase 7 sobre los 95.922 clústeres sin sector.
Criterio de cierre: cobertura sectorial > 90 % y banda de confianza automática > 50 %.

## Resultados medidos

| Métrica | Valor |
|---|---:|
| Registros procesados | 323.001 |
| Empleadores identificados | 316.408 · 97,96 % |
| Empleadores únicos (maestro) | 204.393 |
| Consolidación de variantes | 35,4 % |
| Con sector CIIU | 177.955 · 56,24 % de los empleadores |
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

## Pendientes prioritarios
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
- **R8 Cobertura sectorial 56,2 %** — abierto. Se cierra solo con la fase 7
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
- Pipeline completo sobre 323.001 registros — 97,96 % identificación, 204.393 empleadores únicos, 56,2 % cobertura sectorial — 2026-08-08
- 25 casos de tipificación dirección/negocio, revisados uno a uno — 25/25 — 2026-08-07
- 9 casos de propiedad horizontal (entidad vs domicilio), revisados uno a uno — 9/9 — 2026-08-07
- 5 casos de control del matching aproximado (falsos positivos esperados), rechazados — 5/5 — 2026-08-07
- Estimación de fase 7 contra la API real de precios — USD 149 / USD 75 por lotes — 2026-08-07

## Lección transversal del ciclo de revisión
Las cinco correcciones D8-D12 comparten causa: **dos categorías que comparten vocabulario,
y un ganador elegido implícitamente.** Ninguna aparecía en las métricas agregadas — todas
salieron de mirar filas concretas. La inspección manual de la cabeza de la distribución es
parte del ciclo, no un extra.

## Próxima mejor acción
Exportar `ANTHROPIC_API_KEY` y ejecutar `codigo/04_enriquecimiento.py --todo`, luego
`codigo/05_salida.py` para regenerar los entregables con la cobertura sectorial completa.
