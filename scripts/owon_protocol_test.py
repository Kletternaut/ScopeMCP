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

def build_owon_packet(payload):
    """
    Owon nutzt oft ein Format: 
    4 Bytes Header + Payload
    Header: [Payload-Länge (Little Endian, 4 Bytes)]
    Manche Modelle erwarten auch 'BM' am Anfang.
    """
    if isinstance(payload, str):
        payload = payload.encode('ascii')
    
    length = len(payload)
    # 4 Bytes Länge (Little Endian)
    header = length.to_bytes(4, byteorder='little')
    return header + payload

def main():
    print("--- 🛠️ DS1102 Owon Binary Protocol Test ---")
    
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    print("✅ Gerät gefunden!")
    
    try:
        dev.set_configuration()
        
        # Bekannte Owon-Stil Befehle (oft ohne Doppelpunkt oder mit anderen Headern)
        # Wir testen verschiedene Varianten für 'AUTOSet'
        test_cmds = [
            "AUTOSET",      # Reines ASCII
            ":AUTOSET",     # SCPI-Stil
            "AUTO",         # Kurzform
            "HORI:SCAL 500us", # Beispiel für Zeitablenkung
            "RUN",
            "STOP"
        ]

        for cmd_name in test_cmds:
            # 1. Versuche es als reines ASCII (wie *IDN?)
            print(f"\n🚀 Teste: {cmd_name}")
            
            # Manche Geräte brauchen ein Null-Byte am Ende oder \n
            for suffix in ["\n", "\0", ""]:
                payload = cmd_name + suffix
                packet = build_owon_packet(payload)
                
                print(f"  Sende Paket (Hex): {packet.hex()}")
                dev.write(ENDPOINT_OUT, packet)
                
                time.sleep(0.5)
                
                # Versuche zu lesen (falls das Gerät eine Bestätigung sendet)
                try:
                    res = dev.read(ENDPOINT_IN, 64, timeout=200)
                    print(f"  📥 Antwort: {res.tobytes().hex()} | {''.join([chr(b) if 32 <= b <= 126 else '.' for b in res])}")
                except usb.core.USBError:
                    pass
            
            print("  Warte auf Reaktion am Gerät (Relais-Klicken)...")
            time.sleep(1)

    except Exception as e:
        print(f"❌ Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)
        print("\n--- Test beendet. Bitte Feedback zum Klicken geben. ---")

if __name__ == "__main__":
    main()
