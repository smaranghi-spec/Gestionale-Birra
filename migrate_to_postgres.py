#!/usr/bin/env python3
"""
Script di migrazione dati da SQLite a PostgreSQL.

Utilizzo:
  1. Copia il file gestionale_birra.db nella stessa cartella di questo script
  2. Imposta la variabile DATABASE_URL con l URL PostgreSQL di Render
  3. Esegui: DATABASE_URL="postgresql://..." python migrate_to_postgres.py
"""

import sqlite3
import os
import sys


def get_sqlite_tables(sqlite_conn):
    cursor = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(sqlite_conn, table):
    cursor = sqlite_conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def migrate():
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gestionale_birra.db")
    if not os.path.exists(sqlite_path):
        print(f"ERRORE: File non trovato: {sqlite_path}")
        print("   Copia il file gestionale_birra.db nella cartella del progetto.")
        sys.exit(1)

    pg_url = os.environ.get("DATABASE_URL")
    if not pg_url:
        print("ERRORE: Variabile DATABASE_URL non impostata.")
        print("   Esegui: DATABASE_URL='postgresql://...' python migrate_to_postgres.py")
        sys.exit(1)

    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)

    try:
        import psycopg2
    except ImportError:
        print("ERRORE: psycopg2 non installato. Esegui: pip install psycopg2-binary")
        sys.exit(1)

    print("Connessione a SQLite...")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    print("Connessione a PostgreSQL...")
    pg_conn = psycopg2.connect(pg_url)
    pg_cursor = pg_conn.cursor()

    tables = get_sqlite_tables(sqlite_conn)
    print(f"
Tabelle trovate in SQLite: {', '.join(tables)}
")

    for table in tables:
        columns = get_table_columns(sqlite_conn, table)
        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()

        if not rows:
            print(f"  SKIP {table}: vuota")
            continue

        print(f"  MIGRAZIONE {table}: {len(rows)} righe...")

        pg_cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
            (table,)
        )
        if not pg_cursor.fetchone()[0]:
            print(f"     ATTENZIONE: Tabella {table} non esiste in PostgreSQL - skip")
            continue

        pg_cursor.execute(f"DELETE FROM "{table}"")

        cols_str = ", ".join(f'"'{c}'"' for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))

        inserted = 0
        errors = 0
        for row in rows:
            values = [row[col] for col in columns]
            try:
                pg_cursor.execute(
                    f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})',
                    values
                )
                inserted += 1
            except Exception as e:
                errors += 1
                pg_conn.rollback()

        pg_conn.commit()
        print(f"     OK: {inserted} inserite, {errors} errori")

    print("
Aggiornamento sequenze PostgreSQL...")
    for table in tables:
        try:
            pg_cursor.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('\"'{table}'\"', 'id'),
                    COALESCE((SELECT MAX(id) FROM "{table}"), 1)
                )
            """)
            pg_conn.commit()
        except Exception:
            pg_conn.rollback()

    pg_cursor.close()
    pg_conn.close()
    sqlite_conn.close()

    print("
Migrazione completata con successo!")


if __name__ == "__main__":
    migrate()
