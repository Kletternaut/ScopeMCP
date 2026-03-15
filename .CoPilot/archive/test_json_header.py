import usb.core
import usb.util
import time
import json

VID = 0x5345
PID = 0x1234

def test_json_header():
    print("Suche Oszilloskop...")
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    
    if dev is None:
        print("Fehler: Oszi nicht gefunden. Bitte USB-Verbindung prüfen.")
        return

    # Konfiguration setzen
    dev.set_configuration()
    ep_out = 0x01
    ep_in = 0x81

    def send_cmd(cmd):
        print(f"Sende: {cmd.strip()}")
        dev.write(ep_out, f"{cmd}\r\n")
        time.sleep(0.3) # Erhöhtes Delay auf 300ms für Stabilität

    try:
        # Puffer proaktiv leeren vor dem ersten Kommando
        try:
            dev.read(ep_in, 1024, timeout=100)
        except: pass

        # 1. Handshake (Modell abfragen)
        send_cmd(":MODel?")
        model_resp = dev.read(ep_in, 1024, timeout=1000)
        print(f"Modell-Antwort: {bytes(model_resp).decode('ascii', errors='ignore').strip()}")

        # 2. Den entscheidenden JSON-Header abfragen (aus Wireshark Analyse)
        # Wir versuchen es in einer aggressiven Warteschleife (bis zu 20 Mal), wie DS Wave es tut.
        header_cmd = ":DATA:WAVE:SCREen:HEAD?"
        
        print(f"\nStarte Polling für {header_cmd} (bis zu 20 Versuche)...")
        found_data = False
        
        for attempt in range(1, 21):
            send_cmd(header_cmd)
            time.sleep(0.1) # Kurze Pause nach dem Senden
            
            try:
                # Wir lesen großzügig (2048 Bytes), um den Header sicher zu erfassen
                header_data = dev.read(ep_in, 2048, timeout=500)
                
                if len(header_data) > 0:
                    raw_bytes = bytes(header_data)
                    # Überprüfung auf die ersten NULL-Bytes (Keep-Alive / Dummy)
                    if len(header_data) <= 4 and raw_bytes == b'\x00\x00\x00\x00':
                        print(f"Versuch {attempt}: Nur 4 Null-Bytes (Keep-Alive). Probiere weiter...")
                        continue
                        
                    print(f"ERFOLG bei Versuch {attempt}: {len(header_data)} Bytes empfangen!")
                    
                    # Suche nach dem JSON-Start '{'
                    start_idx = raw_bytes.find(b'{')
                    if start_idx != -1:
                        json_str = raw_bytes[start_idx:].decode('ascii', errors='ignore').strip()
                        print("\n--- GEFUNDENER JSON HEADER ---")
                        try:
                            parsed = json.loads(json_str)
                            print(json.dumps(parsed, indent=2))
                            
                            if "FREQUENCE" in parsed:
                                print(f"\n>>> Frequenz: {parsed['FREQUENCE']} Hz")
                            
                            found_data = True
                            break
                        except json.JSONDecodeError:
                            print("JSON-Teilstring gefunden, aber Dekodierung fehlgeschlagen.")
                    else:
                        print("Daten erhalten, aber keine geschweifte Klammer gefunden.")
            except usb.core.USBError:
                # Timeout ist beim Polling normal, wir ignorieren es und probieren weiter
                print(f"Versuch {attempt}: Timeout...")
                pass
        
        if not found_data:
            print("\nKein JSON-Header gefunden. Eventuell fehlt ein ':RUN' oder das Gerät braucht einen Reset.")

    except usb.core.USBError as e:
        print(f"USB Fehler: {e}")
    finally:
        usb.util.dispose_resources(dev)

if __name__ == "__main__":
    test_json_header()
