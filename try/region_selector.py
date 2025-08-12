import sys
from typing import Optional, Tuple

def select_region_interactive() -> Optional[Tuple[int, int, int, int]]:
    """
    Buka overlay semi-transparan untuk memilih region dengan drag.
    Return: (left, top, width, height) atau None jika dibatalkan (ESC).
    Catatan: Fokus pada layar utama (multi-monitor belum didukung penuh).
    """
    try:
        import tkinter as tk
    except ImportError:
        print("Tkinter tidak tersedia. Gunakan UI aplikasi untuk memasukkan koordinat atau gunakan default.")
        return None

    region = {"x0": None, "y0": None, "x1": None, "y1": None}
    result = {"value": None}

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    try:
        root.attributes("-alpha", 0.3)
    except tk.TclError:
        pass  # alpha mungkin tidak didukung
    root.configure(bg="black")
    root.attributes("-topmost", True)
    root.title("Pilih area - drag mouse, ESC untuk batal, lepaskan klik untuk konfirmasi")

    canvas = tk.Canvas(root, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    rect = None

    def on_press(event):
        nonlocal rect
        region["x0"], region["y0"] = event.x, event.y
        region["x1"], region["y1"] = event.x, event.y
        if rect is not None:
            canvas.delete(rect)
        rect = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red", width=2)

    def on_drag(event):
        nonlocal rect
        region["x1"], region["y1"] = event.x, event.y
        if rect is not None:
            canvas.coords(rect, region["x0"], region["y0"], region["x1"], region["y1"])

    def on_release(event):
        x0, y0, x1, y1 = region["x0"], region["y0"], region["x1"], region["y1"]
        if None in (x0, y0, x1, y1):
            result["value"] = None
        else:
            left = int(min(x0, x1))
            top = int(min(y0, y1))
            width = int(abs(x1 - x0))
            height = int(abs(y1 - y0))
            if width > 0 and height > 0:
                result["value"] = (left, top, width, height)
        root.destroy()

    def on_key(event):
        # ESC untuk batal
        if event.keysym == "Escape":
            result["value"] = None
            root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Key>", on_key)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        result["value"] = None

    return result["value"]