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
        self._meta_cache = None          # FIX 1: Metadaten-Cache
        self._meta_cache_time = 0        # FIX 1: Zeitstempel des Caches

    def get_device(self):
        """Findet das USB-Gerät und initialisiert es einmalig oder bei Verlust."""
        if self._dev:
            try:
                self._dev.idVendor
                return self._dev
            except:
                self._dev = None

        backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
        if dev:
            try:
                dev.set_configuration()
                usb.util.claim_interface(dev, 0)
            except:
                pass
            self._dev = dev
        return self._dev

    def _clear_buffer(self, dev):
        """Leert den USB-Eingangspuffer. FIX 2: Nur noch 3 Versuche statt endlos."""
        for _ in range(3):  # FIX 2: War 'while True' - blockierte bei vollem Puffer!
            try:
                dev.read(EP_IN, 4096, timeout=5)  # FIX 2: 4KB statt 1KB, 5ms statt 10ms
            except:
                break  # Puffer leer, fertig

    def send_cmd(self, dev, cmd):
        """Sende Befehl im Owon-Binär-Format (4 Bytes Länge + Befehl + \\n)."""
        if not cmd.startswith(":"):
            cmd = ":" + cmd
        if not cmd.endswith("\n"):
            cmd += "\n"

        cmd_bytes = cmd.encode('ascii')
        length_header = len(cmd_bytes).to_bytes(4, byteorder='little')
        packet = length_header + cmd_bytes

        # FIX 3: Throttle von 300ms auf 50ms reduziert
        now = time.time()
        elapsed = now - self._last_cmd_time
        if elapsed < 0.05:  # FIX 3: War 0.3 (300ms!) → jetzt 50ms
            time.sleep(0.05 - elapsed)

        self._clear_buffer(dev)
        dev.write(EP_OUT, packet)
        self._last_cmd_time = time.time()

        # Delays je nach Kommandotyp
        if any(kw in cmd.upper() for kw in ["AUT"]):
            time.sleep(1.0)   # Autoset braucht wirklich Zeit
        elif any(kw in cmd.upper() for kw in ["SCAL", "HOR", "TRIG", "OFFS"]):
            time.sleep(0.1)   # Relais-Schaltzeit
        else:
            time.sleep(0.001) # Abfragen fast sofort

    def read_resp(self, dev, size=32768, timeout=800):
        """Liest Antwort vom Gerät mit optimiertem USB-Bulk-Transfer."""
        try:
            data = dev.read(EP_IN, size, timeout=timeout)
            if not data: return None
            return bytes(data)
        except:
            return None

    def get_metadata_cached(self, dev, max_age=2.0):
        """FIX 1: Metadaten mit Cache (max_age Sekunden), spart 1-2 USB-Roundtrips."""
        now = time.time()
        if self._meta_cache and (now - self._meta_cache_time) < max_age:
            return self._meta_cache  # Cache-Hit, kein USB-Transfer!

        self.send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
        header_raw = self.read_resp(dev, size=8192, timeout=500)
        if header_raw and b'{' in header_raw:
            try:
                json_str = header_raw[header_raw.find(b'{'):header_raw.rfind(b'}')+1].decode('ascii', errors='ignore')
                self._meta_cache = json.loads(json_str)
                self._meta_cache_time = now
                return self._meta_cache
            except:
                pass
        return {}

scope = ScopeController()


@mcp.tool()
async def get_live_metadata() -> dict:
    """Holt JSON-Metadaten (Frequenz, Vpp, Timebase, etc.)."""
    dev = scope.get_device()
    if not dev: return {"error": "Device not found"}
    # FIX 1: Cache mit force-refresh (max_age=0 → immer neu laden bei explizitem Aufruf)
    scope._meta_cache = None
    return scope.get_metadata_cached(dev)


@mcp.tool()
async def set_horizontal_scale(scale: str) -> str:
    """Zeitbasis setzen (z.B. '1ms', '500us')."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope._meta_cache = None  # FIX 1: Cache invalidieren nach Änderung
    scope.send_cmd(dev, f":HORizontal:SCALe {scale}")
    return f"Horizontal Scale: {scale}"


@mcp.tool()
async def set_vertical_scale(channel: int, scale: str) -> str:
    """Volt/Div setzen (z.B. '1V', '500mV')."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope._meta_cache = None  # FIX 1: Cache invalidieren nach Änderung
    scope.send_cmd(dev, f":CH{channel}:SCALe {scale}")
    return f"Channel {channel} Scale: {scale}"


@mcp.tool()
async def set_channel_coupling(channel: int, coupling: str) -> str:
    """Kopplung setzen ('AC', 'DC', 'GND')."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope._meta_cache = None  # FIX 1: Cache invalidieren nach Änderung
    scope.send_cmd(dev, f":CH{channel}:COUPling {coupling.upper()}")
    return f"Channel {channel} Coupling: {coupling.upper()}"


@mcp.tool()
async def set_voltage_offset(channel: int, offset: float) -> str:
    """Offset setzen in Volt (z.B. 0.0, -1.5)."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope._meta_cache = None  # FIX 1: Cache invalidieren nach Änderung
    scope.send_cmd(dev, f":CH{channel}:OFFSet {offset:.3f}")
    return f"Channel {channel} Offset: {offset:.3f}V"


