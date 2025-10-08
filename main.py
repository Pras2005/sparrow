# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from . import models, database, websocket, transformation_logic


app = FastAPI(title="RF Scanner API")


raw_manager = websocket.ConnectionManager()
analog_manager = websocket.ConnectionManager()

@app.on_event("startup")
def on_startup():
    """This function runs when the application starts."""
    print("Application starting up...")
    database.setup_database()
    print("Database setup complete.")


@app.post("/scan", status_code=202)
async def receive_scan_data(data: models.RawScanData):
    """
    Receives raw scan data, saves it, and broadcasts both raw and
    simulated analog versions to their respective WebSocket endpoints.
    """
    
    database.save_to_sqlite(data)

    
    await raw_manager.broadcast(data.json())

    
    analog_scan_values = transformation_logic.to_simulated_analog(data.scan)
    analog_data = models.AnalogScanData(timestamp=data.timestamp, scan=analog_scan_values)

    
    await analog_manager.broadcast(analog_data.json())
    
    return {"status": "accepted"}


@app.websocket("/ws/raw")
async def websocket_raw_endpoint(websocket: WebSocket):
    """Broadcasts raw binary scan data [0, 1, ...]."""
    await raw_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        raw_manager.disconnect(websocket)

@app.websocket("/ws/analog")
async def websocket_analog_endpoint(websocket: WebSocket):
    """Broadcasts simulated analog scan data [0.12, 0.87, ...]."""
    await analog_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        analog_manager.disconnect(websocket)

@app.websocket("/ws/reception")
async def websocket_reception_endpoint(websocket: WebSocket):
    """
    A two-way endpoint. It listens for messages from the client and prints them.
    """
    await websocket.accept()
    print("Client connected to reception endpoint.")
    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received message from client: {message}")
    except WebSocketDisconnect:
        print("Client disconnected from reception endpoint.")
