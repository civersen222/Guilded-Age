"""Send Task 1 to CynCo engine."""
import asyncio
import json
import time

PROMPT = (
    "You are working in the CivKings project directory. "
    "Execute these steps exactly:\n\n"
    "1. Create a file called requirements.txt with these exact 3 lines:\n"
    "pygame-ce>=2.5.0\n"
    "pygame-gui>=0.6.14\n"
    "Pillow>=10.0.0\n\n"
    "2. Run this command: pip install -r requirements.txt\n\n"
    '3. Verify imports work by running: python -c "import pygame; import pygame_gui; from PIL import Image; print(\'All imports OK\')"\n\n'
    '4. Git commit: git add requirements.txt && git commit -m "chore: add Pygame-ce, pygame-gui, Pillow dependencies"\n\n'
    "Do each step in order. Use your Write tool for step 1, Bash tool for steps 2-4."
)


async def run():
    from websockets.asyncio.client import connect

    ws = await connect("ws://localhost:9160", ping_interval=None, ping_timeout=None)
    print("Connected to CynCo!")

    # Drain initial events
    try:
        await asyncio.wait_for(ws.recv(), timeout=5)
    except Exception:
        pass

    await ws.send(json.dumps({"type": "user.message", "text": PROMPT}))
    print(f"Sent Task 1 prompt ({len(PROMPT)} chars)")
    print("=" * 60)

    tools = 0
    start = time.time()

    for _ in range(500):
        msg = await asyncio.wait_for(ws.recv(), timeout=300)
        event = json.loads(msg)
        t = event.get("type", "")

        if t == "stream.token":
            print(event.get("text", ""), end="", flush=True)
        elif t == "message.complete":
            elapsed = time.time() - start
            usage = event.get("usage", {})
            print(f"\n\n{'='*60}")
            print(f"TASK 1 COMPLETE - {event.get('stopReason')} | {tools} tools | {elapsed:.0f}s")
            print(f"Tokens: {usage.get('inputTokens',0)} in / {usage.get('outputTokens',0)} out")
            break
        elif t == "approval.request":
            tool = event.get("toolName", "")
            print(f"\n[APPROVE: {tool}]")
            await ws.send(json.dumps({
                "type": "approval.response",
                "requestId": event["requestId"],
                "approved": True,
            }))
        elif t == "tool.start":
            tool = event.get("toolName", "")
            inp = str(event.get("input", {}))[:120]
            tools += 1
            print(f"\n[{tool}] {inp}")
        elif t == "tool.complete":
            err = event.get("isError", False)
            result = str(event.get("result", ""))[:120]
            print(f"  -> {'ERR' if err else 'OK'}: {result[:80]}")
        elif t == "session.error":
            print(f"\nERROR: {event.get('error')}")
            break
        elif t == "context.status":
            util = event.get("utilization", 0)
            if util > 0.5:
                print(f"\n[ctx: {util*100:.0f}%]")

    await ws.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(run())
