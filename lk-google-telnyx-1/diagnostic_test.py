"""Comprehensive diagnostic test for Backboard memory persistence"""
import asyncio
import httpx
from datetime import datetime

BACKBOARD_URL = "http://localhost:3000"

async def diagnostic_test():
    print("=" * 70)
    print("🔍 BACKBOARD MEMORY PERSISTENCE DIAGNOSTIC TEST")
    print("=" * 70)
    
    async with httpx.AsyncClient() as client:
        # Step 1: Check server status
        print("\n📡 Step 1: Checking server status...")
        try:
            resp = await client.get(f"{BACKBOARD_URL}/status", timeout=5.0)
            status = resp.json()
            print(f"   ✅ Server is running")
            print(f"   Assistant ID: {status.get('assistantId')}")
            print(f"   Thread ID: {status.get('threadId')}")
            print(f"   Ready: {status.get('ready')}")
        except Exception as e:
            print(f"   ❌ Server not reachable: {e}")
            print("\n⚠️  Make sure to run: node src/index.js")
            return
        
        # Step 2: Clear old memory by recalling (to see baseline)
        print("\n🧠 Step 2: Checking current memory state...")
        try:
            resp = await client.post(
                f"{BACKBOARD_URL}/recall-memory",
                json={},
                timeout=10.0
            )
            data = resp.json()
            memory = data.get("memory")
            if memory:
                print(f"   📝 Current memory:\n{memory}")
            else:
                print("   📭 No memories found (fresh start)")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Step 3: Store a test conversation (simulating voice agent)
        print("\n💾 Step 3: Storing test conversation...")
        test_transcript = [
            {"role": "assistant", "content": "Hey! How can I help you today?"},
            {"role": "user", "content": "my name is Satheesh and I am working on a hackathon project"},
            {"role": "assistant", "content": "Nice to meet you, Satheesh! A hackathon sounds exciting! What are you building?"},
            {"role": "user", "content": "I'm building a voice assistant with persistent memory"},
            {"role": "assistant", "content": "That's awesome! Good luck with your project!"},
        ]
        
        try:
            resp = await client.post(
                f"{BACKBOARD_URL}/store-transcript",
                json={
                    "transcript": test_transcript,
                    "call_start": datetime.now().isoformat(),
                    "call_end": datetime.now().isoformat(),
                    "duration_seconds": 60,
                    "room_name": "diagnostic_test",
                },
                timeout=15.0
            )
            result = resp.json()
            print(f"   ✅ Transcript stored successfully")
            print(f"   Thread ID: {result.get('thread_id')}")
            print(f"   Messages: {len(test_transcript)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Step 4: Wait for Backboard to process
        print("\n⏳ Step 4: Waiting for Backboard to process (5 seconds)...")
        await asyncio.sleep(5)
        
        # Step 5: Recall memory
        print("\n🔍 Step 5: Recalling memory...")
        try:
            resp = await client.post(
                f"{BACKBOARD_URL}/recall-memory",
                json={},
                timeout=10.0
            )
            data = resp.json()
            memory = data.get("memory")
            if memory:
                print(f"   ✅ Memory recalled successfully!")
                print(f"\n   📝 Memory content:")
                print(f"   {'-' * 66}")
                print(f"   {memory}")
                print(f"   {'-' * 66}")
                
                # Verify key information
                has_name = "satheesh" in memory.lower()
                has_project = "hackathon" in memory.lower() or "voice assistant" in memory.lower()
                
                print(f"\n   📊 Memory verification:")
