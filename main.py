# app/main.py

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError
from . import models, database, websocket, transformation_logic

# --- Initialization ---
app = FastAPI(title="RF Scanner API")

raw_manager = websocket.ConnectionManager()
analog_manager = websocket.ConnectionManager()

@app.on_event("startup")
def on_startup():
    """This function runs when the application starts."""
    print("Application starting up...")
    database.setup_database()
    print("Database setup complete.")

# --- Core Logic (Refactored to a Helper Function) ---
async def process_and_broadcast_scan(data: models.RawScanData):
    """
    Saves, transforms, and broadcasts a scan. This is the central logic
    used by both the HTTP and WebSocket ingestion endpoints.
    """
    # 1. Save the original raw data to the database
    database.save_to_sqlite(data)

    # 2. Broadcast the raw data
    await raw_manager.broadcast(data.json())

    # 3. Transform the data to simulated analog
    analog_scan_values = transformation_logic.to_simulated_analog(data.scan)
    analog_data = models.AnalogScanData(timestamp=data.timestamp, scan=analog_scan_values)

    # 4. Broadcast the new analog data
    await analog_manager.broadcast(analog_data.json())

# --- API Endpoints ---
@app.post("/scan", status_code=222)
async def receive_scan_data_http(data: models.RawScanData):
    """Receives scan data via HTTP POST."""
    await process_and_broadcast_scan(data)
    return {"status": "accepted"}

@app.get("/history", response_model=models.HistoryResponse)
async def get_history(
    channel: int = Query(..., ge=0, le=125, description="Channel to query (0-125)"),
    start_time: int = Query(..., description="Start of time period (Unix ms)"),
    end_time: int = Query(..., description="End of time period (Unix ms)")
):
    """Retrieves historical scan data for a specific channel."""
    historical_data = database.query_history(
        channel=channel,
        start_time=start_time,
        end_time=end_time
    )
    return {"channel": channel, "data": historical_data}

# --- WebSocket Endpoints ---
@app.websocket("/ws/raw")
async def websocket_raw_endpoint(websocket: WebSocket):
    """Broadcasts raw binary scan data."""
    await raw_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        raw_manager.disconnect(websocket)

@app.websocket("/ws/analog")
async def websocket_analog_endpoint(websocket: WebSocket):
    """Broadcasts simulated analog scan data."""
    await analog_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        analog_manager.disconnect(websocket)

@app.websocket("/ws/reception")
async def websocket_reception_endpoint(websocket: WebSocket):
    """Receives scan data via WebSocket and processes it."""
    await websocket.accept()
    print("Client connected to reception endpoint.")
    try:
        while True:
            # Wait for a JSON string from the client
            message = await websocket.receive_text()
            try:
                # Validate the incoming data against our Pydantic model
                data = models.RawScanData.parse_raw(message)
                # If valid, process it just like the HTTP endpoint
                await process_and_broadcast_scan(data)
            except (ValidationError, json.JSONDecodeError) as e:
                # Handle cases where the client sends invalid data
                print(f"Received invalid data on reception websocket: {e}")
                # Optional: Send an error message back to the client
                # await websocket.send_text('{"error": "Invalid data format"}')
    except WebSocketDisconnect:
        print("Client disconnected from reception endpoint.")
