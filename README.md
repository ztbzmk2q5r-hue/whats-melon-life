# Project What's Melon — LIFE

人類が「好きな世界で、好きな人生を生きられる」未来を目指す Project What's Melon の開発リポジトリです。

## Repository purpose

このリポジトリでは、Project What's Melon に関するソースコード、プロトタイプ、共通パッケージ、技術仕様、研究資料を整理して管理します。

## Structure

- `apps/` — 実際に動かすアプリケーションやサービス
- `packages/` — 複数アプリで共有するコード・ライブラリ
- `prototypes/` — 実験・検証段階のコード
- `docs/architecture/` — システム構成・設計
- `docs/specifications/` — 各機能・サービスの仕様
- `docs/roadmap/` — 開発ロードマップ
- `research/` — 技術調査・研究メモ
- `archive/` — 現在は使用していない旧版資料・コード

## Development policy

1. APIキー、アクセストークン、秘密鍵、パスワードなどの秘密情報はコミットしない。
2. ローカルの秘密情報は `.env` 等で管理し、Git の追跡対象外にする。
3. 動作中のサービスは `apps/`、実験段階は `prototypes/` に分離する。
4. 複数サービスから利用するコードは `packages/` に切り出す。
5. 重要な仕様変更は `docs/` に記録する。
6. 古いコードを残す必要がある場合は `archive/` に移す。

## Status

Project What's Melon is under active development.
