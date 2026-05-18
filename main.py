"""
main.py  —  Social Media Post Analyzer & Report Bot  v3.0
"""
import os, sys, json
from analyzer import PostAnalyzer
from logger import log_moderation, export_report_csv, get_stats, clear_logs
from instagram_scraper import fetch_post
from report_engine import ReportEngine

os.makedirs("logs", exist_ok=True)
IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")

def banner():
    print("\n" + "═"*58)
    print("   🛡️   SOCIAL MEDIA ANALYZER & REPORT BOT  v3.0")
    print("═"*58)

def print_post_info(post):
    print("\n── POST INFO " + "─"*45)
    print(f"  👤 Username  : @{post.get('username','N/A')}")
    if post.get("full_name"): print(f"  📛 Name      : {post['full_name']}")
    if post.get("is_verified"): print(f"  ✅ Verified  : Yes")
    if post.get("followers"): print(f"  👥 Followers : {post['followers']:,}")
    if post.get("likes"):     print(f"  ❤️  Likes     : {post['likes']:,}")
    if post.get("comments"):  print(f"  💬 Comments  : {post['comments']:,}")
    cap = post.get('text','')
    print(f"  📝 Caption   : {cap[:120]}{'...' if len(cap)>120 else ''}")
    print(f"  🔍 Method    : {post.get('method','N/A')}")
    print("─"*58)

def print_analysis(a):
    if "error" in a:
        print(f"\n❌ {a['error']}"); return
    flags = "\n              ".join(a["flags"]) if a["flags"] else "✅ None"
    sent = a.get("sentiment_score")
    print("\n── ANALYSIS " + "─"*46)
    print(f"  ⚠️  Flags     : {flags}")
    print(f"  🌡️  Sentiment : {f'{sent:+.2f}' if sent else 'N/A'}")
    print(f"  📈 Confidence: {a['confidence']}%")
    print(f"  🔴 Risk      : {a['recommendation']}")
    print(f"  ✅ Action    : {a['action']}")
    print("─"*58)

def print_stats(s):
    if "error" in s: print(f"\n❌ {s['error']}"); return
    print("\n── STATISTICS " + "─"*44)
    print(f"  Total   : {s['total_analyzed']}")
    rb = s['risk_breakdown']
    print(f"  🚨 Critical : {rb.get('CRITICAL',0)} | 🔴 High: {rb.get('HIGH',0)} | 🟡 Med: {rb.get('MEDIUM',0)} | 🟢 Low: {rb.get('LOW',0)}")
    if s.get("top_flags"):
        print("  Top Flags:")
        for f,c in s["top_flags"]: print(f"    • {f}: {c}x")
    print("─"*58)

def get_report_count():
    print(f"\n📋 Report count:")
    print("   [1] 100      [2] 1,000      [3] 10,000      [4] 1,00,000      [5] Custom")
    presets = {"1":100,"2":1000,"3":10000,"4":100000}
    c = input("   Choice: ").strip()
    if c in presets: return presets[c]
    if c == "5":
        try: return max(1, min(int(input("   Count: ")), 100000))
        except: return 100
    return 100

def get_speed():
    print("⚡ Speed: [1] Normal(~500/s)  [2] Fast(~2k/s)  [3] Max(~10k/s)")
    return {"1":(10,0.05),"2":(20,0.01),"3":(50,0.001)}.get(input("   Choice: ").strip(), (10,0.05))

