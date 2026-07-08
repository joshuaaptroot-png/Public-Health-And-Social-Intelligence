import os
import re
import hashlib
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

CSV_FOLDER = r"C:\Users\Joshu\OneDrive\Desktop\public_health_intelligence\NHS_Open_Data"

#read config file for database connection parameters
config = {}

with open("app.config") as f:
    for line in f:
        key, value = line.strip().split("=", 1)
        config[key] = value

#make connection to the database

DB_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=config["PASSWORD"],
    host=config["HOST"],
    port=int(config["PORT"]),
    database="phs_db"
)

#create the database engine
engine = create_engine(DB_URL)

#ensure naming requirements are compatible with postgres table naming conventions
def clean_name(name):
    cleaned = name.lower()
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = cleaned.strip("_")

    file_hash = hashlib.md5(name.encode()).hexdigest()[:8]

    cleaned = cleaned[:54]

    return f"{cleaned}_{file_hash}"

#ensure schemas exist before loading data
with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze;"))

#load each CSV file into the bronze schema
for file in os.listdir(CSV_FOLDER):
    if file.lower().endswith(".csv"):
        path = os.path.join(CSV_FOLDER, file)
        table_name = clean_name(os.path.splitext(file)[0])

        print(f"Loading {file} into bronze.{table_name}")

        try:
            df = pd.read_csv(
                path,
                dtype=str,
                engine="python"
            )
        except Exception as e:
            print(f" Failed to read: {file}")
            print(e)
            continue

        df["source_file"] = file
        df["loaded_at"] = pd.Timestamp.now()

        try:
            with engine.begin() as conn:
                df.to_sql(
                    name=table_name,
                    con=conn,
                    schema="bronze",
                    if_exists="replace",
                    index=False
                )

            print(f"Committed bronze.{table_name}")

        except Exception as e:
            print(f" Failed to load: {file}")
            print(e)
            continue

print("Done.")