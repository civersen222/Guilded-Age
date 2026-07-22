"""G19 console tests: the file-bridge and the command surface."""

import json
import os
import subprocess
import sys
import time

from gilded.chassis import ATTENTION_PER_TURN
from gilded.console import Console

SEED = 42


def _console(tmp_path) -> Console:
    return Console(str(tmp_path), SEED)


# --- the command surface (direct dispatch) -----------------------------------

def test_state_opens_in_1900(tmp_path):
    c = _console(tmp_path)
    r = c.cmd_state()
    assert r["turn"] == 1 and r["year"] == 1900
    assert r["attention"] == ATTENTION_PER_TURN
    assert r["house"] in c.game.houses
    assert r["provinces"] > 0 and r["enterprises"] > 0
    assert r["game_over"] is None


def test_default_house_is_the_player(tmp_path):
    c = _console(tmp_path)
    assert c.game.houses[c.house].is_player


def test_docket_lists_petitions(tmp_path):
    c = _console(tmp_path)
    r = c.cmd_docket()
    assert "petitions" in r
    assert r["petitions"], "seed 42 opens with paper on the desk"
    p = r["petitions"][0]
    assert {"pid", "kind", "domain", "text", "options"} <= set(p)
    assert p["options"] and "key" in p["options"][0]


def test_rule_spends_attention_and_clears_the_paper(tmp_path):
    c = _console(tmp_path)
    pid = c.game.docket_by_house[c.house][0].pid
    key = c.game.docket_by_house[c.house][0].options[0].key
    before = c.game.attention[c.house]
    r = c.cmd_rule(str(pid), key)
    assert r["ok"] and r["attention"] == before - 1
    assert all(p.pid != pid for p in c.game.docket_by_house[c.house])


def test_rule_can_name_an_executor(tmp_path):
    c = _console(tmp_path)
    p = c.game.docket_by_house[c.house][0]
    who = c.realm.ruler.name
    r = c.cmd_rule(str(p.pid), p.options[0].key, "executor", who)
    assert r["executor"] == who


def test_dial_is_free_and_clamps(tmp_path):
    c = _console(tmp_path)
    before = c.game.attention[c.house]
    r = c.cmd_dial("war", "250")
    assert r["value"] == 100
    assert c.game.attention[c.house] == before      # no attention spent


def test_initiative_marries_through_a_person(tmp_path):
    c = _console(tmp_path)
    other = next(n for n in sorted(c.game.houses) if n != c.house)
    before = c.game.attention[c.house]
    r = c.cmd_initiative("propose_marriage", f"target_house={other}")
    assert r["ok"] and r["messages"]
    assert c.game.attention[c.house] == before - 1


def test_atlas_summary_and_detail(tmp_path):
    c = _console(tmp_path)
    summary = c.cmd_atlas()
    assert summary["provinces"]
    pid = c.game.provinces_of(c.house)[0].pid
    detail = c.cmd_atlas(str(pid))
    assert detail["pid"] == pid and detail["owner"] == c.house
    assert "endowments" in detail and "enterprises" in detail


def test_house_and_chars(tmp_path):
    c = _console(tmp_path)
    h = c.cmd_house()
    assert h["name"] == c.house and h["ruler"]
    assert len(h["seats"]) == 6
    ch = c.cmd_chars()
    assert ch["characters"]
    assert any(row["seat"] == "Ruler" for row in ch["characters"])


def test_end_turn_advances_and_papers_carry_the_gazette(tmp_path):
    c = _console(tmp_path)
    r = c.cmd_end_turn()
    assert r["turn"] == 2
    papers = c.cmd_papers()
    assert "GAZETTE" in papers["text"]


def test_epilogue_only_after_the_age_closes(tmp_path):
    c = _console(tmp_path)
    assert c.cmd_epilogue()["ok"] is False
    c.game.game_over = "century"
    ep = c.cmd_epilogue()
    assert ep["ok"] and ep["ending"] and len(ep["text"]) > 200


def test_save_and_load_roundtrip(tmp_path):
    c = _console(tmp_path)
    c.cmd_end_turn()
    turn = c.game.turn
    c.cmd_save("slot")
    c.cmd_end_turn()
    assert c.game.turn == turn + 1
    r = c.cmd_load("slot")
    assert r["turn"] == turn and c.game.turn == turn


def test_unknown_and_bad_commands_never_raise(tmp_path):
    c = _console(tmp_path)
    assert c.dispatch("nonsense 1 2")["ok"] is False
    assert c.dispatch("rule 9999 grant")["ok"] is False
    assert c.dispatch("")["ok"] is False


# --- the actual file bridge (subprocess) -------------------------------------

def test_bridge_end_to_end(tmp_path):
    d = str(tmp_path)
    proc = subprocess.Popen([sys.executable, "-m", "gilded",
                             "--console", d, "--seed", "42"])
    try:
        def send(cmd):
            with open(os.path.join(d, "cmd_in.txt"), "a") as f:
                f.write(cmd + "\n")

        def last_reply(prev_count, timeout=30):
            path = os.path.join(d, "replies.jsonl")
            t0 = time.time()
            while time.time() - t0 < timeout:
                if os.path.exists(path):
                    lines = open(path).read().splitlines()
                    if len(lines) > prev_count:
                        return json.loads(lines[-1])
                time.sleep(0.05)
            raise TimeoutError("no reply in " + d)

        send("state")
        r = last_reply(0)
        assert r["turn"] == 1 and r["year"] == 1900
        send("end_turn")
        r = last_reply(1)
        assert r["turn"] == 2
        send("quit")
        proc.wait(timeout=15)
    finally:
        if proc.poll() is None:
            proc.kill()
