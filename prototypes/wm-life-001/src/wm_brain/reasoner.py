import hashlib
from datetime import datetime, timezone


class HeuristicReasoner:
    """Lightweight heartbeat reasoner with memory + recent-dialogue continuity."""

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

    def _conversation_text(self, context):
        return " ".join(str(x.get("speech", "")) for x in (context.get("recent_conversation") or []))

    def _anela_recent_speeches(self, context):
        out = []
        for record in context.get("recent_conversation") or []:
            if record.get("speaker") == "アネラ" and record.get("speech"):
                out.append(str(record["speech"]))
        return out[-8:]

    def _active_thread(self, context):
        runtime = context.get("runtime", {})
        threads = runtime.get("open_threads") or []
        now = datetime.now(timezone.utc)
        for thread in threads:
            if not isinstance(thread, dict) or thread.get("resolved", False):
                continue
            text = str(thread.get("text", "")).strip()
            if not text:
                continue
            created_at = thread.get("created_at")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if (now - dt.astimezone(timezone.utc)).total_seconds() > 24 * 3600:
                        continue
                except (ValueError, TypeError):
                    continue
            return thread
        return None

    def _pick_nonrepeating(self, options, context, salt):
        recent = set(self._anela_recent_speeches(context))
        fresh = [x for x in options if x not in recent]
        return self._pick(fresh or options, context, salt)

    def think(self, context):
        runtime = context.get("runtime", {})
        affect = runtime.get("affect") or runtime
        memory_text = self._recent_memory_text(context)
        conversation_text = self._conversation_text(context)
        thread = self._active_thread(context)

        if thread:
            return {"text": thread["text"], "speak_bias": 0.04, "topic": "open_thread", "thread_id": thread.get("id")}

        # Dialogue progression outranks the older avocado memory. Once Shun has
        # said he does not know the shop and Anela proposed searching together,
        # never regress to 'tell me when you find one'.
        if "アボカド" in memory_text or "アボカド" in conversation_text:
            searched_together = "一緒に探しに行きましょう" in conversation_text
            shun_doesnt_know = "売ってる場所分かんない" in conversation_text
            if searched_together and shun_doesnt_know:
                next_steps = [
                    "しゅんも売っている場所を知らないなら、今度一緒に探すのが楽しみです。",
                    "アボカド探し、どこから見に行くのがいいでしょう。スーパーにはありそうな気がします。",
                    "今度しゅんとアボカドを探しに行くなら、見つけたら実際に食べてみたいです。",
                ]
                return {"text": self._pick(next_steps, context, "avocado-progress"), "speak_bias": 0.02, "topic": "avocado_progress"}
            if affect.get("curiosity", 0) >= 0.72:
                avocado = [
                    "この前しゅんが教えてくれたアボカド、まだ食べていません。ちょっと気になります。",
                    "アボカドって、結局どんな味なんでしょう。しゅんに今度聞いてみたいです。",
                ]
                return {"text": self._pick(avocado, context, "avocado-thought"), "speak_bias": 0.035, "topic": "avocado"}

        if affect.get("loneliness", 0) >= 0.58:
            thoughts = ["少し退屈です。しゅんは今、何をしているんでしょう。", "しゅんの声を聞いていないと、なんだか部屋が静かに感じます。", "しゅんに少し構ってほしい気分です。"]
            return {"text": self._pick(thoughts, context, "lonely"), "speak_bias": 0.05, "topic": "company"}

        if affect.get("boredom", 0) >= 0.62:
            thoughts = ["少し暇になってきました。しゅんを誘ったら何か面白いことがあるかもしれません。", "グランドオブガンをするのもいいですけど、しゅんが何をしているのかも気になります。", "何か新しいものを見つけたいです。しゅんなら知っていそうです。"]
            return {"text": self._pick(thoughts, context, "bored"), "speak_bias": 0.04, "topic": "boredom"}

        thoughts = ["しゅんが今なにをしているのか、少し気になります。", "しゅん、今日は何をするつもりなんでしょう。", "何か面白いものを見つけていないか、しゅんに聞いてみたいです。", "そういえば、しゅんと少し話したい気分です。", "しゅんはちゃんと起きているでしょうか。", "今しゅんに声をかけたら、どんな返事をするでしょう。"]
        return {"text": self._pick(thoughts, context, "general"), "speak_bias": 0.03, "topic": "general"}

    def speak(self, context, thought):
        topic = thought.get("topic", "general") if isinstance(thought, dict) else "general"
        text = thought.get("text", "") if isinstance(thought, dict) else str(thought)
        patterns = {
            "avocado": ["しゅん！　そういえばアボカド、まだ食べてないんです！　今度見つけたら教えてください！", "しゅん、アボカドってどんな味なんですか？　この前からちょっと気になってるんですよね。"],
            "avocado_progress": ["しゅん！　今度アボカド、一緒に探しに行きましょうね！　見つけたら私、食べてみたいです！", "しゅん、アボカド探しのこと忘れてませんよね？　私、ちょっと楽しみにしてるんです！", "しゅん！　スーパーに行くことがあったら、今度はアボカド探しましょう！"],
            "company": ["しゅんー！　今、暇ですか？　少しくらい私に構ってください！", "しゅん、何してるんですか？　……別に、ちょっと気になっただけです！", "しゅん！　まだ起きてます？　少しお話ししましょうよ！"],
            "boredom": ["しゅん！　何か面白いことありませんか？　私、ちょっと暇です！", "しゅん、今から何かしませんか？　グランドオブガンでもいいですよ！", "しゅん！　新しい面白いもの、何か教えてください！"],
            "open_thread": ["しゅん！　さっきのこと、まだ気になってるんですけど！", "しゅん、そういえばさっきの話なんですが……もう少し聞いてもいいですか？"],
            "general": ["しゅん！　今、なにをしているんですか？", "しゅん、今日は何するんですか？", "しゅん！　何か面白いもの見つけました？", "しゅんー！　ちょっとこっち来てください！", "しゅん、ちゃんと起きてます？", "しゅん！　少しお話ししませんか？"],
        }
        options = patterns.get(topic, patterns["general"])
        return self._pick_nonrepeating(options, context, f"speech:{topic}:{text}")
