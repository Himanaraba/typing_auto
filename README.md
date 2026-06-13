# typing_auto

タイピングゲーム自動化ツール。画面上で選択した範囲を Windows 標準 OCR で読み取り、認識した英数文字列をそのままキー入力します。

> ⚠️ 学習・実験目的のツールです。オンライン対戦やランキングのある環境での使用は規約違反になり得ます。利用は自己責任で。

## 動作環境

- Windows 10 / 11（Windows OCR を利用するため Windows 専用）
- Python 3.9+

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 起動

```powershell
.\.venv\Scripts\python.exe main.py
```

起動直後に全画面オーバーレイが出るので、**ドラッグで OCR 範囲を選択**します（Esc でキャンセル）。

ホットキーが効かない場合は、PowerShell を**管理者権限**で開き直してから起動してください（`keyboard` がグローバルフック登録に管理者権限を要する場合があります）。

## 操作（ホットキー）

| キー | 動作 |
| --- | --- |
| `F9` | 開始（範囲を OCR → キー入力） |
| `F10` | 停止 |
| `F8` | 範囲を選び直し |
| `Ctrl+Shift+Q` | 終了 |

## 設定

`main.py` 冒頭の定数で調整できます。

| 定数 | 説明 |
| --- | --- |
| `CAPTURE_INTERVAL` | キャプチャ間隔（秒） |
| `TYPE_INTERVAL` | キー入力間隔（秒） |
| `OCR_LANG` | OCR 言語（既定 `en-US`） |
| `KEEP` | 入力に残す文字の正規表現 |

## 仕組み

1. `mss` で選択範囲をキャプチャ
2. `winocr`（Windows 標準 OCR）でテキスト認識
3. 不要な記号を除去し小文字化
4. 前回と異なる場合のみ `keyboard.write` でキー入力

## 使用ライブラリ

`winocr` / `Pillow` / `mss` / `numpy` / `keyboard`

## License

Apache License 2.0 — see [LICENSE](LICENSE).
