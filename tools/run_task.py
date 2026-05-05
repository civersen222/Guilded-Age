"""Send a task prompt to the running CynCo engine and stream the response.

Usage: python tools/run_task.py "your prompt here"
"""
import asyncio
import json
import sys
import time
import os

# Fix Windows encoding for emoji output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


async def run(prompt: str, port: int = 9160):
    from websockets.asyncio.client import connect

    ws = await connect(f"ws://localhost:{port}", ping_interval=None, ping_timeout=None)
    print("Connected to CynCo!")

    # Drain initial events
    try:
        await asyncio.wait_for(ws.recv(), timeout=5)
    except Exception:
        pass

    await ws.send(json.dumps({"type": "user.message", "text": prompt}))
    print(f"Sent prompt ({len(prompt)} chars)\n{'='*60}\n")

    tools = 0
    start = time.time()
    response_text = []

    for _ in range(1000):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=300)
        except asyncio.TimeoutError:
            print("\n\nTIMEOUT waiting for response")
            break

        event = json.loads(msg)
        t = event.get("type", "")

        if t == "stream.token":
            txt = event.get("text", "")
            print(txt, end="", flush=True)
            response_text.append(txt)
        elif t == "message.complete":
            elapsed = time.time() - start
            usage = event.get("usage", {})
            print(f"\n\n{'='*60}")
            print(f"DONE - {event.get('stopReason')} | {tools} tools | {elapsed:.0f}s")
            print(f"Tokens: {usage.get('inputTokens',0)} in / {usage.get('outputTokens',0)} out")
            break
        elif t == "approval.request":
            tool = event.get("toolName", "")
            print(f"\n  >> APPROVE: {tool}")
            await ws.send(json.dumps({
                "type": "approval.response",
                "requestId": event["requestId"],
                "approved": True,
            }))
        elif t == "tool.start":
            tool = event.get("toolName", "")
            inp = str(event.get("input", {}))[:120]
            tools += 1
            print(f"\n  [{tool}] {inp}")
        elif t == "tool.complete":
            err = event.get("isError", False)
            result = str(event.get("result", ""))[:120]
            print(f"  <- {'ERR' if err else 'OK'}: {result[:80]}")
        elif t == "session.error":
            print(f"\nSESSION ERROR: {event.get('error')}")
            break

    await ws.close()
    return "".join(response_text)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/run_task.py \"prompt\"")
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))
