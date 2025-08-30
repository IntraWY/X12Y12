# -*- coding: utf-8 -*-
# pip install opencv-python mss pillow pyperclip
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2, mss, numpy as np, pyperclip, json, os
from PIL import Image, ImageTk

class ROIApp:
    def __init__(self, root):
        self.root = root
        root.title("ROI to PAD - X1 X2 Y1 Y2")
        self.img_bgr = None
        self.img_path = None
        self.monitors = []
        self.roi = None

        # Top controls
        top = tk.Frame(root, pady=6, padx=6)
        top.pack(fill="x")

        tk.Button(top, text="เปิดรูปภาพ", command=self.open_image).pack(side="left")
        tk.Button(top, text="สกรีนช็อต", command=self.capture_monitor).pack(side="left", padx=4)
        tk.Label(top, text="เลือกจอ:").pack(side="left", padx=(12,2))
        self.monitor_var = tk.IntVar(value=1)
        self.monitor_menu = tk.OptionMenu(top, self.monitor_var, 1)
        self.monitor_menu.pack(side="left")
        tk.Button(top, text="อัปเดตรายชื่อจอ", command=self.refresh_monitors).pack(side="left", padx=4)
        tk.Button(top, text="ลากกรอบ ROI", command=self.select_roi).pack(side="left", padx=(12,0))
        tk.Button(top, text="Reset", command=self.reset).pack(side="left", padx=(12,0))

        # Preview
        self.preview = tk.Label(root)
        self.preview.pack(padx=6, pady=6)

        # Output fields
        out = tk.Frame(root, pady=6, padx=6)
        out.pack(fill="x")
        self.x1 = tk.StringVar(); self.x2 = tk.StringVar()
        self.y1 = tk.StringVar(); self.y2 = tk.StringVar()
        for lbl, var in [("X1", self.x1), ("X2", self.x2), ("Y1", self.y1), ("Y2", self.y2)]:
            tk.Label(out, text=lbl).pack(side="left")
            tk.Entry(out, textvariable=var, width=8, state="readonly", justify="center").pack(side="left", padx=(2,10))

        tk.Button(out, text="คัดลอกเป็น CSV", command=self.copy_csv).pack(side="left")
        tk.Button(out, text="บันทึก JSON", command=self.save_json).pack(side="left", padx=4)

        self.refresh_monitors()

    # --- Core actions ---
    def open_image(self):
        path = filedialog.askopenfilename(title="เลือกไฟล์รูป", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.bmp")])
        if not path: return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("ผิดพลาด", "เปิดไฟล์ไม่ได้")
            return
        self.img_bgr = img
        self.img_path = path
        self.roi = None
        self.update_preview(img)

    def capture_monitor(self):
        if not self.monitors:
            self.refresh_monitors()
        idx = max(1, min(self.monitor_var.get(), len(self.monitors)-1))
        with mss.mss() as sct:
            mon = self.monitors[idx]
            shot = sct.grab(mon)
            img = np.array(shot)[:, :, :3]
        self.img_bgr = img
        self.img_path = None
        self.roi = None
        self.update_preview(img)

    def select_roi(self):
        if self.img_bgr is None:
            messagebox.showwarning("ยังไม่มีภาพ", "เปิดรูปหรือสกรีนช็อตก่อน")
            return
        img = self.img_bgr.copy()
        r = cv2.selectROI("ลากกรอบแล้วกด ENTER", img, showCrosshair=True)
        cv2.destroyAllWindows()
        x, y, w, h = map(int, r)
        if w == 0 or h == 0: return
        X1, Y1 = x, y
        X2, Y2 = x + w, y + h
        X1, X2 = sorted([X1, X2])
        Y1, Y2 = sorted([Y1, Y2])
        self.roi = (X1, X2, Y1, Y2)
        self.x1.set(str(X1)); self.x2.set(str(X2))
        self.y1.set(str(Y1)); self.y2.set(str(Y2))

    def reset(self):
        self.img_bgr = None
        self.img_path = None
        self.roi = None
        self.x1.set(""); self.x2.set(""); self.y1.set(""); self.y2.set("")
        self.preview.configure(image="", text="(ไม่มีภาพ)")
        self.preview.image = None

    def copy_csv(self):
        if not self.roi:
            messagebox.showwarning("ยังไม่มี ROI", "ลากกรอบก่อน")
            return
        csv = "{},{},{},{}".format(*self.roi)
        pyperclip.copy(csv)
        messagebox.showinfo("คัดลอกแล้ว", f"คัดลอก: {csv}")

    def save_json(self):
        if not self.roi:
            messagebox.showwarning("ยังไม่มี ROI", "ลากกรอบก่อน")
            return
        default_name = "roi_output.json"
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=default_name,
                                            filetypes=[("JSON","*.json")])
        if not path: return
        data = {"source": self.img_path or "screenshot", "X1": self.roi[0], "X2": self.roi[1],
                "Y1": self.roi[2], "Y2": self.roi[3]}
        if os.path.exists(path):
            try:
                old = json.load(open(path,"r",encoding="utf-8"))
            except Exception:
                old = {}
        else:
            old = {}
        key = os.path.basename(self.img_path) if self.img_path else "screenshot"
        old[key] = data
        json.dump(old, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        messagebox.showinfo("บันทึกแล้ว", f"เซฟ {path}")

    # --- Helpers ---
    def update_preview(self, bgr):
        h, w = bgr.shape[:2]
        scale = min(900 / max(w,1), 600 / max(h,1), 1.0)
        disp = cv2.resize(bgr, (int(w*scale), int(h*scale)))
        rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        imgtk = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.preview.configure(image=imgtk, text="")
        self.preview.image = imgtk

    def refresh_monitors(self):
        with mss.mss() as sct:
            self.monitors = sct.monitors
        menu = self.monitor_menu["menu"]
        menu.delete(0, "end")
        for i in range(1, len(self.monitors)):
            menu.add_command(label=str(i), command=lambda v=i: self.monitor_var.set(v))
        if len(self.monitors) > 1:
            self.monitor_var.set(1)

if __name__ == "__main__":
    root = tk.Tk()
    ROIApp(root)
    root.mainloop()
