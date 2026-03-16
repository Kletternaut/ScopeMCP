import asyncio
import json
import math
import time
import logging
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
from mcp.server.fastmcp import FastMCP
from ds1102_logic import parse_raw_samples, parse_scale_to_volts, VOLTAGE_FORMULA, LSB_PER_DIV

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScopeMCP")

# Oszilloskop Konfiguration & Konstanten
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81
USB_READ_SIZE_LARGE = 32768
USB_READ_SIZE_SMALL = 8192
# LSB_PER_DIV wird direkt aus ds1102_logic importiert
META_CACHE_TTL = 2.0  # Sekunden
CMD_THROTTLE_S = 0.05

# MCP Server Initialisierung
mcp = FastMCP("DS1102-Oscilloscope")


class ScopeController:
    def __init__(self):
        self._dev = None
        self._last_cmd_time = 0
        self._meta_cache = None
        self._meta_cache_time = 0

    def get_device(self):
        """Findet das USB-Geraet und initialisiert es einmalig oder bei Verlust."""
        if self._dev:
            try:
                self._dev.idVendor
                return self._dev
            except Exception:
                logger.warning("USB Device lost, re-initializing...")
                self._dev = None

        try:
            backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
            dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
            if dev:
                dev.set_configuration()
                usb.util.claim_interface(dev, 0)
                self._dev = dev
                logger.info(f"USB Device connected (VID:{VID:04x} PID:{PID:04x})")
        except Exception as e:
            logger.error(f"Failed to initialize USB device: {e}")
            self._dev = None

        return self._dev

    def _clear_buffer(self, dev):
        """Leert den USB-Eingangspuffer."""
        for _ in range(3):
            try:
                dev.read(EP_IN, 4096, timeout=5)
            except usb.core.USBError:
                break
            except Exception:
                break

    def send_cmd(self, dev, cmd, clear_buffer=True):
        """Sendet Befehl im Owon-Binaer-Format."""
        if not cmd.startswith(":"):
            cmd = ":" + cmd
        if not cmd.endswith("\n"):
            cmd += "\n"

        cmd_bytes = cmd.encode("ascii")
        length_header = len(cmd_bytes).to_bytes(4, byteorder="little")
        packet = length_header + cmd_bytes

        now = time.time()
        elapsed = now - self._last_cmd_time
        if elapsed < CMD_THROTTLE_S:
            time.sleep(CMD_THROTTLE_S - elapsed)

        if clear_buffer:
            self._clear_buffer(dev)

        try:
            dev.write(EP_OUT, packet)
        except usb.core.USBError as e:
            logger.error(f"USB Write Error: {e}")
            self._dev = None
            raise

        self._last_cmd_time = time.time()

        if any(kw in cmd.upper() for kw in ["AUT"]):
            time.sleep(1.0)
        elif any(kw in cmd.upper() for kw in ["SCAL", "HOR", "TRIG", "OFFS"]):
            time.sleep(0.1)
        else:
            time.sleep(0.001)

    def read_resp(self, dev, size=USB_READ_SIZE_LARGE, timeout=800):
        """Liest Antwort vom Geraet mit Retry-Logik."""
        for attempt in range(2):
            try:
                data = dev.read(EP_IN, size, timeout=timeout)
                if not data:
                    return None
                return bytes(data)
            except usb.core.USBError as e:
                if attempt == 0:
                    logger.warning(f"USB Read retry due to: {e}")
                    time.sleep(0.05)
                    continue
                logger.error(f"USB Read failed after retry: {e}")
                self._dev = None
                return None
            except Exception as e:
                logger.error(f"Unexpected read error: {e}")
                return None

    def get_metadata_cached(self, dev, max_age=META_CACHE_TTL):
        """Metadaten mit Cache (max_age Sekunden)."""
        now = time.time()
        if self._meta_cache and (now - self._meta_cache_time) < max_age:
            return self._meta_cache

        try:
            self.send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?", clear_buffer=True)
            header_raw = self.read_resp(dev, size=USB_READ_SIZE_SMALL, timeout=500)
            if header_raw and b"{" in header_raw:
                json_str = header_raw[header_raw.find(b"{"):header_raw.rfind(b"}")+1].decode("ascii", errors="ignore")
                self._meta_cache = json.loads(json_str)
                self._meta_cache_time = now
                # DEBUG-Logging entfernt – Key 'OFFSET' durch Live-Test verifiziert.
                return self._meta_cache
        except Exception as e:
            logger.error(f"Metadata fetch failed: {e}")

        return {}


scope = ScopeController()


