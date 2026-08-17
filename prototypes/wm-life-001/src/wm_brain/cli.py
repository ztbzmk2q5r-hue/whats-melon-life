import argparse, json
from datetime import datetime
from .storage import BrainStore
from .reasoner import HeuristicReasoner
from .brain import WMLifeBrain

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", default="state")
    args = p.parse_args()
    out = WMLifeBrain(BrainStore(args.state), HeuristicReasoner()).heartbeat(datetime.now().astimezone())
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
