from flask import Flask, jsonify, render_template, request, send_file, session, redirect
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os, random, string
from dotenv import load_dotenv
from utils.pdf_generator import generate_report_pdf

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ministry-secret-2026")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["student_reports"]

teachers_col = db["teachers"]
students_col = db["students"]
marks_col    = db["marks"]
parents_col  = db["parents"]
schools_col  = db["schools"]

# ── Seed only schools & teachers ─────────────────────────────────────────────
def seed_data():
    if teachers_col.count_documents({}) > 0:
        return

    schools_col.insert_many([
        {"school_id": "SCH001", "name": "Gweru Primary School",  "type": "Primary"},
        {"school_id": "SCH002", "name": "Midlands High School",   "type": "Secondary"},
        {"school_id": "SCH003", "name": "Mkoba Primary School",   "type": "Primary"},
        {"school_id": "SCH004", "name": "Senga Primary School",   "type": "Primary"},
    ])

    teachers_col.insert_many([
        {"teacher_id": "TCH001", "name": "Mr. Moyo",      "password": "teacher123", "school_id": "SCH001", "school_name": "Gweru Primary School",  "subject": "Mathematics", "class": "Grade 5"},
        {"teacher_id": "TCH002", "name": "Mrs. Ncube",    "password": "teacher123", "school_id": "SCH001", "school_name": "Gweru Primary School",  "subject": "English",     "class": "Grade 5"},
        {"teacher_id": "TCH003", "name": "Mr. Dube",      "password": "teacher123", "school_id": "SCH002", "school_name": "Midlands High School",  "subject": "Science",     "class": "Form 2"},
        {"teacher_id": "TCH004", "name": "Ms. Chigumira", "password": "teacher123", "school_id": "SCH002", "school_name": "Midlands High School",  "subject": "History",     "class": "Form 2"},
    ])

with app.app_context():
    seed_data()

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_grade(mark):
    if mark >= 80: return "A"
    if mark >= 70: return "B"
    if mark >= 60: return "C"
    if mark >= 50: return "D"
    return "F"

def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc

def generate_parent_code():
    while True:
        digits = ''.join(random.choices(string.digits, k=4))
        code   = f"PAR+{digits}"
        if not parents_col.find_one({"parent_code": code}):
            return code

def generate_student_id():
    count = students_col.count_documents({}) + 1
    return f"STU{count:04d}"

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    role     = request.form.get("role", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if role == "teacher":
        teacher = teachers_col.find_one({"teacher_id": username, "password": password})
        if teacher:
            school = schools_col.find_one({"school_id": teacher["school_id"]})
            session["role"]        = "teacher"
            session["teacher_id"]  = teacher["teacher_id"]
            session["name"]        = teacher["name"]
            session["school_id"]   = teacher["school_id"]
            session["school_name"] = teacher.get("school_name", school["name"] if school else "Unknown School")
            session["subject"]     = teacher["subject"]
            session["class"]       = teacher["class"]
            return redirect("/teacher")
        return render_template("login.html", error="Invalid Teacher ID or password.", role=role)

    elif role == "parent":
        parent = parents_col.find_one({"parent_code": username})
        if parent:
            session["role"]        = "parent"
            session["parent_code"] = username
            session["student_id"]  = parent["student_id"]
            session["name"]        = parent.get("guardian_name", parent.get("name", "Parent"))
            return redirect("/parent")
        return render_template("login.html", error="Invalid parent code. Please check with your child's teacher.", role=role)

    elif role == "ministry":
        if username == "admin" and password == "ministry2026":
            session["role"] = "ministry"
            session["name"] = "Ministry Admin"
            return redirect("/ministry")
        return render_template("login.html", error="Invalid ministry credentials.", role=role)

    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ── Teacher Portal ────────────────────────────────────────────────────────────
@app.route("/teacher")
def teacher_portal():
    if session.get("role") != "teacher":
        return redirect("/")
    students = list(students_col.find({"school_id": session["school_id"], "class": session["class"]}))
    students = [serialize(s) for s in students]
    return render_template("teacher.html", students=students, session=session)

@app.route("/api/enroll-student", methods=["POST"])
def enroll_student():
    if session.get("role") != "teacher":
        return jsonify({"error": "Unauthorized"}), 401

    data          = request.json
    student_name  = data.get("student_name", "").strip()
    guardian_name = data.get("guardian_name", "").strip()

    if not student_name or not guardian_name:
        return jsonify({"error": "Both student name and guardian name are required."}), 400

    existing = students_col.find_one({
        "name":      student_name,
        "school_id": session["school_id"],
        "class":     session["class"]
    })
    if existing:
        return jsonify({"error": f"A student named '{student_name}' is already enrolled in this class."}), 400

    student_id  = generate_student_id()
    parent_code = generate_parent_code()

    students_col.insert_one({
        "student_id":   student_id,
        "name":         student_name,
        "school_id":    session["school_id"],
        "school_name":  session["school_name"],
        "class":        session["class"],
        "parent_code":  parent_code,
        "enrolled_by":  session["teacher_id"],
        "enrolled_at":  datetime.utcnow().isoformat()
    })

    parents_col.insert_one({
        "parent_code":   parent_code,
        "guardian_name": guardian_name,
        "student_id":    student_id,
        "student_name":  student_name,
        "school_id":     session["school_id"],
        "created_at":    datetime.utcnow().isoformat()
    })

    return jsonify({
        "status":        "success",
        "student_id":    student_id,
        "student_name":  student_name,
        "parent_code":   parent_code,
        "guardian_name": guardian_name
    })

@app.route("/api/submit-marks", methods=["POST"])
def submit_marks():
    if session.get("role") != "teacher":
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    for entry in data["marks"]:
        marks_col.update_one(
            {
                "student_id": entry["student_id"],
                "subject":    session["subject"],
                "term":       data["term"],
                "year":       data["year"]
            },
            {"$set": {
                "mark":            int(entry["mark"]),
                "teacher_comment": entry.get("comment", ""),
                "school_id":       session["school_id"],
                "submitted_at":    datetime.utcnow().isoformat()
            }},
            upsert=True
        )
    return jsonify({"status": "success", "message": "Marks submitted successfully!"})

@app.route("/api/class-marks")
def get_class_marks():
    if session.get("role") != "teacher":
        return jsonify({"error": "Unauthorized"}), 401
    term     = request.args.get("term", "Term 1")
    year     = int(request.args.get("year", 2026))
    students = list(students_col.find({"school_id": session["school_id"], "class": session["class"]}))
    result   = []
    for s in students:
        mark_doc = marks_col.find_one({
            "student_id": s["student_id"],
            "subject":    session["subject"],
            "term":       term,
            "year":       year
        })
        result.append({
            "student_id": s["student_id"],
            "name":       s["name"],
            "mark":       mark_doc["mark"] if mark_doc else "",
            "comment":    mark_doc.get("teacher_comment", "") if mark_doc else ""
        })
    return jsonify(result)

# ── Parent Portal ─────────────────────────────────────────────────────────────
@app.route("/parent")
def parent_portal():
    if session.get("role") != "parent":
        return redirect("/")
    student = students_col.find_one({"student_id": session["student_id"]})
    school  = schools_col.find_one({"school_id": student["school_id"]})
    return render_template("parent.html", student=student, school=school, session=session)

@app.route("/api/student-report")
def get_student_report():
    if session.get("role") != "parent":
        return jsonify({"error": "Unauthorized"}), 401
    term  = request.args.get("term", "Term 1")
    year  = int(request.args.get("year", 2026))
    marks = list(marks_col.find({"student_id": session["student_id"], "term": term, "year": year}))
    result = []
    total  = 0
    for m in marks:
        grade = get_grade(m["mark"])
        result.append({"subject": m["subject"], "mark": m["mark"], "grade": grade, "comment": m.get("teacher_comment", "")})
        total += m["mark"]
    average = round(total / len(marks), 1) if marks else 0
    return jsonify({"marks": result, "average": average, "total_subjects": len(marks)})

@app.route("/api/download-report")
def download_report():
    if session.get("role") != "parent":
        return jsonify({"error": "Unauthorized"}), 401
    term       = request.args.get("term", "Term 1")
    year       = int(request.args.get("year", 2026))
    student    = students_col.find_one({"student_id": session["student_id"]})
    school     = schools_col.find_one({"school_id": student["school_id"]})
    marks      = list(marks_col.find({"student_id": session["student_id"], "term": term, "year": year}))
    marks_data = []
    total      = 0
    for m in marks:
        marks_data.append({"subject": m["subject"], "mark": m["mark"], "grade": get_grade(m["mark"]), "comment": m.get("teacher_comment", "")})
        total += m["mark"]
    average    = round(total / len(marks), 1) if marks else 0
    pdf_buffer = generate_report_pdf(student, school, marks_data, term, year, average)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Report_{student['name'].replace(' ','_')}_{term}_{year}.pdf",
        mimetype="application/pdf"
    )

