import os
import json
import csv
from datetime import datetime

# Logs folder auto-create — kabhi crash nahi karega
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "moderation_log.jsonl")
REPORT_FILE = os.path.join(LOG_DIR, "moderation_report.csv")

os.makedirs(LOG_DIR, exist_ok=True)


def log_moderation(analysis: dict) -> bool:
    """
    Analysis result ko JSONL log file mein save karta hai.
    Returns True on success, False on failure.
    """
    if "error" in analysis:
        print(f"⚠️  Logging skipped (analysis error): {analysis['error']}")
        return False

    log_entry = {
        **analysis,
        "logged_at": datetime.now().isoformat()
    }

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        print(f"✅ Logged → {LOG_FILE}")
        return True
    except IOError as e:
        print(f"❌ Log write failed: {e}")
        return False


def export_report_csv() -> str:
    """
    Saare JSONL logs padhkar ek CSV report banata hai.
    Returns: CSV file path
    """
    if not os.path.exists(LOG_FILE):
        print("❌ Koi log file nahi mili. Pehle kuch posts analyze karo.")
        return ""

    rows = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                rows.append({
                    "logged_at":      entry.get("logged_at", ""),
                    "username":       entry.get("username", ""),
                    "url":            entry.get("url", ""),
                    "flags":          " | ".join(entry.get("flags", [])),
                    "confidence":     entry.get("confidence", 0),
                    "recommendation": entry.get("recommendation", ""),
                    "action":         entry.get("action", ""),
                    "sentiment":      entry.get("sentiment_score", "N/A"),
                    "text_preview":   entry.get("text_preview", "")[:100],
                })
            except json.JSONDecodeError:
                continue

    if not rows:
        print("⚠️  Log file empty hai.")
        return ""

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"📊 CSV Report saved → {REPORT_FILE}")
    return REPORT_FILE


def get_stats() -> dict:
    """
    Log file se summary statistics nikalta hai.
    """
    if not os.path.exists(LOG_FILE):
        return {"error": "No log file found"}

    total = 0
    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    flag_counts = {}

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                total += 1
                rec = entry.get("recommendation", "")
                if "CRITICAL" in rec:
                    risk_counts["CRITICAL"] += 1
                elif "HIGH" in rec:
                    risk_counts["HIGH"] += 1
                elif "MEDIUM" in rec:
                    risk_counts["MEDIUM"] += 1
                else:
                    risk_counts["LOW"] += 1

                for flag in entry.get("flags", []):
                    flag_counts[flag] = flag_counts.get(flag, 0) + 1
            except json.JSONDecodeError:
                continue

    top_flags = sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_analyzed": total,
        "risk_breakdown": risk_counts,
        "top_flags": top_flags
    }


def clear_logs() -> bool:
    """Logs clear karta hai (careful!)"""
    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        print("🗑️  Logs cleared.")
        return True
    except IOError as e:
        print(f"❌ Log clear failed: {e}")
        return False