@mcp.tool()
async def get_connection_status() -> dict:
    """Prueft ob das Scope verbunden und erreichbar ist."""
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return {"connected": False, "error": "No USB device found"}
    try:
        meta = await asyncio.to_thread(scope.get_metadata_cached, dev, 0)
        return {
            "connected": True,
            "model": meta.get("MODEL", "DS1102"),
            "run_status": meta.get("RUNSTATUS"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    except Exception as e:
        logger.error(f"Connection status check failed: {e}")
        return {"connected": False, "error": str(e)}


@mcp.tool()
async def get_live_metadata() -> dict:
    """Holt JSON-Metadaten (Frequenz, Vpp, Timebase, etc.)."""
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return {"error": "Device not found"}
    scope._meta_cache = None
    return await asyncio.to_thread(scope.get_metadata_cached, dev)


@mcp.tool()
async def get_measurements() -> dict:
    """Liefert Messwerte beider Kanaele aus dem Metadaten-Cache (Freq, Period, Scale, Probe).

    Hinweis: Vpp und RMS sind im Metadaten-Cache nicht enthalten.
    Dafuer waeren separate :MEASure:PKPK? / :MEASure:Vrms?-Queries noetig (nicht implementiert).
    Das Feld raw_channel_keys zeigt alle verfuegbaren JSON-Keys der Firmware
    und dient der Diagnose unbekannter Felder (z.B. GridOffset-Key).
    """
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return {"error": "No Device"}

    meta = await asyncio.to_thread(scope.get_metadata_cached, dev, 0)

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "channels": {},
        "timebase": meta.get("TIMEBASE", {}),
        "run_status": meta.get("RUNSTATUS"),
    }

    for i, ch in enumerate(meta.get("CHANNEL", [])):
        name = ch.get("NAME", f"CH{i+1}")
        freq = ch.get("FREQUENCE", 0)
        result["channels"][name] = {
            "frequency_hz": freq,
            "period_ms": round(1000 / freq, 4) if freq and freq > 0 else None,
            "scale": ch.get("SCALE"),
            "probe": ch.get("PROBE"),
            "coupling": ch.get("COUPLING"),
            "display": ch.get("DISPLAY"),
            "raw_channel_keys": list(ch.keys()),
        }

    return result


@mcp.tool()
async def capture_waveform(channel: int, max_samples: int = 500) -> dict:
    """Erfasst Wellenform eines Kanals."""
    if channel not in (1, 2):
        return {"error": f"Invalid channel: {channel}"}

    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return {"error": "No Device"}

    meta = await asyncio.to_thread(scope.get_metadata_cached, dev)

    await asyncio.to_thread(scope.send_cmd, dev, f":DATA:WAVE:SCREEN:CH{channel}?", clear_buffer=True)
    data = await asyncio.to_thread(scope.read_resp, dev, size=USB_READ_SIZE_LARGE, timeout=2000)

    if not data or len(data) < 10:
        return {"error": "No wave data"}

    samples_np = parse_raw_samples(data)
    if samples_np is None:
        logger.error("Parsing error: parse_raw_samples returned None")
        return {"error": "Data corruption during parsing"}

    total = len(samples_np)
    # ceil garantiert downsampled_count <= max_samples (fix fuer off-by-one mit floor)
    step = max(1, math.ceil(total / max_samples))
    final_samples = samples_np[::step].tolist()

    ch_list = meta.get("CHANNEL", [{}, {}])
    ch_info = ch_list[channel - 1] if len(ch_list) >= channel else {}
    offset = ch_info.get("OFFSET", 0)
    
    # Probe factor sicherstellen (Default 1.0 falls nicht vorhanden oder ungültig)
    try:
        probe = float(ch_info.get("PROBE", 1.0))
    except (ValueError, TypeError):
        probe = 1.0

    return {
        "channel": channel,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "raw_samples": final_samples,
        "original_count": total,
        "downsampled_count": len(final_samples),
        "offset": offset,
        "probe": probe,
        "metadata": ch_info,
        "timebase": meta.get("TIMEBASE", {}),
        "lsb_per_div": LSB_PER_DIV,
        "instruction": VOLTAGE_FORMULA,
    }


@mcp.tool()
async def capture_dual_waveform(max_samples: int = 400) -> dict:
    """Erfasst BEIDE Kanaele gleichzeitig."""
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return {"error": "No Device"}

    meta = await asyncio.to_thread(scope.get_metadata_cached, dev)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    results = {}

    await asyncio.to_thread(scope._clear_buffer, dev)

    for ch in [1, 2]:
        await asyncio.to_thread(scope.send_cmd, dev, f":DATA:WAVE:SCREEN:CH{ch}?", clear_buffer=False)
        data = await asyncio.to_thread(scope.read_resp, dev, size=USB_READ_SIZE_LARGE, timeout=2000)

        if data and len(data) > 100:
            samples_np = parse_raw_samples(data)
            if samples_np is not None:
                ch_info = meta.get("CHANNEL", [{}, {}])[ch - 1]
                # Probe factor sicherstellen
                try:
                    probe = float(ch_info.get("PROBE", 1.0))
                except (ValueError, TypeError):
                    probe = 1.0
                
                # ceil garantiert downsampled_count <= max_samples
                step = max(1, math.ceil(len(samples_np) / max_samples))
                results[f"CH{ch}"] = {
                    "samples": samples_np[::step].tolist(),
                    "offset": ch_info.get("OFFSET", 0),
                    "probe": probe,
                    "metadata": ch_info,
                }
            else:
                results[f"CH{ch}_error"] = "Parsing failed"
        else:
            results[f"CH{ch}_error"] = "No data"

    return {
        "timestamp": timestamp,
        "channels": results,
        "timebase": meta.get("TIMEBASE", {}),
        "lsb_per_div": LSB_PER_DIV,
        "instruction": VOLTAGE_FORMULA,
    }


@mcp.tool()
async def run_autoset() -> str:
    """Fuehrt Autoset aus."""
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    scope._meta_cache = None
    await asyncio.to_thread(scope.send_cmd, dev, ":AUToset on")
    return "Autoset initiated."


@mcp.tool()
async def set_run_state(state: str) -> str:
    """RUN oder STOP."""
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    cmd = "run" if "RUN" in state.upper() else "stop"
    await asyncio.to_thread(scope.send_cmd, dev, f":{cmd}")
    return f"Scope is now {cmd.upper()}"


@mcp.tool()
async def set_vertical_scale(channel: int, scale: str) -> str:
    """Volt/Div setzen (z.B. 1V, 500mV)."""
    if channel not in (1, 2):
        return f"Invalid channel: {channel}"
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    scope._meta_cache = None
    await asyncio.to_thread(scope.send_cmd, dev, f":CH{channel}:SCALe {scale}")
    return f"Channel {channel} Scale: {scale}"


@mcp.tool()
async def set_horizontal_scale(scale: str) -> str:
    """Zeitbasis setzen (z.B. 1ms, 500us)."""
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    scope._meta_cache = None
    await asyncio.to_thread(scope.send_cmd, dev, f":HORizontal:SCALe {scale}")
    return f"Horizontal Scale: {scale}"


@mcp.tool()
async def set_channel_coupling(channel: int, coupling: str) -> str:
    """Kopplung setzen (AC, DC, GND)."""
    if channel not in (1, 2):
        return f"Invalid channel: {channel}"
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    scope._meta_cache = None
    await asyncio.to_thread(scope.send_cmd, dev, f":CH{channel}:COUPling {coupling.upper()}")
    return f"Channel {channel} Coupling: {coupling.upper()}"


@mcp.tool()
async def set_voltage_offset(channel: int, offset: float) -> str:
    """Offset setzen in Volt (z.B. 0.0, -1.5)."""
    if channel not in (1, 2):
        return f"Invalid channel: {channel}"
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    scope._meta_cache = None
    await asyncio.to_thread(scope.send_cmd, dev, f":CH{channel}:OFFSet {offset:.3f}")
    return f"Channel {channel} Offset: {offset:.3f}V"


@mcp.tool()
async def set_trigger_mode(mode: str) -> str:
    """Trigger-Modus setzen (AUTO, NORMAL, SINGLE)."""
    valid_modes = ["AUTO", "NORMAL", "SINGLE"]
    mode_up = mode.upper()
    if mode_up not in valid_modes:
        return f"Invalid mode: {mode}. Use {valid_modes}"
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    await asyncio.to_thread(scope.send_cmd, dev, f":TRIGger:SWEep {mode_up}")
    return f"Trigger Mode: {mode_up}"


@mcp.tool()
async def set_trigger_slope(slope: str) -> str:
    """Trigger-Flanke setzen (RISE, FALL)."""
    valid_slopes = ["RISE", "FALL"]
    slope_up = slope.upper()
    if slope_up not in valid_slopes:
        return f"Invalid slope: {slope}. Use {valid_slopes}"
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    await asyncio.to_thread(scope.send_cmd, dev, f":TRIGger:EDGE:SLOpe {slope_up}")
    return f"Trigger Slope: {slope_up}"


@mcp.tool()
async def set_trigger_source(source: str) -> str:
    """Trigger-Quelle setzen (CH1, CH2)."""
    valid_sources = ["CH1", "CH2"]
    source_up = source.upper()
    if source_up not in valid_sources:
        return f"Invalid source: {source}. Use {valid_sources}"
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    await asyncio.to_thread(scope.send_cmd, dev, f":TRIGger:EDGE:SOURce {source_up}")
    return f"Trigger Source: {source_up}"


@mcp.tool()
async def set_trigger_level(level_mv: float) -> str:
    """Trigger-Schwelle in mV setzen (z.B. 500.0 fuer 0.5V)."""
    dev = await asyncio.to_thread(scope.get_device)
    if not dev:
        return "No Device"
    scope._meta_cache = None
    await asyncio.to_thread(scope.send_cmd, dev, f":TRIGger:EDGE:LEVel {level_mv:.1f}mV")
    return f"Trigger Level: {level_mv:.1f}mV"


if __name__ == "__main__":
    mcp.run()
