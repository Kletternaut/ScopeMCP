import pyshark
import sys
import os

def analyze_usb_capture(file_path):
    print(f"--- 🔍 Detaillierte Analyse: {file_path} ---")
    if not os.path.exists(file_path):
        print(f"❌ Datei nicht gefunden: {file_path}")
        return

    # Filter nach USB-Verkehr. Wir suchen nach VID 0x5345 / PID 0x1234
    # Da Wireshark/USB-Pcap oft Bus-Adressen (z.B. 1.10.1) statt VID/PID in den Frames anzeigt,
    # suchen wir erst nach dem Device Descriptor oder schauen uns alle USB-Daten an.
    
    try:
        # Erhöhter Timeout für pyshark auf Windows
        cap = pyshark.FileCapture(file_path, display_filter='usb.capdata or usb.device_descriptor')
        
        found_devices = {}
        
        print("Scanne Pakete... (das kann einen Moment dauern)")
        
        packet_count = 0
        for pkt in cap:
            packet_count += 1
            
            # Versuche das Gerät anhand des Device Descriptors zu finden (falls im Capture)
            if hasattr(pkt, 'usb') and hasattr(pkt.usb, 'idvendor'):
                vid = int(pkt.usb.idvendor, 16)
                pid = int(pkt.usb.idproduct, 16)
                addr = pkt.usb.device_address
                if vid == 0x5345 and pid == 0x1234:
                    print(f"✅ Oszilloskop gefunden an Adresse: {addr}")
                    found_devices[addr] = "Oszilloskop"

            # Wenn wir Daten haben, zeigen wir sie an (vorerst alle, um das Oszilloskop zu finden)
            if hasattr(pkt, 'usb') and hasattr(pkt.usb, 'capdata'):
                data = pkt.usb.capdata.replace(':', '')
                src = pkt.usb.src
                dst = pkt.usb.dst
                
                # Wenn es nach SCPI aussieht (ASCII-Strings)
                try:
                    raw_bytes = bytes.fromhex(data)
                    ascii_str = "".join([chr(b) if 32 <= b <= 126 else "." for b in raw_bytes])
                    
                    # Filtere Mausbewegungen (meist 4-8 bytes binär ohne viel ASCII)
                    if len(raw_bytes) > 2 and any(c in ascii_str for c in "*:IDN?"):
                        print(f"DEBUG: Frame {pkt.number} | {src} -> {dst} | Data: {data} | ASCII: {ascii_str}")
                    elif len(raw_bytes) > 10: # Längere Datenpakete könnten Wellenformen sein
                         print(f"DEBUG: Frame {pkt.number} | {src} -> {dst} | Len: {len(raw_bytes)} | Data (Start): {data[:20]}...")
                except:
                    pass

            if packet_count > 1000: # Limit für den ersten Scan
                print("--- Limit von 1000 Paketen erreicht ---")
                break

    except Exception as e:
        print(f"💥 Fehler: {e}")

if __name__ == "__main__":
    path = "C:\\Users\\Tom\\Documents\\Wireshark\\test.pcapng"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    analyze_usb_capture(path)
