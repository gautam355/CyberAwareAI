import os
import sqlite3
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cyberaware.db")
EMPLOYEE_FILE = os.path.join(BASE_DIR, "employees.txt")
CLICK_FILE = os.path.join(BASE_DIR, "clicked_employees.txt")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Employees table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            email TEXT,
            department TEXT DEFAULT 'General',
            created_at TEXT
        )
    """)

    # Email scan history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT,
            employee_email TEXT,
            email_subject TEXT,
            email_text TEXT,
            phishing_probability INTEGER,
            risk_level TEXT,
            emotional_triggers TEXT,
            red_flags TEXT,
            training_status TEXT,
            training_recommendation TEXT,
            reason TEXT,
            safety_tips TEXT,
            engine_used TEXT,
            scanned_at TEXT
        )
    """)

    # Phishing simulation tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            campaign_name TEXT DEFAULT 'Security Awareness Test',
            token TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'Pending',
            clicked_at TEXT,
            quiz_score INTEGER DEFAULT 0,
            trained_at TEXT
        )
    """)

    conn.commit()

    # Seed employees on fresh database
    existing_count = cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    if existing_count == 0:
        seed_names = []
        if os.path.exists(EMPLOYEE_FILE):
            try:
                with open(EMPLOYEE_FILE, "r", encoding="utf-8") as f:
                    seed_names = [line.strip() for line in f if line.strip()]
            except Exception:
                pass

        if not seed_names:
            seed_names = ["Gautam", "Aayushman", "Nandini", "Arpit"]

        dept_map = {
            "Gautam": ("Cybersecurity", "gautam@company.local"),
            "Aayushman": ("Engineering", "aayushman@company.local"),
            "Nandini": ("Finance", "nandini@company.local"),
            "Arpit": ("Human Resources", "arpit@company.local"),
        }
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name in seed_names:
            dept, email = dept_map.get(name, ("General", f"{name.lower()}@company.local"))
            cursor.execute(
                "INSERT OR IGNORE INTO employees (name, email, department, created_at) VALUES (?, ?, ?, ?)",
                (name, email, dept, now)
            )
        conn.commit()

    conn.close()


def sync_legacy_files():
    """Keep the original employees.txt and clicked_employees.txt in sync."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        employees = cursor.execute("SELECT name FROM employees ORDER BY id ASC").fetchall()
        with open(EMPLOYEE_FILE, "w", encoding="utf-8") as f:
            for emp in employees:
                f.write(f"{emp['name']}\n")

        clicked = cursor.execute(
            "SELECT DISTINCT employee_name FROM simulations WHERE status IN ('Clicked', 'Trained')"
        ).fetchall()
        with open(CLICK_FILE, "w", encoding="utf-8") as f:
            for c in clicked:
                f.write(f"{c['employee_name']}\n")

        conn.close()
    except Exception as e:
        print(f"Sync notice: {e}")


def get_all_employees():
    conn = get_db_connection()
    employees = conn.execute("""
        SELECT e.id, e.name, e.email, e.department, e.created_at,
               COALESCE(s.status, 'Safe') as simulation_status,
               s.clicked_at, s.trained_at
        FROM employees e
        LEFT JOIN (
            SELECT employee_name, status, clicked_at, trained_at,
                   ROW_NUMBER() OVER(PARTITION BY employee_name ORDER BY id DESC) as rn
            FROM simulations
        ) s ON e.name = s.employee_name AND s.rn = 1
        ORDER BY e.id ASC
    """).fetchall()
    conn.close()
    return [dict(e) for e in employees]


