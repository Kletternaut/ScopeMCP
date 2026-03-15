import usb.core
import usb.util
import time
import json

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def final_test_attempt():
    print("--- DS1102 FINAL ATTEMPT ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev: return

    # Nur initialisieren (KEIN set_configuration, KEIN Reset falls möglich)
    try:
        # Puffer gründlich leeren vor dem ersten eigenen Befehl
        start_t = time.time()
        while time.time() - start_t < 1.0:
            try: dev.read(EP_IN, 4096, timeout=10)
            except: break
            
        # Sende Metadaten-Abfrage OHNE vorherige Skalierung
        print("Sende: :DATA:WAVE:SCREEN:HEAD?")
        dev.write(EP_OUT, ":DATA:WAVE:SCREEN:HEAD?\n")
        time.sleep(1.0)
        
        # Versuche zu lesen
        data = dev.read(EP_IN, 8192, timeout=2000)
        print(f"Empfangen: {bytes(data).decode('ascii', errors='ignore')[:100]}...")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    final_test_attempt()
