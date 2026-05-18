"""
instagram_scraper.py
====================
Bina login ke kisi bhi public Instagram post ka caption fetch karta hai.
Multiple methods try karta hai — agar ek fail ho toh doosra.
"""

import re
import json
import time
import random
import requests

# ── User-Agent Pool (rotate karte hain ban se bachne ke liye) ──────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

PROXIES_FILE = "proxies.txt"   # optional — ek proxy per line


def _get_proxies() -> list:
    """proxies.txt se proxy list load karta hai (optional)"""
    try:
        with open(PROXIES_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def _make_session(proxy: str = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept":          "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
        "Referer":         "https://www.instagram.com/",
        "Origin":          "https://www.instagram.com",
    })
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    return s


def extract_shortcode(url: str) -> str | None:
    """URL se post shortcode nikalta hai"""
    for pattern in [
        r"instagram\.com/p/([A-Za-z0-9_-]+)",
        r"instagram\.com/reel/([A-Za-z0-9_-]+)",
        r"instagram\.com/tv/([A-Za-z0-9_-]+)",
        r"instagram\.com/reels/([A-Za-z0-9_-]+)",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


# ── Method 1: GraphQL (most reliable) ─────────────────────────────────────
def _fetch_via_graphql(shortcode: str, session: requests.Session) -> dict | None:
    """Instagram ka internal GraphQL API use karta hai"""
    # Step 1: Homepage hit karo — cookies milenge
    try:
        session.get("https://www.instagram.com/", timeout=10)
        time.sleep(random.uniform(1.0, 2.5))
    except Exception:
        pass

    url = (
        "https://www.instagram.com/api/v1/media/shortcode/"
        f"{shortcode}/?__a=1&__d=dis"
    )
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            item = data.get("items", [{}])[0]
            caption_data = item.get("caption", {}) or {}
            caption = caption_data.get("text", "")
            user    = item.get("user", {})
            return {
                "text":     caption,
                "username": user.get("username", ""),
                "full_name": user.get("full_name", ""),
                "is_verified": user.get("is_verified", False),
                "followers":   user.get("follower_count", 0),
                "likes":       item.get("like_count", 0),
                "comments":    item.get("comment_count", 0),
            }
    except Exception:
        pass
    return None


# ── Method 2: oEmbed API (no auth needed) ─────────────────────────────────
def _fetch_via_oembed(post_url: str, session: requests.Session) -> dict | None:
    """Instagram oEmbed — publicly available, no login"""
    oembed_url = (
        f"https://graph.facebook.com/v18.0/instagram_oembed"
        f"?url={post_url}&maxwidth=320&fields=thumbnail_url,author_name,title"
        f"&access_token=2104280716UPDATE|PLACEHOLDER"
    )
    # Public oEmbed (no token needed for basic)
    public_oembed = f"https://www.instagram.com/oembed/?url={post_url}"
    try:
        r = session.get(public_oembed, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "text":     data.get("title", ""),
                "username": data.get("author_name", ""),
                "full_name": "",
                "is_verified": False,
                "followers":   0,
                "likes":       0,
                "comments":    0,
            }
    except Exception:
        pass
    return None


# ── Method 3: HTML scrape + regex ─────────────────────────────────────────
def _fetch_via_html(post_url: str, session: requests.Session) -> dict | None:
    """HTML page se JSON data nikalta hai (fallback)"""
    try:
        # Mobile version zyada data deta hai
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                          "Version/17.0 Mobile/15E148 Safari/604.1"
        })
        r = session.get(post_url, timeout=15)
        if r.status_code != 200:
            return None

        html = r.text

        # Try 1: __additionalDataLoaded JSON
        m = re.search(r'window\.__additionalDataLoaded\s*\(\s*[^,]+,\s*(\{.+?\})\s*\)', html)
        if m:
            try:
                data = json.loads(m.group(1))
                shortcode_media = data.get("graphql", {}).get("shortcode_media", {})
                if shortcode_media:
                    caption_edges = shortcode_media.get("edge_media_to_caption", {}).get("edges", [])
                    caption = caption_edges[0]["node"]["text"] if caption_edges else ""
                    owner = shortcode_media.get("owner", {})
                    return {
                        "text":      caption,
                        "username":  owner.get("username", ""),
                        "full_name": owner.get("full_name", ""),
                        "is_verified": owner.get("is_verified", False),
                        "followers":   owner.get("edge_followed_by", {}).get("count", 0),
                        "likes":       shortcode_media.get("edge_media_preview_like", {}).get("count", 0),
                        "comments":    shortcode_media.get("edge_media_to_comment", {}).get("count", 0),
                    }
            except Exception:
                pass

        # Try 2: meta tags se caption
        og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
        og_user = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
        if og_desc:
            raw = og_desc.group(1)
            # Format: "123 Likes, 45 Comments - @username: caption text"
            caption_match = re.search(r'[:-]\s*(.+)$', raw, re.DOTALL)
            caption = caption_match.group(1).strip() if caption_match else raw

            username = ""
            if og_user:
                u = re.search(r'@([\w.]+)', og_user.group(1))
                if u:
                    username = u.group(1)

            return {
                "text":      caption,
                "username":  username,
                "full_name": "",
                "is_verified": False,
                "followers":   0,
                "likes":       0,
                "comments":    0,
            }
    except Exception:
        pass
    return None


