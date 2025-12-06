import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            
            # Send a test message
            message = "Create a simple hello world python file"
            await websocket.send(message)
            print(f"Sent: {message}")
            
            # Listen for responses
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    print(f"Received: {data}")
                    
                    if data.get("type") == "token" and "FINISH" in data.get("content", ""):
                        print("Received FINISH signal")
                        break
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
