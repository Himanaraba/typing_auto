"""タイピングゲーム自動化: 範囲選択 → OCR(英数) → そのままキー入力

OCR エンジンは ENGINE で切替:
  "rapidocr" … 既定。rec-only + 保守的スペース復元でベンチ48/48・CER 0% を ~15ms で達成。torch不要・軽量
  "easyocr"  … 代替。単語検出で高精度だが ~90-110ms と重い(torch CPU)
"""

import ctypes
import re
import sys
import threading
import time
import tkinter as tk

import keyboard
import mss
import numpy as np

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

HOTKEY_START = "f9"
HOTKEY_STOP = "f10"
HOTKEY_RESELECT = "f8"
HOTKEY_QUIT = "ctrl+shift+q"

# OCR エンジン: "rapidocr"(軽量高速・既定) / "easyocr"(代替・重い)
ENGINE = "rapidocr"

# 語結合(quartzjudge 等)を保守的に復元する。既知単語でない長いトークンを、
# 両方とも既知単語かつ各3文字以上に分割できる時だけ分割(vexingly 等の過分割は回避)
FIX_SPACES = True

CAPTURE_INTERVAL = 0.05
TYPE_INTERVAL = 0.005

# 暴走防止: OCR が異常に長い文字列を返したら打鍵せず捨てる
MAX_TYPE_LEN = 500

# --- rapidocr 専用設定 ---
# 範囲を1行とみなしテキスト検出(det)を省略する高速モード(~15ms)。複数行は False。
SINGLE_LINE = True
# onnxruntime のスレッド数(rapidocr)。RapidOCR は既定で全コアを使うが小モデルでは
# 同期オーバーヘッドで逆に遅くなる(16T: 152ms / 4T: 15ms)。2〜6 が最速・最安定。
OCR_THREADS = 4
# EasyOCR(torch CPU)用スレッド数。モデルが大きく、実測では 8 が最速(8T: 198ms / 4T: 378ms / 16T: 228ms)
EASYOCR_THREADS = 8
# rec-only パスは RapidOCR 内部のスコア閾値が効かないため自前で適用(低信頼の誤打鍵防止)
MIN_SCORE = 0.5

# OCR結果から残す文字。記号を増やしたければここを広げる
KEEP = re.compile(r"[^a-zA-Z0-9 \-_.,'!?:;/()\"]")


# === OCR エンジン初期化(選択したものだけ遅延 import) ===
if ENGINE == "easyocr":
    import easyocr

    try:
        import torch
        torch.set_num_threads(EASYOCR_THREADS)
    except Exception:
        pass

    _reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def _recognize(img_bgr):
        # readtext は ndarray を BGR とみなす。paragraph=True で単語スペースを正しく結合
        lines = _reader.readtext(img_bgr, detail=0, paragraph=True)
        return " ".join(lines)

elif ENGINE == "rapidocr":
    from rapidocr_onnxruntime import RapidOCR

    _ocr_engine = RapidOCR(
        intra_op_num_threads=OCR_THREADS,
        inter_op_num_threads=OCR_THREADS,
    )

    def _recognize(img_bgr):
        if SINGLE_LINE:
            # det/cls を省略し範囲全体を1行として認識。戻り値は [text, score] のリスト
            result, _ = _ocr_engine(img_bgr, use_det=False, use_cls=False, use_rec=True)
            if not result:
                return ""
            return " ".join(line[0] for line in result if float(line[1]) >= MIN_SCORE)
        # det 込み。戻り値は [box, text, score] を上→下/左→右順で連結
        result, _ = _ocr_engine(img_bgr)
        if not result:
            return ""
        return " ".join(line[1] for line in result)

else:
    raise ValueError(f"未知の ENGINE: {ENGINE!r} ('easyocr' か 'rapidocr')")


# === 保守的スペース復元 ===
if FIX_SPACES:
    import wordninja

    try:
        _WORDCOST = wordninja.DEFAULT_LANGUAGE_MODEL._wordcost  # {word: cost} 頻度辞書
    except Exception:
        _WORDCOST = None

    def fix_spaces(text):
        if not _WORDCOST:
            return text
        out = []
        for tok in text.split():
            # 既知単語でない長い英字トークンのみ対象。両方とも既知単語かつ各3文字以上に
            # 分割できる場合だけ分割する(短い断片を生む分割や既知単語の過分割を避ける)
            if tok.isalpha() and len(tok) >= 6 and tok not in _WORDCOST:
                parts = wordninja.split(tok)
                if len(parts) >= 2 and all(len(p) >= 3 for p in parts) \
                        and all(p in _WORDCOST for p in parts):
                    out.extend(parts)
                    continue
            out.append(tok)
        return " ".join(out)
