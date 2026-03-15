import usb.core
import usb.util
import time
import sys

# Konfiguration
VID = 0x5345
PID = 0x1234
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x81

def main():
    print("--- OWON/Abestop Sniffer-Modus (SCPI Test) ---")
    print("1. DS_WAVE Software schließen.")
    print("2. Ich sende jetzt einige bekannte Initialisierungs-Strings.")
    
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("❌ Gerät nicht gefunden.")
        return

    try:
        # Versuche, das OS-Kernel-Modul zu lösen (wichtig auf Windows/LibUSB)
        try:
            if sys.platform != "win32": # Auf Windows meist nicht nötig/verfügbar
                if dev.is_kernel_driver_active(0):
                    dev.detach_kernel_driver(0)
        except:
            pass

        dev.set_configuration()
        
        # Initialisierungssequenz basierend auf Capture test3.pcapng
        # 1. :MODel?
        # 2. :DATA:WAVE:SCREEN:HEAD?
        # 3. :DATA:WAVE:SCREEN:CH1?
        
        commands = [
            ":MODel?\r\n",
            ":DATA:WAVE:SCREEN:HEAD?\r\n",
            ":DATA:WAVE:SCREEN:CH1?\r\n"
        ]

        for cmd in commands:
            try:
                print(f"📡 Sende: {cmd.strip()}")
                # Manche Owon-Geräte brauchen exakt diese Endung oder Timeout
                dev.write(ENDPOINT_OUT, cmd.encode('ascii'), timeout=2000)
                
                time.sleep(0.3)
                
                # Versuche zu lesen (größerer Buffer für Screen-Daten)
                full_res = b""
                try:
                    while True:
                        res = dev.read(ENDPOINT_IN, 1024, timeout=800)
                        full_res += res.tobytes()
                        if len(res) < 1024:
                            break
                except usb.core.USBError:
                    if not full_res:
                        print("⏳ Keine Antwort (Timeout).")
                
                if full_res:
                    print(f"📥 Antwort Länge: {len(full_res)} Bytes")
                    # Zeige JSON-Anfang oder Hex-Anfang an
                    # (3a 03 ...) oder reine ASCII-Antworten
                    try:
                        ascii_preview = "".join([chr(b) if 32 <= b <= 126 else "." for b in full_res[:100]])
                        print(f"📥 Antwort (Vorschau): {ascii_preview}")
                        
                        if b"{" in full_res:
                            json_start = full_res.find(b'{')
                            header_content = full_res[json_start:].decode('ascii', errors='ignore')
                            print(f"📥 JSON Header (Auszug): {header_content[:150]}...")
                    except:
                        print(f"📥 Antwort (Hex): {full_res[:64].hex()}...")
                    
            except usb.core.USBError as e:
                print(f"⚠️ Fehler beim Senden: {e}")

    except Exception as e:
        print(f"💥 Schwerer Fehler: {e}")

if __name__ == "__main__":
    main()
