import asyncio
from ds1102_mcp import get_status, get_scope_info
import json

async def main():
    print("Triggere Handshake via get_scope_info...")
    info = await get_scope_info()
    print(f"Scope Info: {info}")
    
    print("\nLese Status via get_status...")
    status = await get_status()
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
