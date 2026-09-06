---
name: llm-security-review
description: Revisión de seguridad para aplicaciones con LLM y tool-calling (agentic apps, servidores MCP). Usar cuando se pida un threat model, revisión de seguridad, auditoría, o "qué tan seguro es esto" sobre un sistema que conecta un LLM con herramientas o datos.
---

# Revisión de seguridad — LLM + tool-calling

Al invocarse, revisa el código relevante (servidor MCP, orquestador/agente,
capa de servicio, validación de input) y produce un reporte en `SECURITY.md`
con dos secciones.

## 1. OWASP Top 10 for LLM Applications (2025) — solo categorías relevantes
Para cada categoría aplicable a ESTA arquitectura, evalúa el riesgo concreto
en el código (no genérico) y da una recomendación accionable:

- **LLM01 Prompt Injection** — ¿puede el texto del usuario hacer que el LLM
  ignore el alcance de sus tools o intente acciones fuera de su función?
- **LLM02 Sensitive Information Disclosure** — ¿puede una tool devolver
  datos que no debería, o filtrar detalles internos en un mensaje de error?
- **LLM05 Improper Output Handling** — ¿se sanitiza la salida del LLM antes
  de mostrarla en el frontend o de usarla en otra llamada?
- **LLM06 Excessive Agency** — ¿tiene el LLM más permisos o funciones de las
  que necesita? (ej. ¿alguna tool permite SQL libre o escritura cuando solo
  debería leer?)
- **LLM09 Misinformation** — ¿hay algún camino en el que el LLM pueda
  "inventar" una cifra en vez de estar obligado a llamar la tool
  correspondiente?
- **LLM10 Unbounded Consumption** — ¿puede un agente pedir rangos enormes o
  llamar tools repetidamente sin límite, generando costo o degradación?

Si una categoría del Top 10 no aplica (ej. envenenamiento de datos de
entrenamiento, vulnerabilidades de embeddings/RAG), dilo explícitamente y
por qué — es mejor que forzar un hallazgo débil.

## 2. STRIDE ligero sobre el límite LLM ↔ MCP ↔ Core ↔ Base de datos
Para cada categoría (Spoofing, Tampering, Repudiation, Information
Disclosure, Denial of Service, Elevation of Privilege), da 1-2 líneas de
análisis específico a ese límite y, si aplica, una mitigación concreta o una
nota de "fuera de alcance para este take-home, pendiente para producción".

## Formato de cada hallazgo
**Severidad** (crítico/medio/bajo) — **Descripción específica al código** —
**Recomendación**. Si la mitigación es rápida y de bajo riesgo, impleméntala
directamente y dilo en el reporte; si es más grande, solo documéntala como
mejora futura.

No agregues librerías nuevas de seguridad ni reescribas la arquitectura
completa — el objetivo es un reporte honesto y accionable, no una
reescritura del proyecto.