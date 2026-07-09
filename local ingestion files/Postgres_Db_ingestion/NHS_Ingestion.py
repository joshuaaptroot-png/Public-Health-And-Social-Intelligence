import os
import re
import time
import hashlib
import pandas as pd
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
CHUNK_SIZE = 10000

DB_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=config["PASSWORD"],
    host=config["HOST"],
    port=int(config["PORT"]),
    database="phs_db"
)

engine = create_engine(DB_URL)

def clean_name(name):
    cleaned = name.lower()
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("_")

    file_hash = hashlib.md5(name.encode()).hexdigest()[:8]
    cleaned = cleaned[:54]

    return f"{cleaned}_{file_hash}"

with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))

files = [f for f in os.listdir(CSV_FOLDER) if f.lower().endswith(".csv")]
total_files = len(files)

print(f"Found {total_files} CSV files.")

for file_number, file in enumerate(files, start=1):
    path = os.path.join(CSV_FOLDER, file)
    table_name = clean_name(os.path.splitext(file)[0])
    file_start = time.time()

    print(f"\n[{file_number}/{total_files}] Loading {file}")
    print(f"Target table: bronze.{table_name}")

    try:
        chunks = pd.read_csv(
            path,
            dtype=str,
            chunksize=CHUNK_SIZE,
            engine="python"
        )

        rows_loaded = 0

        for chunk_number, chunk in enumerate(chunks, start=1):
            chunk["source_file"] = file
            chunk["loaded_at"] = pd.Timestamp.now()

            if_exists_mode = "replace" if chunk_number == 1 else "append"

            with engine.begin() as conn:
                chunk.to_sql(
                    name=table_name,
                    con=conn,
                    schema="bronze",
                    if_exists=if_exists_mode,
                    index=False
                )

            rows_loaded += len(chunk)

            elapsed = time.time() - file_start
            print(
                f"Chunk {chunk_number} loaded | "
                f"Rows loaded: {rows_loaded:,} | "
                f"Time elapsed: {elapsed:.1f}s"
            )

        elapsed = time.time() - file_start
        percent = (file_number / total_files) * 100

        print(f"Committed bronze.{table_name}")
        print(f"File progress: {percent:.1f}% complete")
        print(f"Time for file: {elapsed:.1f} seconds")

    except Exception as e:
        print(f"Failed: {file}")
        print(e)
        continue

print("\nDone.")