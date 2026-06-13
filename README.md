# typing_auto

タイピングゲーム自動化ツール。画面上で選択した範囲を OCR で読み取り、認識した英数文字列をそのままキー入力します。既定は **RapidOCR rec-only + 保守的スペース復元**（精度・速度を両立）。

> ⚠️ 学習・実験目的のツールです。オンライン対戦やランキングのある環境での使用は規約違反になり得ます。利用は自己責任で。

> 📝 対象が canvas / WebGL / Unity / Flash 描画のゲーム（寿司打 WebGL版・e-typing 等の多く）の場合、文字は画像として描かれDOM/JSに存在しないため、OCR が唯一の汎用的な読み取り手段です。DOM にテキストを持つ一部の Web ゲームやネイティブアプリは、別途ソース直読み（DOM/UI Automation）の方が高速・正確です。日本語ローマ字を打つ場合は英文向けの `FIX_SPACES` はオフのままにしてください。

## 動作環境

- Windows 10 / 11（`keyboard` のグローバルフックを使うため Windows 想定）
- Python 3.9+

初回起動時に OCR モデル（RapidOCR 同梱、数十 MB）が読み込まれます。

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> 既定は軽量（torch 不要）です。代替の EasyOCR を使う場合のみ PyTorch(CPU) が必要で、初回インストールが大きくなります（下記「OCR エンジンの選択」参照）。

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

`main.py` 冒頭の `ENGINE` で切替できます。

| `ENGINE` | 精度（ベンチ48枚） | 速度の目安 | 依存 |
| --- | --- | --- | --- |
| `"rapidocr"`（既定） | **CER 0% / 48/48 完全一致** | **~14ms/枚** | onnxruntime + wordninja（軽量・torch不要） |
| `"easyocr"` | CER 0% / 47〜48/48 | ~90〜110ms/枚 | PyTorch(CPU)（重い） |

既定の RapidOCR は単一行認識（det 省略）が速く、唯一の弱点だった語結合（`quartzjudge`）を `FIX_SPACES`（保守的スペース復元）が補正することで、EasyOCR と同等の精度を約7倍速で達成します。代替の EasyOCR を使う場合は `requirements.txt` の `easyocr` を有効化してください。

> 複数フォント・サイズ・明暗を含む合成タイピング画像で全エンジンを同一条件比較した結果に基づく既定値です。`winocr`(小フォントで空振り) / `PaddleOCR`(本構成で不調) / 素の `wordninja` 全文後処理(稀語を過分割) は劣ったため不採用。`FIX_SPACES` は「既知単語でない長いトークンを、両方とも既知単語かつ各3文字以上に分割できる時のみ」分割する保守版で、過分割を回避します。

## 設定

`main.py` 冒頭の定数で調整できます。

| 定数 | 説明 |
| --- | --- |
| `CAPTURE_INTERVAL` | キャプチャ間隔（秒） |
| `TYPE_INTERVAL` | キー入力間隔（秒） |
| `MAX_TYPE_LEN` | この長さを超える OCR 結果は誤認識とみなし打鍵しない |
| `FIX_SPACES` | 【英文向け】語結合を英単語辞書で保守的に復元。日本語ローマ字には効かないため既定 `False`。英文タイピング時のみ `True` |
| `OCR_THREADS` | (rapidocr) 推論スレッド数。多コアでも 2〜6 が最速・最安定（過剰生成は逆効果） |
| `EASYOCR_THREADS` | (easyocr) torch スレッド数。実測では 8 が最速 |
| `SINGLE_LINE` | (rapidocr) `True` で検出(det)を省く高速モード。複数行は `False` |
| `MIN_SCORE` | (rapidocr rec-only) このスコア未満の認識は捨てる |
| `KEEP` | 入力に残す文字の正規表現 |

> 💡 タイピングゲームは1行ずつ表示されることが多いので、**問題文1行だけ**を範囲選択するのが最も安定します。

## 仕組み

1. `mss` で選択範囲をキャプチャ
2. 直前フレームと画素が同一なら OCR をスキップ（待機中はほぼ 0 コスト）
3. OCR（既定 RapidOCR rec-only）でテキスト認識 → 不要記号を除去し小文字化
4. `FIX_SPACES` で語結合を保守的に復元
5. 前回と異なる場合のみ、1文字ずつ（停止を即反映できるよう）キー入力

## 使用ライブラリ

`rapidocr-onnxruntime` / `wordninja` / `mss` / `numpy` / `keyboard` ／ 任意 `easyocr`

## License

Apache License 2.0 — see [LICENSE](LICENSE).
