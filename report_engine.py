"""
report_engine.py
================
Real-time report generator — ek post ke liye 1 lakh tak reports handle karta hai.
Threaded, batched, progress bar ke saath.
"""

import os
import json
import time
import random
import threading
import queue
from datetime import datetime
from analyzer import PostAnalyzer

# ── Report Templates ──────────────────────────────────────────────────────
# Har category ke liye multiple templates — variety ke liye rotate hote hain

REPORT_TEMPLATES = {
    "Hate Speech": [
        "This post contains hate speech targeting specific groups and violates community guidelines.",
        "Reported for hate speech. This content promotes discrimination and should be removed.",
        "This content uses slurs and derogatory language against individuals or groups.",
        "Post contains language that incites hatred. Requesting immediate review.",
        "This account is spreading hate speech. Please investigate and take action.",
    ],
    "Spam / Engagement Farming": [
        "This post is spam promoting fake engagement. Please remove.",
        "Reported for spam — this is engagement farming content violating guidelines.",
        "This account is spamming follow-for-follow content. Action needed.",
        "Spam detected: post encourages fake interactions. Please review.",
        "This is automated spam content. Requesting account review.",
    ],
    "Potential Phishing / Scam": [
        "This post is a scam trying to steal money or personal information.",
        "Reported for fraud. This content is deceiving users with fake prizes.",
        "Phishing attempt detected. User is being tricked into giving personal data.",
        "This is a financial scam post. Please remove immediately.",
        "Reported for fraud and misleading content targeting vulnerable users.",
    ],
    "Direct Threat": [
        "This post contains a direct threat of violence. Immediate action required.",
        "User is making credible threats. Please remove content and investigate.",
        "This is threatening content that puts someone's safety at risk.",
        "Reported for violent threats. This post must be taken down immediately.",
        "Credible threat of harm detected. Urgent review requested.",
    ],
    "Self-Harm / Suicidal": [
        "This post contains content that may encourage self-harm. Please review.",
        "Reported for content promoting self-harm or suicidal behavior.",
        "This post may put someone's life at risk. Immediate review needed.",
        "Sensitive content about self-harm detected. Please offer support resources.",
        "Reported for self-harm encouragement. Urgent moderator attention needed.",
    ],
    "Radicalization / Extremism": [
        "This post promotes extremist ideology and may radicalize viewers.",
        "Reported for extremist content violating anti-terrorism policies.",
        "This account is spreading radical content. Please investigate.",
        "Extremist propaganda detected. Requesting immediate removal.",
        "This content promotes violent extremism. Action urgently needed.",
    ],
    "Bot-like Symbol Spam": [
        "This appears to be automated bot activity. Please investigate account.",
        "Reported for bot behavior — unnatural posting patterns detected.",
        "This account shows signs of automation. Review requested.",
        "Bot-like spam activity detected. Please restrict this account.",
        "Automated spam content. Account likely violates bot policies.",
    ],
    "Adult / NSFW Content": [
        "This post contains adult content not appropriate for this platform.",
        "Reported for NSFW content violating community standards.",
        "Inappropriate adult content detected. Please remove.",
        "This post contains explicit material. Moderation needed.",
        "Adult content violation. Requesting content removal.",
    ],
    "Suspicious Short Post + Link": [
        "Suspicious link in post — may lead to malicious website.",
        "Reported for distributing potentially harmful links.",
        "This post contains a suspicious external link. Review needed.",
        "Possible malware link detected in post. Please investigate.",
        "Short post with unverified link — possible phishing attempt.",
    ],
    "DEFAULT": [
        "This post violates community guidelines. Please review.",
        "Reported for content that does not comply with platform policies.",
        "This content is inappropriate and should be reviewed by moderators.",
        "Requesting review of this post for policy violations.",
        "Community guideline violation detected. Action requested.",
    ]
}

# ── Report Categories (Instagram actual report types) ─────────────────────
INSTAGRAM_REPORT_TYPES = {
    "Hate Speech":              "hate_speech",
    "Spam / Engagement Farming": "spam",
    "Potential Phishing / Scam": "fraud_or_scam",
    "Direct Threat":            "violence_or_threats",
    "Self-Harm / Suicidal":     "suicide_or_self_injury",
    "Radicalization / Extremism": "terrorism",
    "Bot-like Symbol Spam":     "spam",
    "Adult / NSFW Content":     "nudity_or_sexual_activity",
    "Suspicious Short Post + Link": "fraud_or_scam",
    "DEFAULT":                  "other",
}


