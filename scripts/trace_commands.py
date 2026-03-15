import pyshark
import binascii

def trace_commands(file_path):
    print(f"\n--- Commands in {file_path} ---")
    cap = pyshark.FileCapture(file_path)
    
    for packet in cap:
        try:
            # Check ALL layers for data fields
            for layer in packet.layers:
                field_names = layer.field_names
                for field in field_names:
                    val = layer.get_field(field)
                    if not val or not isinstance(val, str): continue
                    
                    try:
                        # If it's a hex string (e.g. 53:50:42)
                        if ':' in val and all(c in '0123456789abcdefABCDEF:' for c in val):
                           data = binascii.unhexlify(val.replace(':', ''))
                           # Check for SPB or commands
                           if b'SPB' in data:
                               print(f"[# {packet.number}] Found SPB in {layer.layer_name}.{field}")
                               print(f"    - Hex: {data.hex(' ')}")
                           
                           decoded = data.decode('ascii', errors='ignore').strip()
                           if len(decoded) > 2 and (':' in decoded or '?' in decoded or decoded.isupper()):
                               print(f"[# {packet.number}] CMD Pattern: {decoded}")
                        
                        # If it's already a string
                        elif any(c in val for c in [':', '?', 'START']):
                            print(f"[# {packet.number}] CMD String: {val}")
                    except:
                        pass
        except: pass
    cap.close()

if __name__ == "__main__":
    trace_commands(r'c:\Users\Tom\Oszi\analysis\dswave_complete_init.pcapng')
