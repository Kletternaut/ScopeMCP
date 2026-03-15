import asyncio
import json
import time
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

class ScopeController:
    def __init__(self):
        self._dev = None
        self._last_cmd_time = 0

    def get_device(self):
        """Findet das USB-Gerät und initialisiert es einmalig oder bei Verlust."""
        if self._dev:
            try:
                # Teste ob Gerät noch da ist
                self._dev.idVendor
                return self._dev
            except:
                self._dev = None

        backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
        if dev:
            try:
                # Unter Windows oft nötig für libusb-win32 Stabilität
                dev.set_configuration()
                usb.util.claim_interface(dev, 0)
            except:
                pass
            self._dev = dev
        return self._dev

    def _clear_buffer(self, dev):
        """Leert den USB-Eingangspuffer gründlich."""
        try:
            while True:
                dev.read(EP_IN, 4096, timeout=10)
        except:
            pass

    def send_cmd(self, dev, cmd):
        """Sende Befehl mit erzwungenen Pausen für Hardware-Stabilität."""
        if not cmd.endswith("\n"):
            cmd += "\n"
        
        # Erzwinge Pause zwischen Befehlen (Rate Limiting)
        now = time.time()
        elapsed = now - self._last_cmd_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)

        self._clear_buffer(dev)
        dev.write(EP_OUT, cmd.encode('ascii'))
        self._last_cmd_time = time.time()
        
        # Relais brauchen Zeit zum Schalten
        if "SCAL" in cmd.upper():
            time.sleep(1.5)
        else:
            time.sleep(0.1)

    def read_resp(self, dev, size=8192, timeout=2000):
        """Liest Antwort vom Gerät."""
        try:
            data = dev.read(EP_IN, size, timeout=timeout)
            if not data: return None
            return bytes(data)
        except Exception:
            return None

scope = ScopeController()

@mcp.tool()
async def get_live_metadata() -> dict:
    """Ruft den vollständigen JSON-Metadaten-Header ab (Frequenz, Vpp, Timebase, etc.)."""
    dev = scope.get_device()
    if not dev: return {"error": "Oszi nicht gefunden oder nicht eingeschaltet."}
    
    scope.send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    time.sleep(0.5)
    header_raw = scope.read_resp(dev, size=8192, timeout=2000)
    
    if header_raw and b'{' in header_raw:
        try:
            start = header_raw.find(b'{')
            end = header_raw.rfind(b'}') + 1
            json_str = header_raw[start:end].decode('ascii', errors='ignore')
            return json.loads(json_str)
        except Exception as e:
            return {"error": f"JSON parse error: {str(e)}", "raw_len": len(header_raw)}
    
    return {"error": "Keine Metadaten-Antwort erhalten (Timeout). Bitte Gerät neu starten."}

@mcp.tool()
async def set_horizontal_scale(scale: str) -> str:
    """Setzt die Zeitbasis (Horizontal-Skalierung). Beispiele: '1ms', '500us', '100ns'."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    scope.send_cmd(dev, f":HORizontal:SCALe {scale}")
    return f"Horizontal-Skalierung auf {scale} gesetzt. (1.5s Pause für Stabilisierung erfolgt)"

@mcp.tool()
async def set_vertical_scale(channel: int, scale: str) -> str:
    """Setzt die vertikale Skalierung für einen Kanal. Beispiele: '1.00V', '500mV', '2V'."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    scope.send_cmd(dev, f":CH{channel}:SCALe {scale}")
    return f"Kanal {channel} Skalierung auf {scale} gesetzt. (Hardware-Relais geschaltet)"

@mcp.tool()
async def run_autoset() -> str:
    """Führt ein Autoset am Oszilloskop durch."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    scope.send_cmd(dev, ":AUToset on")
    time.sleep(3) # Autoset dauert lange
    return "Autoset ausgeführt."

@mcp.tool()
async def set_running_state(state: str) -> str:
    """Setzt das Oszilloskop auf 'RUN' oder 'STOP'."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    cmd = "STOP" if state.upper() == "STOP" else "RUN"
    # Befehl formatieren: :run oder :stop
    scope.send_cmd(dev, f":{cmd.lower()}")
    return f"Status auf {cmd} gesetzt."

if __name__ == "__main__":
    mcp.run()
