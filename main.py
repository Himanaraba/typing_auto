"""タイピングゲーム自動化: 範囲選択 → Windows標準OCR(英数) → そのままキー入力"""

import ctypes
import re
import sys
import threading
import time
import tkinter as tk

import keyboard
import mss
import numpy as np
import winocr
from PIL import Image

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

CAPTURE_INTERVAL = 0.05
TYPE_INTERVAL = 0.005
OCR_LANG = "en-US"

# OCR結果から残す文字。記号を増やしたければここを広げる
KEEP = re.compile(r"[^a-zA-Z0-9 \-_.,'!?:;/()\"]")


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


def ocr_image(img_bgr):
    rgb = img_bgr[:, :, ::-1]
    pil = Image.fromarray(rgb)
    result = winocr.recognize_pil_sync(pil, OCR_LANG)
    text = result.get("text", "") if isinstance(result, dict) else ""
    return KEEP.sub("", text).lower()


def typing_loop(state):
    sct = mss.mss()
    last_text = ""
    while state["running"]:
        try:
            img = np.array(sct.grab(state["region"]))[:, :, :3]
            text = ocr_image(img)
            if text and text != last_text:
                keyboard.write(text, delay=TYPE_INTERVAL)
                last_text = text
        except Exception as ex:
            print(f"[ERR] {ex}", file=sys.stderr)
        time.sleep(CAPTURE_INTERVAL)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=== タイピングゲーム自動化 (Windows OCR / 英数) ===")
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

    state = {"running": False, "quit": False, "region": region}

    def start():
        if state["running"] or state["region"] is None:
            return
        state["running"] = True
        threading.Thread(target=typing_loop, args=(state,), daemon=True).start()
        print("[開始]")

    def stop():
        if state["running"]:
            state["running"] = False
            print("[停止]")

    def reselect():
        stop()
        time.sleep(0.1)
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
