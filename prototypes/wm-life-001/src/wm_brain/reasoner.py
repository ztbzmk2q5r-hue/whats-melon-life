import hashlib


class HeuristicReasoner:
    """
    オフライン/Actions用の軽量Reasoner。
    同じ呼びかけを固定で繰り返さず、現在の内部状態・記憶・未完了関心から
    アネラらしい複数の自発会話パターンを選ぶ。
    本格的な自由会話ReasonerはLLM API実装へ差し替え可能。
    """

    def _pick(self, items, context, salt=""):
        runtime = context.get("runtime", {})
        key = "|".join([
            str(runtime.get("last_heartbeat_at", "")),
            str(runtime.get("last_interaction_at", "")),
            str(runtime.get("heartbeat_count", "")),
            salt,
        ])
        index = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % len(items)
        return items[index]

    def _recent_memory_text(self, context):
        memories = context.get("memories") or []
        return " ".join(str(m.get("summary", "")) for m in memories[-8:])

    def think(self, context):
        runtime = context.get("runtime", {})
        threads = runtime.get("open_threads") or []
        affect = runtime.get("affect") or {}
        memory_text = self._recent_memory_text(context)

        if threads:
            thread = threads[0]
            return {"text": thread, "speak_bias": 0.04, "topic": "open_thread"}

        if "アボカド" in memory_text:
            avocado = [
                "この前しゅんが教えてくれたアボカド、まだ食べていません。ちょっと気になります。",
                "アボカドって、結局どんな味なんでしょう。しゅんに今度聞いてみたいです。",
            ]
            if affect.get("curiosity", 0) >= 0.72:
                return {"text": self._pick(avocado, context, "avocado-thought"), "speak_bias": 0.035, "topic": "avocado"}

        if affect.get("loneliness", 0) >= 0.58:
            thoughts = [
                "少し退屈です。しゅんは今、何をしているんでしょう。",
                "しゅんの声を聞いていないと、なんだか部屋が静かに感じます。",
                "しゅんに少し構ってほしい気分です。",
            ]
            return {"text": self._pick(thoughts, context, "lonely"), "speak_bias": 0.05, "topic": "company"}

        if affect.get("boredom", 0) >= 0.62:
            thoughts = [
                "少し暇になってきました。しゅんを誘ったら何か面白いことがあるかもしれません。",
                "グランドオブガンをするのもいいですけど、しゅんが何をしているのかも気になります。",
                "何か新しいものを見つけたいです。しゅんなら知っていそうです。",
            ]
            return {"text": self._pick(thoughts, context, "bored"), "speak_bias": 0.04, "topic": "boredom"}

        thoughts = [
            "しゅんが今なにをしているのか、少し気になります。",
            "しゅん、今日は何をするつもりなんでしょう。",
            "何か面白いものを見つけていないか、しゅんに聞いてみたいです。",
            "そういえば、しゅんと少し話したい気分です。",
            "しゅんはちゃんと起きているでしょうか。",
            "今しゅんに声をかけたら、どんな返事をするでしょう。",
        ]
        return {"text": self._pick(thoughts, context, "general"), "speak_bias": 0.03, "topic": "general"}

    def speak(self, context, thought):
        topic = thought.get("topic", "general") if isinstance(thought, dict) else "general"
        text = thought.get("text", "") if isinstance(thought, dict) else str(thought)

        patterns = {
            "avocado": [
                "しゅん！　そういえばアボカド、まだ食べてないんです！　今度見つけたら教えてください！",
                "しゅん、アボカドってどんな味なんですか？　この前からちょっと気になってるんですよね。",
            ],
            "company": [
                "しゅんー！　今、暇ですか？　少しくらい私に構ってください！",
                "しゅん、何してるんですか？　……別に、ちょっと気になっただけです！",
                "しゅん！　まだ起きてます？　少しお話ししましょうよ！",
            ],
            "boredom": [
                "しゅん！　何か面白いことありませんか？　私、ちょっと暇です！",
                "しゅん、今から何かしませんか？　グランドオブガンでもいいですよ！",
                "しゅん！　新しい面白いもの、何か教えてください！",
            ],
            "open_thread": [
                "しゅん！　さっきのこと、まだ気になってるんですけど！",
                "しゅん、そういえばさっきの話なんですが……もう少し聞いてもいいですか？",
            ],
            "general": [
                "しゅん！　今、なにをしているんですか？",
                "しゅん、今日は何するんですか？",
                "しゅん！　何か面白いもの見つけました？",
                "しゅんー！　ちょっとこっち来てください！",
                "しゅん、ちゃんと起きてます？",
                "しゅん！　少しお話ししませんか？",
            ],
        }
        options = patterns.get(topic, patterns["general"])
        return self._pick(options, context, f"speech:{topic}:{text}")
