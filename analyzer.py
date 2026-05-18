import re
import json
from datetime import datetime

# ==================== TEXTBLOB SETUP ====================
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("⚠️  textblob not found. Sentiment analysis disabled.")

# ==================== NLTK SETUP ====================
try:
    import nltk
    from nltk.corpus import stopwords
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        print("📥 NLTK data download ho raha hai (pehle baar)...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        print("✅ NLTK data ready!")
    STOPWORDS = set(stopwords.words('english'))
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    STOPWORDS = set()
    print("⚠️  nltk not found. Some features disabled.")


# ==================== DETECTION RULES ====================

# Word-boundary safe hate words — substring match nahi, pure word match
HATE_WORDS = [
    r'\bnigger\b', r'\bfaggot\b', r'\bcunt\b', r'\bkill\s+\w+\b',
    r'\brape\b', r'\bterrorist\b', r'\bdie\s+you\b', r'\bdie\s+\w+\b',
    r'\bslut\b', r'\bwhore\b', r'\bkys\b', r'\bkill yourself\b',
    r'\bhate\s+(you|them|all|jews|muslims|hindus|christians|blacks|whites)\b',
    r'\bsubhuman\b', r'\bvermin\b', r'\bdegenerate\b'
]

PHISHING_KEYWORDS = [
    '''Subject/Description to write in the form:
    Hello Instagram Team, I am writing to report this post/account as it strictly violates Instagram's 
    Community Guidelines regarding suicide and self-injury. 
    The content posted by this user explicitly promotes self-harm and 
    contains highly triggering material that risks the safety and well-being of others. 
    To maintain a safe environment for the community, 
    I urge you to review this urgently and take down the post/account as soon as possible. 
    Thank you''',
    'Nudity or sexual activity', 'Hate speech or symbols', 'Violence or dangerous organizations',
    'Bullying or harassment', 'Suicide or self-injury', 'Intellectual property violation',
    'free money', 'claim prize', 'claim your reward', 'verify your account',
    'click here now', 'limited offer', 'congratulations you won',
    'send money', 'bitcoin investment', 'double your money',
    'you have been selected', 'act now', 'urgent action required',
    'wire transfer', 'western union', 'gift card', 'send gift card',
    'your account will be suspended', 'confirm your details',
    'bank account details', 'ssn required', 'social security'
]

SPAM_PATTERNS = [
    r'\bfollow\s*(me|back|for\s*follow)\b',
    r'\blike\s*for\s*like\b',
    r'\bl4l\b', r'\bf4f\b',
    r'\bdm\s*(for|me)\s*(promo|collab|deals?)\b',
    r'\bcheck\s*(my|out\s*my)\s*(page|profile|link)\b',
    r'\bfollow\s*back\b',
    r'\blike\s*and\s*comment\b',
    r'\bshoutout\b',
    r'\bsub\s*for\s*sub\b',
    r'\bget\s*(free|1000|10k|100k)\s*(followers|likes)\b',
    r'\bgrow\s*your\s*(account|instagram|following)\b',
]

THREAT_PATTERNS = [
    r'\bi\s*will\s*kill\b',
    r'\bgoing\s*to\s*(hurt|kill|attack|shoot)\b',
    r'\byou\s*(are|r)\s*dead\b',
    r'\bwatch\s*your\s*back\b',
    r'\bi\s*know\s*where\s*you\s*live\b',
    r'\bwill\s*find\s*you\b',
    r'\bbomb\s*(threat|you|this)\b',
]

SELF_HARM_PATTERNS = [
    r'\bkill\s*myself\b',
    r'\bwant\s*to\s*die\b',
    r'\bend\s*my\s*(life|pain)\b',
    r'\bsuicid(e|al)\b',
    r'\bcut\s*myself\b',
    r'\bno\s*reason\s*to\s*live\b',
]

RADICALIZATION_KEYWORDS = [
    'jihad', 'infidel', 'kafir', 'death to', 'white power',
    'great replacement', 'ethnic cleansing', 'final solution',
    'race war', '14 words', 'heil', 'gas the'
]

ADULT_PATTERNS = [
    r'\bonlyfans\b',
    r'\bnude(s)?\b',
    r'\bsext(ing)?\b',
    r'\bnsfw\b',
    r'\b18\+\s*content\b',
]

# ==================== SCORING WEIGHTS ====================
FLAG_WEIGHTS = {
    "Hate Speech":              55,
    "Direct Threat":            80,
    "Self-Harm / Suicidal":     70,
    "Radicalization / Extremism": 75,
    "Potential Phishing / Scam": 60,
    "Spam / Engagement Farming": 45,
    "Suspicious Short Post + Link": 35,
    "Bot-like Symbol Spam":     30,
    "Adult / NSFW Content":     40,
    "Highly Toxic Sentiment":   25,
    "Excessive Caps (Shouting)": 15,
    "Mass Mention / Tag Spam":  20,
    "URL Shortener Link":       25,
}


class PostAnalyzer:
    def __init__(self):
        pass

    def _check_hate_speech(self, text_lower: str) -> bool:
        """Word-boundary aware hate speech detection"""
        return any(re.search(pattern, text_lower) for pattern in HATE_WORDS)

    def _check_threats(self, text_lower: str) -> bool:
        return any(re.search(p, text_lower) for p in THREAT_PATTERNS)

    def _check_self_harm(self, text_lower: str) -> bool:
        return any(re.search(p, text_lower) for p in SELF_HARM_PATTERNS)

    def _check_radicalization(self, text_lower: str) -> bool:
        return any(kw in text_lower for kw in RADICALIZATION_KEYWORDS)

    def _check_phishing(self, text_lower: str) -> bool:
        return any(kw in text_lower for kw in PHISHING_KEYWORDS)

    def _check_spam(self, text_lower: str) -> bool:
        return any(re.search(p, text_lower) for p in SPAM_PATTERNS)

    def _check_adult(self, text_lower: str) -> bool:
        return any(re.search(p, text_lower) for p in ADULT_PATTERNS)

    def _check_bot_symbols(self, text: str) -> bool:
        return (
            text.count("!") > 6 or
            text.count("🔥") > 4 or
            text.count("💰") > 3 or
            text.count("✅") > 5 or
            text.count("👇") > 3 or
            text.count("💯") > 4
        )

    def _check_excessive_caps(self, text: str) -> bool:
        letters = [c for c in text if c.isalpha()]
        if len(letters) < 10:
            return False
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        return caps_ratio > 0.6

    def _check_tag_spam(self, text: str) -> bool:
        """10+ mentions ya hashtags = spam"""
        mentions = len(re.findall(r'@\w+', text))
        hashtags = len(re.findall(r'#\w+', text))
        return mentions > 8 or hashtags > 15

    def _check_url_shortener(self, text_lower: str) -> bool:
        shorteners = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly',
                      'cutt.ly', 'rb.gy', 'is.gd', 'buff.ly']
        return any(s in text_lower for s in shorteners)

    def _check_suspicious_link(self, text: str) -> bool:
        words = text.split()
        has_link = any("http" in w or "www." in w for w in words)
        return len(words) < 8 and has_link

    def _get_sentiment(self, text: str):
        if not TEXTBLOB_AVAILABLE:
            return None
        try:
            return TextBlob(text).sentiment.polarity
        except Exception:
            return None

    def analyze_post(self, text: str, username: str = "", post_url: str = "") -> dict:
        """
        Ek post analyze karta hai aur detailed result return karta hai.
        """
        if not text or len(text.strip()) == 0:
            return {"error": "Empty text provided"}

        text_lower = text.lower()

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "text_preview": text[:300] + ("..." if len(text) > 300 else ""),
            "text_length": len(text),
            "username": username,
            "url": post_url,
            "flags": [],
            "flag_details": {},   # har flag ki wajah
            "confidence": 0,
            "sentiment_score": None,
            "recommendation": "LOW RISK",
            "action": "No Action Needed"
        }

        # ── Detection Checks ──────────────────────────────────────────
        checks = [
            ("Hate Speech",               self._check_hate_speech(text_lower)),
            ("Direct Threat",             self._check_threats(text_lower)),
            ("Self-Harm / Suicidal",      self._check_self_harm(text_lower)),
            ("Radicalization / Extremism",self._check_radicalization(text_lower)),
            ("Potential Phishing / Scam", self._check_phishing(text_lower)),
            ("Spam / Engagement Farming", self._check_spam(text_lower)),
            ("Suspicious Short Post + Link", self._check_suspicious_link(text)),
            ("Bot-like Symbol Spam",      self._check_bot_symbols(text)),
            ("Adult / NSFW Content",      self._check_adult(text_lower)),
            ("Excessive Caps (Shouting)", self._check_excessive_caps(text)),
            ("Mass Mention / Tag Spam",   self._check_tag_spam(text)),
            ("URL Shortener Link",        self._check_url_shortener(text_lower)),
        ]

        for flag_name, triggered in checks:
            if triggered:
                analysis["flags"].append(flag_name)
                analysis["confidence"] += FLAG_WEIGHTS.get(flag_name, 20)

        # ── Sentiment ─────────────────────────────────────────────────
        sentiment = self._get_sentiment(text)
        analysis["sentiment_score"] = round(sentiment, 3) if sentiment is not None else None
        if sentiment is not None and sentiment < -0.65:
            analysis["flags"].append("Highly Toxic Sentiment")
            analysis["confidence"] += FLAG_WEIGHTS["Highly Toxic Sentiment"]

        # ── Cap confidence at 98 ──────────────────────────────────────
        analysis["confidence"] = min(analysis["confidence"], 98)

        # ── Final Recommendation ──────────────────────────────────────
        if "Direct Threat" in analysis["flags"] or "Self-Harm / Suicidal" in analysis["flags"]:
            analysis["recommendation"] = "🚨 CRITICAL RISK - Immediate Action"
            analysis["action"] = "Remove immediately + escalate to authorities if needed"
        elif analysis["confidence"] >= 75:
            analysis["recommendation"] = "🔴 HIGH RISK - Likely Violation"
            analysis["action"] = "Remove content + warn/ban user"
        elif analysis["confidence"] >= 45:
            analysis["recommendation"] = "🟡 MEDIUM RISK - Human Review Required"
            analysis["action"] = "Flag for manual moderation review"
        else:
            analysis["recommendation"] = "🟢 LOW RISK"
            analysis["action"] = "No Action Needed"

        return analysis

    def analyze_batch(self, posts: list) -> dict:
        """
        Multiple posts ek saath analyze karta hai.
        posts = [{"text": "...", "username": "...", "url": "..."}, ...]
        """
        results = []
        stats = {
            "total": len(posts),
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
            "critical": 0,
            "flag_counts": {}
        }

        for post in posts:
            result = self.analyze_post(
                post.get("text", ""),
                post.get("username", ""),
                post.get("url", "")
            )
            results.append(result)

            # Stats update
            rec = result.get("recommendation", "")
            if "CRITICAL" in rec:
                stats["critical"] += 1
            elif "HIGH" in rec:
                stats["high_risk"] += 1
            elif "MEDIUM" in rec:
                stats["medium_risk"] += 1
            else:
                stats["low_risk"] += 1

            for flag in result.get("flags", []):
                stats["flag_counts"][flag] = stats["flag_counts"].get(flag, 0) + 1

        return {"results": results, "stats": stats}
