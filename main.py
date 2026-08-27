import os
import feedparser
import requests
import tweepy
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# API keys
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")


def get_news():
    print("🌍 Scanning News...")

    rss_url = "https://news.google.com/rss/search?q=schengen+visa+rules+2026&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)

    if os.path.exists("history.txt"):
        with open("history.txt", "r", encoding="utf-8") as f:
            history = f.read().splitlines()
    else:
        history = []

    for entry in feed.entries:
        if entry.link not in history:
            return entry

    return None


def generate_content(news_entry):
    print("🤖 AI is analyzing with DeepSeek...")

    if not DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY is not configured!")
        return None

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

    prompt = f"""
Summarize this news for social media.

News title:
{news_entry.title}

News link:
{news_entry.link}

Create two versions.

Format your response EXACTLY like this:

TELEGRAM: (English summary with relevant emojis, 2-4 sentences)

X_POST: (Short English post suitable for X/Twitter with relevant hashtags)
"""

    try:
        completion = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        text = completion.choices[0].message.content

        print("✅ DeepSeek generated content!")

        parts = text.split("X_POST:", 1)

        telegram_text = parts[0].replace("TELEGRAM:", "").strip()
        x_text = parts[1].strip() if len(parts) > 1 else ""

        return {
            "telegram": telegram_text,
            "x": x_text
        }

    except Exception as e:
        print(f"❌ DeepSeek Error: {e}")
        return None


def post_to_x(tweet_text):
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


def send_telegram(text, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"{text}\n\n🔗 {link}"
        }
    )

    print("✅ Sent to Telegram!")


if __name__ == "__main__":
    news = get_news()

    if news:
        ai_content = generate_content(news)

        if ai_content:
            send_telegram(
                ai_content["telegram"],
                news.link
            )

            if ai_content["x"]:
                post_to_x(ai_content["x"])

            with open("history.txt", "a", encoding="utf-8") as f:
                f.write(news.link + "\n")

            print("✅ News processed successfully!")

    else:
        print("ℹ️ No new news found.")
