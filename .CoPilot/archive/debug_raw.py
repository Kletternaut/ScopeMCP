import usb.core
import usb.util
import time

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def debug_raw_response():
    print("--- DS1102 RAW RESPONSE DEBUG ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Oszi nicht gefunden.")
        return

    dev.set_configuration()

    def check(msg):
        print(f"\nSende: {msg}")
        # Buffer leeren
        try:
            while True: dev.read(EP_IN, 4096, timeout=10)
        except: pass

        dev.write(EP_OUT, f"{msg}\r\n")
        time.sleep(1.0)
        
        try:
            resp = dev.read(EP_IN, 8192, timeout=2000)
            print(f"RAW HEX: {resp.hex()[:100]}...")
            print(f"RAW TEXT: {resp.decode('ascii', errors='ignore')[:100]}...")
            if b'{' in resp:
                print("JSON GEFUNDEN!")
        except Exception as e:
            print(f"FEHLER beim Lesen: {e}")

    # Teste verschiedene Abfragen
    check(":DATA:WAVE:SCREEN:HEAD?")
    check("*IDN?")
    
    # Skalierung ändern und nochmal prüfen
    print("\n--- TEST: Skalierung auf 1V stellen ---")
    dev.write(EP_OUT, ":CH1:SCALe 1V\r\n")
    time.sleep(1.5)
    check(":DATA:WAVE:SCREEN:HEAD?")

if __name__ == "__main__":
    debug_raw_response()
