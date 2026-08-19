import tkinter as tk
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
import time
import json
import os
from datetime import datetime
from transformers import pipeline

# ==========================================
# 1. إعدادات المظهر والواجهة
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

DATABASE_FILE = "users_database.json"

# جدول النقاط الأساسية للفرز ومكافأة إعادة الملء
POINTS_MAP = {
    "paper": 5,
    "cardboard": 5,
    "plastic": 10,
    "metal": 15,
    "can": 15
}
REFILL_REWARD = 20  # مكافأة مضاعفة لتشجيع إعادة ملء المياه الشخصية

# ==========================================
# 2. إدارة قاعدة البيانات والنقاط
# ==========================================
class DatabaseManager:
    def __init__(self):
        if not os.path.exists(DATABASE_FILE):
            data = {
                "250100323": {"name": "Reem Tamer", "points": 50},
                "1002": {"name": "Ahmed Mohamed", "points": 15}
            }
            with open(DATABASE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    def get_user(self, user_id):
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
        return db.get(user_id)

    def update_points(self, user_id, delta):
        with open(DATABASE_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
        if user_id in db:
            db[user_id]["points"] += delta
            with open(DATABASE_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=4, ensure_ascii=False)
            return db[user_id]["points"]
        return None

# ==========================================
# 3. التطبيق الرئيسي (CustomTkinter)
# ==========================================
class SmartBinApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Smart Recycling & Refill Station")
        self.geometry("1100x680")
        self.resizable(False, False)

        self.db = DatabaseManager()
        self.current_user_id = "250100323"  # حساب المستخدم الحالي
        self.current_user = self.db.get_user(self.current_user_id)

        # تهيئة موديل الذكاء الاصطناعي
        self.classifier = None
        self.is_scanning = False
        self.last_detection_text = "Place item inside the box"
        self.last_confidence = 0.0

        self._build_ui()
        self._load_model_threaded()

        # تشغيل الكاميرا
        self.cap = cv2.VideoCapture(0)
        self.last_ai_time = 0
        self.update_camera_feed()

    def _build_ui(self):
        # شبكة التقسيم الرئيسية (عمودين)
        self.grid_columnconfigure(0, weight=3) # عمود الكاميرا (يسار)
        self.grid_columnconfigure(1, weight=2) # عمود لوحة التحكم (يمين)
        self.grid_rowconfigure(0, weight=1)

        # --- الجانب الأيسر: عرض الكاميرا ---
        self.left_frame = ctk.CTkFrame(self, corner_radius=15)
        self.left_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        self.title_label = ctk.CTkLabel(self.left_frame, text="Waste Scanner (Live Feed)", font=("Arial", 20, "bold"))
        self.title_label.pack(pady=10)

        self.camera_label = ctk.CTkLabel(self.left_frame, text="")
        self.camera_label.pack(expand=True, fill="both", padx=10, pady=5)

        self.status_bar = ctk.CTkLabel(self.left_frame, text="AI Model: Initializing...", font=("Arial", 14), text_color="#A0A0A0")
        self.status_bar.pack(pady=8)

        # --- الجانب الأيمن: لوحة المستخدم والنقاط ---
        self.right_frame = ctk.CTkFrame(self, corner_radius=15)
        self.right_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        # بيانات الطالب
        self.user_card = ctk.CTkFrame(self.right_frame, fg_color="#2B2B2B", corner_radius=12)
        self.user_card.pack(fill="x", padx=15, pady=15)

        self.user_name_lbl = ctk.CTkLabel(self.user_card, text=f"Student: {self.current_user['name']}", font=("Arial", 18, "bold"))
        self.user_name_lbl.pack(pady=(10, 2))

        self.user_id_lbl = ctk.CTkLabel(self.user_card, text=f"ID: {self.current_user_id}", font=("Arial", 13), text_color="#888888")
        self.user_id_lbl.pack(pady=(0, 10))

        # بطاقة الرصيد
        self.points_card = ctk.CTkFrame(self.right_frame, fg_color="#1E3A2F", corner_radius=12)
        self.points_card.pack(fill="x", padx=15, pady=10)

        self.pts_title = ctk.CTkLabel(self.points_card, text="YOUR BALANCE", font=("Arial", 13, "bold"), text_color="#4ECCA3")
        self.pts_title.pack(pady=(12, 0))

        self.points_display = ctk.CTkLabel(self.points_card, text=f"{self.current_user['points']} PTS", font=("Arial", 36, "bold"), text_color="#4ECCA3")
        self.points_display.pack(pady=(0, 12))

        # بطاقة نتيجة الفرز الفوري
        self.detection_card = ctk.CTkFrame(self.right_frame, fg_color="#2B2B2B", corner_radius=12)
        self.detection_card.pack(fill="x", padx=15, pady=10)

        self.det_title = ctk.CTkLabel(self.detection_card, text="DETECTED ITEM", font=("Arial", 12, "bold"), text_color="#AAAAAA")
        self.det_title.pack(pady=(8, 0))

        self.detection_lbl = ctk.CTkLabel(self.detection_card, text=self.last_detection_text, font=("Arial", 16, "bold"))
        self.detection_lbl.pack(pady=(2, 8))

        # زر إعادة ملء المياه (مكافأة مضاعفة النقاط)
        self.refill_btn = ctk.CTkButton(
            self.right_frame, 
            text=f"Refill Bottle (+{REFILL_REWARD} Double Pts)", 
            font=("Arial", 16, "bold"),
            height=50,
            fg_color="#00ADB5",
            hover_color="#007B80",
            command=self.handle_water_refill
        )
        self.refill_btn.pack(fill="x", padx=15, pady=(20, 10))

        # رسائل التنبيه والعمليات
        self.alert_lbl = ctk.CTkLabel(self.right_frame, text="", font=("Arial", 13, "bold"))
        self.alert_lbl.pack(pady=5)

    def _load_model_threaded(self):
        def load():
            self.classifier = pipeline("image-classification", model="yangy50/garbage-classification")
            self.status_bar.configure(text="AI Model: Ready", text_color="#4ECCA3")
        threading.Thread(target=load, daemon=True).start()

    def update_camera_feed(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1) # وضع مرآة لسهولة التجربة
            h, w, _ = frame.shape

            # مربع الفحص في المنتصف
            box_size = 260
            x1 = int((w - box_size) / 2)
            y1 = int((h - box_size) / 2)
            x2, y2 = x1 + box_size, y1 + box_size

            roi = frame[y1:y2, x1:x2]

            # فحص الـ AI كل 1.5 ثانية
            now = time.time()
            if self.classifier and not self.is_scanning and (now - self.last_ai_time > 1.5):
                self.last_ai_time = now
                threading.Thread(target=self._run_inference, args=(roi.copy(),), daemon=True).start()

            cv2.rectangle(frame, (x1, y1), (x2, y2), (78, 204, 163), 2)
            cv2.putText(frame, "Scan Box", (x1 + 10, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (78, 204, 163), 2)

            # تحويل الإطار إلى واجهة Tkinter
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image).resize((580, 435))
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.configure(image=imgtk)

        self.after(20, self.update_camera_feed)

    def _run_inference(self, roi_img):
        self.is_scanning = True
        try:
            gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            if gray.std() > 25: # تأكيد وجود جسم داخل الصندوق
                pil_img = Image.fromarray(cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB))
                preds = self.classifier(pil_img)
                top = preds[0]
                label, score = top['label'].lower(), top['score']

                if score > 0.70:
                    matched_key = next((k for k in POINTS_MAP if k in label), None)
                    if matched_key:
                        earned = POINTS_MAP[matched_key]
                        self.detection_lbl.configure(text=f"{label.upper()} (+{earned} Pts)", text_color="#4ECCA3")
                        new_balance = self.db.update_points(self.current_user_id, earned)
                        self.points_display.configure(text=f"{new_balance} PTS")
                        self.show_alert(f"+{earned} Points Added for {matched_key.upper()}!", "#4ECCA3")
                        time.sleep(2.5) # مهلة قبل الفحص التالي
                else:
                    self.detection_lbl.configure(text="Scanning...", text_color="#AAAAAA")
            else:
                self.detection_lbl.configure(text="Place item inside box", text_color="#AAAAAA")
        finally:
            self.is_scanning = False

    def handle_water_refill(self):
        # إضافة النقاط المضاعفة بدلاً من الخصم
        new_bal = self.db.update_points(self.current_user_id, REFILL_REWARD)
        self.points_display.configure(text=f"{new_bal} PTS")
        self.show_alert(f"+{REFILL_REWARD} Eco-Reward Points Added for Refill!", "#00ADB5")

    def show_alert(self, msg, color):
        self.alert_lbl.configure(text=msg, text_color=color)
        self.after(3500, lambda: self.alert_lbl.configure(text=""))

    def on_closing(self):
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = SmartBinApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()