import pyshark
import os

def analyze_pcap(file_path):
    print(f"--- 🔍 Analysiere: {file_path} ---")
    if not os.path.exists(file_path):
        print(f"❌ Datei nicht gefunden: {file_path}")
        return

    # Wir filtern nach USB-Out-Paketen zum Oszilloskop (Endpoint 0x01)
    # Da wir die genaue Bus-Adresse nicht wissen, schauen wir uns alle USB-Pakete an,
    # die Daten (Payload) enthalten.
    
    try:
        cap = pyshark.FileCapture(file_path, display_filter='usb.capdata')
        
        packet_count = 0
        for pkt in cap:
            try:
                # Extrahiere die Rohdaten
                raw_data = pkt.usb.capdata.replace(':', '')
                src = pkt.usb.src
                dst = pkt.usb.dst
                
                # Wir suchen nach Paketen vom Host zum Gerät
                # Oft ist "host" die Quelle
                print(f"📦 Paket {packet_count}: {src} -> {dst}")
                print(f"   Daten (Hex): {raw_data}")
                
                # Versuche ASCII-Decoder
                try:
                    ascii_data = bytes.fromhex(raw_data).decode('ascii', errors='replace')
                    print(f"   Daten (ASCII): {ascii_data}")
                except:
                    pass
                
                packet_count += 1
                if packet_count > 20: # Nur die ersten 20 zur Übersicht
                    print("... (weitere Pakete übersprungen)")
                    break
            except AttributeError:
                continue
        
        cap.close()
    except Exception as e:
        print(f"💥 Fehler bei der Analyse: {e}")
        print("Hinweis: tshark (Teil von Wireshark) muss im PATH liegen.")

if __name__ == "__main__":
    analyze_pcap(r"c:\Users\Tom\Oszi\dswave_complete_init.pcapng")
