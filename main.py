# app/main.py

import json
import threading # Import the threading module
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError
from . import models, database, websocket, transformation_logic, ml_predictor

# --- Initialization ---
app = FastAPI(title="RF Scanner API")

raw_manager = websocket.ConnectionManager()
analog_manager = websocket.ConnectionManager()
prediction_manager = websocket.ConnectionManager()


# --- Application Lifecycle Events ---
@app.on_event("startup")
def on_startup():
    """This function runs when the application starts."""
    print("Application starting up...")
    database.setup_database() # Ensure DB and table exist
    ml_predictor.load_model()
    
    # Create and start the background worker thread for writing to the database
    # daemon=True ensures the thread will exit when the main app exits
    writer_thread = threading.Thread(target=database.database_writer_worker, daemon=True)
    writer_thread.start()
    print("Database writer thread started.")


# --- Core Data Processing Logic ---
async def process_and_broadcast_scan(data: models.RawScanData):
    """
    Saves, transforms, broadcasts a scan, and triggers a prediction.
    """
    # 1. Save and broadcast raw data
    # This call is now non-blocking and will not cause lock errors
    database.save_to_sqlite(data) 
    await raw_manager.broadcast(data.json())

    # 2. Transform and broadcast analog data
    analog_scan_values = transformation_logic.to_simulated_analog(data.scan)
    analog_data = models.AnalogScanData(timestamp=data.timestamp, scan=analog_scan_values)
    await analog_manager.broadcast(analog_data.json())
    
    # 3. Get a prediction from the ML model
    prediction = ml_predictor.predict_next_state(
        new_scan=data.scan, 
        last_timestamp=data.timestamp
    )
    
    # 4. If a prediction was generated, broadcast it
    if prediction:
        await prediction_manager.broadcast(prediction.json())


# --- API and WebSocket Endpoints (No changes needed below this line) ---
# Your existing endpoints will work perfectly with this new setup.

@app.post("/scan", status_code=202)
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
        channel=channel, start_time=start_time, end_time=end_time
    )
    return {"channel": channel, "data": historical_data}

@app.websocket("/ws/raw")
async def websocket_raw_endpoint(websocket: WebSocket):
    # ... (code is correct)
    await raw_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        raw_manager.disconnect(websocket)


@app.websocket("/ws/analog")
async def websocket_analog_endpoint(websocket: WebSocket):
    # ... (code is correct)
    await analog_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        analog_manager.disconnect(websocket)

@app.websocket("/ws/prediction")
async def websocket_prediction_endpoint(websocket: WebSocket):
    # ... (code is correct)
    await prediction_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        prediction_manager.disconnect(websocket)

@app.websocket("/ws/reception")
async def websocket_reception_endpoint(websocket: WebSocket):
    # ... (code is correct)
    await websocket.accept()
    print("Client connected to reception endpoint.")
    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = models.RawScanData.parse_raw(message)
                await process_and_broadcast_scan(data)
            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Received invalid data on reception websocket: {e}")
    except WebSocketDisconnect:
        print("Client disconnected from reception endpoint.")
