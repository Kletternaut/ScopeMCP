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
        # Auf Linux muss der Kernel-Treiber oft gelöst werden, damit PyUSB zugreifen kann
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
                print("ℹ️ Kernel-Treiber gelöst (Linux).")
        except NotImplementedError:
            # Unter Windows wird diese Methode nicht unterstützt (kein Fehler)
            pass
        except Exception as e:
            print(f"⚠️ Warnung beim Lösen des Kernel-Treibers: {e}")

        dev.set_configuration()
    return dev

def send_cmd(dev, cmd):
    """Sende Befehl mit \r\n Terminator und Wartezeit für Hardware-Stabilität."""
    if not cmd.endswith("\r\n"):
        cmd += "\r\n"
    dev.write(EP_OUT, cmd.encode('ascii'))
    time.sleep(0.3)

def read_resp(dev, size=8192, timeout=2000):
    """Liest Antwort vom Gerät."""
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        if len(data) == 0: return None
        return data.tobytes()
    except Exception:
        return None

@mcp.tool()
async def get_live_metadata() -> dict:
    """Ruft den vollständigen JSON-Metadaten-Header ab (Frequenz, Vpp, Timebase, etc.).
    Dies ist die zuverlässigste Methode für dieses Modell (V3.1.0).
    """
    dev = get_device()
    if not dev: return {"error": "Device not found"}
    
    # Handshake zur Sicherheit
    send_cmd(dev, ":MODel?")
    read_resp(dev, timeout=500) 

    # Den JSON-Header abrufen
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = read_resp(dev, size=4096, timeout=3000)
    
    if header_raw and b'{' in header_raw:
        try:
            json_str = header_raw[header_raw.find(b'{'):].decode('ascii', errors='ignore').strip()
            return json.loads(json_str)
        except Exception as e:
            return {"error": f"JSON parse error: {str(e)}", "raw": header_raw.hex()[:100]}
    
    return {"error": "No JSON header received (Timeout or empty)"}

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
    """Gibt den aktuell gelesenen Status (Modell, Skalierung, Zeitbasis, JSON-Metadaten) zurück."""
    dev = get_device()
    if not dev: return {"error": "Device not found"}
    
    # 1. Metadaten (JSON) als Basis
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = read_resp(dev, size=4096)
    header_json = {}
    if header_raw and b'{' in header_raw:
        try:
            json_str = header_raw[header_raw.find(b'{'):].decode('ascii', errors='ignore')
            header_json = json.loads(json_str)
        except: pass

    # 2. Modell Info
    send_cmd(dev, ":MODel?")
    model = read_resp(dev).decode('ascii', errors='ignore').strip() if not header_json else header_json.get("MODEL")
    
    return {
        "model": model,
        "metadata": header_json,
        "status": header_json.get("RUNSTATUS", "UNKNOWN")
    }

@mcp.tool()
async def set_horizontal_scale(scale: str) -> str:
    """Setzt die Zeitbasis (Horizontal-Skalierung). Beispiele: '1ms', '500us', '100ns'."""
    dev = get_device()
    if not dev: return "Device not found"
    send_cmd(dev, f":HORizontal:SCALe {scale}")
    return f"Horizontal-Skalierung auf {scale} gesetzt."

@mcp.tool()
async def set_vertical_scale(channel: int, scale: str) -> str:
    """Setzt die vertikale Skalierung für einen Kanal. Beispiele: '1.00V', '500mV'."""
    dev = get_device()
    if not dev: return "Device not found"
    send_cmd(dev, f":CH{channel}:SCALe {scale}")
    return f"Kanal {channel} Skalierung auf {scale} gesetzt."

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
