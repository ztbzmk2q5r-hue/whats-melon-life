import hashlib
from datetime import datetime, timezone

class HeuristicReasoner:
    """Heartbeat reasoner with memory, dialogue continuity, event-driven reactivation and final speech guards."""
    TOPIC_COOLDOWN = {"company": 3, "boredom": 3, "food_general": 4, "general": 2, "open_thread": 1}

    def _pick(self, items, context, salt=""):
        r=context.get("runtime",{}); key="|".join([str(r.get("last_heartbeat_at","")),str(r.get("heartbeat_count","")),salt])
        return items[int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%len(items)]

    def _records(self,c): return c.get("recent_conversation") or []
    def _anela_speech(self,c): return [str(x["speech"]) for x in self._records(c) if x.get("speaker") in ("アネラ","anela") and x.get("speech")]
    def _recent_speech(self,c): return self._anela_speech(c)[-12:]
    def _speech_history(self,c): return set(self._anela_speech(c))

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
        history=self._speech_history(c); fresh=[x for x in opts if x not in history]
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
          "ask_avocado_update":["しゅん！　アボカドの話ですか！？　何か分かったなら私にも教えなさい！"],
          "invite_game":["しゅん！　グランドオブガンやるんですか！？　私も混ぜなさい！","しゅん！　グランドオブガンするなら私もやります！　さあ、一緒に遊びましょう！"],
          "ask_new_thing":["しゅん！　何か新しいもの知ってるんですか！？　私にも教えなさい！","しゅん、また面白いもの見つけましたね！？　私にも見せなさい！"],
          "ask_current_activity":["しゅん！　なにしてるんですか！　私も混ぜなさい！","しゅん！　何かしてますね！？　私も混ぜなさい！"],
          "ask_today":["しゅん！　今日は何してたんですか！？　私にも聞かせなさい！","しゅん！　今日、何か面白いことあったんですか！？　私にも教えなさい！"],
          "ask_food_now":["しゅん！　何か食うのですか！？　私も食べます！","しゅん、お腹空きました！　何か食べるなら私の分も用意しなさい！"],
          "ask_unknown_food":["しゅん！　まだ私の知らない食べ物があるんですか！？　教えなさい！","しゅん！　次は何を食うのですか！？　私も知りたいです！"],
          "continue_thread":["しゅん！　さっきの話、まだ続きがあるんですね！？　聞かせなさい！"]}
        options=p.get(intent,p["ask_today"])
        history=self._speech_history(c)
        fresh=[x for x in options if x not in history]
        if fresh:return self._pick(fresh,c,"speech:"+intent+":"+t.get("text",""))

        # Exact speech already used anywhere in the available conversation
        # history is exhausted, not merely cooled down. Fallbacks stay inside
        # the active intent and retain Anela's close, royal, slightly bossy voice.
        fallbacks={
          "invite_game":[
            "しゅん、グランドオブガンするんですね！　なら私も入れなさい！",
            "しゅん！　私、グランドオブガンしたくなりました！　付き合いなさい！",
            "しゅん、グランドオブガンの時間ですよ！　今日は私と遊びましょう！"],
          "ask_new_thing":[
            "しゅん、今日は何か私の知らないものを見つけましたね！？　見せなさい！",
            "しゅん！　日本の面白いもの、また一つ教えなさい！",
            "しゅん、私がまだ知らない面白いものってあります？　あるなら早く教えなさい！",
            "しゅん！　また新しい日本のものを発見したいです！　何か探しましょう！"],
          "ask_current_activity":[
            "しゅん！　今なにしてるんですか！？　面白そうなら私もやります！",
            "しゅん！　今何してるんですか！　私も入れなさい！"],
          "ask_today":[
            "しゅん！　今日のこと、私にも聞かせなさい！",
            "しゅん！　今日はどんな一日だったんですか！？　全部聞きます！"],
          "ask_food_now":[
            "しゅん！　そろそろ何か食べるんですよね！？　私も食べます！",
            "しゅん！　お腹空きました！　何か食べましょう！"],
          "ask_unknown_food":[
            "しゅん！　日本にはまだ食ってないものがありますね！？　何がおすすめですか！",
            "しゅん！　私の知らない食べ物、まだありますよね！？　次を教えなさい！",
            "しゅん！　まだ食べたことのない日本の料理があるなら、私にも教えなさい！"],
          "continue_thread":[
            "しゅん！　さっきの話の続き、まだあるんですね！？　聞かせなさい！",
            "しゅん！　さっきの話、まだ終わってないですよね！　続きを話しなさい！"],
          "ask_avocado_update":[
            "しゅん！　アボカドについて何か分かったんですか！？　教えなさい！",
            "しゅん！　アボカドの新情報ですね！？　私にも聞かせなさい！"],
        }.get(intent,["しゅん！　今日のこと、私にも聞かせなさい！"])
        unused=[x for x in fallbacks if x not in history]
        if unused:return self._pick(unused,c,"fallback:"+intent+":"+t.get("text",""))

        # Keep the active intent even after the finite pool is exhausted.
        n=int((c.get("runtime",{}) or {}).get("heartbeat_count",0))
        stems={
          "invite_game":"しゅん！　グランドオブガンするなら私も混ぜなさい！",
          "ask_new_thing":"しゅん！　今日は私の知らないものを一つ教えなさい！",
          "ask_current_activity":"しゅん！　なにしてるんですか！　私も混ぜなさい！",
          "ask_today":"しゅん！　今日あったこと、私にも聞かせなさい！",
          "ask_food_now":"しゅん！　何か食うのですか！？　私も食べます！",
          "ask_unknown_food":"しゅん！　まだ知らない日本の食べ物があるなら教えなさい！",
          "continue_thread":"しゅん！　さっきの話、続きを聞かせなさい！",
          "ask_avocado_update":"しゅん！　アボカドの続報があるなら聞かせなさい！",
        }.get(intent,"しゅん！　今日のこと、私にも聞かせなさい！")
        return stems+f"　今度は第{n}回目ですね！"
