import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package
import matplotlib.pyplot as plt
import numpy as np
import json
import re

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def send_cmd(dev, cmd):
    if not cmd.endswith("\r\n"):
        cmd += "\r\n"
    dev.write(EP_OUT, cmd.encode('ascii'))

def read_resp(dev, size=16384, timeout=1000):
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        return data.tobytes()
    except usb.core.USBError:
        return None

def parse_value(val_str):
    """Extrahiert Zahl und Einheit (z.B. '500mV' -> 0.5, '50us' -> 5e-05)"""
    if not val_str or not isinstance(val_str, str): return 1.0
    match = re.match(r"([0-9.]+)([a-zA-Z]*)", val_str)
    if not match: return 1.0
    
    val = float(match.group(1))
    unit = match.group(2).lower()
    
    multipliers = {
        'v': 1.0, 'mv': 1e-3, 'uv': 1e-6,
        's': 1.0, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9
    }
    return val * multipliers.get(unit, 1.0)

def parse_header(header_data):
    try:
        msg_len = int.from_bytes(header_data[:4], byteorder='little')
        json_str = header_data[4:4+msg_len].decode('ascii', errors='replace')
        return json.loads(json_str)
    except Exception:
        return None

def main():
    print("--- 📺 DS1102 Live Monitor (mit Volt-Umrechnung) ---")
    
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    try:
        dev.set_configuration()
        
        plt.ion()
        fig, ax = plt.subplots(figsize=(10, 5))
        line, = ax.plot([], [], color='yellow', linewidth=1)
        ax.set_facecolor('black')
        ax.grid(color='darkgreen', linestyle='-', alpha=0.3)
        
        while True:
            # 1. Metadaten holen
            send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
            header_raw = read_resp(dev)
            header = parse_header(header_raw) if header_raw else None
            
            # 2. Wellenform holen
            send_cmd(dev, ":DATA:WAVE:SCREEN:CH1?")
            wave_raw = b""
            for _ in range(5):
                chunk = read_resp(dev, size=16384, timeout=200)
                if chunk: wave_raw += chunk
                if len(wave_raw) > 3000: break
            
            if len(wave_raw) > 4:
                # Rohwerte (0-255)
                raw_samples = np.frombuffer(wave_raw[4:], dtype=np.uint8).astype(float)
                
                # Umrechnung in Volt basierend auf Header
                if header and "CH1" in header:
                    v_scale = parse_value(header["CH1"].get("SCALE", "1V"))
                    v_offset = header["CH1"].get("OFFSET", 0) # Meist in Pixeln/Rohwerten
                    # Annahme: 25 Divisionen (oder ähnl.), 128 ist die Mitte
                    # Die Formel variiert je nach Owon-Modell, wir starten mit einer Standard-Approximation:
                    # (Raw - Zero) * (Volt/Div / Pixel_pro_Div)
                    volt_samples = (raw_samples - 128) * (v_scale / 25.0) 
                    
                    line.set_data(np.arange(len(volt_samples)), volt_samples)
                    ax.set_ylim(-v_scale*5, v_scale*5)
                    ax.set_ylabel("Spannung (V)")
                    
                    tb = header.get("TIMEBASE", {}).get("SCALE", "?")
                    ax.set_title(f"DS1102 Live - Zeitbasis: {tb} | CH1: {header['CH1']['SCALE']}/Div")
                else:
                    line.set_data(np.arange(len(raw_samples)), raw_samples)
                    ax.set_ylim(0, 255)
                    ax.set_ylabel("Rohwert (0-255)")

                ax.set_xlim(0, len(raw_samples))
                fig.canvas.draw()
                fig.canvas.flush_events()
                
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n🛑 Monitor beendet.")
    except Exception as e:
        print(f"💥 Fehler: {e}")
    finally:
        plt.ioff()
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
