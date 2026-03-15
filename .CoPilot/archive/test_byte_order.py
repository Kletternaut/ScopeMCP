
import struct

# CH1 Header Auszug vom Terminal (ersten 200 Samples, die wir als >h gelesen haben)
# Wir schauen uns das erste Sample an: 28675. Wenn es Little-Endian wäre:
s1_big = [28675, -4094, 24579]
# 28675 hex is 0x7003. 
# Byte 0: 0x70, Byte 1: 0x03.
# Wenn wir es als Little-Endian <h lesen würden:
# Byte 0: 0x70, Byte 1: 0x03 -> 0x0370 = 880.

def convert_to_le(vals):
    results = []
    for v in vals:
        b = struct.pack('>h', v) # Back to bytes in Big Endian
        le = struct.unpack('<h', b)[0] # Read as Little Endian
        results.append(le)
    return results

ch1_samples_le = convert_to_le([28675, -4094, 24579, 4099, -32765, 8195])
print(f"Versuch Little Endian für CH1: {ch1_samples_le}")

# CH2: 8445 hex is 0x20FD. Little Endian 0xFD20 -> -736? 
# Hmm. 8445 als >h. Byte0=0x20 (32), Byte1=0xFD (253).
# Als <h: 0xFD20 (Signed 16-bit: -736).
ch2_samples_le = convert_to_le([8445, -16132, 12541, -12036])
print(f"Versuch Little Endian für CH2: {ch2_samples_le}")
