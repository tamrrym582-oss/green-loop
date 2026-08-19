from flask import Flask, render_template_string, request, redirect, url_for
import json
import os
import webbrowser
import threading
from datetime import datetime, date, timedelta

app = Flask(__name__)
DATABASE_FILE = "users_database.json"

# ==========================================
# التعامل مع قاعدة البيانات والستريك
# ==========================================
def load_db():
    if not os.path.exists(DATABASE_FILE):
        initial_db = {
            "250100323": {
                "name": "Reem Tamer",
                "points": 50,
                "streak": 3,
                "last_active": str(date.today()),
                "history": [
                    {"action": "Plastic Sorting", "points": "+10", "time": "2026-08-18 10:30"},
                    {"action": "Water Refill", "points": "+20", "time": "2026-08-19 12:15"}
                ]
            }
        }
        save_db(initial_db)
        return initial_db
    with open(DATABASE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def update_streak(user_data):
    today = date.today()
    last_active_str = user_data.get("last_active")
    
    if not last_active_str:
        user_data["streak"] = 1
    else:
        last_active = datetime.strptime(last_active_str, "%Y-%m-%d").date()
        if today == last_active:
            pass # نفس اليوم، لا يتغير
        elif today == last_active + timedelta(days=1):
            user_data["streak"] = user_data.get("streak", 0) + 1 # يوم متتالي
        else:
            user_data["streak"] = 1 # انقطع الستريك
            
    user_data["last_active"] = str(today)

# ==========================================
# تصميم صفحة الويب المتكاملة (HTML + Bootstrap)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Green Loop | بوابة الاستدامة واللوحة الطلابية</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #E0E0E0; font-family: 'Cairo', sans-serif; padding-bottom: 40px; }
        .navbar { background-color: #1E1E1E; border-bottom: 2px solid #00ADB5; }
        .card { background-color: #1E1E1E; border: 1px solid #2C394B; border-radius: 16px; }
        .pts-badge { background: linear-gradient(135deg, #00ADB5, #4ECCA3); color: #121212; font-weight: 800; border-radius: 10px; padding: 4px 12px; }
        .streak-badge { background: #FF9F43; color: #121212; font-weight: 800; border-radius: 10px; padding: 4px 10px; }
        .btn-custom { background-color: #00ADB5; color: #ffffff; font-weight: 700; border-radius: 10px; }
        .btn-custom:hover { background-color: #4ECCA3; color: #121212; }
    </style>
</head>
<body>

<nav class="navbar navbar-dark mb-4 py-3">
    <div class="container text-center justify-content-center">
        <span class="navbar-brand fs-3 fw-bold text-success">🌿 Green Loop Campus Station</span>
    </div>
</nav>

<div class="container">
    {% if message %}
    <div class="alert alert-{{ msg_type }} alert-dismissible fade show text-center" role="alert">
        {{ message }}
    </div>
    {% endif %}

    <div class="row g-4">
        <!-- الجانب الأيمن: تسجيل الدخول / التسجيل وحساب الطالب -->
        <div class="col-lg-5">
            <!-- كارت تسجيل الدخول أو الطالب الحالي -->
            {% if student %}
            <div class="card p-4 shadow-sm mb-4 border-success">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h4 class="fw-bold text-white mb-0">{{ student.name }}</h4>
                    <span class="streak-badge">🔥 {{ student.streak or 1 }} </span>
                </div>
                <p class="text-secondary mb-3">الرقم الجامعي: {{ current_id }}</p>
                
                <div class="bg-dark p-3 rounded-3 d-flex justify-content-between align-items-center mb-3">
                    <span class="fs-6 text-light">الرصيد الإجمالي:</span>
                    <span class="fs-4 pts-badge">{{ student.points }} PTS</span>
                </div>

                <h6 class="text-warning fw-bold mt-2">📜 آخر العمليات (Activity Log):</h6>
                <div class="table-responsive" style="max-height: 180px; overflow-y: auto;">
                    <table class="table table-dark table-sm table-borderless small mb-0">
                        <tbody>
                            {% for act in student.history[::-1] %}
                            <tr class="border-bottom border-secondary">
                                <td>{{ act.action }}</td>
                                <td class="text-success fw-bold">{{ act.points }}</td>
                                <td class="text-secondary text-end">{{ act.time }}</td>
                            </tr>
                            {% else %}
                            <tr><td colspan="3" class="text-muted text-center">لا توجد عمليات مسجلة بعد</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

                <a href="/" class="btn btn-outline-secondary btn-sm mt-3 w-100">تسجيل الخروج</a>
            </div>
            {% else %}
            <!-- نافذة تسجيل الدخول والتسجيل -->
            <div class="card p-4 shadow-sm mb-4">
                <ul class="nav nav-pills nav-fill mb-3" id="pills-tab" role="tablist">
                    <li class="nav-item"><button class="nav-link active" data-bs-toggle="pill" data-bs-target="#login-tab">تسجيل الدخول</button></li>
                    <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#register-tab">طالب جديد</button></li>
                </ul>
                <div class="tab-content">
                    <!-- Login Form -->
                    <div class="tab-pane fade show active" id="login-tab">
                        <form method="POST" action="/login">
                            <div class="mb-3">
                                <label class="form-label text-secondary">الرقم الجامعي (ID):</label>
                                <input type="text" name="student_id" class="form-control bg-dark text-white border-secondary" placeholder="مثال: 250100323" required>
                            </div>
                            <button type="submit" class="btn btn-custom w-100">دخول</button>
                        </form>
                    </div>
                    <!-- Register Form -->
                    <div class="tab-pane fade" id="register-tab">
                        <form method="POST" action="/register">
                            <div class="mb-3">
                                <label class="form-label text-secondary">اسم الطالب بالكامل:</label>
                                <input type="text" name="name" class="form-control bg-dark text-white border-secondary" placeholder="مثال: فارس محمد" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-secondary">الرقم الجامعي (ID):</label>
                                <input type="text" name="student_id" class="form-control bg-dark text-white border-secondary" placeholder="مثال: 250100324" required>
                            </div>
                            <button type="submit" class="btn btn-custom w-100">إنشاء حساب جديد</button>
                        </form>
                    </div>
                </div>
            </div>
            {% endif %}

            <!-- جدول احتساب المكافآت -->
            <div class="card p-4 shadow-sm">
                <h5 class="fw-bold text-warning mb-3">🎁 جدول احتساب النقاط</h5>
                <ul class="list-group list-group-flush bg-transparent">
                    <li class="list-group-item bg-transparent text-light d-flex justify-content-between">
                        <span>إعادة ملء زجاجة مياه (Refill)</span>
                        <span class="text-info fw-bold">+20 نقطة (مضاعفة)</span>
                    </li>
                    <li class="list-group-item bg-transparent text-light d-flex justify-content-between">
                        <span>علبة معدنية (Can)</span>
                        <span class="text-success fw-bold">+15 نقطة</span>
                    </li>
                    <li class="list-group-item bg-transparent text-light d-flex justify-content-between">
                        <span>زجاجة بلاستيك (Plastic)</span>
                        <span class="text-success fw-bold">+10 نقاط</span>
                    </li>
                    <li class="list-group-item bg-transparent text-light d-flex justify-content-between">
                        <span>مخلفات ورقية (Paper)</span>
                        <span class="text-success fw-bold">+5 نقاط</span>
                    </li>
                </ul>
            </div>
        </div>

        <!-- الجانب الأيسر: لوحة الشرف (Leaderboard) -->
        <div class="col-lg-7">
            <div class="card p-4 shadow-sm">
                <h4 class="fw-bold mb-3 text-warning">🏆 لوحة الشرف لأبطال الاستدامة (Leaderboard)</h4>
                <div class="table-responsive">
                    <table class="table table-dark table-hover align-middle mb-0">
                        <thead>
                            <tr class="text-secondary border-secondary">
                                <th>#</th>
                                <th>اسم الطالب</th>
                                <th>الرقم الجامعي</th>
                                <th>الستريك</th>
                                <th class="text-center">إجمالي النقاط</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in leaderboard %}
                            <tr>
                                <td class="fw-bold">
                                    {% if loop.index == 1 %}🥇{% elif loop.index == 2 %}🥈{% elif loop.index == 3 %}🥉{% else %}{{ loop.index }}{% endif %}
                                </td>
                                <td class="fw-bold text-white">{{ user.name }}</td>
                                <td class="text-muted">{{ user.id }}</td>
                                <td><span class="badge bg-secondary">🔥 {{ user.streak }} يوم</span></td>
                                <td class="text-center"><span class="pts-badge">{{ user.points }} PTS</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ==========================================
# المسارات والـ Endpoints
# ==========================================
@app.route("/")
def index():
    db = load_db()
    student_id = request.args.get("logged_id", "")
    message = request.args.get("msg", "")
    msg_type = request.args.get("type", "info")

    student = db.get(student_id)

    # تجهيز لوحة الشرف
    leaderboard = []
    for uid, info in db.items():
        leaderboard.append({
            "id": uid,
            "name": info.get("name", "Unknown"),
            "points": info.get("points", 0),
            "streak": info.get("streak", 1)
        })
    leaderboard.sort(key=lambda x: x["points"], reverse=True)

    return render_template_string(
        HTML_TEMPLATE,
        student=student,
        current_id=student_id,
        leaderboard=leaderboard,
        message=message,
        msg_type=msg_type
    )

@app.route("/login", methods=["POST"])
def login():
    student_id = request.form.get("student_id", "").strip()
    db = load_db()
    if student_id in db:
        update_streak(db[student_id])
        save_db(db)
        return redirect(url_for("index", logged_id=student_id, msg="مرحباً بعودتك!", type="success"))
    return redirect(url_for("index", msg="الرقم الجامعي غير مسجل، يرجى التسجيل أولاً.", type="danger"))

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    student_id = request.form.get("student_id", "").strip()
    db = load_db()

    if not student_id or not name:
        return redirect(url_for("index", msg="يرجى إدخال جميع البيانات المطلوبة.", type="warning"))

    if student_id in db:
        return redirect(url_for("index", msg="هذا الرقم الجامعي مسجل بالفعل!", type="danger"))

    db[student_id] = {
        "name": name,
        "points": 0,
        "streak": 1,
        "last_active": str(date.today()),
        "history": [
            {"action": "Account Created", "points": "+0", "time": datetime.now().strftime("%Y-%m-%d %H:%M")}
        ]
    }
    save_db(db)
    return redirect(url_for("index", logged_id=student_id, msg="تم إنشاء الحساب بنجاح!", type="success"))

# دالة الفتح التلقائي في المتصفح
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1.2, open_browser).start()
    app.run(debug=True, port=5000, use_reloader=False)