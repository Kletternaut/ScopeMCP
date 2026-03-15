import time
import json
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package

# Oszilloskop Konfiguration
VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def get_device():
    """Hilfsfunktion zum Finden des USB-Geräts."""
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    if dev:
        try:
            dev.set_configuration()
        except Exception as e:
            print(f"Fehler: Konnte Gerät nicht konfigurieren: {e}")
            return None
    return dev

def send_cmd(dev, cmd):
    """Sende Befehl mit \\n Terminator."""
    if not cmd.endswith("\n"):
        cmd += "\n"
    dev.write(EP_OUT, cmd.encode('ascii'))
    time.sleep(0.1)

def read_resp(dev, size=8192, timeout=2000):
    """Liest Antwort vom Gerät."""
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        return data.tobytes()
    except Exception as e:
        print(f"Fehler beim Lesen: {e}")
        return None

def main():
    dev = get_device()
    if not dev:
        print(json.dumps({"error": "Oszilloskop nicht gefunden."}))
        return

    # 1. Autoset
    send_cmd(dev, ":AUToset on")
    print("Autoset gesendet...")
    
    # 2. 5 Sekunden warten
    time.sleep(5)
    
    # 3. Status abrufen
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = read_resp(dev)
    status = {"error": "Kein Status empfangen"}
    if header_raw and b'{' in header_raw:
        json_str = header_raw[header_raw.find(b'{'):].decode('ascii', errors='ignore')
        try:
            status = json.loads(json_str)
        except Exception as e:
            status = {"error": f"JSON Fehler: {e}", "raw": json_str}
    
    # 4. Wellenform erfassen (Channel 1)
    send_cmd(dev, ":DATA:WAVE:SCREEN:CH1?")
    # Wir erwarten hier potentiell viele Daten. 
    # Nach dem Befehl liest man normalerweise erst den Header oder direkt das Paket.
    # Da ich nicht genau weiß, wie die Struktur im detail aussieht, 
    # lese ich einen Block.
    wave_data = read_resp(dev, size=16384)
    
    result = {
        "status": status,
        "wave_info": {
            "received_bytes": len(wave_data) if wave_data else 0,
            "sample_points": wave_data[:20].hex() if wave_data else None # Ersten 20 Bytes als Hex zur Info
        }
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
