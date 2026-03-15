import usb.core
import usb.util
import time

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def debug_read():
    print("--- USB Read Debugger ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Oszi nicht gefunden.")
        return

    dev.set_configuration()

    # 1. Puffer leeren
    print("Leere Puffer...")
    try:
        while True:
            raw = dev.read(EP_IN, 1024, timeout=100)
            print(f"Altdaten gefunden: {len(raw)} bytes")
    except:
        print("Puffer leer.")

    # 2. Test HEAD?
    cmd = ":DATA:WAVE:SCREEN:HEAD?"
    print(f"Sende: {cmd}")
    dev.write(EP_OUT, f"{cmd}\r\n")
    
    time.sleep(1.0)
    
    try:
        raw = dev.read(EP_IN, 4096, timeout=3000)
        print(f"Empfangen ({len(raw)} bytes):")
        print("-" * 20)
        # Drucke Hex und Text
        print(raw[:200]) # Zeige ersten Teil
        if b'{' in raw:
            start = raw.find(b'{')
            print("\nJSON Form gefunden!")
            print(raw[start:].decode('ascii', errors='ignore'))
        else:
            print("\nKEIN JSON GEFUNDEN.")
    except Exception as e:
        print(f"READ ERROR: {e}")

    # 3. Test IDN?
    cmd = "*IDN?"
    print(f"\nSende: {cmd}")
    dev.write(EP_OUT, f"{cmd}\r\n")
    time.sleep(0.5)
    try:
        raw = dev.read(EP_IN, 1024, timeout=2000)
        print(f"Antwort IDN: {raw}")
    except Exception as e:
        print(f"IDN ERROR: {e}")

if __name__ == "__main__":
    debug_read()