def record_simulation_click(employee_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing = cursor.execute(
        "SELECT id, status FROM simulations WHERE employee_name = ? ORDER BY id DESC LIMIT 1",
        (employee_name,)
    ).fetchone()

    if existing:
        if existing["status"] != "Trained":
            cursor.execute(
                "UPDATE simulations SET status = 'Clicked', clicked_at = ? WHERE id = ?",
                (now, existing["id"])
            )
    else:
        token = f"sim_{employee_name.lower()}_{int(datetime.now().timestamp())}"
        cursor.execute("""
            INSERT INTO simulations (employee_name, campaign_name, token, status, clicked_at)
            VALUES (?, 'Phishing Awareness Test', ?, 'Clicked', ?)
        """, (employee_name, token, now))

    conn.commit()
    conn.close()
    sync_legacy_files()


def record_training_completion(employee_name, score=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE simulations
        SET status = 'Trained', trained_at = ?, quiz_score = ?
        WHERE employee_name = ?
    """, (now, score, employee_name))
    conn.commit()
    conn.close()
    sync_legacy_files()


def save_email_scan(scan_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_str(val):
        if isinstance(val, list):
            return "\n".join(str(v) for v in val)
        return str(val) if val else ""

    triggers = scan_data.get("emotional_triggers", [])
    flags = scan_data.get("red_flags", [])
    tips = scan_data.get("safety_tips", "")

    cursor.execute("""
        INSERT INTO email_scans (
            employee_name, employee_email, email_subject, email_text,
            phishing_probability, risk_level, emotional_triggers, red_flags,
            training_status, training_recommendation, reason, safety_tips,
            engine_used, scanned_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scan_data.get("employee_name", "Unknown"),
        scan_data.get("employee_email", ""),
        scan_data.get("email_subject", "No Subject"),
        scan_data.get("email_text", ""),
        scan_data.get("phishing_probability", 50),
        scan_data.get("risk_level", "MEDIUM"),
        ", ".join(triggers) if isinstance(triggers, list) else str(triggers),
        ", ".join(flags) if isinstance(flags, list) else str(flags),
        scan_data.get("training_status", "Caution Advised"),
        to_str(scan_data.get("training_recommendation", "")),
        to_str(scan_data.get("reason", "")),
        to_str(tips),
        scan_data.get("engine_used", "CyberAware Engine"),
        now
    ))
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scan_id


def get_scan_by_id(scan_id):
    conn = get_db_connection()
    scan = conn.execute("SELECT * FROM email_scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    return dict(scan) if scan else None


def get_dashboard_metrics():
    conn = get_db_connection()
    cursor = conn.cursor()

    total_employees = cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    total_scans = cursor.execute("SELECT COUNT(*) FROM email_scans").fetchone()[0]
    high_risk_scans = cursor.execute(
        "SELECT COUNT(*) FROM email_scans WHERE risk_level = 'HIGH'"
    ).fetchone()[0]
    sim_clicked = cursor.execute(
        "SELECT COUNT(DISTINCT employee_name) FROM simulations WHERE status IN ('Clicked', 'Trained')"
    ).fetchone()[0]
    sim_trained = cursor.execute(
        "SELECT COUNT(DISTINCT employee_name) FROM simulations WHERE status = 'Trained'"
    ).fetchone()[0]

    dept_stats = cursor.execute("""
        SELECT e.department, COUNT(e.id) as total,
               COUNT(CASE WHEN s.status IN ('Clicked', 'Trained') THEN 1 END) as vulnerable
        FROM employees e
        LEFT JOIN simulations s ON e.name = s.employee_name
        GROUP BY e.department
    """).fetchall()

    recent_scans = cursor.execute("""
        SELECT id, employee_name, email_subject, phishing_probability, risk_level, scanned_at
        FROM email_scans ORDER BY id DESC LIMIT 5
    """).fetchall()

    conn.close()

    ctr = round((sim_clicked / total_employees * 100), 1) if total_employees > 0 else 0
    compliance = round((sim_trained / sim_clicked * 100), 1) if sim_clicked > 0 else 100

    return {
        "total_employees": total_employees,
        "total_scans": total_scans,
        "high_risk_scans": high_risk_scans,
        "sim_clicked": sim_clicked,
        "sim_trained": sim_trained,
        "click_through_rate": ctr,
        "compliance_rate": compliance,
        "department_stats": [dict(d) for d in dept_stats],
        "recent_scans": [dict(s) for s in recent_scans]
    }
