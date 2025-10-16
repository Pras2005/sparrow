# app/database.py

import sqlite3
import queue
import threading
from .models import RawScanData

DB_FILE = "scans.db"
NUM_CHANNELS = 126

# A thread-safe queue to hold incoming scan data before it's written to the DB
db_queue = queue.Queue()

def setup_database():
    """Creates the database and the 'wide' table if they don't exist."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Enable Write-Ahead Logging (WAL) mode for better concurrency.
    # This is a good practice even with the queue.
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Your original 'wide' table schema. Note the change to REAL for float values.
    columns = ", ".join([f"channel_{i} REAL" for i in range(NUM_CHANNELS)])
    create_table_sql = f"CREATE TABLE IF NOT EXISTS scans (timestamp INTEGER PRIMARY KEY, {columns})"
    
    cursor.execute(create_table_sql)
    conn.commit()
    conn.close()

def database_writer_worker():
    """
    A dedicated worker that runs in a separate thread.
    It pulls data from the queue and writes it to the database one by one,
    preventing any lock conflicts.
    """
    print("Database writer worker started.")
    while True:
        try:
            # This will block and wait until an item is available in the queue
            data: RawScanData = db_queue.get()

            # Perform the actual database write
            conn = sqlite3.connect(DB_FILE, timeout=10) # Use a timeout for safety
            cursor = conn.cursor()

            if len(data.scan) != NUM_CHANNELS:
                print(f"Error: Scan data has {len(data.scan)} channels, expected {NUM_CHANNELS}.")
                db_queue.task_done()
                continue # Skip this invalid record

            columns = ", ".join([f"channel_{i}" for i in range(NUM_CHANNELS)])
            placeholders = ", ".join(["?" for _ in range(NUM_CHANNELS)])
            insert_sql = f"INSERT OR IGNORE INTO scans (timestamp, {columns}) VALUES (?, {placeholders})"
            
            values_to_insert = [data.timestamp] + data.scan
            
            cursor.execute(insert_sql, values_to_insert)
            conn.commit()
            conn.close()

            db_queue.task_done()
        except Exception as e:
            print(f"Error in database writer: {e}")

def save_to_sqlite(data: RawScanData):
    """
    This function is now extremely fast. It just adds the data to the
    queue and returns immediately, without waiting for the database write.
    """
    db_queue.put(data)

# You will need to implement this function based on your 'wide' schema
def query_history(channel: int, start_time: int, end_time: int):
    """
    Queries the 'wide' table for a specific channel's history.
    NOTE: This can be slow on large datasets with a wide schema.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # We need to select the specific channel column by its name
    query_sql = f"""
    SELECT timestamp, channel_{channel} as value 
    FROM scans 
    WHERE timestamp >= ? AND timestamp <= ?
    """
    
    cursor.execute(query_sql, (start_time, end_time))
    rows = cursor.fetchall()
    conn.close()
    
    # Convert rows to the expected Pydantic model format
    return [models.HistoricalDataPoint(timestamp=row['timestamp'], value=row['value']) for row in rows]
