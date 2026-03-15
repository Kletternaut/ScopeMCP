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
    """Baut ein klassisches Owon-Paket: 4 Bytes Länge (LE) + Payload"""
    if isinstance(payload, str):
        payload = payload.encode('ascii')
    length = len(payload)
    header = length.to_bytes(4, byteorder='little')
    return header + payload

def main():
    print("--- ⚡ DS1102 'Wake-Up' Brute-Force Test ---")
    
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
    
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    print("✅ Gerät gefunden!")
    
    try:
        dev.set_configuration()
        
        # Liste verschiedener Initialisierungs-Versuche
        # Wir testen ASCII, ASCII mit CRLF, Owon-Binary-Format und BM-Header
        test_variants = [
            # 1. Reines ASCII (aus pcapng Analyse)
            ("SCPI :MODel? (CRLF)", b":MODel?\r\n"),
            ("SCPI :STOP (CRLF)", b":STOP\r\n"),
            ("SCPI :RUN (CRLF)", b":RUN\r\n"),
            
            # 2. Owon Binary Format (4 Bytes Length + Cmd)
            ("Owon Bin: :MODel?", build_owon_packet(":MODel?")),
            ("Owon Bin: START", build_owon_packet("START")),
            
            # 3. BM Header (Owon/Lilliput spezifisch)
            ("BM Header Init", b"BM\x01\x00\x00\x00\x00\x00"),
            
            # 4. Spezieller PC-Mode Switch
            ("PC-Link Command", b"START\0"),
            ("PC-Mode SCPI", b":MODel?\0")
        ]

        for name, data in test_variants:
            print(f"\n🚀 Teste {name}...")
            print(f"   Sende (Hex): {data.hex()}")
            
            try:
                dev.write(ENDPOINT_OUT, data)
                time.sleep(0.5)
                
                # Versuche zu lesen
                try:
                    res = dev.read(ENDPOINT_IN, 1024, timeout=500)
                    print(f"   📥 ANTWORT: {res.tobytes().hex()} | {''.join([chr(b) if 32 <= b <= 126 else '.' for b in res])}")
                    print("   ✨ GEWONNEN! Gerät hat geantwortet.")
                except usb.core.USBError:
                    print("   ⏳ Keine Antwort (Timeout).")
                    
            except Exception as e:
                print(f"   ⚠️ Fehler beim Senden: {e}")
            
            # Kurze Pause zwischen den Varianten für das Gerät
            time.sleep(0.5)

    except Exception as e:
        print(f"❌ Schwerer Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)
        print("\n--- Test beendet. Achte auf Klicken am Gerät! ---")

if __name__ == "__main__":
    main()
