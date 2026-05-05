"""
CivKings - Save/Load System
Handles JSON serialization/deserialization of game state.
"""
import json
import os
import shutil
from typing import Optional, Dict, List, Any
from datetime import datetime

SAVE_DIR = "saves"


def _default_serializer(obj: Any) -> Any:
    """Handle non-serializable objects during JSON dump."""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    if hasattr(obj, 'name') and hasattr(obj, '__class__'):
        return f"<{obj.__class__.__name__}: {obj.name}>"
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, tuple):
        return list(obj)
    if hasattr(obj, 'value'):  # Enum
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def save_game(game: Any, filename: Optional[str] = None, slot: Optional[int] = None) -> str:
    """Save the current game state to a JSON file.
    
    Args:
        game: Game instance to save
        filename: Custom filename (defaults to auto-generated)
        slot: Save slot number (1-10)
    
    Returns:
        Path to the saved file
    """
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    if slot is not None:
        path = os.path.join(SAVE_DIR, f"save_slot_{slot}.json")
    elif filename:
        if not filename.endswith(".json"):
            filename = filename + ".json"
        path = os.path.join(SAVE_DIR, filename)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        turn = getattr(game, 'state', None)
        turn_num = getattr(turn, 'turn', 0) if turn else 0
        path = os.path.join(SAVE_DIR, f"save_{timestamp}_turn{turn_num}.json")
    
    data = _serialize_game(game)
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=_default_serializer)
    
    return path


def _serialize_game(game: Any) -> Dict[str, Any]:
    """Convert game state to a serializable dict."""
    data = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "turn": getattr(game.state, 'turn', 1),
        "phase": getattr(game.state, 'phase', 'Player'),
        "game_over": getattr(game.state, 'game_over', False),
        "victory": getattr(game.state, 'victory', None),
        "player_civ": game.player_civ.name if hasattr(game.player_civ, 'name') else str(game.player_civ),
        "civilizations": {name: _serialize_obj(civ) for name, civ in game.civilizations.items()},
        "cities": {name: _serialize_obj(city) for name, city in game.cities.items()},
        "units": {name: _serialize_obj(unit) for name, unit in game.units.items()},
        "gold": game.gold,
        "research": {
            name: {
                "researched": list(getattr(tm, 'researched', {}).keys()) if hasattr(tm, 'researched') else [],
                "current_research": getattr(tm, 'current_research', None),
                "research_progress": getattr(tm, 'research_progress', 0),
            }
            for name, tm in game.research.items()
        },
        "characters": [_serialize_obj(c) for c in game.characters],
        "dynasty": _serialize_obj(game.dynasty) if game.dynasty else None,
        "court": _serialize_obj(game.court) if game.court else None,
        "diplomacy": _serialize_obj(game.diplomacy_manager) if hasattr(game, 'diplomacy_manager') else None,
        "religion": _serialize_obj(game.religion_manager) if hasattr(game, 'religion_manager') else None,
        "map_data": {
            "width": getattr(game.map, 'width', 0),
            "height": getattr(game.map, 'height', 0),
            "tiles": {
                str(pos): _serialize_obj(tile)
                for pos, tile in getattr(game.map, 'tiles', {}).items()
            }
        },
        "ai_players": {
            name: getattr(ai, 'difficulty', 'medium')
            for name, ai in getattr(game, 'ai_players', {}).items()
        },
    }
    return data


def _serialize_obj(obj: Any, _seen: Optional[set] = None) -> Any:
    """Recursively serialize an object with cycle detection."""
    if obj is None:
        return None
    if _seen is None:
        _seen = set()
    obj_id = id(obj)
    if obj_id in _seen:
        return f"<cycle:{type(obj).__name__}>"
    _seen.add(obj_id)
    try:
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                result[key] = _serialize_obj(value, _seen)
            return result
        if isinstance(obj, dict):
            return {str(k): _serialize_obj(v, _seen) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_serialize_obj(item, _seen) for item in obj]
        if isinstance(obj, set):
            return [_serialize_obj(item, _seen) for item in obj]
        if hasattr(obj, 'value'):  # Enum
            return obj.value
        if isinstance(obj, (str, int, float, bool)):
            return obj
        return str(obj)
    finally:
        _seen.discard(obj_id)


def load_game(filepath: str) -> Optional[Dict[str, Any]]:
    """Load game state from a JSON file.
    
    Args:
        filepath: Path to the save file
    
    Returns:
        Dict of game data, or None if load failed
    """
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, IOError, KeyError) as e:
        print(f"Failed to load save file: {e}")
        return None


def get_save_slots() -> List[Dict[str, Any]]:
    """Get list of available save slots with metadata.
    
    Returns:
        List of dicts with 'slot', 'file', 'turn', 'timestamp', 'civilization'
    """
    if not os.path.exists(SAVE_DIR):
        return []
    
    slots = []
    for filename in sorted(os.listdir(SAVE_DIR)):
        if filename.endswith('.json'):
            filepath = os.path.join(SAVE_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                slots.append({
                    'slot': filename,
                    'file': filepath,
                    'turn': data.get('turn', '?'),
                    'timestamp': data.get('timestamp', 'Unknown'),
                    'civilization': data.get('player_civ', 'Unknown'),
                    'game_over': data.get('game_over', False),
                    'victory': data.get('victory', None),
                })
            except (json.JSONDecodeError, IOError):
                continue
    
    return slots


def delete_save(filepath: str) -> bool:
    """Delete a save file.
    
    Args:
        filepath: Path to the save file
    
    Returns:
        True if deleted, False if failed
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except OSError:
        return False


def auto_save(game: Any, slot: int = 0) -> str:
    """Create an auto-save with the current slot number.
    
    Args:
        game: Game instance
        slot: Auto-save slot number
    
    Returns:
        Path to the saved file
    """
    return save_game(game, slot=slot)
