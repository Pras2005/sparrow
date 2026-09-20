# Sparrow (RF Scanner API)

A high-performance **FastAPI** application designed to ingest, process, store, and predict Radio Frequency (RF) scan data in real-time. This system acts as a middleware layer handling raw signal data, translating it into simulated analog formats, and broadcasting both current and predicted future states over WebSockets.

## Core Domain Models & Features

- **Real-Time Data Ingestion**: Accepts raw RF scan vectors (arrays of integers representing channel states) and UNIX timestamps via HTTP POST (`/scan`) or WebSocket (`/ws/reception`).
- **Data Transformation**: Converts raw binary channel values into a simulated analog scale (float arrays) to emulate hardware signal characteristics (`transformation_logic.py`).
- **Machine Learning Prediction**: Integrates a pre-trained Keras LSTM model (`flysky_lstm_final_model_old_data.keras`) to predict the future state of RF channels based on the latest incoming sequences.
- **Asynchronous Storage Worker**: Employs a dedicated background threading model (`database.database_writer_worker`) to persist historical channel states to SQLite without blocking the main event loop, preventing lock contention under high throughput.
- **WebSocket Broadcasting**: Maintains three separate WebSocket managers:
  - `/ws/raw`: Streams raw scan inputs as they arrive.
  - `/ws/analog`: Streams the transformed analog representations.
  - `/ws/prediction`: Streams ML-predicted future channel states.

## Prerequisites

- **Python 3.9+**
- **TensorFlow / Keras** (For loading the `.keras` model)
- **FastAPI** & **Uvicorn**
- **SQLite3**

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url> sparrow
   cd sparrow
   ```
2. **Setup virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. **Install Dependencies**:
   *(Assuming standard environment setup since requirements.txt may not be explicitly listed)*
   ```bash
   pip install fastapi uvicorn pydantic tensorflow pandas
   ```

## Usage / Running Locally

Start the application using Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- **API Documentation**: Available at `http://127.0.0.1:8000/docs`
- **Simulation**: You can optionally run `python simulation_relay.py` to stream mock RF data into the ingest endpoint for testing.

## Project Structure

```text
.
├── main.py                  # FastAPI application entry point, lifecycle events, route definitions
├── models.py                # Pydantic schemas (RawScanData, AnalogScanData, PredictionData)
├── database.py              # SQLite storage logic and background writer thread
├── websocket.py             # WebSocket connection management and broadcasting logic
├── transformation_logic.py  # Algorithms to convert raw data to simulated analog responses
├── ml_predictor.py          # Wrapper for loading and querying the Keras LSTM model
├── flysky_lstm_final_model_old_data.keras  # Pre-trained ML weights for prediction
└── simulation_relay.py      # Utility script to simulate incoming RF scanner hardware data
```
