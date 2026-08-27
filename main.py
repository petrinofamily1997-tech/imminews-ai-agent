import os
import feedparser
import requests
import tweepy
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# =========================
# API KEYS
# =========================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")


# =========================
# GET NEWS
# =========================

def get_news():
    print("🌍 Scanning News...")

    rss_url = (
        "https://news.google.com/rss/search?"
        "q=schengen+visa+rules+2026"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )

    feed = feedparser.parse(rss_url)

    if os.path.exists("history.txt"):
        with open("history.txt", "r", encoding="utf-8") as f:
            history = f.read().splitlines()
    else:
        history = []

    for entry in feed.entries:
        if entry.link not in history:
            print(f"📰 Found news: {entry.title}")
            return entry

    print("ℹ️ No new news found.")
    return None


# =========================
# AI GENERATION
# =========================

def generate_content(news_entry):
    print("🤖 AI is analyzing with Groq...")

    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY is not configured!")
        return None

    try:
        client = Groq(api_key=GROQ_API_KEY)

        prompt = f"""
You are a professional immigration news editor.

Analyze the following news:

TITLE:
{news_entry.title}

SOURCE:
{news_entry.link}

Create content for two platforms.

IMPORTANT:
- Write in English.
- Do not invent facts.
- Do not add information that is not supported by the news title.
- Keep the information clear and useful.
- Use emojis for Telegram.
- Make the X post short and engaging.
- Include relevant hashtags in the X post.

Return EXACTLY this format:

TELEGRAM:
[2-4 sentence English summary with relevant emojis]

X_POST:
[Short English post with relevant hashtags]
"""

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )

        text = completion.choices[0].message.content

        if not text:
            print("❌ Groq returned an empty response.")
            return None

        print("✅ Groq generated content!")

        parts = text.split("X_POST:", 1)

        telegram_text = parts[0].replace("TELEGRAM:", "").strip()

        if len(parts) > 1:
            x_text = parts[1].strip()
        else:
            x_text = ""

        return {
            "telegram": telegram_text,
            "x": x_text
        }

    except Exception as e:
        print(f"❌ Groq Error: {e}")
        return None


# =========================
# POST TO X
# =========================

def post_to_x(tweet_text):
    if not all([
        X_API_KEY,
        X_API_SECRET,
        X_ACCESS_TOKEN,
        X_ACCESS_SECRET
    ]):
        print("⚠️ X API credentials are not configured. Skipping X.")
        return

    try:
        client_x = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET
        )

        client_x.create_tweet(text=tweet_text)

        print("✅ Posted to X!")

    except Exception as e:
        print(f"❌ X Error: {e}")


# =========================
# SEND TO TELEGRAM
# =========================

def send_telegram(text, link):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials are not configured!")
        return

    try:
        url = (
            f"https://api.telegram.org/"
            f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        )

        response = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"{text}\n\n🔗 {link}"
            },
            timeout=30
        )

        response.raise_for_status()

        print("✅ Sent to Telegram!")

    except Exception as e:
        print(f"❌ Telegram Error: {e}")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    news = get_news()

    if news:

        ai_content = generate_content(news)

        if ai_content:

            # Telegram
            send_telegram(
                ai_content["telegram"],
                news.link
            )

            # X
            if ai_content["x"]:
                post_to_x(ai_content["x"])

            # Save processed news
            with open("history.txt", "a", encoding="utf-8") as f:
                f.write(news.link + "\n")

            print("✅ News processed successfully!")

    else:
        print("ℹ️ Nothing to process.")
