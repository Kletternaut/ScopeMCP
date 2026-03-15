
import usb.core
import usb.util
import usb.backend.libusb1
import libusb_package
import time
import json
import struct

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def get_scope_device():
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    if dev:
        try:
            dev.set_configuration()
        except:
            pass
    return dev

def send_cmd(dev, cmd):
    if not cmd.startswith(":"):
        cmd = ":" + cmd
    cmd_bytes = cmd.encode('ascii')
    length_header = len(cmd_bytes).to_bytes(4, byteorder='little')
    packet = length_header + cmd_bytes
    dev.write(EP_OUT, packet)
    time.sleep(0.5)

def read_resp(dev, size=65536, timeout=5000):
    try:
        data = dev.read(EP_IN, size, timeout=timeout)
        return bytes(data)
    except Exception as e:
        print(f"Read error: {e}")
        return None

def main():
    dev = get_scope_device()
    if not dev:
        print("Fehler: Oszilloskop nicht gefunden.")
        return

    # 1. JSON Header abfragen
    print("--- Abfrage JSON Header ---")
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = read_resp(dev)
    if not header_raw:
        print("Keine Antwort auf HEAD-Abfrage.")
        return

    try:
        start = header_raw.find(b'{')
        end = header_raw.rfind(b'}') + 1
        header_text = header_raw[start:end].decode('ascii', errors='ignore')
        header_json = json.loads(header_text)
        
        # Extrahiere Scale und Probe
        ch1_meta = header_json.get("CH1", {})
        ch2_meta = header_json.get("CH2", {})
        
        scale1 = ch1_meta.get("Scale", "N/A")
        probe1 = ch1_meta.get("Probe", "N/A")
        scale2 = ch2_meta.get("Scale", "N/A")
        probe2 = ch2_meta.get("Probe", "N/A")
        
        print(f"CH1: Scale={scale1}, Probe={probe1}")
        print(f"CH2: Scale={scale2}, Probe={probe2}")
        
    except Exception as e:
        print(f"Fehler beim Parsen des Headers: {e}")
        header_json = {}

    # 2. Rohdaten CH1
    print("\n--- Abfrage CH1 Rohdaten ---")
    send_cmd(dev, ":DATA:WAVE:SCREEN:CH1?")
    ch1_raw = read_resp(dev)
    
    # 3. Rohdaten CH2
    print("\n--- Abfrage CH2 Rohdaten ---")
    send_cmd(dev, ":DATA:WAVE:SCREEN:CH2?")
    ch2_raw = read_resp(dev)

    def process_channel(data, name):
        if not data:
            print(f"{name}: Keine Daten empfangen.")
            return
        
        # OWON/DS1102 Format: 4 Bytes Header (Länge), dann Rohdaten
        # In ds1102_mcp.py sahen wir, dass Rohdaten oft direkt folgen.
        # Wir überspringen die ersten 4 Bytes (Längen-Header der Antwort)
        actual_payload = data[4:]
        
        # 16-bit signed little-endian samples
        samples = []
        num_samples = len(actual_payload) // 2
        for i in range(min(200, num_samples)):
            val = struct.unpack('<h', actual_payload[i*2:i*2+2])[0]
            samples.append(val)
        
        print(f"{name} (Erste 200 Samples): {samples}")
        
        # Berechnung LSB für 1.96V PK-PK
        return samples

    s1 = process_channel(ch1_raw, "CH1")
    s2 = process_channel(ch2_raw, "CH2")

    # Analyse: Welcher Rohwert entspricht 1.96V?
    # Annahme: Spannung = (Rohwert / Faktor) * Scale * Probe ?
    # Wenn 1.96V PK-PK gemeldet wird, und wir Scale=1V haben...
    if header_json:
        # Extraktion der V-Werte aus Strings wie "1V" oder "200mV"
        def parse_scale(s):
            if not s or not isinstance(s, str): return 1.0
            if "mV" in s: return float(s.replace("mV", "")) / 1000.0
            if "V" in s: return float(s.replace("V", ""))
            return 1.0

        def parse_probe(p):
            if not p or not isinstance(p, str): return 1.0
            return float(p.replace("X", ""))

        v_scale1 = parse_scale(scale1)
        v_probe1 = parse_probe(probe1)
        
        # Wenn Faktor 250 (wie oft bei Owon/DS1102 für Screen-Daten)
        # PK-PK in LSB = (1.96V / (v_scale1 * v_probe1)) * 250 ?
        # Oder ist der Faktor 25 pro Division? (10 Divisionen vertikal?)
        # 250 LSB = 10 Divisionen?
        
        target_v = 1.96
        lsb_needed = (target_v / (v_scale1 * v_probe1)) * 25 # Pro Division (Annahme 1 Div = 25 LSB)
        lsb_needed_total = (target_v / (v_scale1 * v_probe1)) * 25 # Dies wäre pro Division skaliert.
        
        # Wenn das Display 10 Divisionen hat:
        # 250 LSB = Full Scale (10 Div)
        # 1 Div = 25 LSB
        # Spannung = (LSB / 25) * Scale * Probe
        
        print(f"\nBerechnung für 1.96V PK-PK bei Scale={v_scale1}V, Probe={v_probe1}X:")
        print(f"Erwarteter LSB PK-PK (bei Faktor 25 LSB/Div): {(target_v / (v_scale1 * v_probe1)) * 25:.2f}")
        print(f"Erwarteter LSB PK-PK (bei Faktor 250 LSB/Total?): {(target_v / (v_scale1 * v_probe1)) * 250:.2f}")

if __name__ == "__main__":
    main()
