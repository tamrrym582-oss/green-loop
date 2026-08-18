from transformers import pipeline
from PIL import Image

# 1. تحميل الموديل المتخصص في النفايات (أول مرة هياخد ثواني يحمل)
print("Loading model... please wait")
classifier = pipeline("image-classification", model="yangy50/garbage-classification")

# 2. تحديد الصورة وفحصها
image_name = "test.jpg"  # اتأكدي إن صورة الورقة موجودة بنفس الاسم ده جنب الكود

img = Image.open(image_name)
results = classifier(img)

# 3. عرض النتيجة
top_result = results[0]
label = top_result['label'].lower()
score = top_result['score']

print("\n" + "="*35)
print(f"Result     : {label}")
print(f"Confidence : {score:.1%}")

if "paper" in label or "cardboard" in label:
    print(">> Target Bin : [ PAPER / 📄ورق ]")
    print(">> Arduino    : Send 'A'")
elif "plastic" in label:
    print(">> Target Bin : [ PLASTIC / 🍶بلاستيك ]")
    print(">> Arduino    : Send 'P'")
elif "metal" in label or "can" in label:
    print(">> Target Bin : [ METAL /🥫 كانز ]")
    print(">> Arduino    : Send 'C'")
else:
    print(f">> Other Item: {label}")
print("="*35)