def analyze_link_flow(url=None):
    if not url:
        print("\n🔗 Instagram URL dalo:")
        url = input("   > ").strip()
    if not url: print("❌ Empty!"); return

    print(f"\n📡 Fetching post...")
    post = fetch_post(url, ig_username=IG_USERNAME, ig_password=IG_PASSWORD,
                      use_proxy=os.path.exists("proxies.txt"), max_retries=3)
    if not post:
        print("\n💡 Tips: 1) Post public ho  2) VPN try karo  3) proxies.txt add karo")
        return

    print_post_info(post)

    analyzer = PostAnalyzer()
    analysis = analyzer.analyze_post(post["text"], post.get("username",""), url)
    analysis.update({"followers": post.get("followers",0),
                     "likes": post.get("likes",0),
                     "comments": post.get("comments",0)})
    print_analysis(analysis)
    if "error" in analysis: return
    log_moderation(analysis)

    if "LOW" in analysis.get("recommendation","") and not analysis["flags"]:
        if input("\n✅ Safe post. Phir bhi report? (yes/no): ").strip().lower() != "yes":
            return

    count = get_report_count()
    workers, delay = get_speed()
    ReportEngine(analysis, total_reports=count, workers=workers, delay=delay).run()

    if input("\n💾 CSV export? (yes/no): ").strip().lower() == "yes":
        export_report_csv()

def main():
    banner()
    while True:
        print("\n  MENU:")
        print("  1. 🔗 Instagram link → analyze + report")
        print("  2. 📝 Text manually analyze")
        print("  3. 📂 Batch links (JSON file)")
        print("  4. 📊 Statistics")
        print("  5. 💾 CSV Export")
        print("  6. 🗑️  Clear logs")
        print("  7. 🚪 Exit")
        c = input("\n  Option: ").strip()

        if c == "1":
            analyze_link_flow()

        elif c == "2":
            print("\n📝 Text paste karo (2x Enter = done):")
            lines, blank = [], 0
            while True:
                try:
                    l = input()
                    if l == "": blank += 1
                    else: blank = 0
                    if blank >= 2: break
                    lines.append(l)
                except EOFError: break
            text = "\n".join(lines).strip()
            if not text: print("❌ Empty!"); continue
            username = input("👤 Username (optional): ").strip()
            url_in = input("🔗 URL (optional): ").strip()
            analyzer = PostAnalyzer()
            analysis = analyzer.analyze_post(text, username, url_in)
            print_analysis(analysis)
            log_moderation(analysis)
            if "error" not in analysis and analysis["flags"]:
                if input("\n📋 Reports banane hain? (yes/no): ").strip().lower() == "yes":
                    count = get_report_count()
                    w, d = get_speed()
                    ReportEngine(analysis, total_reports=count, workers=w, delay=d).run()

        elif c == "3":
            path = input('\n📂 JSON file path:\n   Format: [{"url": "..."}]\n   > ').strip()
            if not os.path.exists(path): print("❌ File nahi mili"); continue
            try:
                with open(path) as f: items = json.load(f)
            except Exception as e: print(f"❌ {e}"); continue
            analyzer = PostAnalyzer()
            results = []
            for i, item in enumerate(items, 1):
                url = item.get("url","")
                if not url: continue
                print(f"\n[{i}/{len(items)}] {url[:50]}...")
                post = fetch_post(url, IG_USERNAME, IG_PASSWORD, max_retries=2)
                if not post: print("   ❌ Fetch failed"); continue
                a = analyzer.analyze_post(post["text"], post.get("username",""), url)
                log_moderation(a)
                results.append(a)
                print(f"   ✅ {a['recommendation']} | {a['flags']}")
            print(f"\n✅ {len(results)}/{len(items)} done")
            flagged = [a for a in results if a.get("flags")]
            if flagged and input(f"Flagged {len(flagged)} posts ke reports? (yes/no): ").strip().lower()=="yes":
                try: count_each = int(input("Har post ke liye kitne? ").strip() or "100")
                except: count_each = 100
                w, d = get_speed()
                for a in flagged:
                    ReportEngine(a, total_reports=count_each, workers=w, delay=d).run()

        elif c == "4": print_stats(get_stats())
        elif c == "5":
            p = export_report_csv()
            if p: print(f"✅ Saved → {p}")
        elif c == "6":
            if input("⚠️  Confirm delete all? (yes/no): ").strip().lower()=="yes": clear_logs()
        elif c == "7": print("\n👋 Bye!\n"); sys.exit(0)
        else: print("❌ 1-7 mein se choose karo")

if __name__ == "__main__":
    main()
