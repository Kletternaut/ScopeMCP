import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package

# Oszilloskop Konfiguration (Owon / Abestop DS1102)
VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def main():
    print("--- 🛠️ DS1102 Flush & Command Test ---")
    
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden. Prüfe Kabel und WinUSB-Treiber.")
        return

    print("✅ Gerät gefunden!")
    
    try:
        # Konfiguration setzen
        dev.set_configuration()
        
        print("🧹 Leere USB-Puffer (Flush)...")
        # Wir lesen so lange, bis ein Timeout kommt (Puffer leer)
        # Das Oszilloskop scheint einen konstanten Datenstrom zu senden.
        flushed_bytes = 0
        start_time = time.time()
        while time.time() - start_time < 2: # Maximal 2 Sekunden flushen
            try:
                data = dev.read(ENDPOINT_IN, 16384, timeout=100)
                flushed_bytes += len(data)
            except usb.core.USBError:
                # Timeout bedeutet Puffer ist vorerst leer
                break
        print(f"✅ {flushed_bytes} Bytes aus dem Puffer entfernt.")

        # Test-Befehle aus der pcapng Analyse
        # Wir testen MODel? und einen Befehl, der oft ein Klicken auslöst (falls verfügbar)
        test_cmds = [
            ":MODel?\r\n",
            ":DATA:WAVE:SCREEN:HEAD?\r\n"
        ]

        for cmd in test_cmds:
            print(f"\n📡 Sende: {repr(cmd)}")
            dev.write(ENDPOINT_OUT, cmd.encode('ascii'))
            
            # Kurze Pause für die Verarbeitung am Gerät
            time.sleep(0.2)
            
            # Versuche die Antwort zu lesen
            try:
                res = dev.read(ENDPOINT_IN, 1024, timeout=1000)
                print(f"📥 Antwort (Hex): {res.tobytes().hex()[:100]}...")
                ascii_res = "".join([chr(b) if 32 <= b <= 126 else '.' for b in res])
                print(f"📥 Antwort (ASCII): {ascii_res[:100]}")
            except usb.core.USBError as e:
                print(f"⏳ Keine Antwort auf {cmd.strip()}: {e}")

    except Exception as e:
        print(f"❌ Fehler: {e}")
    finally:
        # Ressourcen freigeben
        usb.util.dispose_resources(dev)
        print("\n--- Test beendet ---")

if __name__ == "__main__":
    main()
