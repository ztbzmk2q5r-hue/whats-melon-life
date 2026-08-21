import hashlib
from datetime import datetime, timezone

class HeuristicReasoner:
    """Heartbeat reasoner with memory, dialogue continuity and event-driven topic reactivation."""
    TOPIC_COOLDOWN = {"company": 3, "boredom": 3, "food_general": 4, "general": 2, "open_thread": 1}

    def _pick(self, items, context, salt=""):
        r=context.get("runtime",{}); key="|".join([str(r.get("last_heartbeat_at","")),str(r.get("heartbeat_count","")),salt])
        return items[int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%len(items)]

    def _mem(self,c): return " ".join(str(m.get("summary","")) for m in (c.get("memories") or [])[-8:])
    def _records(self,c): return c.get("recent_conversation") or []
    def _recent_speech(self,c): return [str(x["speech"]) for x in self._records(c) if x.get("speaker")=="アネラ" and x.get("speech")][-10:]

    def _cool(self,c,topic):
        r=c.get("runtime",{}); last=(r.get("topic_last_spoken") or {}).get(topic)
        if last is None:return False
        return int(r.get("heartbeat_count",0))-int(last)<self.TOPIC_COOLDOWN.get(topic,2)

    def _new_user_event_for(self,c,keyword,topic_names):
        """Reactivate a dormant subject only when Shun adds new relevant information after Anela last spoke on it."""
        records=self._records(c)
        last_topic_index=-1
        for i,x in enumerate(records):
            if x.get("speaker")=="アネラ" and x.get("topic") in topic_names:
                last_topic_index=i
            elif x.get("speaker")=="アネラ" and keyword in str(x.get("speech","")):
                last_topic_index=i
        for x in records[last_topic_index+1:]:
            if x.get("speaker") in ("shun","しゅん") and keyword in str(x.get("speech","")):
                return True
        return False

    def _active_thread(self,c):
        now=datetime.now(timezone.utc)
        for t in c.get("runtime",{}).get("open_threads") or []:
            if not isinstance(t,dict) or t.get("resolved",False) or not str(t.get("text","")).strip():continue
            try:
                d=datetime.fromisoformat(str(t.get("created_at","")).replace("Z","+00:00"))
                if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
                if (now-d.astimezone(timezone.utc)).total_seconds()>86400:continue
            except (ValueError,TypeError):continue
            return t
        return None

    def _fresh(self,opts,c,salt):
        recent=set(self._recent_speech(c)); fresh=[x for x in opts if x not in recent]
        return self._pick(fresh or opts,c,salt)

    def think(self,c):
        r=c.get("runtime",{}); a=r.get("affect") or r; t=self._active_thread(c)
        if t and not self._cool(c,"open_thread"):
            return {"text":t["text"],"speak_bias":.04,"topic":"open_thread","thread_id":t.get("id")}

        # Long-term memories do not automatically become conversation topics again.
        # A dormant subject needs a new external event from Shun to reactivate it.
        if self._new_user_event_for(c,"アボカド",{"avocado","avocado_progress"}):
            return {"text":"しゅんがまたアボカドの話をしました。何か新しいことがあったのか気になりますね！","speak_bias":.025,"topic":"avocado_reactivated"}

        candidates=[]
        if a.get("boredom",0)>=.38 and not self._cool(c,"boredom"):
            candidates.append({"text":self._pick(["グランドオブガン、今日は何をしようか考えるのも楽しいですね。","何か新しい日本のものを見つけたいです。しゅんならまた変なものを知ってそうですね！"],c,"bored"),"speak_bias":.025,"topic":"boredom"})
        if a.get("affection",0)>=.7 and not self._cool(c,"company"):
            candidates.append({"text":self._pick(["そういえば、しゅんは今どうしてるんでしょう。少し話したいですね。","しゅんに何か面白いことがあったか聞いてみたいです。"],c,"company"),"speak_bias":.02,"topic":"company"})
        if a.get("hunger",0)>=.65 and not self._cool(c,"food_general"):
            candidates.append({"text":self._pick(["なんだかお腹が空いてきました。日本にはまだ知らない食べ物がいっぱいですね！","今日はまだ知らない食べ物のことを、しゅんに聞いてみたいですね！"],c,"food"),"speak_bias":.02,"topic":"food_general"})
        if candidates:return self._pick(candidates,c,"attention-shift")
        return {"text":self._pick(["今日は何か面白いことが起きないでしょうか。","しゅんは今何をしているんでしょう。","グランドオブガンでもしながら少し考えます。"],c,"general"),"speak_bias":.01,"topic":"general"}

    def speak(self,c,t):
        topic=t.get("topic","general")
        p={
          "avocado_reactivated":["しゅん！　アボカドの話ですね！　何か新しいこと分かったんですか？"],
          "company":["しゅん！　今なにしてるんですか？　何か面白いことありました？","しゅんー！　少しお話ししましょう！　今日は何してたんですか？"],
          "boredom":["しゅん！　グランドオブガンやりませんか？　今日は何して遊びましょう！","しゅん！　何か新しいもの教えてください！　まだ知らないものがいっぱいですね！"],
          "food_general":["しゅん、お腹空きました！　今日は何かおいしいもの食べたいですね！","しゅん！　私がまだ知らない食べ物、何か教えてください！　日本にはいっぱいありそうですね！"],
          "open_thread":["しゅん！　さっきの話、続きが気になります！　もう少し聞かせてください！"],
          "general":["しゅん！　今日は何か面白いことありました？","しゅん、今なにしてるんですか？　私もちょっと暇なんですよ！","しゅん！　グランドオブガンでもします？　何かするなら一緒ですね！"]}
        return self._fresh(p.get(topic,p["general"]),c,"speech:"+topic+":"+t.get("text",""))
