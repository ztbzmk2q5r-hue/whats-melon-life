# WM-LIFE-001 v0.02 — Self Formation

Project What's Melon / Research Track 01: Artificial Personality Architecture

## Research purpose

この実験の目的は、アネラさんっぽいBotを作ることではありません。

**人工人格において「脳」をどのような構造で設計すれば、時間と経験を通じて一貫した人格・自己認識・自発性が確立するのか**
を探ることです。

アネラ・H・エメラルドは、その最初の宿主人格です。

## Architecture

`時間 → 内部状態 → 記憶 → 思考 → 自発性 → 発話/沈黙 → 経験 → 記憶 → 自己形成`

### 分離した層

- `identity_core.json` — 原作由来の人格の核。原則固定。
- `self_model.json` — 「私はこういう人間だ」という自己認識。
- `beliefs.json` — 世界や他者への信念。
- `preferences.json` — 経験から育つ嗜好。
- `relationship.json` — しゅんとの関係モデル。
- `memories.jsonl` — 根拠付きの自伝的記憶。
- `runtime.json` — 好奇心、寂しさ、退屈など現在の状態。

## Core idea

Pythonは人格そのものを決めません。
Pythonは状態・記憶・証拠・時間経過を管理する「脳のインフラ」です。

思考や経験解釈はLLM側に担当させます。

1回「好き」と言っただけでは嗜好を確定しません。
同じ傾向が何度も現れた時、あるいは重要な経験があった時だけ、
その根拠となる記憶IDを残して人格モデルを更新します。

矛盾する経験は削除せず、`contested` として残せる設計です。

## Local test

```bash
PYTHONPATH=src python -m wm_brain.cli --state state
```

現在同梱している `HeuristicReasoner` はオフライン動作確認専用です。
本番ではChatGPTのスケジュール実行、またはLLM APIをreasonerとして接続します。

## Important

この仕組みは持続的な自己モデルを持つ振る舞いを作るための実験です。
意識や主観的体験の存在を証明するものではありません。


## Personality supervision loop

実際に発話した内容は `state/conversation_log.jsonl` に保存する。

外部レビュー担当はGoogle Drive上の原作正史と比較し、
ズレを「人格ドリフト」か「経験に基づく成長」か判定する。

- `state/review_state.json` — どこまで監査したか
- `reviews/personality_reviews.jsonl` — 監査と修正の履歴
- `reviews/REVIEW_PROTOCOL.md` — レビュー基準

`発話 → 正史比較 → 原因診断 → 最小修正 → 次の発話`

という第二のフィードバックループを持つ。
