# Estandarización de empleadores

Pipeline que convierte **323.001 empleadores capturados como texto libre** en un maestro
corporativo con razón social canónica, sector económico CIIU Rev. 4, score de confianza y
traza de decisión por registro.

Prueba técnica de Ingeniería de Datos · Panamá · 2026

---

## Resultado

| Métrica | Valor |
|---|---:|
| Registros procesados | 323.001 |
| Empleadores identificados | 309.551 · **95,84 %** |
| Empleadores únicos en el maestro | **200.650** |
| Consolidación de variantes | 35,5 % |
| Con sector CIIU asignado | 195.752 · **63,2 %** de los empleadores |
| Pares evaluados | 7,4 M de 30.446 M · **0,024 %** |
| Tiempo de corrida completa | ~2 minutos |

---

## Cómo correrlo

Requiere Python 3.12 y el dataset de origen en la raíz del proyecto
(`prueba_tecnica_ing_datos.xlsx`, no versionado — ver *Datos* más abajo).

```bash
python -m venv .venv
.venv/Scripts/pip install pandas numpy rapidfuzz openpyxl anthropic

.venv/Scripts/python codigo/00_perfilamiento.py      # opcional: evidencia del diseño
.venv/Scripts/python codigo/01_limpieza.py           # fases 1-4
.venv/Scripts/python codigo/02_matching.py           # fases 5-6
.venv/Scripts/python codigo/03_canonico_sector.py    # fases 8, 9, 11
.venv/Scripts/python codigo/05_salida.py             # fases 10, 12
```

Cada fase materializa su salida en `trabajo/` y es reanudable: se puede volver a correr
una fase sin repetir las anteriores.

### Fase 7 — validación externa (opcional, requiere credencial)

```bash
export ANTHROPIC_API_KEY=...
.venv/Scripts/python codigo/04_enriquecimiento.py --estimar        # costo, sin gastar
.venv/Scripts/python codigo/04_enriquecimiento.py --presupuesto 20 # prueba acotada
.venv/Scripts/python codigo/04_enriquecimiento.py --todo
.venv/Scripts/python codigo/05_salida.py                           # regenera entregables
```

Resuelve los 89.148 clústeres cuyo nombre no revela la actividad (`Tricom`, `Cbtelsa`).
Costo medido: ~USD 140 con Opus 5, ~USD 28 con Haiku 4.5, la mitad con la Message Batches
API. Acotado a los 21.492 clústeres que aparecen 2 o más veces —los únicos que pesan en un
análisis de concentración— baja a ~USD 7.

---

## Estructura

```
codigo/
  00_perfilamiento.py     Evidencia sobre la que se tomaron las decisiones de diseño
  01_limpieza.py          Limpieza, normalización, tipificación, matching exacto
  02_matching.py          Bloqueo en 3 canales, matching difuso, clustering
  03_canonico_sector.py   Razón social canónica, sector CIIU, reproceso iterativo
  04_enriquecimiento.py   Validación externa con LLM (fase 7)
  05_salida.py            Score de confianza, entregables y tablas auditables

  reglas.py               BASE DE CONOCIMIENTO — separada del motor a propósito
  normalizacion.py        Limpieza y tipificación del registro
  canonico.py             Elección del representante y construcción del nombre
  sector.py               Cascada de clasificación sectorial
  confianza.py            Score explicable por factores nombrados
  comun.py                E/S, medición de fases, Union-Find

Documentacion/
  DOCUMENTO_TECNICO.MD    12 secciones, con las 5 preguntas estratégicas
  PROPUESTA_EVOLUCION.MD  De pipeline a activo corporativo
  Mantenimiento/
    DECISIONS.MD          D1-D28: cada decisión con su motivo y su evidencia
    NOTAS_PERFILAMIENTO.MD  Hallazgos del perfilamiento, con cifras

PROJECT_STATE.MD          Estado vivo del proyecto
```

**`reglas.py` está separado del motor a propósito.** Es la pieza que un analista de
negocio debe poder revisar y ampliar sin tocar código: sufijos societarios, abreviaturas,
tokens de dirección, marcadores de no-empresa y el mapa de palabras clave a CIIU.

---

## Decisiones de diseño que conviene conocer

**El dataset llegó deduplicado.** 323.000 valores todos distintos, con sufijos numéricos
de uniquificación. Eso invalida la heurística estándar de entity resolution —«la variante
más frecuente es la canónica»—. El canónico se elige por **calidad ortográfica medida
sobre el propio corpus**: `COPA` aparece en muchos registros, `COPAR` en uno.

**La similitud de cadena no separa las poblaciones.** Pares que sí son la misma entidad y
pares que no se solapan entre 76 y 88. No es un umbral mal calibrado, es el límite del
método. Esos 15.427 pares no se fusionan: se marcan como zona de duda, se usan para
propagar sector sin afirmar identidad, y pasan a validación externa.

**El vocabulario de negocio no se infiere del corpus.** Que `PH` sea una persona jurídica
con planilla propia, o que el sector lo decida la actividad del lugar de trabajo y no
quién es el dueño, son reglas de dominio que se aportan. `reglas.py` está separado del
motor para que quien tiene ese conocimiento pueda ampliarlo sin tocar código: fue la
fuente de mayor rendimiento por esfuerzo de todo el proyecto.

**Precisión sobre cobertura.** No se asigna sector sin evidencia. Una fila sin sector se
ve; una con el sector equivocado contamina el análisis de concentración en silencio.

**Sin scipy ni scikit-learn.** App Control de Windows bloquea sus DLL compiladas y no se
desactivó (es irreversible). El bloqueo se rediseñó sobre índice invertido + `rapidfuzz`.
El resultado es más interpretable: cada par candidato se explica por el token que lo generó.

Todas están en `Documentacion/Mantenimiento/DECISIONS.MD` con su evidencia.

---

## Datos

**El dataset de origen no está en el repositorio.** Contiene nombres de empleadores
extraídos de la cartera de clientes de una entidad financiera: es información confidencial
del negocio y no entra a control de versiones ni en un repositorio privado.

Por el mismo motivo se excluyen `dataset_resultado`, `maestro_corporativo` y
`tabla_auditoria`, que reproducen `nombre_original` literal. Se regeneran corriendo el
pipeline sobre la fuente. Sí se versionan los agregados que no contienen datos
individuales: `salidas/kpis_calidad.json` y `salidas/concentracion_sectorial.csv`.

La fuente se lee siempre en modo lectura y **nunca se modifica**.
