-- =============================================================================
-- FinTalk — Esquema Postgres
-- =============================================================================
-- Derivado del CSV de ejemplo (kpi_sample_2000...csv). Columnas del CSV:
--   company_name, ticker, sector, kpi, period_start, period_end, period,
--   estimate_type (historical | qtd), value, unit, as_of
--
-- Decisiones de modelado (para defender en la sesión en vivo):
--
-- 1. Normalizamos company/kpi a tablas propias en vez de una sola tabla ancha.
--    El CSV repite "Acme E-commerce,ACME,E-commerce" en cada fila; eso es
--    denormalización de archivo plano. En la DB lo separamos para tener una
--    sola fuente de verdad del ticker/sector y para que los FKs garanticen
--    integridad (no puede existir un estimate de un KPI que no existe).
--
-- 2. `estimate_type` del CSV NO es una columna: es la partición natural de los
--    datos en dos tablas con llaves distintas.
--      - historical -> `quarterly_estimates`: 1 valor por (kpi, trimestre).
--      - qtd        -> `qtd_estimates`: varios snapshots por trimestre, cada
--        uno fechado con `as_of_date` (quarter-to-date, se revisa mientras el
--        trimestre avanza).
--    Meterlos en la misma tabla obligaría a una llave única condicional y a
--    columnas que sólo aplican a la mitad de las filas.
--
-- 3. `unit` es funcionalmente dependiente del nombre del KPI en estos datos
--    (ASP ($) -> $, Units Sold -> units, ...). La guardamos en `kpis`, no en
--    cada fila de estimate, para no repetirla ~20 veces por KPI.
--
-- 4. Ningún SQL libre del LLM toca estas tablas: la capa `core/` expone
--    funciones tipadas. Este esquema es la frontera de datos.
-- =============================================================================

-- Búsqueda difusa por nombre/ticker para la tool `find_company`.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- -----------------------------------------------------------------------------
-- companies
-- -----------------------------------------------------------------------------
CREATE TABLE companies (
    id         SERIAL PRIMARY KEY,
    ticker     TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,
    sector     TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices trigram: permiten `name ILIKE '%strm%'` y `similarity()` rápidos
-- para la búsqueda difusa sin escaneo completo de tabla.
CREATE INDEX idx_companies_name_trgm   ON companies USING gin (name gin_trgm_ops);
CREATE INDEX idx_companies_ticker_trgm ON companies USING gin (ticker gin_trgm_ops);
CREATE INDEX idx_companies_sector_trgm ON companies USING gin (sector gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- kpis  (un KPI pertenece a una empresa)
-- -----------------------------------------------------------------------------
CREATE TABLE kpis (
    id         SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    unit       TEXT NOT NULL,
    UNIQUE (company_id, name)
);

CREATE INDEX idx_kpis_company_id ON kpis (company_id);

-- -----------------------------------------------------------------------------
-- quarterly_estimates  (estimate_type = 'historical')
-- Un único valor consolidado por KPI y trimestre fiscal.
-- -----------------------------------------------------------------------------
CREATE TABLE quarterly_estimates (
    id             SERIAL PRIMARY KEY,
    kpi_id         INTEGER NOT NULL REFERENCES kpis (id) ON DELETE CASCADE,
    fiscal_quarter TEXT NOT NULL
        CHECK (fiscal_quarter ~ '^[0-9]{4}Q[1-4]$'),   -- p.ej. '2025Q3'
    period_start   DATE NOT NULL,
    period_end     DATE NOT NULL,
    value          NUMERIC(20, 4) NOT NULL,
    UNIQUE (kpi_id, fiscal_quarter),
    CHECK (period_end >= period_start)
);

CREATE INDEX idx_qe_kpi_quarter ON quarterly_estimates (kpi_id, fiscal_quarter);

-- -----------------------------------------------------------------------------
-- qtd_estimates  (estimate_type = 'qtd')
-- Serie de snapshots dentro del trimestre en curso, fechados por `as_of_date`.
-- -----------------------------------------------------------------------------
CREATE TABLE qtd_estimates (
    id             SERIAL PRIMARY KEY,
    kpi_id         INTEGER NOT NULL REFERENCES kpis (id) ON DELETE CASCADE,
    fiscal_quarter TEXT NOT NULL
        CHECK (fiscal_quarter ~ '^[0-9]{4}Q[1-4]$'),
    period_start   DATE NOT NULL,
    period_end     DATE NOT NULL,
    value          NUMERIC(20, 4) NOT NULL,
    as_of_date     DATE NOT NULL,
    UNIQUE (kpi_id, as_of_date),
    CHECK (period_end >= period_start)
);

-- La consulta típica ("último QTD") ordena por as_of_date desc dentro de un KPI.
CREATE INDEX idx_qtd_kpi_asof ON qtd_estimates (kpi_id, as_of_date DESC);
