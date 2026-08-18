from ultralytics import YOLO
import cv2

# 1. تحميل الموديل الجاهز مباشرة (سيحمله تلقائياً في ثانيتين أول مرة فقط)
model = YOLO('yolov8n.pt')

# 2. فئات الفرز المستهدفة في الماكينة
def process_detection(image_path):
    # تشغيل الفحص على الصورة
    results = model(image_path)
    
    found_item = False
    
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            confidence = float(box.conf[0])
            
            # فلترة الكائنات الخاصة بمشروعك
            if confidence > 0.45:
                print("\n" + "="*40)
                print(f"تم التعرف على: {class_name} (نسبة التأكد: {confidence:.1%})")
                
                if class_name in ['bottle']:
                    print(">> السلة: بلاستيك (Plastic)")
                    print(">> إشارة الآردوينو: 'P'")
                    found_item = True
                elif class_name in ['cup']:
                    print(">> السلة: كانز أو أكواب (Can / Cup)")
                    print(">> إشارة الآردوينو: 'C'")
                    found_item = True
                elif class_name in ['book', 'paper']:
                    print(">> السلة: ورق (Paper)")
                    print(">> إشارة الآردوينو: 'A'")
                    found_item = True
                print("="*40)
                
    if not found_item:
        print("\nلم يتم التعرف على جسم مصنف، جربي تقريب الزجاجة أو الكان أكثر من الكاميرا.")

if __name__ == '__main__':
    # ضعي صورة كان أو زجاجة باسم test.jpg في نفس الفولدر
    process_detection('test.jpg')