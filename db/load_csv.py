"""
Carga el CSV de ejemplo en el esquema de db/schema.sql.

Uso:
    createdb fintalk
    psql fintalk -f db/schema.sql
    python db/load_csv.py kpi_sample_2000__282_29__281_29.csv

Requiere:  pip install "psycopg[binary]"
Config:    DATABASE_URL (default: postgresql://localhost/fintalk)

Es idempotente: usa upserts, así que se puede correr varias veces.
"""

import csv
import os
import sys

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/fintalk")


def load(csv_path: str) -> None:
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        # 1. companies: una fila por ticker
        companies = {
            r["ticker"]: (r["company_name"], r["sector"]) for r in rows
        }
        for ticker, (name, sector) in companies.items():
            cur.execute(
                """
                INSERT INTO companies (ticker, name, sector)
                VALUES (%s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE
                    SET name = EXCLUDED.name, sector = EXCLUDED.sector
                """,
                (ticker, name, sector),
            )

        # 2. kpis: una fila por (ticker, kpi)
        kpis = {(r["ticker"], r["kpi"]): r["unit"] for r in rows}
        for (ticker, kpi_name), unit in kpis.items():
            cur.execute(
                """
                INSERT INTO kpis (company_id, name, unit)
                VALUES ((SELECT id FROM companies WHERE ticker = %s), %s, %s)
                ON CONFLICT (company_id, name) DO UPDATE SET unit = EXCLUDED.unit
                """,
                (ticker, kpi_name, unit),
            )

        # 3. estimates: se enrutan por estimate_type
        for r in rows:
            kpi_id_sql = """
                (SELECT k.id FROM kpis k
                 JOIN companies c ON c.id = k.company_id
                 WHERE c.ticker = %s AND k.name = %s)
            """
            if r["estimate_type"] == "historical":
                cur.execute(
                    f"""
                    INSERT INTO quarterly_estimates
                        (kpi_id, fiscal_quarter, period_start, period_end, value)
                    VALUES ({kpi_id_sql}, %s, %s, %s, %s)
                    ON CONFLICT (kpi_id, fiscal_quarter) DO UPDATE
                        SET value = EXCLUDED.value
                    """,
                    (r["ticker"], r["kpi"], r["period"],
                     r["period_start"], r["period_end"], r["value"]),
                )
            elif r["estimate_type"] == "qtd":
                cur.execute(
                    f"""
                    INSERT INTO qtd_estimates
                        (kpi_id, fiscal_quarter, period_start, period_end,
                         value, as_of_date)
                    VALUES ({kpi_id_sql}, %s, %s, %s, %s, %s)
                    ON CONFLICT (kpi_id, as_of_date) DO UPDATE
                        SET value = EXCLUDED.value
                    """,
                    (r["ticker"], r["kpi"], r["period"], r["period_start"],
                     r["period_end"], r["value"], r["as_of"]),
                )
            else:
                raise ValueError(f"estimate_type desconocido: {r['estimate_type']!r}")

        conn.commit()

    print(
        f"OK: {len(companies)} empresas, {len(kpis)} KPIs, {len(rows)} filas de estimates"
    )


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "kpi_sample_2000__282_29__281_29.csv"
    load(path)
