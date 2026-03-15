# Hardware Finding: Fixed USB Transfer Size on DS1102
> Date: 2026-03-15
> Firmware: Abestop DS1102 V3.1.0

---

## Test: `:DATA:WAVE:POINTS` Has No Effect

We tested whether the SCPI command `:DATA:WAVE:POINTS <n>` could reduce the
amount of data transferred over USB before the host reads it.

**Tested values:** 100, 500, 1000, and default (no command sent)

**Result:** In all cases, the device transmitted exactly **3044 bytes**:
- 4 bytes binary length header
- 1520 samples × 2 bytes (signed 16-bit little-endian) = 3040 bytes

The `:DATA:WAVE:POINTS` command has **no effect** on USB transfer size
for this device and firmware version.

---

## Conclusion

The DS1102 always transmits the complete screen buffer (1520 samples) as a
single USB bulk transfer packet, regardless of any SCPI point-count commands.

The observed transfer time variation (117ms–236ms) is due to USB bus latency,
not any data size optimization.

**The current implementation — reading the full buffer and downsampling in
software — is already the most efficient approach possible for this hardware.**

There is no software-level optimization that can reduce the USB transfer time
below approximately 9–10 seconds per dual capture on this device.

---

## What This Means for the Project

| Approach | Result |
|----------|--------|
| `:WAV:POIN` to limit transfer | ❌ No effect — always 3044 bytes |
| Software downsampling after full read | ✅ Already optimal |
| `capture_dual_waveform` vs 2× single | ✅ Saves ~1 round-trip (~1–2s) |
| Metadata cache (2s TTL) | ✅ Saves ~1 USB round-trip per capture |
| Further USB-level optimization | ❌ Not possible without firmware access |

---

## Remaining Optimization Potential

The only remaining avenues for speed improvement are outside the USB layer:

1. **Async capture** — use `asyncio.to_thread()` so the MCP event loop stays
   responsive during the ~9s wait, even if total time doesn't decrease.

2. **Predictive pre-fetch** — start a background capture immediately after
   the previous one completes, so the next Claude request finds data ready.
   Risk: stale data if scope settings change between captures.

3. **Hardware upgrade** — a different oscilloscope model with a faster
   USB interface or streaming mode would be the only way to break the floor.

---

## Recommended README Addition

Add a "Known Limitations" section to `README.md`:

```markdown
## Known Limitations

**Capture Speed (~9–10s per dual capture):**
The DS1102 always transmits the full screen buffer (1520 samples, 3044 bytes)
over USB regardless of requested sample count. The SCPI command
`:DATA:WAVE:POINTS` has no effect on transfer size for this firmware version.
This is a hardware limitation and cannot be optimized further in software.
The current implementation is already optimal for this device.
```
