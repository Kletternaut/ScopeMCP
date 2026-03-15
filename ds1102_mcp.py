import asyncio
import json
import time
import numpy as np
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
from mcp.server.fastmcp import FastMCP

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

# MCP Server Initialisierung
mcp = FastMCP("DS1102-Oscilloscope")

def get_device():
    """Hilfsfunktion zum Finden des USB-Geräts."""
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    if dev:
        dev.set_configuration()
    return dev

def send_cmd(dev, cmd):
    """Sende Befehl mit \n Terminator."""
    if not cmd.endswith("\n"):
        cmd += "\n"
    dev.write(EP_OUT, cmd.encode('ascii'))
    time.sleep(0.1)

def read_resp(dev, size=8192, timeout=2000):
    """Liest Antwort vom Gerät."""
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        return data.tobytes()
    except Exception:
        return None

@mcp.tool()
async def get_scope_info() -> str:
    """Gibt Modellinformationen des Oszilloskops zurück."""
    dev = get_device()
    if not dev: return "Fehler: Oszilloskop nicht verbunden."
    
    send_cmd(dev, ":MODel?")
    resp = read_resp(dev)
    if resp:
        return f"Modell: {resp.decode('ascii', errors='ignore').strip()}"
    return "Keine Antwort vom Gerät."

@mcp.tool()
async def get_status() -> dict:
    """Liest die aktuellen Einstellungen (Zeitbasis, Volt-Skalierung, etc.) aus."""
    dev = get_device()
    if not dev: return {"error": "Device not found"}
    
    send_cmd(dev, ":MODel?") # Erneuter Handshake zur Sicherheit
    read_resp(dev)
    
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = read_resp(dev)
    if header_raw and b'{' in header_raw:
        json_str = header_raw[header_raw.find(b'{'):].decode('ascii', errors='ignore')
        try:
            return json.loads(json_str)
        except:
            return {"error": "JSON parse error", "raw": json_str}
    return {"error": "No metadata received"}

@mcp.tool()
async def run_autoset() -> str:
    """Führt ein Autoset am Oszilloskop durch."""
    dev = get_device()
    if not dev: return "Device not found"
    send_cmd(dev, ":AUToset on")
    return "Autoset Befehl gesendet."

@mcp.tool()
async def set_running_state(state: str) -> str:
    """Setzt das Oszilloskop auf 'RUN' oder 'STOP'.
    
    Args:
        state: 'RUN' oder 'STOP'
    """
    dev = get_device()
    if not dev: return "Device not found"
    
    if state.upper() == "STOP":
        send_cmd(dev, ":RUNning STOP")
    else:
        send_cmd(dev, ":RUNning RUN")
    return f"Status auf {state.upper()} gesetzt."

@mcp.tool()
async def capture_waveform(channel: int = 1) -> dict:
    """Erfasst die aktuelle Wellenform eines Kanals und gibt die Rohdaten zurück.
    
    Args:
        channel: Kanalnummer (1 oder 2)
    """
    dev = get_device()
    if not dev: return {"error": "Device not found"}
    
    cmd = f":DATA:WAVE:SCREEN:CH{channel}?"
    send_cmd(dev, cmd)
    wave_raw = read_resp(dev)
    
    if wave_raw:
        # Header (4 Bytes) ignorieren, Daten sind Big-Endian 16-Bit
        samples_raw = wave_raw[4:]
        samples = np.frombuffer(samples_raw, dtype='>i2')
        return {
            "channel": channel,
            "sample_count": len(samples),
            "data": samples.tolist()[:100], # Nur die ersten 100 Punkte für die Übersicht
            "full_data_info": f"{len(samples)} Punkte empfangen"
        }
    return {"error": "Capture failed"}

if __name__ == "__main__":
    mcp.run()
