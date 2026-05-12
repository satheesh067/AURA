"""Quick test to see what Backboard returns for recall-memory"""
import asyncio
import httpx

async def check_memory():
    async with httpx.AsyncClient() as client:
        print("Calling /recall-memory endpoint...")
        resp = await client.post(
            "http://localhost:3000/recall-memory",
            json={},
            timeout=10.0
        )
        
        print(f"Status: {resp.status_code}")
        data = resp.json()
        memory = data.get("memory")
        
        if memory:
            print(f"\n✅ Memory found:\n{memory}\n")
        else:
            print("\n❌ No memory returned\n")
        
        print(f"Full response: {data}")

asyncio.run(check_memory())
