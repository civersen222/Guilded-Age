"""Simple CynCo WebSocket client — sends one task and streams the response.

Assumes the engine is already running on ws://localhost:9160.
Start the engine first with:
  cd C:\\Users\\civer\\civkings
  LOCALCODE_MODEL=qwen3.6 LOCALCODE_PROVIDER=llama-cpp bun C:\\Users\\civer\\localcode\\engine\\main.ts

Then run:
  python tools/cynco_client.py "your task prompt here"
"""
import asyncio
import json
import sys
import time


async def run_task(prompt: str, port: int = 9160):
    import websockets

    print(f"Connecting to ws://localhost:{port}...")

    ws = await websockets.connect(
        f"ws://localhost:{port}",
        ping_interval=None,
        ping_timeout=None,
        close_timeout=60,
        max_size=50_000_000,
    )
    print("Connected!")

    # Drain any initial events (session.ready, etc.)
    try:
        for _ in range(5):
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            event = json.loads(raw)
            etype = event.get('type', '')
            if etype == 'session.ready':
                model = event.get('model', '?')
                ctx = event.get('contextLength', '?')
                print(f"Session ready: model={model}, context={ctx}")
                break
            else:
                print(f"[{etype}]")
    except asyncio.TimeoutError:
        print("No session.ready (may have been sent already), proceeding...")

    # Send the task
    msg = json.dumps({"type": "user.message", "text": prompt})
    await ws.send(msg)
    print(f"\nSent prompt ({len(prompt)} chars)")
    print(f"\n{'='*60}")
    print("CynCo Response:")
    print(f"{'='*60}\n")

    tool_count = 0
    start = time.time()

    try:
        async for raw_msg in ws:
            event = json.loads(raw_msg)
            etype = event.get('type', '')

            if etype == 'stream.token':
                print(event.get('text', ''), end='', flush=True)

            elif etype == 'approval.request':
                req_id = event.get('requestId', '')
                tool = event.get('toolName', '')
                print(f"\n  >> AUTO-APPROVE: {tool}")
                await ws.send(json.dumps({
                    "type": "approval.response",
                    "requestId": req_id,
                    "approved": True,
                }))

            elif etype == 'tool.start':
                tool = event.get('toolName', '')
                inp = str(event.get('input', {}))[:100]
                tool_count += 1
                print(f"\n  >> [{tool}] {inp}")

            elif etype == 'tool.complete':
                tool = event.get('toolName', '')
                err = event.get('isError', False)
                result = str(event.get('result', ''))[:150]
                status = 'ERR' if err else 'OK'
                print(f"  << [{tool} {status}] {result[:80]}")

            elif etype == 'message.complete':
                elapsed = time.time() - start
                stop = event.get('stopReason', '?')
                usage = event.get('usage', {})
                print(f"\n\n{'='*60}")
                print(f"DONE — stop: {stop} | tools: {tool_count} | time: {elapsed:.1f}s")
                print(f"tokens: {usage.get('inputTokens', 0)} in / {usage.get('outputTokens', 0)} out")
                print(f"{'='*60}")
                break

            elif etype == 'session.error':
                print(f"\n\nSESSION ERROR: {event.get('error', '?')}")
                break

            elif etype == 'context.status':
                util = event.get('utilization', 0)
                if util > 0.7:
                    print(f"\n  [context: {util*100:.0f}% used]")

    except Exception as e:
        print(f"\n\nERROR: {e}")
    finally:
        await ws.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/cynco_client.py \"your task prompt\"")
        sys.exit(1)

    prompt = sys.argv[1]
    asyncio.run(run_task(prompt))


if __name__ == '__main__':
    main()
