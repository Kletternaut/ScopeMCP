import usb.core
import usb.util
import time

VID = 0x5345
PID = 0x1234

def dswave_emulation():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("Oszi nicht gefunden.")
        return

    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except: pass

    dev.set_configuration()
    ep_out = 0x01
    ep_in = 0x81

    print("--- DS Wave Emulations-Modus ---")
    
    # 1. Initialisierung wie in DS Wave
    cmds = [
        ":MODel?",
        ":TRIGger:SWEEp AUTO",
        ":RUN"
    ]
    
    for c in cmds:
        dev.write(ep_out, f"{c}\r\n")
        time.sleep(0.1)
        try:
            r = dev.read(ep_in, 1024, timeout=500)
            print(f"Antwort auf {c}: {bytes(r).decode('ascii', errors='ignore').strip()}")
        except: pass

    # 2. Die 'Endlos'-Schleife für den Daten-Dump
    # Wir schicken den Request und lesen dann AGGRESSIV den Puffer
    request = ":DATA:WAVE:SCReen:CH1?\r\n"
    print(f"\nSende Daten-Request: {request.strip()}")
    
    # JETZT: Wir fluten den Request (manche Geräte brauchen das als Trigger)
    for _ in range(5):
        dev.write(ep_out, request)
        time.sleep(0.05)

    print("Starte aggressives Lesen (Loop)...")
    start_time = time.time()
    total_received = 0
    
    # Wir erhöhen den Puffer drastisch (64KB Chunks)
    while time.time() - start_time < 20: # 20 Sekunden Test
        try:
            # Wir versuchen einen "Blank Read", um hängende Daten abzuholen
            chunk = dev.read(ep_in, 1024*64, timeout=100)
            if len(chunk) > 0:
                total_received += len(chunk)
                
                # Wenn wir nur 4 oder 0 bytes kriegen, schicken wir den Request erneut
                if len(chunk) <= 4:
                    dev.write(ep_out, request)
                    continue
                
                print(f"!!! DATENSTROM ERKANNT: {len(chunk)} Bytes empfangen (Total: {total_received})")
                
                # Wir dumpen die ersten 100 bytes hex in eine Datei zur Analyse
                with open("dump_debug.bin", "ab") as f:
                    f.write(chunk)
                
                if b"SPB" in chunk:
                    print("Marker 'SPB' GEFUNDEN!")
                if b"{" in chunk:
                    print("JSON GEFUNDEN!")
                    
                # Nach dem ersten großen Erfolg lesen wir weiter, bis der Stream versiegt
                while True:
                    try:
                        next_chunk = dev.read(ep_in, 1024*64, timeout=500)
                        total_received += len(next_chunk)
                        print(f"Stream läuft: +{len(next_chunk)} bytes (Gesamt: {total_received})")
                    except usb.core.USBError:
                        print("Stream versiegt.")
                        break
                break
        except usb.core.USBError:
            # Falls gar nichts kommt, Request erneut schicken
            dev.write(ep_out, request)
            time.sleep(0.1)
            continue

    if total_received == 0:
        print("Immer noch keine Daten. Ist ein Signal an CH1 angeschlossen?")
    
    usb.util.dispose_resources(dev)

if __name__ == "__main__":
    dswave_emulation()
