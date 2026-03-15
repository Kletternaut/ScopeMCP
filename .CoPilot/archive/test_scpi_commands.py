import usb.core
import usb.util
import time
import json
import libusb_package

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def get_scope():
    backend = libusb_package.get_libusb1_backend()
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    if dev:
        try:
            dev.set_configuration()
            usb.util.claim_interface(dev, 0)
        except:
            pass
    return dev

def _clear_buffer(dev):
    """Leert den USB-Eingangspuffer."""
    try:
        while True:
            dev.read(EP_IN, 1024, timeout=10)
    except:
        pass

def send_cmd(dev, cmd):
    if not cmd.endswith("\n"):
        cmd += "\n"
    _clear_buffer(dev)
    print(f"Sende: {cmd.strip()}")
    dev.write(EP_OUT, cmd.encode('ascii'))
    # Längere Pause nach Steuerbefehlen
    if any(kw in cmd.upper() for kw in ["SCAL", "HOR", "TRIG", "AUT", "COUP"]):
        time.sleep(2.0)
    else:
        time.sleep(0.5)

def get_header(dev):
    # KEIN _clear_buffer hier, da wir auf die Antwort warten
    cmd = ":DATA:WAVE:SCREEN:HEAD?\n"
    print(f"Sende: {cmd.strip()}")
    dev.write(EP_OUT, cmd.encode('ascii'))
    time.sleep(1.0) 
    try:
        data = dev.read(EP_IN, 8192, timeout=5000)
        if not data: 
            print("Keine Daten erhalten.")
            return None
        raw = bytes(data)
        print(f"Empfangen: {len(raw)} Bytes")
        if b'{' in raw:
            start = raw.find(b'{')
            end = raw.rfind(b'}') + 1
            json_str = raw[start:end].decode('ascii', errors='ignore')
            return json.loads(json_str)
    except Exception as e:
        print(f"Fehler: {e}")
    return None

def run_test():
    dev = get_scope()
    if not dev:
        print("Fehler: Oszilloskop nicht gefunden.")
        return

    print("--- Test der SCPI-Befehle (Stabilitäts-Fokus) ---")
    
    # 1. Trigger Level Test
    print("\n[*] Trigger-Level 1.50V setzen")
    send_cmd(dev, ":TRIGger:LEVel 1.50V")
    header = get_header(dev)
    if header:
        print(f"Header Trig: { {k:v for k,v in header.items() if 'trig' in k.lower()} }")
    
    # 2. Trigger Flanke Test
    print("\n[*] Trigger-Flanke FALLING setzen")
    send_cmd(dev, ":TRIGger:EDGE:SLOPE FALLING")
    header = get_header(dev)
    if header:
        print(f"Header Trig: { {k:v for k,v in header.items() if 'trig' in k.lower()} }")

    # 3. Kopplung Test
    print("\n[*] CH1 Kopplung AC setzen")
    send_cmd(dev, ":CH1:COUPling AC")
    header = get_header(dev)
    if header:
        print(f"Header CH1: { {k:v for k,v in header.items() if 'ch1' in k.lower()} }")

    print("\n--- Tests abgeschlossen ---")
    usb.util.dispose_resources(dev)

if __name__ == "__main__":
    run_test()
