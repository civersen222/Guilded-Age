"""Send Task 2 to CynCo — create pygame_app package structure."""
import asyncio
import json
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROMPT = """Create the pygame_app package for the CivKings project. Execute these steps:

STEP 1: Run this bash command to create directories:
mkdir -p pygame_app/screens pygame_app/map pygame_app/panels pygame_app/popups pygame_app/effects pygame_app/audio

STEP 2: Create 7 __init__.py files. Each should contain just: # pygame_app package
Create them at:
- pygame_app/__init__.py
- pygame_app/screens/__init__.py
- pygame_app/map/__init__.py
- pygame_app/panels/__init__.py
- pygame_app/popups/__init__.py
- pygame_app/effects/__init__.py
- pygame_app/audio/__init__.py

STEP 3: Create pygame_app/constants.py with this content:
\"\"\"Shared constants for the CivKings Pygame GUI.\"\"\"

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 30
TITLE = 'CivKings: Dynasty & Dominion'

BG = (10, 11, 13)
PANEL_BG = (22, 24, 29)
PANEL_BG2 = (35, 38, 45)
ACCENT = (35, 38, 45)
HIGHLIGHT = (197, 160, 89)
TEXT = (224, 224, 224)
SUBTLE = (136, 136, 136)
BORDER = (51, 54, 61)
GOLD = (197, 160, 89)
RED = (178, 58, 58)
GREEN = (58, 178, 78)
BLUE = (58, 120, 178)

HEX_SIZE = 64
HEX_HEIGHT_RATIO = 0.866

RESOURCE_BAR_HEIGHT = 40
ACTION_BAR_HEIGHT = 50
LEFT_PANEL_WIDTH = 260
RIGHT_PANEL_WIDTH = 280
MINIMAP_SIZE = 200

MAP_X = LEFT_PANEL_WIDTH
MAP_Y = RESOURCE_BAR_HEIGHT
MAP_W = SCREEN_WIDTH - LEFT_PANEL_WIDTH - RIGHT_PANEL_WIDTH
MAP_H = SCREEN_HEIGHT - RESOURCE_BAR_HEIGHT - ACTION_BAR_HEIGHT

TERRAIN_COLORS = {
    'PLAINS': (61, 77, 61),
    'GRASSLAND': (74, 93, 74),
    'FOREST': (45, 74, 45),
    'HILLS': (90, 90, 61),
    'MOUNTAIN': (74, 74, 74),
    'DESERT': (106, 90, 58),
    'TUNDRA': (180, 190, 200),
    'WATER_COAST': (40, 80, 120),
    'OCEAN': (26, 58, 90),
}

STEP 4: Commit:
git add pygame_app/; git commit -m "feat: create pygame_app package structure with constants"

Execute all 4 steps now."""


async def run():
    from websockets.asyncio.client import connect
    ws = await connect('ws://localhost:9160', ping_interval=None, ping_timeout=None)
    print('Connected!')
    try:
        await asyncio.wait_for(ws.recv(), timeout=5)
    except Exception:
        pass

    await ws.send(json.dumps({'type': 'user.message', 'text': PROMPT}))
    print(f'Sent prompt ({len(PROMPT)} chars)\n{"="*60}\n')

    tools = 0
    start = time.time()

    for _ in range(500):
        msg = await asyncio.wait_for(ws.recv(), timeout=300)
        event = json.loads(msg)
        t = event.get('type', '')

        if t == 'stream.token':
            print(event.get('text', ''), end='', flush=True)
        elif t == 'message.complete':
            elapsed = time.time() - start
            usage = event.get('usage', {})
            print(f'\n\n{"="*60}')
            print(f'DONE - {event.get("stopReason")} | {tools} tools | {elapsed:.0f}s')
            print(f'Tokens: {usage.get("inputTokens",0)} in / {usage.get("outputTokens",0)} out')
            break
        elif t == 'approval.request':
            print(f'\n  >> APPROVE: {event.get("toolName")}')
            await ws.send(json.dumps({
                'type': 'approval.response',
                'requestId': event['requestId'],
                'approved': True,
            }))
        elif t == 'tool.start':
            tool = event.get('toolName', '')
            inp = str(event.get('input', {}))[:120]
            tools += 1
            print(f'\n  [{tool}] {inp}')
        elif t == 'tool.complete':
            err = event.get('isError', False)
            result = str(event.get('result', ''))[:120]
            print(f'  <- {"ERR" if err else "OK"}: {result[:80]}')
        elif t == 'session.error':
            print(f'\nSESSION ERROR: {event.get("error")}')
            break

    await ws.close()

asyncio.run(run())
