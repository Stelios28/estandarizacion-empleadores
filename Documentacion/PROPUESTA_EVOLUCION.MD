# Propuesta de evolución del producto analítico

**De un pipeline de limpieza a un activo corporativo reutilizable**

---

## El punto de partida

Lo entregado es un **pipeline**: entra un archivo, sale un archivo. Resuelve el
problema planteado, pero su valor se agota cuando termina de correr.

Lo que sigue convierte ese pipeline en un **activo**: algo que el banco usa todos
los días, que se enriquece solo, y sobre lo cual se construyen otras capacidades.

La diferencia importa porque el trabajo duro ya está hecho. El maestro corporativo
de 204.393 entidades, las reglas sectoriales y el motor de resolución son el 80 % del
esfuerzo. Lo que falta es exponerlos.

---

## Fase 1 — De archivo a servicio (0-3 meses)

**El maestro deja de ser un CSV y pasa a ser una API.**

| Entregable | Qué habilita |
|---|---|
| `GET /empleadores?q=` — búsqueda con tolerancia a errores | **Autocompletado en el formulario de vinculación.** Ataca el problema en origen |
| `POST /resolver` — texto libre → `id_empleador` + confianza | Cualquier sistema del banco puede normalizar sin replicar el motor |
| `GET /empleadores/{id}` — ficha completa | Consulta desde originación, cobranza, comercial |
| Carga incremental nocturna | Solo procesa lo nuevo; el maestro absorbe el resto |

**Métrica de éxito:** variantes nuevas de empleadores existentes por carga → tiende
a cero. Ese único número dice si el problema dejó de generarse.

**Por qué esta fase primero:** todas las demás dependen de que el dato deje de
ensuciarse. Limpiar hacia atrás sin cerrar el grifo es trabajo recurrente.

---

## Fase 2 — Enriquecimiento continuo (3-6 meses)

**El maestro se conecta a las fuentes de verdad y deja de depender solo del texto.**

- **Reconciliación con Registro Público** — razón social exacta, forma societaria,
  vigencia, disolución. Mensual.
- **Cruce con RUC/DGI** — el ancla determinística más fuerte para deduplicar. Un
  RUC compartido cierra el caso sin fuzzy.
- **Panamá Emprende** — actividad económica declarada. Reemplaza la inferencia
  sectorial por un hecho.
- **Estructura de grupos** — matriz, subsidiarias, sucursales. Los códigos de
  sucursal ya detectados (`EMPRESAS MELO 019`, `020`, `025`…) son la semilla.
- **Cierre de la fase 7** — validación externa sobre los 95.922 clústeres
  pendientes, con caché acumulativa.

**Efecto medible:** cobertura sectorial de 56 % a > 90 %; confianza en banda
automática de 9,4 % a > 60 %.

**Señal de riesgo que aparece gratis:** un cambio de razón social o una disolución
en Registro Público es, por sí misma, información de riesgo que hoy nadie observa.

---

## Fase 3 — Del maestro a la decisión (6-12 meses)

**El sector económico deja de ser una etiqueta y pasa a ser una variable de modelo.**

| Capacidad | Uso |
|---|---|
| **Concentración por empleador** | Riesgo correlacionado. "Si esta empresa despide, ¿cuánta cartera cae?" — hoy imposible de responder |
| **Concentración sectorial e HHI** | Insumo directo de ICAAP y stress testing |
| **PD sectorial** | Variable explicativa en originación y comportamiento. Probablemente el mayor lift inmediato |
| **Cambio de empleador** | Evento de riesgo observable, hoy invisible |
| **Coherencia ingreso-sector** | Detector de sobreestimación de ingresos en originación |
| **Estabilidad del empleador** | Rotación observada de clientes por empleador |

**El caso de negocio más fuerte de toda la propuesta:** hoy el banco no puede
responder *"¿cuánta exposición tengo a los empleados de un solo empleador?"* porque
el mismo empleador aparece con hasta 60 grafías. Eso es riesgo correlacionado no
medido — el tipo de riesgo que sorprende a los comités.

---

## Fase 4 — Producto transversal (12+ meses)

