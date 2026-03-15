import pyshark
import binascii
import struct

def search_any_spb(file_path):
    print(f"\n--- Deep Searching ANY SPB in {file_path} ---")
    cap = pyshark.FileCapture(file_path)
    
    last_known_cmd = "None"
    
    for packet in cap:
        try:
            # Check every layer's all fields
            for layer in packet.layers:
                field_names = layer.field_names
                for field in field_names:
                    val = layer.get_field(field)
                    if not val or not isinstance(val, str): continue
                    
                    try:
                        # Case 1: Hex string
                        if ':' in val or (len(val) > 20 and all(c in '0123456789abcdefABCDEF' for c in val)):
                            data = binascii.unhexlify(val.replace(':', ''))
                            
                            # Search for 'SPB'
                            if b'SPB' in data:
                                idx = data.find(b'SPB')
                                print(f"[FRAME {packet.number}] FOUND 'SPB' (Hex: 53 50 42) in {layer.layer_name}.{field}")
                                print(f"    - Preceding Cmd: {last_known_cmd}")
                                print(f"    - Offset: {idx}")
                                print(f"    - Block Size: {len(data)}")
                                
                                # Check frequency at 1076
                                freq_offset = idx + 1076
                                if len(data) >= freq_offset + 4:
                                     freq_bytes = data[freq_offset:freq_offset+4]
                                     freq = struct.unpack('<f', freq_bytes)[0]
                                     print(f"    - Frequency at 1076: {freq} Hz")
                                     print(f"    - Hex at 1076: {freq_bytes.hex(' ')}")
                                
                                # Show start of SPB block
                                print(f"    - Header: {data[idx:idx+32].hex(' ')}")
                            
                            # Update commands if it's typical SCPI
                            if 2 < len(data) < 100:
                                try:
                                    s = data.decode('ascii', errors='ignore').strip()
                                    if any(c in s for c in [':', '?', 'START']):
                                        last_known_cmd = s
                                except: pass
                    except: pass
        except: pass
    cap.close()

if __name__ == "__main__":
    search_any_spb(r'c:\Users\Tom\Oszi\analysis\dswave_capture.pcapng')
    search_any_spb(r'c:\Users\Tom\Oszi\analysis\test2.pcapng')
