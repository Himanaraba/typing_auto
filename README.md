# typing_auto

タイピングゲーム自動化ツール。画面上で選択した範囲を RapidOCR（ONNX Runtime）で読み取り、認識した英数文字列をそのままキー入力します。

> ⚠️ 学習・実験目的のツールです。オンライン対戦やランキングのある環境での使用は規約違反になり得ます。利用は自己責任で。

## 動作環境

- Windows 10 / 11（`keyboard` のグローバルフックを使うため Windows 想定。OCR 自体はクロスプラットフォーム）
- Python 3.9+

初回起動時に RapidOCR のモデル（数十 MB）が読み込まれます。

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
| `SINGLE_LINE` | `True` で検出(det)を省く高速モード(~30ms、範囲を1行とみなす)。複数行は `False`（精度↑だが数秒） |
| `KEEP` | 入力に残す文字の正規表現 |

> 💡 タイピングゲームは1行ずつ表示されることが多いので、`SINGLE_LINE=True`（既定）のまま**問題文1行だけ**を範囲選択するのが最速・最精度です。

## 仕組み

1. `mss` で選択範囲をキャプチャ
2. `RapidOCR`（ONNX Runtime / CPU）でテキスト認識
3. 不要な記号を除去し小文字化
4. 前回と異なる場合のみ `keyboard.write` でキー入力

## 使用ライブラリ

`rapidocr-onnxruntime` / `mss` / `numpy` / `keyboard`

## License

Apache License 2.0 — see [LICENSE](LICENSE).
