from datetime import datetime
import math
from .models import clamp

def hours_since(iso, now, default=18.0):
    if not iso:
        return default
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=now.tzinfo)
    return max(0.0, (now-dt).total_seconds()/3600.0)

def advance_affect(rt, now):
    dt = hours_since(rt.last_heartbeat_at, now, default=3.0)
    step = min(8.0, max(0.25, dt))/3.0
    rt.boredom = clamp(rt.boredom + 0.030*step)
    rt.loneliness = clamp(rt.loneliness + 0.020*step)
    rt.curiosity = clamp(rt.curiosity + 0.012*step)
    rt.hunger = clamp(rt.hunger + 0.018*step)
    rt.energy = clamp(rt.energy + (0.65-rt.energy)*0.08*step)
    return rt

def initiative(rt, now, thought_bias=0.0):
    since_spoke = hours_since(rt.last_spoke_at, now, default=18.0)
    time_pressure = clamp(since_spoke/24.0)
    score = (
        0.22*rt.curiosity +
        0.18*rt.playfulness +
        0.20*rt.affection +
        0.14*rt.boredom +
        0.11*rt.loneliness +
        0.08*rt.energy +
        0.07*time_pressure +
        thought_bias
    )
    threshold = max(0.57, 0.76-min(since_spoke,36.0)*0.0045)
    return clamp(score), threshold

class WMLifeBrain:
    """
    state -> time -> memory/context -> thought -> initiative -> action -> persistence

    LLMはreasonerとして差し替える。
    Pythonは人格そのものではなく、脳の構造と履歴管理を担当する。
    """
    def __init__(self, store, reasoner):
        self.store = store
        self.reasoner = reasoner

    def heartbeat(self, now):
        rt = self.store.load_runtime()
        rt = advance_affect(rt, now)
        rt.heartbeat_count += 1
        rt.last_heartbeat_at = now.isoformat()

        context = {
            "identity_core": self.store.load_json("identity_core.json"),
            "self_model": self.store.load_json("self_model.json"),
            "beliefs": self.store.load_json("beliefs.json"),
            "preferences": self.store.load_json("preferences.json"),
            "relationship": self.store.load_json("relationship.json"),
            "runtime": rt.to_dict(),
            "memories": self.store.memories()[-20:]
        }

        thought = self.reasoner.think(context)
        rt.current_thought = thought["text"]

        score, threshold = initiative(rt, now, thought.get("speak_bias",0.0))
        rt.initiative = score
        speech = None

        if score >= threshold:
            speech = self.reasoner.speak(context, thought)
            rt.last_spoke_at = now.isoformat()
            rt.speech_count += 1
            rt.silence_streak = 0
            rt.loneliness *= 0.78
            rt.boredom *= 0.82

            # Every actual utterance becomes auditable research data.
            self.store.append_conversation({
                "id": f"speech-{rt.speech_count:06d}",
                "timestamp": now.isoformat(),
                "speaker": "アネラ",
                "target": "しゅん",
                "thought": thought["text"],
                "speech": speech,
                "initiative_score": round(score, 4),
                "threshold": round(threshold, 4),
                "review_status": "pending"
            })
        else:
            rt.silence_streak += 1

        self.store.save_runtime(rt)
        return {
            "should_speak": score >= threshold,
            "speech": speech,
            "initiative_score": round(score,4),
            "threshold": round(threshold,4),
            "thought": thought["text"]
        }
