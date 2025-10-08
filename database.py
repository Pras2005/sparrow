# app/database.py

import sqlite3
from .models import RawScanData

DB_FILE = "scans.db"
NUM_CHANNELS = 126

def setup_database():
    """Creates the database and table if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create a column for the timestamp and for each of the 126 channels
    # Example: "CREATE TABLE scans (timestamp INTEGER PRIMARY KEY, channel_0 INTEGER, ...)"
    columns = ", ".join([f"channel_{i} INTEGER" for i in range(NUM_CHANNELS)])
    create_table_sql = f"CREATE TABLE IF NOT EXISTS scans (timestamp INTEGER PRIMARY KEY, {columns})"
    
    cursor.execute(create_table_sql)
    conn.commit()
    conn.close()

def save_to_sqlite(data: RawScanData):
    """Saves a single scan record to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Ensure the scan data has the correct number of channels
    if len(data.scan) != NUM_CHANNELS:
        print(f"Error: Scan data has {len(data.scan)} channels, expected {NUM_CHANNELS}.")
        return

    # Prepare the INSERT statement with placeholders
    columns = ", ".join([f"channel_{i}" for i in range(NUM_CHANNELS)])
    placeholders = ", ".join(["?" for _ in range(NUM_CHANNELS)])
    insert_sql = f"INSERT INTO scans (timestamp, {columns}) VALUES (?, {placeholders})"
    
    # The values to insert: the timestamp and all the scan values
    values_to_insert = [data.timestamp] + data.scan
    
    cursor.execute(insert_sql, values_to_insert)
    conn.commit()
    conn.close()