class ReportEngine:
    def __init__(self, analysis: dict, total_reports: int = 100,
                 workers: int = 10, delay: float = 0.05):
        """
        analysis      : PostAnalyzer ka result
        total_reports : Kitne reports generate karne hain (max 100,000)
        workers       : Parallel threads (speed control)
        delay         : Har report ke beech delay (seconds)
        """
        self.analysis      = analysis
        self.total_reports = min(total_reports, 100_000)
        self.workers       = workers
        self.delay         = delay
        self.analyzer      = PostAnalyzer()

        # Queues & counters
        self._report_queue  = queue.Queue()
        self._done_count    = 0
        self._failed_count  = 0
        self._lock          = threading.Lock()
        self._stop_event    = threading.Event()

        # Output
        os.makedirs("logs", exist_ok=True)
        self.report_file    = f"logs/reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.summary_file   = f"logs/report_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # ── Report generation ──────────────────────────────────────────────────
    def _build_report(self, report_num: int) -> dict:
        """Ek report object banata hai"""
        flags = self.analysis.get("flags", ["DEFAULT"])
        primary_flag = flags[0] if flags else "DEFAULT"

        templates = REPORT_TEMPLATES.get(primary_flag, REPORT_TEMPLATES["DEFAULT"])
        ig_type   = INSTAGRAM_REPORT_TYPES.get(primary_flag, "other")

        # Slight variation — same report baar baar nahi lagega
        template = templates[report_num % len(templates)]

        return {
            "report_id":       f"RPT-{report_num:07d}",
            "generated_at":    datetime.now().isoformat(),
            "target_url":      self.analysis.get("url", ""),
            "target_username": self.analysis.get("username", ""),
            "report_type":     ig_type,
            "primary_flag":    primary_flag,
            "all_flags":       flags,
            "confidence":      self.analysis.get("confidence", 0),
            "risk_level":      self.analysis.get("recommendation", ""),
            "report_reason":   template,
            "status":          "queued",
        }

    # ── Worker thread ──────────────────────────────────────────────────────
    def _worker(self):
        while not self._stop_event.is_set():
            try:
                report = self._report_queue.get(timeout=1)
            except queue.Empty:
                break

            time.sleep(self.delay + random.uniform(0, self.delay * 0.5))

            # Save to JSONL
            try:
                with self._lock:
                    with open(self.report_file, "a", encoding="utf-8") as f:
                        report["status"] = "sent"
                        f.write(json.dumps(report) + "\n")
                    self._done_count += 1
            except Exception:
                with self._lock:
                    self._failed_count += 1

            self._report_queue.task_done()

    # ── Progress bar ──────────────────────────────────────────────────────
    def _progress_bar(self, current, total, width=40):
        pct  = current / total if total > 0 else 0
        done = int(width * pct)
        bar  = "█" * done + "░" * (width - done)
        return f"[{bar}] {current:,}/{total:,} ({pct*100:.1f}%)"

    # ── Main run ──────────────────────────────────────────────────────────
    def run(self, show_progress: bool = True) -> dict:
        """
        Reports generate karta hai + real-time progress dikhata hai.
        Returns summary dict.
        """
        start_time = time.time()
        print(f"\n🚀 Report Engine Start")
        print(f"   📌 Target   : @{self.analysis.get('username', 'N/A')}")
        print(f"   🔗 URL      : {self.analysis.get('url', 'N/A')[:60]}")
        print(f"   ⚠️  Risk     : {self.analysis.get('recommendation', '')}")
        print(f"   📊 Reports  : {self.total_reports:,}")
        print(f"   🧵 Threads  : {self.workers}")
        print(f"   💾 Output   : {self.report_file}")
        print()

        # Fill queue
        for i in range(1, self.total_reports + 1):
            self._report_queue.put(self._build_report(i))

        # Start workers
        threads = []
        for _ in range(self.workers):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            threads.append(t)

        # Progress display
        try:
            while self._done_count + self._failed_count < self.total_reports:
                if show_progress:
                    done    = self._done_count
                    elapsed = time.time() - start_time
                    rate    = done / elapsed if elapsed > 0 else 0
                    eta     = (self.total_reports - done) / rate if rate > 0 else 0
                    bar     = self._progress_bar(done, self.total_reports)
                    print(f"\r  {bar}  {rate:.0f}/s  ETA:{eta:.0f}s   ", end="", flush=True)
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("\n\n⚠️  User ne interrupt kiya — gracefully stopping...")
            self._stop_event.set()

        # Wait for all threads
        for t in threads:
            t.join(timeout=5)

        elapsed = time.time() - start_time
        rate    = self._done_count / elapsed if elapsed > 0 else 0

        print(f"\n\n{'═'*55}")
        print(f"  ✅ REPORT GENERATION COMPLETE")
        print(f"{'═'*55}")
        print(f"  📊 Total Reports : {self._done_count:,}")
        print(f"  ❌ Failed        : {self._failed_count:,}")
        print(f"  ⚡ Speed         : {rate:.0f} reports/sec")
        print(f"  ⏱️  Time Taken    : {elapsed:.1f}s")
        print(f"  💾 Saved to      : {self.report_file}")
        print(f"{'═'*55}")

        # Summary
        summary = {
            "generated_at":   datetime.now().isoformat(),
            "target_url":     self.analysis.get("url", ""),
            "target_username": self.analysis.get("username", ""),
            "risk_level":     self.analysis.get("recommendation", ""),
            "flags":          self.analysis.get("flags", []),
            "total_reports":  self._done_count,
            "failed":         self._failed_count,
            "speed_per_sec":  round(rate, 1),
            "elapsed_seconds": round(elapsed, 1),
            "report_file":    self.report_file,
        }

        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"  📋 Summary saved : {self.summary_file}")

        return summary


def quick_report(analysis: dict, count: int = 1000) -> dict:
    """One-liner helper — seedha call karo"""
    engine = ReportEngine(analysis, total_reports=count, workers=20, delay=0.01)
    return engine.run()
