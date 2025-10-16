import serial
import serial.tools.list_ports
import requests
import json
import time
import sys

# --- Configuration ---
FASTAPI_URL = 'http://127.0.0.1:8000/scan'
BAUD_RATE = 115200 # Match this to your ESP32 firmware

def select_port():
    """
    Lists available serial ports and prompts the user to select one.
    """
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("❌ No serial ports found. Make sure your ESP32 is plugged in.")
        return None

    print("Please select the ESP32's serial port:")
    for i, port in enumerate(ports):
        print(f"  [{i}] {port.device}: {port.description}")

    while True:
        try:
            choice = int(input("Enter the number of the port: "))
            if 0 <= choice < len(ports):
                return ports[choice].device
            else:
                print("Invalid number. Please try again.")
        except (ValueError, KeyboardInterrupt):
            print("\nNo port selected. Exiting.")
            return None

def run_relay():
    """
    Reads JSON data from the selected serial port and relays it to the FastAPI server.
    """
    serial_port_name = select_port()
    if not serial_port_name:
        sys.exit()

    print("\n--- Starting Hardware Relay ---")
    print(f"📡 Listening to ESP32 on: {serial_port_name}")
    print(f"🚀 Forwarding data to: {FASTAPI_URL}")
    print("Press CTRL+C to stop.")

    ser = None
    try:
        ser = serial.Serial(serial_port_name, BAUD_RATE, timeout=1)
        
        while True:
            # 1. Read a line of data from the ESP32
            line = ser.readline().decode('utf-8', errors='ignore').strip()

            if line:
                try:
                    # 2. The line from the ESP32 should already be a JSON string.
                    # We parse it into a Python dictionary to send with requests.
                    payload = json.loads(line)
                    timestamp = payload.get('timestamp', 'N/A')

                    # 3. Send the data to the FastAPI server
                    requests.post(FASTAPI_URL, json=payload, timeout=0.5)
                    
                    # Use \r to print on the same line for a cleaner output
                    print(f"Relayed scan from timestamp: {timestamp}        ", end="\r")

                except json.JSONDecodeError:
                    # This handles cases where the ESP32 might send incomplete or non-JSON data
                    print("Received malformed data, skipping...         ", end="\r")
                except requests.exceptions.RequestException:
                    # This handles when the FastAPI server is not running or unreachable
                    print(f"Cannot connect to server. Retrying...        ", end="\r")
                    time.sleep(2)

    except serial.SerialException as e:
        print(f"\nError: Could not open serial port '{serial_port_name}'.")
        print("Please check permissions and ensure no other program is using it.")
    except KeyboardInterrupt:
        print("\n--- Relay stopped by user ---")
    finally:
        if ser and ser.is_open:
            ser.close()
            print(f"Serial port {serial_port_name} closed.")

if __name__ == "__main__":
    run_relay()
