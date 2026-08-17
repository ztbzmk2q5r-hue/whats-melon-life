class HeuristicReasoner:
    """
    オフライン動作確認用。
    本番ではChatGPTスケジュールまたはLLM API実装に差し替える。
    """
    def think(self, context):
        threads = context["runtime"].get("open_threads") or []
        if threads:
            return {"text": threads[0], "speak_bias": 0.04}
        return {"text": "しゅんが今なにをしているのか、少し気になります。", "speak_bias": 0.03}

    def speak(self, context, thought):
        return "しゅん！　今、なにをしているんですか？　なんとなく気になりました！"