# ── Ministry Dashboard ────────────────────────────────────────────────────────
@app.route("/ministry")
def ministry_portal():
    if session.get("role") != "ministry":
        return redirect("/")
    return render_template("ministry.html", session=session)

@app.route("/api/ministry/overview")
def ministry_overview():
    if session.get("role") != "ministry":
        return jsonify({"error": "Unauthorized"}), 401
    all_marks = list(marks_col.find())
    avg_mark  = round(sum(m["mark"] for m in all_marks) / len(all_marks), 1) if all_marks else 0
    return jsonify({
        "total_students": students_col.count_documents({}),
        "total_schools":  schools_col.count_documents({}),
        "total_teachers": teachers_col.count_documents({}),
        "avg_mark":       avg_mark
    })

@app.route("/api/ministry/school-performance")
def school_performance():
    if session.get("role") != "ministry":
        return jsonify({"error": "Unauthorized"}), 401
    schools = list(schools_col.find())
    result  = []
    for school in schools:
        marks = list(marks_col.find({"school_id": school["school_id"]}))
        avg   = round(sum(m["mark"] for m in marks) / len(marks), 1) if marks else 0
        result.append({"school": school["name"], "average": avg})
    return jsonify(result)

@app.route("/api/ministry/grade-distribution")
def grade_distribution():
    if session.get("role") != "ministry":
        return jsonify({"error": "Unauthorized"}), 401
    marks = list(marks_col.find())
    dist  = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for m in marks:
        dist[get_grade(m["mark"])] += 1
    return jsonify(dist)

@app.route("/api/ministry/subject-performance")
def subject_performance():
    if session.get("role") != "ministry":
        return jsonify({"error": "Unauthorized"}), 401
    pipeline = [
        {"$group": {"_id": "$subject", "avg": {"$avg": "$mark"}}},
        {"$sort": {"avg": -1}}
    ]
    result = list(marks_col.aggregate(pipeline))
    return jsonify([{"subject": r["_id"], "average": round(r["avg"], 1)} for r in result])

@app.route("/api/ministry/recent-enrollments")
def recent_enrollments():
    if session.get("role") != "ministry":
        return jsonify({"error": "Unauthorized"}), 401
    students = list(students_col.find({}, sort=[("enrolled_at", -1)], limit=10))
    return jsonify([{
        "name":        s["name"],
        "school_name": s.get("school_name", ""),
        "class":       s["class"],
        "enrolled_at": s.get("enrolled_at", ""),
        "student_id":  s["student_id"]
    } for s in students])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
