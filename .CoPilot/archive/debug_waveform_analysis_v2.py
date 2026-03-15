
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
            usb.util.claim_interface(dev, 0)
        except:
            pass
    return dev

def send_cmd(dev, cmd):
    if not cmd.endswith("\n"):
        cmd += "\n"
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
        return None

def main():
    dev = get_scope_device()
    if not dev:
        print("Fehler: Oszilloskop nicht gefunden.")
        return

    # INITIALISIERUNG
    print("--- Initialisierung ---")
    send_cmd(dev, ":MODel?")
    model_resp = read_resp(dev)
    print(f"Modell-Antwort: {model_resp}")

    # 1. JSON Header abfragen
    print("\n--- Abfrage JSON Header ---")
    send_cmd(dev, ":DATA:WAVE:SCREEN:HEAD?")
    header_raw = read_resp(dev)
    header_json = {}
    
    if header_raw:
        # Debug: Print raw header to see format
        print(f"Raw Header (len={len(header_raw)}): {header_raw[:100]}")
        start = header_raw.find(b'{')
        end = header_raw.rfind(b'}') + 1
        if start != -1 and end != -1:
            try:
                header_text = header_raw[start:end].decode('ascii', errors='ignore')
                header_json = json.loads(header_text)
                
                ch1_meta = header_json.get("CH1", {})
                ch2_meta = header_json.get("CH2", {})
                
                scale1 = ch1_meta.get("Scale", "N/A")
                probe1 = ch1_meta.get("Probe", "N/A")
                scale2 = ch2_meta.get("Scale", "N/A")
                probe2 = ch2_meta.get("Probe", "N/A")
                
                print(f"CH1: Scale={scale1}, Probe={probe1}")
                print(f"CH2: Scale={scale2}, Probe={probe2}")
            except Exception as e:
                print(f"JSON Parse Error: {e}")
        else:
            print("JSON Start/End Marker nicht gefunden.")

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
            return None
        
        # Header überspringen (Längen-Bytes)
        actual_payload = data[4:]
        
        # 16-bit signed BIG-endian samples
        samples = []
        num_samples = len(actual_payload) // 2
        for i in range(min(200, num_samples)):
            val = struct.unpack('>h', actual_payload[i*2:i*2+2])[0]
            samples.append(val)
        
        print(f"{name} (Erste 200 Samples): {samples}")
        return samples

    s1 = process_channel(ch1_raw, "CH1")
    s2 = process_channel(ch2_raw, "CH2")

    if header_json and "CH1" in header_json:
        def parse_scale(s):
            if not s or s == "N/A": return 1.0
            s = str(s)
            if "mV" in s: return float(s.replace("mV", "")) / 1000.0
            if "V" in s: return float(s.replace("V", ""))
            return 1.0

        def parse_probe(p):
            if not p or p == "N/A": return 1.0
            p = str(p)
            try: return float(p.replace("X", ""))
            except: return 1.0

        v_scale1 = parse_scale(header_json["CH1"].get("Scale"))
        v_probe1 = parse_probe(header_json["CH1"].get("Probe"))
        
        target_v = 1.96
        print(f"\n--- Analyse für 1.96V PK-PK bei CH1 (Scale={v_scale1}V, Probe={v_probe1}X) ---")
        
        if s1:
            actual_pkpk = max(s1) - min(s1)
            print(f"Gemessener PK-PK Rohwert (CH1, first 200): {actual_pkpk}")
            
            # Rückrechnung des Faktors (LSB pro Division)
            # Spannung = (LSB / Faktor) * Scale * Probe
            # => Faktor = (LSB * Scale * Probe) / Spannung ? Nein.
            # => Faktor = LSB / (Spannung / (Scale * Probe))
            
            calculated_factor = actual_pkpk / (target_v / (v_scale1 * v_probe1))
            print(f"Berechneter Faktor (LSB/Div): {calculated_factor:.2f}")
            print(f"Vergleich: Faktor 25 LSB/Div -> Erwartet { (target_v / (v_scale1 * v_probe1)) * 25 } LSB")
            print(f"Vergleich: Faktor 100 LSB/Div -> Erwartet { (target_v / (v_scale1 * v_probe1)) * 100 } LSB")

if __name__ == "__main__":
    main()
