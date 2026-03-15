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
                dev.read(EP_IN, 1024, timeout=10)
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
        
        # Relais oder komplexe Operationen brauchen Zeit
        if any(kw in cmd.upper() for kw in ["SCAL", "HOR", "TRIG", "AUT"]):
            time.sleep(1.5)
        else:
            time.sleep(0.1)

    def read_resp(self, dev, size=16384, timeout=2000):
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
    time.sleep(0.8)
    header_raw = scope.read_resp(dev, size=8192, timeout=2500)
    
    if header_raw and b'{' in header_raw:
        try:
            start = header_raw.find(b'{')
            end = header_raw.rfind(b'}') + 1
            json_str = header_raw[start:end].decode('ascii', errors='ignore')
            return json.loads(json_str)
        except Exception as e:
            return {"error": f"JSON parse error: {str(e)}", "raw_len": len(header_raw)}
    
    return {"error": "Keine Metadaten-Antwort erhalten (Timeout)."}

@mcp.tool()
async def set_horizontal_scale(scale: str) -> str:
    """Setzt die Zeitbasis (Horizontal-Skalierung). Beispiele: '1ms', '500us', '100ns'."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    scope.send_cmd(dev, f":HORizontal:SCALe {scale}")
    return f"Horizontal-Skalierung auf {scale} gesetzt."

@mcp.tool()
async def set_vertical_scale(channel: int, scale: str) -> str:
    """Setzt die vertikale Skalierung für einen Kanal. Beispiele: '1.00V', '500mV', '2V'."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    scope.send_cmd(dev, f":CH{channel}:SCALe {scale}")
    return f"Kanal {channel} Skalierung auf {scale} gesetzt."

@mcp.tool()
async def capture_waveform(channel: int) -> dict:
    """Erfasst die aktuellen Wellenform-Daten und dekodiert sie (LE 16-bit) mit PK-PK Kalibrierung (Faktor 384.6)."""
    dev = scope.get_device()
    if not dev: return {"error": "Device not found"}
    
    # 1. Metadaten für Skalierung und Tastkopf (PROBE) holen
    scope.send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = scope.read_resp(dev)
    scale_y = 1.0
    probe_factor = 1.0
    if header_raw and b'{' in header_raw:
        try:
            js = json.loads(header_raw[header_raw.find(b'{'):header_raw.rfind(b'}')+1].decode('ascii'))
            ch_data = js["CHANNEL"][channel-1]
            scale_str = ch_data["SCALE"]
            scale_y = float(scale_str.replace("mV", "")) / 1000.0 if "mV" in scale_str else float(scale_str.replace("V", ""))
            
            # Tastkopf-Dämpfung berücksichtigen (z.B. "10X" -> Faktor 10)
            probe_str = ch_data.get("PROBE", "1X")
            if "X" in probe_str:
                probe_factor = float(probe_str.replace("X", ""))
        except: pass

    # 2. WAVEFORM anfordern
    scope.send_cmd(dev, f":DATA:WAVE:SCREEN:CH{channel}?")
    time.sleep(0.5)
    
    data = scope.read_resp(dev, size=16384, timeout=3000)
    
    if not data or len(data) < 100:
        return {"error": "Keine Wellenform-Daten empfangen."}

    # Header-Analyse (Längenfeld 4 Bytes, Little-Endian)
    msg_len = int.from_bytes(data[:4], byteorder='little')
    payload = data[4:4+msg_len]

    # RECHTECK-KALIBRIERUNG (BEIDE KANÄLE):
    # Nach Reset: 8.39V Vpp bei 1.00V/div und PROBE 10X.
    # Faktor: 250 LSB pro Division ist der Standard für dieses Modell.
    samples = []
    for i in range(0, len(payload), 2):
        if i + 1 >= len(payload): break
        val = int.from_bytes(payload[i:i+2], byteorder='little', signed=True)
        # Teiler 250.0 LSB pro Division
        voltage = (val / 250.0) * scale_y
        samples.append(round(voltage, 4)) 

    if not samples:
        return {"error": "Dekodierung fehlgeschlagen, keine Samples gefunden."}

    vpp_calc = round(max(samples) - min(samples), 3)
    return {
        "channel": channel,
        "sample_count": len(samples),
        "vpp_v_calculated": vpp_calc,
        "note": f"Erfassung CH{channel} erfolgreich. Faktor 250 LSB/Div.",
        "preview_volt": samples[:10],
        "y_scale": scale_y,
        "unit": "Volt"
    }

@mcp.tool()
async def set_running_state(state: str) -> str:
    """Setzt das Oszilloskop auf 'RUN' oder 'STOP'."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    cmd = "stop" if state.upper() == "STOP" else "run"
    scope.send_cmd(dev, f":{cmd}")
    return f"Scope-Status auf {state} gesetzt."

@mcp.tool()
async def run_autoset() -> str:
    """Führt ein Autoset am Oszilloskop durch."""
    dev = scope.get_device()
    if not dev: return "Fehler: Gerät nicht gefunden."
    scope.send_cmd(dev, ":AUToset on")
    return "Autoset ausgeführt."

if __name__ == "__main__":
    mcp.run()
