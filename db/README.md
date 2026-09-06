# Capa de datos

## Correr

```bash
# 1. Postgres local
docker compose -f db/docker-compose.yml up -d

# 2. Crear el esquema
export DATABASE_URL=postgresql://fintalk:fintalk@localhost:5432/fintalk
psql "$DATABASE_URL" -f db/schema.sql

# 3. Cargar el CSV de ejemplo
pip install "psycopg[binary]"
python db/load_csv.py kpi_sample_2000__282_29__281_29.csv
```

## Modelo

| Tabla                 | Grano                                   | Origen (CSV)                |
|-----------------------|-----------------------------------------|----------------------------|
| `companies`           | 1 fila por ticker                       | company_name, ticker, sector |
| `kpis`                | 1 fila por (empresa, KPI)               | kpi, unit                  |
| `quarterly_estimates` | 1 fila por (KPI, trimestre fiscal)      | filas `estimate_type=historical` |
| `qtd_estimates`       | 1 fila por (KPI, `as_of_date`)          | filas `estimate_type=qtd`  |

Las decisiones de diseño están comentadas en [`schema.sql`](schema.sql).

## Notas

- `db/schema.sql` no pudo probarse en este entorno (sin Docker/psql). Validar
  al levantar Postgres por primera vez.
- `pg_trgm` habilita la búsqueda difusa por nombre/ticker de `find_company`.
