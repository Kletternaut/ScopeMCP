import usb.core
import usb.util
import usb.backend.libusb1
import time
import libusb_package

# Oszilloskop Konfiguration (VID/PID für Owon/Abestop)
VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def main():
    print("--- 🔬 DS1102 Protokoll-Tester (Basierend auf Analyse) ---")
    
    # Nutze libusb_package als Backend für Windows
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden. Prüfe Kabel und WinUSB-Treiber.")
        return

    print("✅ Gerät gefunden!")
    
    try:
        dev.set_configuration()
        
        # Diese Befehle wurden in pcapng gefunden:
        # :MODel?
        # :DATA:WAVE:SCREEN:HEAD?
        # :DATA:WAVE:SCREEN:CH1?
        
        test_commands = [
            ":MODel?\r\n",
            ":DATA:WAVE:SCREEN:HEAD?\r\n",
            ":DATA:WAVE:SCREEN:CH1?\r\n"
        ]

        for cmd in test_commands:
            print(f"\n📡 Sende: {repr(cmd)}")
            dev.write(ENDPOINT_OUT, cmd.encode('ascii'), timeout=2000)
            
            time.sleep(0.3)
            
            # Versuche die Antwort zu lesen
            try:
                # Wir lesen bis zu 1024 Bytes (Metadaten sind klein, CH1 ist groß)
                res = dev.read(ENDPOINT_IN, 1024, timeout=1000)
                print(f"📥 Antwort (Hex): {res.tobytes().hex()[:100]}...")
                
                # ASCII-Darstellung zur schnellen Identifikation
                ascii_res = "".join([chr(b) if 32 <= b <= 126 else '.' for b in res])
                print(f"📥 Antwort (ASCII): {ascii_res[:100]}")
            except usb.core.USBError as e:
                print(f"⏳ Keine Antwort oder Timeout: {e}")

    except Exception as e:
        print(f"❌ Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)
        print("\n--- Test beendet ---")

if __name__ == "__main__":
    main()
