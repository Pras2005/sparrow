# app/models.py
from pydantic import BaseModel
from typing import List

# For incoming raw data
class RawScanData(BaseModel):
    timestamp: int
    scan: List[int]

# For outgoing simulated analog data
class AnalogScanData(BaseModel):
    timestamp: int
    scan: List[float] # The only change is from int to float
