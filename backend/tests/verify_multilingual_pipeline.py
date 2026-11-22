import asyncio
import json
import websockets
import requests


async def test_multilingual(lang, query):
    res = requests.post("http://127.0.0.1:8000/api/v1/sessions", json={
        "language": lang,
        "voiceName": "Kore",
        "systemInstruction": "You are Sahayak AI. Respond in the user language in 1 short sentence.",
        "temperature": 0.7,
        "maxOutputTokens": 200,
    })
    data = res.json()
    sid = data["sessionId"]
    tok = data["token"]
    uri = f"ws://127.0.0.1:8000/ws/live/{sid}?token={tok}"
    async with websockets.connect(uri) as ws:
        raw = await ws.recv()
        greeting = json.loads(raw)
        g_text = greeting["payload"]["text"]
        print(f"[{lang}] Greeting: {g_text}")

        await ws.send(json.dumps({"type": "text", "payload": {"text": query}}))

        while True:
            resp = json.loads(await ws.recv())
            if resp["type"] == "text":
                r_text = resp["payload"]["text"]
                print(f"[{lang}] Response: {r_text}")
                break
            elif resp["type"] == "function_call":
                fc_id = resp["payload"]["id"]
                fc_name = resp["payload"]["name"]
                await ws.send(json.dumps({
                    "type": "function_response",
                    "payload": {
                        "functionCallId": fc_id,
                        "name": fc_name,
                        "result": {"info": "Information verified"},
                    },
                }))


async def main():
    await test_multilingual("en-IN", "Who are you? Tell me in one sentence.")
    await test_multilingual("hi-IN", "आप कौन हैं? एक वाक्य में बताएं।")


if __name__ == "__main__":
    asyncio.run(main())

