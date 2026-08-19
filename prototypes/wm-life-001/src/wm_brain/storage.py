import json
from pathlib import Path
from .models import RuntimeState

class BrainStore:
    def __init__(self, root):
        self.root = Path(root)

    def load_json(self, name):
        return json.loads((self.root/name).read_text(encoding="utf-8"))

    def save_json(self, name, data):
        (self.root/name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )

    def load_runtime(self):
        return RuntimeState(**self.load_json("runtime.json"))

    def save_runtime(self, runtime):
        self.save_json("runtime.json", runtime.to_dict())

    def memories(self):
        path = self.root/"memories.jsonl"
        if not path.exists():
            return []
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

    def conversations(self):
        path = self.root/"conversation_log.jsonl"
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def append_memory(self, memory):
        with (self.root/"memories.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(memory, ensure_ascii=False) + "\n")

    def append_conversation(self, record):
        with (self.root/"conversation_log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
