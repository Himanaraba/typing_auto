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


def show(word):
    label.config(text=word)
    entry.delete(0, tk.END)
    focus_entry()
    root.update_idletasks()
    tstate["region"] = label_region()


def begin():
    show(WORDS[0])
    word_start["t"] = time.time()
    tstate["running"] = True
    threading.Thread(target=main.typing_loop, args=(tstate,), daemon=True).start()
    info.config(text="テスト実行中... 自動で進みます")
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
