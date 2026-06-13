# typing_auto

タイピングゲーム自動化ツール。画面上で選択した範囲を OCR で読み取り、認識した英数文字列をそのままキー入力します。既定は **EasyOCR**（精度重視）。

> ⚠️ 学習・実験目的のツールです。オンライン対戦やランキングのある環境での使用は規約違反になり得ます。利用は自己責任で。

## 動作環境

- Windows 10 / 11（`keyboard` のグローバルフックを使うため Windows 想定）
- Python 3.9+

初回起動時に OCR モデルが読み込まれます（EasyOCR は初回のみモデルを自動ダウンロード）。

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> EasyOCR は PyTorch(CPU) を含むため初回インストールは大きめ（数百 MB〜）です。軽量に済ませたい場合は下記「OCR エンジンの選択」を参照。

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

## OCR エンジンの選択

`main.py` 冒頭の `ENGINE` で切替できます。

| `ENGINE` | 精度（ベンチ48枚） | 速度の目安 | 依存 |
| --- | --- | --- | --- |
| `"easyocr"`（既定） | **CER 0% 前後（ベンチ47〜48/48）** | ~200ms/枚 | PyTorch(CPU) |
| `"rapidocr"` | CER 0.17% / 45/48 | ~15–50ms/枚 | onnxruntime（軽量・torch不要） |

軽量・高速を優先する場合は `ENGINE = "rapidocr"` にし、`requirements.txt` の `rapidocr-onnxruntime` を有効化してインストールしてください。

> 複数フォント・サイズ・明暗を含む合成タイピング画像で各エンジンを同一条件比較した結果に基づく既定値です。`winocr`(小フォントで空振り) / `PaddleOCR`(本構成で不調) / `wordninja`後処理(稀語を過分割) は精度面で劣ったため不採用。

## 設定

`main.py` 冒頭の定数で調整できます。

| 定数 | 説明 |
| --- | --- |
| `CAPTURE_INTERVAL` | キャプチャ間隔（秒） |
| `TYPE_INTERVAL` | キー入力間隔（秒） |
| `MAX_TYPE_LEN` | この長さを超える OCR 結果は誤認識とみなし打鍵しない |
| `OCR_THREADS` | 推論スレッド数。多コアでも 2〜6 が最速・最安定（過剰生成は逆効果） |
| `SINGLE_LINE` | (rapidocr時) `True` で検出(det)を省く高速モード。複数行は `False` |
| `MIN_SCORE` | (rapidocr rec-only時) このスコア未満の認識は捨てる |
| `KEEP` | 入力に残す文字の正規表現 |

> 💡 タイピングゲームは1行ずつ表示されることが多いので、**問題文1行だけ**を範囲選択するのが最も安定します。

## 仕組み

1. `mss` で選択範囲をキャプチャ
2. 直前フレームと画素が同一なら OCR をスキップ（待機中はほぼ 0 コスト）
3. OCR（既定 EasyOCR）でテキスト認識 → 不要記号を除去し小文字化
4. 前回と異なる場合のみ、1文字ずつ（停止を即反映できるよう）キー入力

## 使用ライブラリ

`easyocr`（既定）/ `mss` / `numpy` / `keyboard` ／ 任意 `rapidocr-onnxruntime`

## License

Apache License 2.0 — see [LICENSE](LICENSE).
