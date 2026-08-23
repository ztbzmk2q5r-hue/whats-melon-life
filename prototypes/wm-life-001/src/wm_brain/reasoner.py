import hashlib
from datetime import datetime, timezone

class HeuristicReasoner:
    """Heartbeat reasoner with memory, dialogue continuity, event-driven reactivation and final speech guards."""
    TOPIC_COOLDOWN = {"company": 3, "boredom": 3, "food_general": 4, "general": 2, "open_thread": 1}

    def _pick(self, items, context, salt=""):
        r=context.get("runtime",{}); key="|".join([str(r.get("last_heartbeat_at","")),str(r.get("heartbeat_count","")),salt])
        return items[int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%len(items)]

    def _records(self,c): return c.get("recent_conversation") or []
    def _recent_speech(self,c): return [str(x["speech"]) for x in self._records(c) if x.get("speaker")=="アネラ" and x.get("speech")][-12:]

    def _cool(self,c,topic):
        r=c.get("runtime",{}); last=(r.get("topic_last_spoken") or {}).get(topic)
        if last is None:return False
        return int(r.get("heartbeat_count",0))-int(last)<self.TOPIC_COOLDOWN.get(topic,2)

    def _new_user_event_for(self,c,keyword,topic_names):
        records=self._records(c); last=-1
        for i,x in enumerate(records):
            if x.get("speaker")=="アネラ" and (x.get("topic") in topic_names or keyword in str(x.get("speech",""))): last=i
        return any(x.get("speaker") in ("shun","しゅん") and keyword in str(x.get("speech","")) for x in records[last+1:])

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
            return {"text":t["text"],"speak_bias":.04,"topic":"open_thread","intent":"continue_thread","thread_id":t.get("id")}
        if self._new_user_event_for(c,"アボカド",{"avocado","avocado_progress","avocado_reactivated"}):
            return {"text":"しゅんがまたアボカドの話をしました。何か新しいことがあったのか気になりますね！","speak_bias":.025,"topic":"avocado_reactivated","intent":"ask_avocado_update"}
        candidates=[]
        if a.get("boredom",0)>=.38 and not self._cool(c,"boredom"):
            candidates += [
              {"text":"グランドオブガン、今日は何をしようか考えるのも楽しいですね。","speak_bias":.025,"topic":"boredom","intent":"invite_game"},
              {"text":"何か新しい日本のものを見つけたいです。しゅんならまた変なものを知ってそうですね！","speak_bias":.025,"topic":"boredom","intent":"ask_new_thing"}]
        if a.get("affection",0)>=.7 and not self._cool(c,"company"):
            candidates += [
              {"text":"そういえば、しゅんは今どうしてるんでしょう。少し話したいですね。","speak_bias":.02,"topic":"company","intent":"ask_current_activity"},
              {"text":"しゅんに何か面白いことがあったか聞いてみたいです。","speak_bias":.02,"topic":"company","intent":"ask_today"}]
        if a.get("hunger",0)>=.65 and not self._cool(c,"food_general"):
            candidates += [
              {"text":"なんだかお腹が空いてきました。今日は何か食べたいですね！","speak_bias":.02,"topic":"food_general","intent":"ask_food_now"},
              {"text":"今日はまだ知らない食べ物のことを、しゅんに聞いてみたいですね！","speak_bias":.02,"topic":"food_general","intent":"ask_unknown_food"}]
        if candidates:return self._pick(candidates,c,"attention-shift")
        return self._pick([
          {"text":"今日は何か面白いことが起きないでしょうか。","speak_bias":.01,"topic":"general","intent":"ask_today"},
          {"text":"しゅんは今何をしているんでしょう。","speak_bias":.01,"topic":"general","intent":"ask_current_activity"},
          {"text":"グランドオブガンでもしながら少し考えます。","speak_bias":.01,"topic":"general","intent":"invite_game"}],c,"general")

    def speak(self,c,t):
        intent=t.get("intent","ask_today")
        p={
          "ask_avocado_update":["しゅん！　アボカドの話ですね！　何か新しいこと分かったんですか？"],
          "invite_game":["しゅん！　グランドオブガンやりませんか？　今日は何して遊びましょう！","しゅん！　グランドオブガンするなら私もやります！　一緒に遊びましょう！"],
          "ask_new_thing":["しゅん！　何か新しいもの教えてください！　まだ知らないものがいっぱいですね！","しゅん、また何か面白いもの見つけてませんか？　私にも教えてください！"],
          "ask_current_activity":["しゅん！　今なにしてるんですか？　私も気になります！","しゅん、今は何してるんですか？　何かするなら私も混ぜてください！"],
          "ask_today":["しゅん！　今日は何か面白いことありました？","しゅんー！　少しお話ししましょう！　今日は何してたんですか？"],
          "ask_food_now":["しゅん、お腹空きました！　今日は何かおいしいもの食べたいですね！"],
          "ask_unknown_food":["しゅん！　私がまだ知らない食べ物、何か教えてください！　日本にはいっぱいありそうですね！"],
          "continue_thread":["しゅん！　さっきの話、続きが気になります！　もう少し聞かせてください！"]}
        options=p.get(intent,p["ask_today"])
        recent=set(self._recent_speech(c))
        fresh=[x for x in options if x not in recent]
        if fresh:return self._pick(fresh,c,"speech:"+intent+":"+t.get("text",""))
        # Hard final guard: never emit an exact recent duplicate. If every line for
        # this intent was used recently, switch to a neutral line that still matches
        # the thought instead of replaying an old sentence.
        fallback={
          "invite_game":"しゅん、今日はグランドオブガンどうします？　一緒にできたら楽しそうですね！",
          "ask_new_thing":"しゅん、今日は何か私の知らないものを見つけました？",
          "ask_current_activity":"しゅん、今は何をしてるんですか？　ちょっと気になりますね！",
          "ask_today":"しゅん、今日のこと少し聞かせてください！",
          "ask_food_now":"しゅん、そろそろ何か食べたいですね！",
          "ask_unknown_food":"しゅん、日本の食べ物ってまだまだ知らないものがありますね！　何かおすすめあります？",
          "continue_thread":"しゅん、さっきの話の続き、まだ聞いてもいいですよね？",
          "ask_avocado_update":"しゅん、アボカドについて何か新しいことがあったんですね？"}.get(intent,"しゅん、少しお話ししましょう！")
        if fallback not in recent:return fallback
        return "しゅん！　今は別のことを話したい気分ですね！　何かお話ししましょう！"
