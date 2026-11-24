import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

import database
from ai_engine import analyze_email_with_ai

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cyberaware-secret-2026")

database.init_db()

# 4 realistic email scenarios for 1-click demo during presentation
SAMPLE_EMAILS = [
    {
        "id": "ms_password",
        "title": "Microsoft 365: Password Expiry",
        "category": "Credential Phishing",
        "subject": "ACTION REQUIRED: Your Microsoft 365 password expires today",
        "content": (
            "Dear Employee,\n\n"
            "Your Microsoft 365 password is set to expire in 2 hours. "
            "To avoid losing access to your emails and files, please verify your credentials immediately.\n\n"
            "CLICK HERE TO VERIFY: http://login-microsoft365-verify.com/auth\n\n"
            "Failure to update will result in immediate account suspension.\n\n"
            "— IT Security Team"
        )
    },
    {
        "id": "ceo_wire",
        "title": "CEO: Urgent Wire Transfer",
        "category": "Business Email Compromise",
        "subject": "Quick request — in a meeting, need your help",
        "content": (
            "Hi,\n\n"
            "I'm stuck in a board meeting and can't talk. I need you to urgently process "
            "a wire transfer of $14,850 to a vendor before end of day. "
            "Please confirm you're available and I'll send the details.\n\n"
            "Keep this between us until the deal is announced tomorrow.\n\n"
            "Thanks"
        )
    },
    {
        "id": "hr_payroll",
        "title": "HR: Payroll Account Update",
        "category": "Financial Phishing",
        "subject": "Important: Update your direct deposit details for this month's salary",
        "content": (
            "Dear Team Member,\n\n"
            "HR is updating payroll records this month. "
            "To ensure your salary is deposited correctly, please re-verify your bank account details "
            "by clicking the link below before 5 PM today.\n\n"
            "Update here: http://payroll-portal-company.net/verify\n\n"
            "Missing the deadline may delay your salary by 2 weeks.\n\n"
            "— Human Resources Department"
        )
    },
    {
        "id": "safe_email",
        "title": "Normal: Team Meeting Invite",
        "category": "Legitimate Email",
        "subject": "Team All-Hands Meeting — Thursday 3 PM",
        "content": (
            "Hi everyone,\n\n"
            "Just a reminder about our quarterly all-hands meeting this Thursday at 3 PM in Conference Room B.\n\n"
            "We'll cover project updates, upcoming goals, and open Q&A.\n\n"
            "No action needed — just show up! See you there.\n\n"
            "— Team Coordinator"
        )
    }
]


@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    dashboard_data_text = ""

    if request.method == "POST":
        employee_name = request.form.get("employee", "Employee")
        employee_email = request.form.get("email_id", "employee@company.local")
        email_text = request.form.get("email", "")
        email_subject = request.form.get("subject", "Suspicious Email")

        if email_text:
            analysis = analyze_email_with_ai(email_text, employee_name, employee_email)
            analysis["employee_name"] = employee_name
            analysis["employee_email"] = employee_email
            analysis["email_subject"] = email_subject
            analysis["email_text"] = email_text
            scan_id = database.save_email_scan(analysis)
            analysis["scan_id"] = scan_id
            result = analysis

    metrics = database.get_dashboard_metrics()
    employees = database.get_all_employees()

    for emp in employees:
        status = emp["simulation_status"]
        if status == "Clicked":
            dashboard_data_text += f"{emp['name']} | Clicked Phishing Link | Training Required\n"
        elif status == "Trained":
            dashboard_data_text += f"{emp['name']} | Completed Training | Safe\n"
        else:
            dashboard_data_text += f"{emp['name']} | No Interaction | Safe\n"

    return render_template(
        "index.html",
        result=result,
        dashboard_data=dashboard_data_text,
        metrics=metrics,
        employees=employees,
        sample_emails=SAMPLE_EMAILS
    )


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json() or {}
    employee_name = data.get("employee", "Employee")
    employee_email = data.get("email_id", "")
    email_text = data.get("email", "")
    email_subject = data.get("subject", "Email Analysis")

    if not email_text.strip():
        return jsonify({"error": "Email content is required."}), 400

    analysis = analyze_email_with_ai(email_text, employee_name, employee_email)
    analysis["employee_name"] = employee_name
    analysis["employee_email"] = employee_email
    analysis["email_subject"] = email_subject
    analysis["email_text"] = email_text
    scan_id = database.save_email_scan(analysis)
    analysis["scan_id"] = scan_id

    return jsonify({"success": True, "analysis": analysis})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(database.get_dashboard_metrics())


@app.route("/api/employees", methods=["GET"])
def api_employees():
    return jsonify(database.get_all_employees())


@app.route("/api/employees/add", methods=["POST"])
def api_add_employee():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    department = data.get("department", "General").strip()

    if not name:
        return jsonify({"error": "Employee name is required"}), 400

    conn = database.get_db_connection()
    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO employees (name, email, department, created_at) VALUES (?, ?, ?, ?)",
            (name, email or f"{name.lower()}@company.local", department, now)
        )
        conn.commit()
        database.sync_legacy_files()
        return jsonify({"success": True, "message": f"{name} added successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.route("/click/<employee>")
def track_click(employee):
    employee = employee.strip()
    database.record_simulation_click(employee)
    return render_template("simulation_landing.html", employee=employee)


@app.route("/api/complete-quiz", methods=["POST"])
def api_complete_quiz():
    data = request.get_json() or {}
    employee = data.get("employee", "").strip()
    score = data.get("score", 100)
    if employee:
        database.record_training_completion(employee, score)
        return jsonify({"success": True, "message": f"Training recorded for {employee}."})
    return jsonify({"error": "Employee name required"}), 400


@app.route("/report/<int:scan_id>")
def view_report(scan_id):
    scan = database.get_scan_by_id(scan_id)
    if not scan:
        return "Report not found.", 404
    return render_template("report.html", scan=scan)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n{'='*50}")
    print(f"  🛡️  CyberAware AI — Running on http://127.0.0.1:{port}")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
