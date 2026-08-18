import cv2
import time
import numpy as np
from PIL import Image
from transformers import pipeline
import serial

# 1. إعداد اتصال الآردوينو
ARDUINO_PORT = 'COM3'
try:
    arduino = serial.Serial(ARDUINO_PORT, 9600, timeout=1)
    time.sleep(2)
    print(f"[+] Connected to Arduino on {ARDUINO_PORT}")
except Exception:
    arduino = None
    print("[-] Simulation Mode (No Arduino)")

# 2. تحميل الموديل
print("Loading AI model...")
classifier = pipeline("image-classification", model="yangy50/garbage-classification")
print("[+] Model loaded successfully!")

cap = cv2.VideoCapture(0)

last_prediction_time = 0
prediction_interval = 1.0  # فحص كل ثانية
current_label = "Waiting for item..."
current_bin = "Place item inside the box"
current_score = 0.0

def send_to_arduino(cmd):
    if arduino:
        arduino.write(cmd.encode())
        print(f"[Hardware] Sent: '{cmd}'")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    
    # تحديد صندوق الكشف في منتصف الكاميرا (ROI)
    box_size = 280
    x1 = int((w - box_size) / 2)
    y1 = int((h - box_size) / 2)
    x2 = x1 + box_size
    y2 = y1 + box_size

    # قص الجزء الموجود داخل الصندوق فقط للفحص
    roi = frame[y1:y2, x1:x2]

    current_time = time.time()

    if current_time - last_prediction_time > prediction_interval:
        # تحويل منطقة الصندوق لـ PIL Image
        rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_roi)

        # حساب تباين الألوان (لو الصندوق سادة/فاضي يتجاهل الفحص)
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray_roi)

        if std_dev > 25:  # تأكيد وجود تفاصيل وجسم حقيقي وليس خلفية سادة
            results = classifier(pil_img)
            top = results[0]
            label = top['label'].lower()
            score = top['score']

            # رفع نسبة التأكد لـ 80% لمنع التخمين الخاطئ
            if score > 0.80:
                current_label = label
                current_score = score

                if "paper" in label or "cardboard" in label:
                    current_bin = "PAPER (A)"
                    send_to_arduino('A')
                elif "plastic" in label:
                    current_bin = "PLASTIC (P)"
                    send_to_arduino('P')
                elif "metal" in label or "can" in label:
                    current_bin = "METAL / CAN (C)"
                    send_to_arduino('C')
                else:
                    current_bin = f"OTHER ({label})"
            else:
                current_label = "Scanning..."
                current_bin = "Hold item still..."
        else:
            current_label = "Box Empty"
            current_bin = "Place item inside"
            current_score = 0.0

        last_prediction_time = current_time

    # ==========================================
    # واجهة الشاشة
    # ==========================================
    # رسم مربع الفحص في المنتصف
    box_color = (0, 255, 0) if current_label not in ["Box Empty", "Scanning..."] else (255, 255, 255)
    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
    cv2.putText(frame, "Put Item Here", (x1 + 10, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

    # شريط المعلومات بالأعلى
    cv2.rectangle(frame, (10, 10), (480, 100), (0, 0, 0), -1)
    cv2.putText(frame, f"Status: {current_label} ({current_score:.1%})", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Bin   : {current_bin}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    cv2.imshow("Smart Waste Sorter", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()