@mcp.tool()
async def capture_waveform(channel: int, max_samples: int = 500) -> dict:
    """Erfasst Wellenform mit optimierten Wartezeiten."""
    dev = scope.get_device()
    if not dev: return {"error": "No Device"}

    # FIX 1: Metadaten aus Cache holen (kein extra USB-Roundtrip wenn frisch)
    meta = scope.get_metadata_cached(dev)

    # FIX 4: Keine extra time.sleep(0.1) nach send_cmd - timeout in read_resp reicht
    scope.send_cmd(dev, f":DATA:WAVE:SCREEN:CH{channel}?")
    data = scope.read_resp(dev, size=16384, timeout=2000)  # FIX 4: War 1500ms
    if not data or len(data) < 10: return {"error": "No wave data"}

    raw_samples = []
    for i in range(4, len(data) - 1, 2):
        val = int.from_bytes(data[i:i+2], byteorder='little', signed=True)
        raw_samples.append(val)

    total = len(raw_samples)
    step = max(1, total // max_samples)
    final_samples = raw_samples[::step]

    ch_info = meta.get("CHANNEL", [{}, {}])[channel - 1]
    return {
        "channel": channel,
        "raw_samples": final_samples,
        "original_count": total,
        "downsampled_count": len(final_samples),
        "metadata": {
            "scale_v_per_div_raw": ch_info.get("SCALE", "1V"),
            "probe_factor": ch_info.get("PROBE", "1X"),
            "grid_offset": ch_info.get("OFFSET", 0),
            "lsb_per_div": 250.0
        },
        "instruction": "voltage = (raw - offset) / 250 * scale * probe"
    }


@mcp.tool()
async def capture_dual_waveform(max_samples: int = 400) -> dict:
    """Erfasst BEIDE Kanäle gleichzeitig. Optimiert für maximalen USB-Durchsatz."""
    dev = scope.get_device()
    if not dev: return {"error": "No Device"}

    # FIX 1: Metadaten aus Cache - bei Dual-Capture besonders wertvoll
    meta = scope.get_metadata_cached(dev)

    results = {}
    for ch in [1, 2]:
        scope.send_cmd(dev, f":DATA:WAVE:SCREEN:CH{ch}?")
        # FIX 4: Kein time.sleep() hier - read_resp wartet mit Timeout
        data = scope.read_resp(dev, size=8192, timeout=2000)  # FIX 4: War 1500ms

        if data and len(data) > 100:
            raw = []
            for i in range(4, len(data) - 1, 2):
                if i + 1 >= len(data): break
                raw.append(int.from_bytes(data[i:i+2], byteorder='little', signed=True))

            step = max(1, len(raw) // max_samples)
            results[f"CH{ch}"] = {
                "samples": raw[::step],
                "meta": meta.get("CHANNEL", [{}, {}])[ch - 1]
            }

    return {
        "channels": results,
        "lsb_per_div": 250.0,
        "instruction": "voltage = (raw - offset) / 250 * scale * probe"
    }


@mcp.tool()
async def set_trigger_mode(mode: str) -> str:
    """Modus setzen ('AUTO', 'NORMAL', 'SINGLE')."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope.send_cmd(dev, f":TRIGger:SWEep {mode.upper()}")
    return f"Trigger Mode: {mode.upper()}"


@mcp.tool()
async def set_trigger_slope(slope: str) -> str:
    """Flanke setzen ('RISE' oder 'FALL')."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope.send_cmd(dev, f":TRIGger:EDGE:SLOpe {slope.upper()}")
    return f"Trigger Slope: {slope.upper()}"


@mcp.tool()
async def set_trigger_source(source: str) -> str:
    """Quelle setzen ('CH1' oder 'CH2')."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope.send_cmd(dev, f":TRIGger:EDGE:SOURce {source.upper()}")
    return f"Trigger Source: {source.upper()}"


@mcp.tool()
async def run_autoset() -> str:
    """Führt Autoset aus."""
    dev = scope.get_device()
    if not dev: return "No Device"
    scope._meta_cache = None  # FIX 1: Cache invalidieren nach Autoset
    scope.send_cmd(dev, ":AUToset on")
    return "Autoset initiated."


@mcp.tool()
async def set_run_state(state: str) -> str:
    """'RUN' oder 'STOP'."""
    dev = scope.get_device()
    if not dev: return "No Device"
    cmd = "run" if "RUN" in state.upper() else "stop"
    scope.send_cmd(dev, f":{cmd}")
    return f"Scope is now {cmd.upper()}"


if __name__ == "__main__":
    mcp.run()