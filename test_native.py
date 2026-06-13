"""ネイティブ統合テスト。

自作の軽量タイピングゲーム(大きくお題を表示する Tk ウィンドウ)に対して、
本体 main.py のパイプライン(画面キャプチャ → OCR → キー打鍵)を実画面で実走し、
お題ごとに「OCRが正しく読めて正しいキーを打てたか」を検証する。

- 本体が注入したキーは、前面・フォーカス済みの Entry に入る。各お題ごとに
  Entry の中身がお題と一致したら成功とみなす(= capture→OCR→inject が正しく通った)。
- keyboard フックは自分で注入したキーを拾わないため、検証には使えない(Entryで判定する)。

使い方:
    .venv\\Scripts\\python.exe test_native.py
"""
import random
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import tkinter as tk

import main  # 本体パイプラインを再利用(import 時に DPI awareness も設定される)

# お題プール(ローマ字想定。o/0・l/1/i・m/rn・連続子音など OCR が苦戦しやすい語を含める)
WORD_POOL = [
    "sushi", "ramen", "tempura", "wasabi", "tokyo", "kyoto", "osaka", "sakura",
    "konnichiwa", "arigatou", "gozaimasu", "shinkansen", "matcha", "yokohama",
    "fujisan", "ohayou", "itadakimasu", "natsukashii", "kakkoii", "ittekimasu",
    "minna", "gakkou", "nippon", "ringo", "mikan", "tamago", "kingyo",
]
N_WORDS = 10  # 毎回ランダムに N 語出題
PER_WORD_TIMEOUT = 6.0
FONT = ("Consolas", 48)

# ゲームのキー取りこぼしを模擬: この間隔より速く来たキーは捨てる(0で無効)。
# 実ゲーム(WebGL/30〜60fps)が速すぎる打鍵を落とす挙動を再現し、TYPE_INTERVAL が
# 十分かを検証する。本体 TYPE_INTERVAL がこれより小さいと取りこぼしで NG になる。
CONSUME_INTERVAL = 0.02

WORDS = random.sample(WORD_POOL, min(N_WORDS, len(WORD_POOL)))

# テスト中は本体のデバッグ表示は止め、差分スキップは有効(実運用に合わせる)
main.DEBUG = False
main.SKIP_UNCHANGED = True

root = tk.Tk()
root.title("typing test target")
root.geometry("900x320+200+200")
root.configure(bg="white")
root.attributes("-topmost", True)

label = tk.Label(root, text="", font=FONT, bg="white", fg="black")
label.pack(expand=True, pady=20)
entry = tk.Entry(root, font=("Consolas", 20), width=40)  # 注入キーの受け皿(フォーカス確保用)
entry.pack(pady=10)
info = tk.Label(root, text="準備中...", font=("Meiryo UI", 12), bg="white", fg="gray")
info.pack()

# キー取りこぼし模擬: CONSUME_INTERVAL より速く来たキーは捨てる(default挿入を抑止)
_last_accept = {"t": 0.0}


def on_keypress(e):
    if e.char and e.char.isprintable():
        now = time.time()
        if CONSUME_INTERVAL > 0 and (now - _last_accept["t"]) < CONSUME_INTERVAL:
            return "break"  # 速すぎ → 取りこぼし
        _last_accept["t"] = now
    return None


entry.bind("<KeyPress>", on_keypress)

tstate = {"running": False, "region": None}
idx = {"v": 0}
word_start = {"t": 0.0}
results = []


def label_region():
    root.update_idletasks()
    x, y = label.winfo_rootx(), label.winfo_rooty()
    w, h = label.winfo_width(), label.winfo_height()
    m = 6  # マージン
    return {"left": max(0, x - m), "top": max(0, y - m), "width": w + 2 * m, "height": h + 2 * m}


def focus_entry():
    root.lift()
    root.focus_force()
    entry.focus_force()


def show(word, refocus=False):
    label.config(text=word)
    entry.delete(0, tk.END)
    if refocus:
        focus_entry()
    root.update_idletasks()
    tstate["region"] = label_region()


WARMUP_WORD = "ready"
SETTLE_SEC = 4.0  # 起動直後はフォーカスが定まりにくいので数秒確保してから採点開始
_last_focus = {"t": 0.0}


def begin():
    # 採点前のフォーカス確立フェーズ。確立後はフォーカスを触らない(揺さぶると取りこぼすため)
    show(WARMUP_WORD, refocus=True)
    _last_focus["t"] = time.time()
    word_start["t"] = time.time()
    tstate["running"] = True
    threading.Thread(target=main.typing_loop, args=(tstate,), daemon=True).start()
    info.config(text="フォーカス確立中...")
    root.after(100, settle)


def settle():
    now = time.time()
    # 数回だけ穏やかにフォーカスを確保(連打しない)
    if now - _last_focus["t"] > 1.2:
        focus_entry()
        _last_focus["t"] = now
    if now - word_start["t"] < SETTLE_SEC:
        root.after(100, settle)
        return
    info.config(text="テスト実行中... 自動で進みます")
    show(WORDS[0])  # 以降フォーカスは触らない
    word_start["t"] = time.time()
    root.after(50, poll)


def poll():
    i = idx["v"]
    if i >= len(WORDS):
        finish()
        return
    word = WORDS[i]
    got = entry.get().strip()  # 本体が注入してフォーカス先Entryに入った文字列
    done = False
    # お題切替の遷移フレーム由来の断片は前方に累積するため、末尾一致で「最終的に正しく
    # 打てたか」を判定する(OCR誤読なら末尾も一致しない)
    if got.endswith(word):
        results.append((word, got, True))
        tag = "OK" if got == word else "OK*"  # OK* は遷移ノイズ込みで末尾一致
        print(f"[{tag}] お題={word!r}  打鍵={got!r}")
        done = True
    elif time.time() - word_start["t"] > PER_WORD_TIMEOUT:
        results.append((word, got, False))
        print(f"[NG] お題={word!r}  打鍵={got!r}  (timeout)")
        done = True
    if done:
        idx["v"] += 1
        if idx["v"] < len(WORDS):
            show(WORDS[idx["v"]])
            word_start["t"] = time.time()
    root.after(50, poll)


def finish():
    tstate["running"] = False
    n_ok = sum(1 for _, _, ok in results if ok)
    print(f"\n=== 結果: {n_ok}/{len(results)} 成功 ===")
    for w, g, ok in results:
        if not ok:
            print(f"   NG: お題={w!r} 打鍵={g!r}")
    root.destroy()


root.after(1200, begin)  # ウィンドウ描画を待ってから開始
# 全体タイムアウト保険(ハング防止)
root.after(int((PER_WORD_TIMEOUT * len(WORDS) + 8) * 1000), root.destroy)
root.mainloop()
