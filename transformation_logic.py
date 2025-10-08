# app/transformation_logic.py

import random
from typing import List

# These can be tuned to change the look of the spectrogram
NOISE_FLOOR_MIN = 0.0
NOISE_FLOOR_MAX = 0.2
SIGNAL_MIN = 0.6
SIGNAL_MAX = 1.0

def to_simulated_analog(scan: List[int]) -> List[float]:
    """
    Converts a binary scan [0, 1] to a simulated analog scan [0.0-1.0].
    """
    analog_scan = []
    for value in scan:
        if value == 1:
            new_value = random.uniform(SIGNAL_MIN, SIGNAL_MAX)
        else:
            new_value = random.uniform(NOISE_FLOOR_MIN, NOISE_FLOOR_MAX)
        analog_scan.append(round(new_value, 4))
    return analog_scan
