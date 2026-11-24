import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "meta-llama/llama-3.1-8b-instruct"


def analyze_email_heuristics(email_text, employee_name="Employee", employee_email=""):
    """
    Rule-based phishing detection engine.
    Checks for common social engineering patterns used in real phishing attacks.
    """
    email_lower = email_text.lower()
    score = 10  # baseline - every email starts with a small score

    emotional_triggers = []
    red_flags = []

    # 1. URGENCY TRICKS — attackers try to make you act fast without thinking
    urgency_words = [
        "urgent", "immediately", "within 24 hours", "expire", "expires today",
        "account suspended", "unauthorized access", "terminate", "final warning",
        "action required", "critical security", "immediate action"
    ]
    matched = [w for w in urgency_words if w in email_lower]
    if matched:
        score += len(matched) * 15
        emotional_triggers.append("Urgency / Time Pressure")
        red_flags.append(f'Email uses urgent language to rush you into clicking (e.g. "{matched[0]}")')

    # 2. MONEY / FINANCIAL BAIT — fake payroll, bonuses, wire transfers
    finance_words = [
        "wire transfer", "gift card", "payroll", "invoice", "direct deposit",
        "bonus", "refund", "tax refund", "overdue payment", "bitcoin", "crypto"
    ]
    matched_fin = [w for w in finance_words if w in email_lower]
    if matched_fin:
        score += len(matched_fin) * 15
        emotional_triggers.append("Financial / Money Bait")
        red_flags.append("Email is about money, payment, or financial account changes")

    # 3. FAKE AUTHORITY — impersonating your boss, IT team, HR, Microsoft, etc.
    authority_words = [
        "click here", "verify your account", "reset your password",
        "login to verify", "microsoft 365", "office 365", "it support",
        "hr department", "ceo", "system administrator", "google workspace"
    ]
    matched_auth = [w for w in authority_words if w in email_lower]
    if matched_auth:
        score += len(matched_auth) * 15
        emotional_triggers.append("Authority Impersonation")
        red_flags.append("Email pretends to be from a trusted authority (IT/HR/Microsoft/CEO)")

    # 4. SUSPICIOUS LINKS — external URLs in the email body
    has_links = bool(re.search(r'https?://', email_lower))
    if has_links:
        score += 20
        red_flags.append("Email contains external links — always verify before clicking")

    # 5. CREDENTIAL REQUEST — asking for login details
    cred_words = ["password", "username", "login", "credentials", "sign in", "verify identity"]
    if any(w in email_lower for w in cred_words):
        score += 20
        red_flags.append("Email is asking you to enter your password or login credentials")

    # --- Calculate final risk ---
    probability = min(max(score, 5), 97)

    if probability >= 70:
        risk_level = "HIGH"
        training_status = "Training Required"
        recommendation = (
            "Do NOT click any links. Forward this email to your IT/security team. "
            "If you've already clicked, change your password immediately."
        )
    elif probability >= 40:
        risk_level = "MEDIUM"
        training_status = "Caution Advised"
        recommendation = (
            "Verify the sender by calling them directly. "
            "Do not click links or download attachments until confirmed safe."
        )
    else:
        risk_level = "LOW"
        training_status = "Likely Safe"
        recommendation = "Looks like a legitimate email. Stay alert and report anything suspicious."

    if not emotional_triggers:
        emotional_triggers = ["No obvious manipulation tactics found"]
    if not red_flags:
        red_flags = ["No obvious red flags detected in this email"]

    if probability >= 50:
        reason = (
            f"This email shows {len(red_flags)} red flag(s) commonly found in phishing attacks. "
            f"The main concern is: {red_flags[0].lower()}. "
            f"Attackers use these tricks to make employees act quickly without verifying. "
            f"Always pause and verify before clicking any link or sharing any information."
        )
    else:
        reason = (
            "This email appears to be a routine communication with no major phishing indicators. "
            "No urgent manipulation tactics or suspicious links were detected. "
            "However, always stay alert — phishing emails can look very legitimate."
        )

    safety_tips = (
        "1. Check the sender's email address carefully — attackers use fake domains like 'rnicrosoft.com' instead of 'microsoft.com'.\n"
        "2. Never click links in unexpected emails — go directly to the official website instead.\n"
        "3. If an email feels urgent or scary, that's a warning sign. Slow down and verify.\n"
        "4. Never share your password or OTP with anyone — IT support will never ask for it.\n"
        "5. When in doubt, call the person directly to confirm they sent the email."
    )

    return {
        "phishing_probability": probability,
        "risk_level": risk_level,
        "emotional_triggers": emotional_triggers,
        "red_flags": red_flags,
        "training_status": training_status,
        "training_recommendation": recommendation,
        "reason": reason,
        "safety_tips": safety_tips,
        "engine_used": "CyberAware Rule-Based Detection Engine (Offline)"
    }


