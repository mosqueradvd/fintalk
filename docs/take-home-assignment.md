# YipitData | Senior Software Engineer Assignment (Agent Platform)

> Fuente de verdad del enunciado. Ante cualquier duda de requisitos exactos o
> criterios de evaluación, consultar este archivo (o el PDF original) antes
> que el resumen en CLAUDE.md.

## Uso de herramientas de IA
Se recomienda usar agentes de IA (Claude Code, Cursor, Copilot) para el
ejercicio. El uso de IA no se penaliza. Se evalúa:
- **Usage** — si se usaron las herramientas de IA de forma efectiva y responsable
- **Application** — si se supo cuándo confiar en la salida de la IA y cuándo el
  problema requería diseño manual deliberado (ej. schemas de tools, manejo de
  errores, seguridad)
- **Understanding Limits** — si se entienden los modos de falla del tool-calling
  de LLMs y cómo se protegió contra ellos

Incluir en el README una sección corta sobre dónde se usó IA y dónde se
tomaron decisiones manuales deliberadas. Se espera conocer todos los detalles
de implementación y poder responder preguntas en vivo sobre arquitectura y
decisiones, además de codear features de seguimiento en la sesión en vivo.

## Objetivo
Crear una aplicación full-stack que permita a clientes "Public Investor"
recibir un resumen de métricas de desempeño de productos de inversionistas
públicos alojados en el Portal. La app debe servir datos a través de un
servidor MCP (Model Context Protocol) y un frontend de chat, permitiendo
consumo tanto por agentes de IA como por usuarios humanos.

## Problema
YipitData produce estimados trimestrales de KPIs (Total Revenue, Subscribers,
Units Sold, ASP, etc.) para empresas públicas. Para cada (empresa, KPI) se
publica:
- Estimados históricos trimestrales (alineados a trimestres fiscales), y
- Estimados Quarter-to-Date (QTD) que reflejan desempeño intra-trimestre en
  un punto en el tiempo.

La app debe facilitar que un asistente de IA, actuando en nombre de
inversionistas con poco tiempo:
1. Encuentre una empresa y sus KPIs, y
2. Responda preguntas sobre tendencias (histórico vs QTD), con capacidad de
   drill-down cuando se necesite.

Ejemplo: para "Imaginary Streaming Company (IGC)" en el sector Software, KPIs
como Global Net Added Subscribers, U.S. Net Added Subscribers y Total Revenue
(en $MM), cada uno con su estimado real trimestral y su estimado QTD.

## Backend
- Listar o buscar sectores, empresas y KPIs disponibles
- Retornar todos los estimados de KPI para una empresa dada, incluyendo
  histórico y el estimado QTD actual

## Servidor MCP
- Exponer 2-4 tools que permitan a un LLM buscar empresas, obtener estimados
  de KPI y consultar datos QTD
- Pensar en cómo un asistente de IA querría interactuar naturalmente con
  estos datos — qué tools y parámetros tienen sentido desde la perspectiva
  de un LLM
- Manejar input inválido explícitamente: qué pasa cuando un agente llama una
  tool con un ticker inexistente o un nombre de KPI mal escrito — retornar
  errores de los que el LLM se pueda recuperar
- Loggear las llamadas a tools (tool, argumentos, resultado) para poder
  inspeccionar el comportamiento del agente después
- El README debe incluir instrucciones claras de cómo conectarse y usar el
  servidor MCP desde un cliente de IA (Claude Desktop, Cursor, o similar)

## Frontend
- Preguntas en lenguaje natural vía chat (ej. "What's IGC's QTD subscriber
  growth this quarter?")
- Respuesta generada por un LLM llamando las tools de MCP construidas
- Visibilidad de qué tools llamó el agente y con qué argumentos

## Dataset de ejemplo
Se provee un CSV de muestra con datos de KPIs para desarrollo.

## Restricciones / supuestos
- Los clientes son inversionistas públicos con poco tiempo, necesitan
  insights clave rápido
- Los datasets de KPI ya están limpios, procesados y disponibles en una base
  de datos (Postgres) — se provee un CSV de muestra
- Los snapshots QTD se actualizan a lo sumo diariamente; no hay streaming en
  tiempo real
- No se requiere login / autenticación de usuario

## Stack sugerido
- Frontend: cualquier lenguaje/framework que abarque Javascript/Typescript/React
- Backend: Python + framework preferido (FastAPI recomendado)
- MCP: Python + framework preferido (FastMCP recomendado)

## Entregables esperados
- Codebase de la aplicación full-stack funcionando
- Servidor MCP funcional que expone la API de datos, con instrucciones de
  conexión desde un cliente de IA
- README.md con instrucciones para correr la app, decisiones clave de
  arquitectura/diseño, y la sección de uso de IA
- Un resumen breve de mejoras futuras
- Un diagrama de arquitectura simple (a mano, Excalidraw, o Mermaid)

## Criterios de evaluación
- Efectividad de la arquitectura para resolver los retos técnicos clave
- Claridad y practicidad del diagrama de arquitectura
- Adecuación y justificación de las decisiones tecnológicas dados los
  supuestos/restricciones
- Confiabilidad, desempeño y escalabilidad de la solución
- Robustez del plan de observabilidad, monitoreo y auditoría
- Calidad de la implementación del servidor MCP — diseño de tools,
  discoverability, y qué tan natural es para un LLM interactuar con los datos
- Uso efectivo y responsable de herramientas de IA

## Sesión de revisión en vivo (60 min)
- Preguntas del entrevistador sobre arquitectura y decisiones de diseño (~15 min)
- Codear features de seguimiento en vivo en el propio repo. El entrevistador
  introducirá un cambio o bug pequeño y realista (ej. mejorar cómo el sistema
  maneja una pregunta sobre un KPI que no existe) y se trabajará junto con el
  candidato. Herramientas de IA son bienvenidas en esta parte (~30 min)
- Discusión de supuestos, trade-offs adicionales, y cómo el diseño se
  extendería a una plataforma de agentes en producción: aislamiento de datos
  multi-tenant, fronteras de seguridad entre el LLM y la capa de datos, y
  observabilidad/auditoría de tool calls (~15 min)
