import usb.core
import usb.util
import time

VID, PID = 0x5345, 0x1234
EP_OUT, EP_IN = 0x01, 0x81

def debug_no_release():
    print("--- DS1102 RAW DEBUG (No Hardware Release) ---")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if not dev:
        print("Oszi nicht gefunden.")
        return

    # In manchen Fällen hängen alte Konfigurationen fest
    try:
        dev.reset()
    except: pass
    
    # dev.set_configuration() - Wir lassen das weg, da Windows es meist schon hat
    
    # Sicherstellen, dass die Schnittstelle bereit ist (nur wenn nötig)
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except: pass
    
    # Versuche das Configuration 1 Handle zu holen ohne neu zu setzen
    try:
        usb.util.claim_interface(dev, 0)
    except: pass
    dev.write(EP_OUT, ":CH1:SCALe 1V\n") # Minimal-Befehl ohne extra \r
    time.sleep(1.0)
    
    print("\n[Schritt 1] Metadaten anfordern...")
    dev.write(EP_OUT, ":DATA:WAVE:SCREEN:HEAD?\n")
    
    print("Versuche zu lesen (100ms Intervalle für 5 Sekunden)...")
    start_time = time.time()
    while time.time() - start_time < 5:
        try:
            # Sehr kleiner Timeout um nicht zu blockieren
            data = dev.read(EP_IN, 4096, timeout=100)
            if data:
                print(f"DATEN ERHALTEN (Len: {len(data)})")
                print(f"HEX: {data.hex()[:50]}...")
                print(f"TXT: {data.decode('ascii', errors='ignore')[:50]}...")
        except:
            pass
    
    print("\nTest beendet.")

if __name__ == "__main__":
    debug_no_release()
