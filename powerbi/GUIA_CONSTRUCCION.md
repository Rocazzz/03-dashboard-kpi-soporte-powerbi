# Guía para construir el dashboard en Power BI Desktop

Tiempo estimado: 2–3 horas. Al terminar, guarda el archivo como `powerbi/dashboard_soporte.pbix`, exporta una captura a `img/dashboard_powerbi.png` y súbelos al repositorio.

## 1. Importar datos (Power Query)
1. **Inicio → Obtener datos → Texto/CSV** e importa los 5 archivos de `data/modelo_estrella/`.
2. En **Transformar datos** revisa tipos:
   - `fact_tickets`: `fecha_apertura` y `fecha_cierre` → Fecha/hora; `cumple_sla`, `escalado`, `resuelto_primer_contacto` → Verdadero/Falso; `csat` → Número entero.
   - `dim_fecha[fecha]` → Fecha.
3. Configura la región en **Archivo → Opciones → Configuración regional → Inglés (EE. UU.)** para el archivo actual si los decimales se leen mal (los CSV usan punto decimal).

## 2. Modelo estrella (vista Modelo)
| Desde (muchos) | Hacia (uno) | Columna |
|---|---|---|
| fact_tickets | dim_fecha | fecha_id |
| fact_tickets | dim_agente | agente_id |
| fact_tickets | dim_categoria | categoria_id |
| fact_tickets | dim_canal | canal_id |

- Dirección de filtro: **única** (de dimensión a hechos).
- Marca `dim_fecha` como **tabla de fechas** (columna `fecha`).
- Ordena `dim_fecha[mes]` por `mes_num`.

## 3. Medidas
Crea una tabla `_Medidas` (Inicio → Especificar datos → vacía) y pega las medidas de `medidas_dax.dax`. Comprueba que coincidan con `data/kpis_referencia.csv`.

## 4. Diseño (usa `img/prototipo_dashboard.png` como referencia)
- **Fila 1 – Tarjetas:** Total Tickets, % Cumplimiento SLA, % FCR, % CSAT, Backlog.
- **Fila 2:** gráfico combinado (columnas = Total Tickets por mes, línea = % SLA) + barras de % SLA por categoría con formato condicional (`Color SLA`).
- **Fila 3:** tickets por agente, mediana de primera respuesta por canal, tickets por día de la semana.
- **Segmentadores:** trimestre, nivel del agente (N1/N2), prioridad, canal.
- Agrega un **tooltip** con Tiempo Medio de Resolución y % Escalados.

## 5. Publicar
Publica en Power BI Service (o exporta a PDF) y agrega el enlace / captura al README.
