# app/ml_predictor.py

import tensorflow as tf
import numpy as np
from collections import deque
from . import models
import os

# --- Model & Prediction State (Updated for the Old Model) ---
model = None
SEQUENCE_LENGTH = 50  # <-- CHANGED: The old model expects a sequence of 50
NUM_CHANNELS = 126
# The history now stores a simple, flat list of active channel numbers
scan_history = deque(maxlen=SEQUENCE_LENGTH)


def load_model():
    """Loads the pre-trained Keras model into memory."""
    global model
    
    # Path is now pointed back to the old model file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, 'flysky_lstm_final_model_old_data.keras')

    print(f"Attempting to load OLD model from: {model_path}")
    model = tf.keras.models.load_model(model_path)
    print("ML model loaded successfully.")


def predict_next_state(new_scan: list, last_timestamp: int) -> models.PredictionData | None:
    """
    Processes a new 126-element binary scan, updates the simple history,
    and runs a prediction with the old single-label model.
    """
    global model, scan_history
    
    # --- NEW LOGIC ---
    # 1. Convert the 126-element binary scan into a list of active channel numbers.
    # For example, [0, 0, 1, 0, 1, ...] becomes [2, 4, ...]
    active_channels = np.where(np.array(new_scan) == 1)[0]
    
    # 2. Add all newly found active channels to our history
    for ch in active_channels:
        scan_history.append(ch)
    
    # 3. Only run prediction if we have enough history
    if len(scan_history) >= SEQUENCE_LENGTH:
        # Prepare the input: a simple array of the last 50 channel numbers
        input_sequence = np.array(list(scan_history))

        # Add a batch dimension -> shape becomes (1, 50)
        model_input_batch = np.expand_dims(input_sequence, axis=0)
        
        # Run prediction
        predicted_probabilities = model.predict(model_input_batch, verbose=0)[0]
        
        # Convert the raw NumPy array of probabilities to a standard Python list
        prediction_scan_data = predicted_probabilities.tolist()

        # Create the prediction data object
        predicted_timestamp = last_timestamp + 200 # Simple estimation
        
        prediction = models.PredictionData(
            timestamp=predicted_timestamp, 
            scan=prediction_scan_data
        )
        return prediction

    # Return None if we don't have enough history yet
    return None