# ── Method 4: instagrapi (login required, last resort) ────────────────────
def _fetch_via_instagrapi(shortcode: str, username: str, password: str) -> dict | None:
    import os
    try:
        from instagrapi import Client
        cl = Client()
        session_file = f"logs/ig_session_{username}.json"
        if os.path.exists(session_file):
            cl.load_settings(session_file)
        cl.login(username, password)
        cl.dump_settings(session_file)

        media_pk = cl.media_pk_from_code(shortcode)
        media    = cl.media_info(media_pk)
        user     = media.user

        return {
            "text":      media.caption_text or "",
            "username":  user.username if user else "",
            "full_name": user.full_name if user else "",
            "is_verified": user.is_verified if user else False,
            "followers":   user.follower_count if user else 0,
            "likes":       media.like_count or 0,
            "comments":    media.comment_count or 0,
        }
    except ImportError:
        return None
    except Exception as e:
        print(f"   instagrapi error: {e}")
        return None


# ── Main public function ───────────────────────────────────────────────────
def fetch_post(url: str, ig_username: str = "", ig_password: str = "",
               use_proxy: bool = False, max_retries: int = 3) -> dict | None:
    """
    Kisi bhi public Instagram post ka data fetch karta hai.
    Methods try karta hai: GraphQL → oEmbed → HTML scrape → instagrapi (if credentials)

    Returns dict:
        text, username, full_name, is_verified, followers, likes, comments
    Returns None if all methods fail.
    """
    shortcode = extract_shortcode(url)
    if not shortcode:
        print("❌ Invalid Instagram URL")
        return None

    proxies = _get_proxies() if use_proxy else []

    for attempt in range(max_retries):
        proxy = random.choice(proxies) if proxies else None
        session = _make_session(proxy)

        if attempt > 0:
            wait = random.uniform(2, 5) * attempt
            print(f"   ⏳ Retry {attempt}/{max_retries - 1} — {wait:.1f}s wait...")
            time.sleep(wait)

        # Method 1: GraphQL
        print(f"   🔍 Method 1: GraphQL API...")
        result = _fetch_via_graphql(shortcode, session)
        if result and result.get("text"):
            print("   ✅ GraphQL se data mila!")
            result["method"] = "graphql"
            result["url"] = url
            result["shortcode"] = shortcode
            return result

        # Method 2: oEmbed
        print(f"   🔍 Method 2: oEmbed API...")
        result = _fetch_via_oembed(url, session)
        if result and result.get("text"):
            print("   ✅ oEmbed se data mila!")
            result["method"] = "oembed"
            result["url"] = url
            result["shortcode"] = shortcode
            return result

        # Method 3: HTML scrape
        print(f"   🔍 Method 3: HTML scraping...")
        result = _fetch_via_html(url, session)
        if result and result.get("text"):
            print("   ✅ HTML scrape se data mila!")
            result["method"] = "html"
            result["url"] = url
            result["shortcode"] = shortcode
            return result

        time.sleep(random.uniform(1.5, 3.5))

    # Method 4: instagrapi (only if credentials given)
    if ig_username and ig_password:
        print(f"   🔍 Method 4: instagrapi (login)...")
        result = _fetch_via_instagrapi(shortcode, ig_username, ig_password)
        if result and result.get("text"):
            print("   ✅ instagrapi se data mila!")
            result["method"] = "instagrapi"
            result["url"] = url
            result["shortcode"] = shortcode
            return result

    print("❌ Saare methods fail ho gaye.")
    print("   Possible reasons:")
    print("   • Post private hai")
    print("   • Instagram ne IP block kiya — VPN try karo")
    print("   • proxies.txt mein proxies add karo")
    return None
