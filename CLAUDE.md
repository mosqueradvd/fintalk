# YipitData — Agent Platform Take-Home

## Objetivo
App full-stack que sirve estimados trimestrales de KPIs de empresas públicas
(históricos + QTD) a inversionistas, vía chat en lenguaje natural y vía un
servidor MCP consumible por agentes externos (Claude Desktop, Cursor, etc).
Take-home técnico para el rol de AI Infrastructure Senior Engineer en YipitData.
Habrá sesión de revisión en vivo (60 min): Q&A de arquitectura, cambio/bug en
vivo sobre el propio repo, y discusión de extensión a producción.

## Cómo trabajar conmigo en este proyecto
- Actúa como mentor: David nunca ha construido un proyecto full-stack de este
  tipo solo. Explica el POR QUÉ de cada decisión no obvia, no solo el qué —
  él tiene que poder defenderlas en la sesión en vivo sin apoyo de IA.
- Antes de generar código nuevo, di en 1-2 líneas qué vas a hacer y por qué,
  para que quede como aprendizaje, no como caja negra.
- Prioriza código legible y modular sobre código clever.

## Stack y decisiones de arquitectura ya tomadas
- Backend: Python + FastAPI. MCP: FastMCP. DB: Postgres. Frontend: React/Next.js.
- **Capa de servicio compartida (`core/`)**: funciones puras (search_companies,
  get_kpis_for_company, get_estimates) que importan TANTO la API REST como las
  tools de MCP. Evita duplicar lógica/queries y evita el doble salto
  MCP→REST→DB.
- **El chat backend es un cliente MCP real** (usa la Claude API con tool-use
  contra nuestro propio MCP server), no solo llama las funciones del core
  directo. Así el mismo camino de tools sirve para nuestro frontend y para
  clientes externos.
- Errores de tools deben ser recuperables por el LLM: nunca un 404 seco.
  Ej: `{"error": "kpi_not_found", "suggestions": [...]}`.
- Ningún SQL libre generado por el LLM — todo pasa por funciones tipadas y
  validadas (frontera de seguridad LLM↔datos).
- Cada tool call se loggea (tool, args, resultado, latencia) para auditoría.

## Modelo de datos (borrador)
- `companies` (ticker, nombre, sector)
- `kpis` (nombre, unidad, company_id)
- `quarterly_estimates` (company, kpi, fiscal_quarter, valor)
- `qtd_estimates` (company, kpi, valor, as_of_date)

## Tools de MCP planeadas (2-4)
- `find_company(query)` — búsqueda difusa por nombre o ticker
- `list_kpis(ticker)` — KPIs disponibles para una empresa
- `get_kpi_history(ticker, kpi, quarters=8)` — histórico trimestral
- `get_qtd_estimate(ticker, kpi)` — última estimación QTD

## Plan de construcción (orden)
1. [ ] Esquema Postgres a partir del CSV de ejemplo
2. [ ] Capa de servicio (`core/`)
3. [ ] API REST FastAPI sobre el core
4. [ ] Servidor MCP (FastMCP) con las 4 tools + errores + logging
5. [ ] Orquestador de chat (Claude API tool-use como cliente MCP)
6. [ ] Frontend de chat (input + respuesta + panel de tool calls)
7. [ ] Observabilidad + manejo de errores end-to-end
8. [ ] README (cómo correr, cómo conectar cliente MCP externo, decisiones,
       mejoras futuras, sección de uso de IA) + diagrama de arquitectura

## Estado actual
Aún no se ha escrito código. Este archivo se creó tras la sesión de
planeación inicial. Actualizar la sección "Plan de construcción" marcando
pasos completados a medida que avancemos.

## Para el README final (recordatorio)
Incluir sección honesta de dónde se usó IA vs. dónde David decidió
manualmente (diseño de tool schemas, formato de errores, frontera de
seguridad) — es parte de los criterios de evaluación.