from pathlib import Path
import tempfile, shutil, sys
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT/"src"))

from wm_brain.storage import BrainStore
from wm_brain.brain import WMLifeBrain
from wm_brain.reasoner import HeuristicReasoner
from wm_brain.formation import accumulate_claim

def check(x, msg):
    if not x:
        raise AssertionError(msg)

# Test heartbeat continuity
with tempfile.TemporaryDirectory() as td:
    dst = Path(td)/"state"
    shutil.copytree(ROOT/"state", dst)
    store = BrainStore(dst)
    before_count = store.load_runtime().heartbeat_count
    brain = WMLifeBrain(store, HeuristicReasoner())
    now = datetime(2026,8,15,22,30,tzinfo=timezone(timedelta(hours=9)))
    out = brain.heartbeat(now)
    rt = store.load_runtime()
    check(rt.heartbeat_count == before_count + 1, "heartbeat count")
    check(rt.last_heartbeat_at == now.isoformat(), "timestamp persisted")
    check(bool(out["thought"]), "thought exists")


# Actual speech must be persisted without crashing
class AlwaysSpeakReasoner(HeuristicReasoner):
    def think(self, context):
        return {"text": "発話保存テスト", "speak_bias": 1.0}

with tempfile.TemporaryDirectory() as td:
    dst = Path(td)/"state"
    shutil.copytree(ROOT/"state", dst)
    store = BrainStore(dst)
    brain = WMLifeBrain(store, AlwaysSpeakReasoner())
    now = datetime(2026,8,16,12,0,tzinfo=timezone(timedelta(hours=9)))
    out = brain.heartbeat(now)
    check(out["should_speak"], "forced speech did not trigger")
    log = (dst/"conversation_log.jsonl").read_text(encoding="utf-8").strip()
    check(bool(log), "speech was not persisted")

# One experience must not establish personality
c = {"claims":[]}
claim = accumulate_claim(c, {
    "key":"likes_horror_with_shun",
    "statement":"しゅんと一緒ならホラーも好き",
    "direction":"support","weight":0.8
}, "m1")
check(claim["status"] == "candidate", "one-shot personality drift detected")

# Repetition can establish it
for i in (2,3):
    claim = accumulate_claim(c, {
        "key":"likes_horror_with_shun",
        "statement":"しゅんと一緒ならホラーも好き",
        "direction":"support","weight":0.8
    }, f"m{i}")
check(claim["status"] == "established", "repeated evidence did not establish")

# Contradiction must be preserved rather than deleted
for i in range(3):
    claim = accumulate_claim(c, {
        "key":"likes_horror_with_shun",
        "statement":"しゅんと一緒ならホラーも好き",
        "direction":"contradict","weight":0.8
    }, f"c{i}")
check(len(claim["contradicting_memory_ids"]) == 3, "contradiction lost")

print("WM-LIFE-001 v0.02 tests: PASS")