**El maestro deja de ser de Riesgo y pasa a ser del banco.**

| Área | Uso del maestro |
|---|---|
| **Comercial** | Empresas con muchos empleados bancarizados y sin relación corporativa = pipeline de banca empresa cuantificado |
| **Nómina** | Identificar convenios de pago potenciales |
| **Cobranza** | Segmentar por estabilidad del empleador; priorizar gestión |
| **Cumplimiento** | Cruce con listas de sanciones y personas expuestas |
| **Analítica de clientes** | Sector del empleador como variable de segmentación y propensión |
| **Planeación** | Exposición del banco a la economía real, por sector y por grupo económico |

**El maestro corporativo es infraestructura, no un proyecto.** Como el catálogo de
productos o el maestro de clientes: se construye una vez, se mantiene siempre, y
todo lo demás se apoya en él.

---

## Extensiones técnicas de alto valor

**Aprendizaje del feedback humano.** Cada corrección de un analista sobre un
registro de baja confianza es una etiqueta. Con unos miles se puede entrenar un
clasificador que reemplace parte de las reglas escritas a mano y que mejore solo.
El score de confianza ya identifica exactamente qué revisar primero.

**Embeddings semánticos para la zona de duda.** Los 15.730 pares que la similitud de
cadena no resuelve son un conjunto acotado y bien delimitado. Un modelo de
embeddings entrenado sobre razones sociales panameñas resolvería buena parte sin
llamadas externas, y a costo marginal cero una vez entrenado.

**Vocabulario de negocio como activo mantenido.** Cinco de las correcciones de mayor
impacto (D8-D12) salieron de revisar filas concretas, no de las métricas. La que más
rescató —`PH` = propiedad horizontal— no era derivable del dato: es una sigla local con
estatuto jurídico. `reglas.py` está separado del motor precisamente para que quien tiene
ese conocimiento lo aporte sin tocar código; falta el paso siguiente, que es darle una
interfaz y un dueño.

**Consola de curaduría.** Una interfaz donde un analista revise clústeres dudosos,
apruebe o divida fusiones, y edite el maestro — con versionado y auditoría. Es lo
que convierte el pipeline en un sistema operado, no ejecutado.

**Extensión a otros campos de texto libre.** El mismo motor —bloqueo, matching,
resolución, confianza— aplica sin cambios conceptuales a direcciones, nombres de
clientes, descripciones de garantías y razones sociales de proveedores. La
arquitectura ya está separada en base de conocimiento (`reglas.py`) y motor: cambiar
de dominio es cambiar el primero.

---

## Riesgos de la evolución

| Riesgo | Mitigación |
|---|---|
| El maestro se degrada si nadie lo mantiene | Dueño de datos designado; el mantenimiento es un rol, no una tarea |
| El autocompletado no se adopta | Medirlo desde el día uno con el KPI de variantes nuevas; sin adopción no hay proyecto |
| Sobre-agrupación en el maestro | Precisión sobre recall ya es la política; los clústeres grandes se revisan con la consola de curaduría |
| Dependencia de fuentes externas | Caché persistente y degradación elegante: sin red, el motor determinístico sigue funcionando |
| El costo de la fase 7 crece sin control | Presupuesto por corrida ya implementado; el maestro absorbe casos y el costo baja con el tiempo |

---

## Secuencia recomendada

```
Mes 0-3    │ API de búsqueda + autocompletado en vinculación
           │ ▸ cierra el grifo, sin esto lo demás es trabajo recurrente
           │
Mes 3-6    │ Reconciliación con Registro Público, RUC y Panamá Emprende
           │ ▸ cobertura sectorial > 90 %, confianza automática > 60 %
           │
Mes 6-12   │ Variables de riesgo en producción
           │ ▸ concentración por empleador, PD sectorial, stress testing
           │
Mes 12+    │ Consola de curaduría, extensión a otros campos, uso transversal
           │ ▸ el maestro como infraestructura del banco
```

**El primer paso no es técnico.** Es decidir quién es el dueño del maestro
corporativo. Sin esa decisión, lo demás es un proyecto que termina; con ella, es una
capacidad que permanece.
