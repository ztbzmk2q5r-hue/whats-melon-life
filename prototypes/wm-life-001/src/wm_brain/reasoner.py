import hashlib
from datetime import datetime, timezone

class HeuristicReasoner:
    """Heartbeat reasoner with memory, dialogue continuity and attention cooldowns."""
    TOPIC_COOLDOWN = {"avocado": 8, "avocado_progress": 8, "company": 3, "boredom": 3, "general": 2, "open_thread": 1}

    def _pick(self, items, context, salt=""):
        r=context.get("runtime",{}); key="|".join([str(r.get("last_heartbeat_at","")),str(r.get("heartbeat_count","")),salt])
        return items[int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%len(items)]

    def _mem(self,c): return " ".join(str(m.get("summary","")) for m in (c.get("memories") or [])[-8:])
    def _conv(self,c): return " ".join(str(x.get("speech","")) for x in (c.get("recent_conversation") or []))
    def _recent_speech(self,c): return [str(x["speech"]) for x in (c.get("recent_conversation") or []) if x.get("speaker")=="アネラ" and x.get("speech")][-10:]

    def _cool(self,c,topic):
        r=c.get("runtime",{}); last=(r.get("topic_last_spoken") or {}).get(topic)
        if last is None: return False
        return int(r.get("heartbeat_count",0))-int(last) < self.TOPIC_COOLDOWN.get(topic,2)

    def _active_thread(self,c):
        now=datetime.now(timezone.utc)
        for t in c.get("runtime",{}).get("open_threads") or []:
            if not isinstance(t,dict) or t.get("resolved",False) or not str(t.get("text","")).strip(): continue
            try:
                d=datetime.fromisoformat(str(t.get("created_at","")).replace("Z","+00:00"))
                if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
                if (now-d.astimezone(timezone.utc)).total_seconds()>86400:continue
            except (ValueError,TypeError): continue
            return t
        return None

    def _fresh(self,opts,c,salt):
        recent=set(self._recent_speech(c)); fresh=[x for x in opts if x not in recent]
        return self._pick(fresh or opts,c,salt)

    def think(self,c):
        r=c.get("runtime",{}); a=r.get("affect") or r; mem=self._mem(c); conv=self._conv(c); t=self._active_thread(c)
        if t and not self._cool(c,"open_thread"):
            return {"text":t["text"],"speak_bias":.04,"topic":"open_thread","thread_id":t.get("id")}

        # A remembered subject is a candidate, never a permanent priority.
        # Avocado receives a long cooldown after any avocado-family speech.
        avocado_cool=self._cool(c,"avocado") or self._cool(c,"avocado_progress")
        if not avocado_cool and ("アボカド" in mem or "アボカド" in conv) and a.get("curiosity",0)>=.72:
            progressed="一緒に探しに行きましょう" in conv and "売ってる場所分かんない" in conv
            if progressed:
                xs=["今度しゅんとアボカドを探すなら、見つけた後に食べてみるのが楽しみです。","アボカド探しは約束しました。今は別のことも気になります。"]
                return {"text":self._pick(xs,c,"avo-progress"),"speak_bias":.01,"topic":"avocado_progress"}
            xs=["この前覚えたアボカド、いつか食べてみたいです。","アボカドの味はまだ知らないので、いつか確かめたいです。"]
            return {"text":self._pick(xs,c,"avo"),"speak_bias":.015,"topic":"avocado"}

        # Attention shifts to other needs while a recent subject cools down.
        candidates=[]
        if a.get("boredom",0)>=.38 and not self._cool(c,"boredom"):
            candidates.append({"text":self._pick(["グランドオブガン、今日は何をしようか考えるのも楽しいですね。","何か新しい日本のものを見つけたいです。しゅんならまた変なものを知ってそうですね！"],c,"bored"),"speak_bias":.025,"topic":"boredom"})
        if a.get("affection",0)>=.7 and not self._cool(c,"company"):
            candidates.append({"text":self._pick(["そういえば、しゅんは今どうしてるんでしょう。少し話したいですね。","しゅんに何か面白いことがあったか聞いてみたいです。"],c,"company"),"speak_bias":.02,"topic":"company"})
        if a.get("hunger",0)>=.65 and not self._cool(c,"food_general"):
            candidates.append({"text":self._pick(["なんだかお腹が空いてきました。日本にはまだ知らない食べ物がいっぱいですね！","次はアボカド以外の食べ物も覚えてみたいですね！"],c,"food"),"speak_bias":.02,"topic":"food_general"})
        if candidates: return self._pick(candidates,c,"attention-shift")
        return {"text":self._pick(["今日は何か面白いことが起きないでしょうか。","しゅんは今何をしているんでしょう。","グランドオブガンでもしながら少し考えます。"],c,"general"),"speak_bias":.01,"topic":"general"}

    def speak(self,c,t):
        topic=t.get("topic","general")
        p={
          "avocado":["しゅん！　アボカド、いつか食べてみたいですね！　でも今日は別のものも気になります！"],
          "avocado_progress":["しゅん！　アボカド探しは今度のお楽しみですね！　見つけたら一緒に食べましょう！"],
          "company":["しゅん！　今なにしてるんですか？　何か面白いことありました？","しゅんー！　少しお話ししましょう！　今日は何してたんですか？"],
          "boredom":["しゅん！　グランドオブガンやりませんか？　今日は何して遊びましょう！","しゅん！　何か新しいもの教えてください！　まだ知らないものがいっぱいですね！"],
          "food_general":["しゅん！　アボカド以外にも、私がまだ知らない食べ物ってあります？　いっぱいありそうですね！","しゅん、お腹空きました！　今日は何かおいしいもの食べたいですね！"],
          "open_thread":["しゅん！　さっきの話、続きが気になります！　もう少し聞かせてください！"],
          "general":["しゅん！　今日は何か面白いことありました？","しゅん、今なにしてるんですか？　私もちょっと暇なんですよ！","しゅん！　グランドオブガンでもします？　何かするなら一緒ですね！"]}
        return self._fresh(p.get(topic,p["general"]),c,"speech:"+topic+":"+t.get("text",""))
