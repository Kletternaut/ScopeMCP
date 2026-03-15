import usb.core
import usb.util
import time
import sys

# Konfiguration
VID = 0x5345
PID = 0x1234
# Wir versuchen am Endpoint 0x81 (IN) zu lauschen, 
# da Windows passives Lauschen an OUT-Endpoints oft blockiert.
# Wenn die Software einen Befehl schickt, kommt oft eine Bestätigung (ACK) 
# am IN-Endpoint zurück.
ENDPOINT_IN = 0x81 

def main():
    print("--- 🕵️ USB PASSIVE SNIFFER (Abestop DS1102) ---")
    print("Ziel: Wir fangen die Antworten (ACKs) ab, wenn du in DS_WAVE klickst.")
    print("Wichtig: Dieses Skript versucht NICHT das Gerät exklusiv zu sperren.\n")

    # Gerät finden
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    
    if dev is None:
        print("❌ Gerät nicht gefunden. Prüfe das USB-Kabel.")
        return

    print(f"✅ Oszilloskop erkannt: {dev.product}")
    print("🚀 Schritt 1: Starte jetzt DS_WAVE.")
    print("🚀 Schritt 2: Klicke auf 'Automatisch einstellen' (Autoset).")
    print("--- Lausche auf Daten am Endpoint 0x81 (Drücke Strg+C zum Beenden) ---\n")

    try:
        # Wir versuchen zu lesen, ohne set_configuration() aufzurufen,
        # um die bestehende Verbindung von DS_WAVE nicht zu kappen.
        while True:
            try:
                # Wir lesen kleine Pakete (64 Bytes)
                # Timeout ist kurz (100ms), um die CPU nicht zu blockieren
                data = dev.read(ENDPOINT_IN, 64, timeout=100)
                if data:
                    hex_data = data.tobytes().hex()
                    ascii_data = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in data])
                    print(f"📥 [{time.strftime('%H:%M:%S')}] Daten: {hex_data} | ASCII: {ascii_data}")
            except usb.core.USBError as e:
                # [Errno 10060] oder 'timeout' ist normal, wenn nichts gesendet wird
                if e.errno == 10060 or "timeout" in str(e).lower():
                    pass
                elif "access denied" in str(e).lower() or "busy" in str(e).lower():
                    # Falls der Zugriff komplett verweigert wird
                    pass
                else:
                    print(f"⚠️ USB Fehler: {e}")
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n🛑 Sniffer beendet.")
    except Exception as e:
        print(f"💥 Fehler: {e}")

if __name__ == "__main__":
    main()