else:
    def fix_spaces(text):
        return text


def ocr_image(img_bgr):
    text = KEEP.sub("", _recognize(img_bgr)).lower()
    return fix_spaces(text)


def select_region():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    root.configure(bg="black", cursor="cross")

    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        root,
        text="ドラッグで範囲選択 / Esc でキャンセル",
        bg="white", fg="black",
        font=("Meiryo UI", 14),
    ).place(relx=0.5, y=30, anchor="n")

    state = {"start_widget": None, "start_screen": None, "rect": None, "result": None}

    def on_press(e):
        state["start_widget"] = (e.x, e.y)
        state["start_screen"] = (e.x_root, e.y_root)
        state["rect"] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def on_drag(e):
        if state["rect"] is not None:
            x1, y1 = state["start_widget"]
            canvas.coords(state["rect"], x1, y1, e.x, e.y)

    def on_release(e):
        if state["start_screen"] is None:
            return
        sx, sy = state["start_screen"]
        ex, ey = e.x_root, e.y_root
        x, y = min(sx, ex), min(sy, ey)
        w, h = abs(ex - sx), abs(ey - sy)
        if w > 5 and h > 5:
            state["result"] = {"left": x, "top": y, "width": w, "height": h}
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda _: root.destroy())

    root.mainloop()
    return state["result"]


def type_cancellable(text, state):
    """1文字ずつ送出。各文字前に running を確認し、stop/再選択を即座に反映できるようにする。"""
    if len(text) > MAX_TYPE_LEN:
        return
    for ch in text:
        if not state["running"]:
            return
        keyboard.write(ch)
        time.sleep(TYPE_INTERVAL)


def typing_loop(state):
    sct = mss.mss()
    last_text = ""
    last_frame = None
    while state["running"]:
        try:
            img = np.array(sct.grab(state["region"]))[:, :, :3]
            # フレーム差分ゲーティング: 画素が前回と同一なら OCR をスキップ。
            # 待機中はほぼ 0 コスト、テキストが変わった瞬間だけ OCR が走る。
            if last_frame is not None and img.shape == last_frame.shape \
                    and np.array_equal(img, last_frame):
                time.sleep(CAPTURE_INTERVAL)
                continue
            last_frame = img
            text = ocr_image(img)
            if text and text != last_text:
                type_cancellable(text, state)
                last_text = text
        except Exception as ex:
            print(f"[ERR] {ex}", file=sys.stderr)
        time.sleep(CAPTURE_INTERVAL)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"=== タイピングゲーム自動化 (OCR={ENGINE} / 英数) ===")
    print(
        f"開始: {HOTKEY_START.upper()} / "
        f"停止: {HOTKEY_STOP.upper()} / "
        f"範囲再選択: {HOTKEY_RESELECT.upper()} / "
        f"終了: {HOTKEY_QUIT.upper()}"
    )

    print("最初の範囲を選択してください...")
    region = select_region()
    if region is None:
        print("キャンセルされました")
        return
    print(f"選択範囲: {region}")

    state = {"running": False, "quit": False, "region": region, "thread": None}

    def start():
        # 旧スレッドがまだ生きているなら二重起動しない(stop→start 連打対策)
        t = state["thread"]
        if state["running"] or state["region"] is None or (t and t.is_alive()):
            return
        state["running"] = True
        state["thread"] = threading.Thread(target=typing_loop, args=(state,), daemon=True)
        state["thread"].start()
        print("[開始]")

    def stop():
        if state["running"]:
            state["running"] = False
            print("[停止]")
        t = state["thread"]
        # 停止要求後、実際にループが抜けるまで待つ(自スレッドからの join は避ける)
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=1.0)

    def reselect():
        stop()
        new_region = select_region()
        if new_region:
            state["region"] = new_region
            print(f"範囲更新: {new_region}")

    def quit_app():
        state["running"] = False
        state["quit"] = True
        print("[終了]")

    keyboard.add_hotkey(HOTKEY_START, start)
    keyboard.add_hotkey(HOTKEY_STOP, stop)
    keyboard.add_hotkey(HOTKEY_RESELECT, reselect)
    keyboard.add_hotkey(HOTKEY_QUIT, quit_app)

    try:
        while not state["quit"]:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
