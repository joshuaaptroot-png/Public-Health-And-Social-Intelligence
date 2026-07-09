import os
import re
import csv
import time
import hashlib
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

config_path = Path(__file__).parent / "app.config"

config = {}

with open(config_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        key, value = line.split("=", 1)
        config[key] = value

CSV_FOLDER = config["PATH"]

DB_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=config["PASSWORD"],
    host=config["HOST"],
    port=int(config["PORT"]),
    database="phs_db"
)

engine = create_engine(DB_URL)

#method to clean name and ensure postgresSQL conventions are met

def clean_name(name):
    cleaned = name.lower()
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("_")

    file_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    cleaned = cleaned[:54]

    return f"{cleaned}_{file_hash}"

#put names in quotes
def quote_ident(name):
    return '"' + name.replace('"', '""') + '"'

#read headers
def get_csv_headers(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return next(reader)

#ensure column names match postgresSQL conventions and are unique
def clean_column_name(name, position):
    cleaned = name.lower().strip()
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("_")

    if not cleaned:
        cleaned = f"column_{position}"

    return cleaned[:55]

#method to create the table in the bronze schema with the cleaned column names
def create_bronze_table(conn, table_name, headers):
    seen = {}
    columns = []

    for i, header in enumerate(headers, start=1):
        col = clean_column_name(header, i)

        if col in seen:
            seen[col] += 1
            col = f"{col}_{seen[col]}"
        else:
            seen[col] = 1

        columns.append(col)

    column_sql = ",\n        ".join(
        f"{quote_ident(col)} TEXT" for col in columns
    )

    full_table_name = f"bronze.{quote_ident(table_name)}"

    conn.execute(text(f'DROP TABLE IF EXISTS {full_table_name};'))

    conn.execute(text(f"""
        CREATE TABLE {full_table_name} (
            {column_sql}
        );
    """))

    return columns

class ProgressFile:
    def __init__(self, path, total_size):
        self.file = open(path, "r", encoding="utf-8-sig", newline="")
        self.total_size = total_size
        self.bytes_read = 0
        self.last_print = time.time()
        self.start = time.time()

    def read(self, size=-1):
        data = self.file.read(size)

        self.bytes_read += len(data.encode("utf-8", errors="ignore"))

        now = time.time()
        if now - self.last_print >= 2:
            percent = (self.bytes_read / self.total_size) * 100
            elapsed = now - self.start
            mb_read = self.bytes_read / (1024 * 1024)
            speed = mb_read / elapsed if elapsed > 0 else 0

            print(
                f"\rCopy progress: {percent:.1f}% | "
                f"{mb_read:,.1f} MB read | "
                f"{speed:,.1f} MB/s",
                end="",
                flush=True
            )

            self.last_print = now

        return data

    def close(self):
        self.file.close()

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))

files = [f for f in os.listdir(CSV_FOLDER) if f.lower().endswith(".csv")]
total_files = len(files)

print(f"Found {total_files} CSV files.")

for file_number, file in enumerate(files, start=1):
    path = os.path.join(CSV_FOLDER, file)
    table_name = clean_name(os.path.splitext(file)[0])
    file_start = time.time()
    file_size = os.path.getsize(path)

    print(f"\n[{file_number}/{total_files}] Loading {file}")
    print(f"Target table: bronze.{table_name}")
    print(f"File size: {file_size / (1024 * 1024):,.1f} MB")

    try:
        headers = get_csv_headers(path)

        with engine.begin() as conn:
            create_bronze_table(conn, table_name, headers)

        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()

        progress_file = ProgressFile(path, file_size)

        copy_sql = f"""
            COPY bronze.{quote_ident(table_name)}
            FROM STDIN
            WITH CSV HEADER
        """

        cursor.copy_expert(copy_sql, progress_file)
        print()

        raw_conn.commit()

        cursor.close()
        raw_conn.close()
        progress_file.close()

        elapsed = time.time() - file_start
        percent = (file_number / total_files) * 100

        print(f"Committed bronze.{table_name}")
        print(f"Overall file progress: {percent:.1f}% complete")
        print(f"Time for file: {elapsed:.1f} seconds")

    except Exception as e:
        print(f"Failed: {file}")
        print(e)
        continue

print("\nDone.")