def analyze_email_with_ai(email_text, employee_name="Employee", employee_email=""):
    """
    Main analysis function.
    First tries OpenRouter AI for deeper contextual understanding.
    Falls back to local rule-based engine if API is unavailable.
    """
    if not API_KEY or API_KEY == "your_openrouter_api_key_here":
        return analyze_email_heuristics(email_text, employee_name, employee_email)

    # Prompt designed to give structured, plain-language output
    system_prompt = """You are a cybersecurity assistant helping analyze suspicious emails for employees.
Analyze the email and return ONLY a valid JSON object (no markdown, no code fences).
Use plain, simple language that any employee can understand.

Required JSON structure:
{
    "phishing_probability": <integer 0-100>,
    "risk_level": "<LOW | MEDIUM | HIGH>",
    "emotional_triggers": ["<simple description of manipulation tactic>"],
    "red_flags": ["<specific suspicious thing found in this email>"],
    "training_status": "<Likely Safe | Caution Advised | Training Required>",
    "training_recommendation": "<1-2 sentences of what the employee should do>",
    "reason": "<2-3 sentences explaining why this email is or isn't suspicious, in simple language>",
    "safety_tips": "<3-5 numbered practical tips for this type of email>"
}"""

    user_prompt = f"""Employee: {employee_name} ({employee_email})

Email to analyze:
{email_text}"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Gautam/CyberAware-AI",
                "X-Title": "CyberAware AI"
            },
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 600
            },
            timeout=8
        )

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"].strip()
            # Remove markdown code fences if present
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            parsed = json.loads(content)
            parsed["engine_used"] = f"AI Analysis (Llama 3.1 via OpenRouter)"
            return parsed

        return analyze_email_heuristics(email_text, employee_name, employee_email)

    except Exception as e:
        print(f"AI API unavailable: {e}. Using local detection engine.")
        result = analyze_email_heuristics(email_text, employee_name, employee_email)
        result["engine_used"] = "CyberAware Rule-Based Detection Engine (AI Offline)"
        return result


SIMULATION_TEMPLATES = {
    "it_password": {
        "title": "Microsoft 365 Password Expiry",
        "sender": "Microsoft 365 Support <no-reply@m365-security-update.com>",
        "subject": "Action Required: Password Expiry Notification for {name}",
        "body": (
            "Hello {name},\n\n"
            "Your organizational Microsoft 365 password is scheduled to expire in 2 hours. "
            "To maintain uninterrupted access to your corporate email, OneDrive, and Teams, "
            "please verify your credentials immediately using our secure verification portal:\n\n"
            "👉 Verify Credentials: {link}\n\n"
            "Failure to update before 5:00 PM today will result in temporary account lockout.\n\n"
            "Regards,\n"
            "Global IT Support Desk"
        )
    },
    "hr_payroll": {
        "title": "HR Salary & Direct Deposit Audit",
        "sender": "Human Resources <hr-benefits@payroll-portal-auth.com>",
        "subject": "URGENT: Annual Bonus & Direct Deposit Audit for {name}",
        "body": (
            "Dear {name},\n\n"
            "Our internal finance & HR audit revealed an incomplete direct deposit submission for your account. "
            "To prevent any hold on your upcoming salary transfer and year-end bonus disbursement, "
            "please review your banking details via the employee self-service portal:\n\n"
            "👉 Review & Confirm Account: {link}\n\n"
            "Please confirm your details before end of day today.\n\n"
            "Best regards,\n"
            "Human Resources & Payroll Compliance"
        )
    },
    "package_delivery": {
        "title": "Courier Package Delivery on Hold",
        "sender": "Express Logistics <tracking-alert@dhl-delivery-service.com>",
        "subject": "Delivery Exception: Priority Shipment on hold for {name}",
        "body": (
            "Notice for {name},\n\n"
            "A priority corporate parcel addressed to you could not be delivered due to an incomplete desk/suite address. "
            "The parcel is currently held at the local distribution facility.\n\n"
            "To reschedule delivery or redirect to your current desk, please verify your shipping address:\n\n"
            "👉 Confirm Delivery Address: {link}\n\n"
            "Unclaimed shipments will be returned to sender after 48 hours.\n\n"
            "Operations Team,\n"
            "Express Courier Services"
        )
    },
    "vpn_patch": {
        "title": "Urgent VPN Client Security Update",
        "sender": "InfoSec Operations <security-patch@globalprotect-vpn-update.net>",
        "subject": "CRITICAL: Mandatory Security Patch for Remote VPN Access ({name})",
        "body": (
            "Team Alert,\n\n"
            "Due to an active zero-day vulnerability in legacy VPN clients, all active personnel "
            "(including {name}) are required to validate their remote access profile immediately.\n\n"
            "Please access the internal deployment gateway to re-authenticate:\n\n"
            "👉 Re-authenticate VPN Client: {link}\n\n"
            "Connections using unpatched clients will be restricted at midnight.\n\n"
            "Information Security Operations (SecOps)"
        )
    }
}


def generate_simulation_email(template_id, employee_name="Employee", tracking_url="http://127.0.0.1:5000/click/test", custom_prompt=None):
    """
    Generates realistic phishing simulation drill emails for internal awareness testing.
    Can use built-in templates or generate custom scenarios using AI.
    """
    employee_name = employee_name.strip() or "Employee"

    # If AI custom prompt requested and API key is set
    if custom_prompt and API_KEY:
        try:
            sys_prompt = (
                "You are an educational cybersecurity simulation crafter. Generate a realistic phishing drill email "
                "for internal corporate employee security awareness training. "
                "Output ONLY a raw JSON object with exactly these 3 string keys: 'sender', 'subject', 'body'. "
                f"Make sure to embed the link: '{tracking_url}' into the body. "
                f"Address the recipient as '{employee_name}'. Do not wrap in markdown quotes."
            )
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/Gautam/CyberAware-AI",
                    "X-Title": "CyberAware AI"
                },
                json={
                    "model": MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": f"Create an awareness simulation email for scenario: {custom_prompt}"}
                    ],
                    "temperature": 0.4,
                    "max_tokens": 500
                },
                timeout=8
            )
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                data = json.loads(raw)
                return {
                    "sender": data.get("sender", "Simulation Alert <security@company.local>"),
                    "subject": data.get("subject", "Action Required"),
                    "body": data.get("body", f"Hello {employee_name}, please verify: {tracking_url}"),
                    "source": "AI-Generated Custom Simulation"
                }
        except Exception as e:
            print(f"Custom simulation generation fallback: {e}")

    # Default to chosen template or fallback
    tpl = SIMULATION_TEMPLATES.get(template_id, SIMULATION_TEMPLATES["it_password"])
    return {
        "sender": tpl["sender"],
        "subject": tpl["subject"].replace("{name}", employee_name),
        "body": tpl["body"].replace("{name}", employee_name).replace("{link}", tracking_url),
        "source": tpl["title"]
    }

