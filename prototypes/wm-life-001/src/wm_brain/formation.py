MIN_SUPPORT_COUNT = 3
MIN_SUPPORT_WEIGHT = 2.2
MIN_CONFIDENCE = 0.66

def accumulate_claim(container, candidate, memory_id):
    """
    1回の経験で人格を確定しない。
    記憶IDを証拠として蓄積し、十分な反復があった時だけestablishedにする。
    """
    container.setdefault("claims", [])
    key = candidate["key"]
    claim = next((x for x in container["claims"] if x["key"] == key), None)
    if claim is None:
        claim = {
            "key": key,
            "statement": candidate["statement"],
            "status": "candidate",
            "confidence": 0.25,
            "supporting_memory_ids": [],
            "contradicting_memory_ids": [],
            "support_weight": 0.0,
            "contradict_weight": 0.0
        }
        container["claims"].append(claim)

    weight = float(candidate.get("weight", 0.5))
    direction = candidate.get("direction", "support")

    if direction == "contradict":
        if memory_id not in claim["contradicting_memory_ids"]:
            claim["contradicting_memory_ids"].append(memory_id)
            claim["contradict_weight"] += weight
    else:
        if memory_id not in claim["supporting_memory_ids"]:
            claim["supporting_memory_ids"].append(memory_id)
            claim["support_weight"] += weight

    claim["confidence"] = max(
        0.05,
        min(0.98, 0.25 + 0.18*claim["support_weight"] - 0.20*claim["contradict_weight"])
    )

    if (len(claim["supporting_memory_ids"]) >= MIN_SUPPORT_COUNT
        and claim["support_weight"] >= MIN_SUPPORT_WEIGHT
        and claim["confidence"] >= MIN_CONFIDENCE):
        claim["status"] = "established"

    if (claim["status"] == "established"
        and claim["contradict_weight"] > claim["support_weight"] * 0.8):
        claim["status"] = "contested"

    return claim
