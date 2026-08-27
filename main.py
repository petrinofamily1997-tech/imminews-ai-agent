import os
import random
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
# NEWS SOURCES
# =========================

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=finance+economy+markets&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=personal+finance+money&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=investing+stocks+economy&hl=en-US&gl=US&ceid=US:en",
]


# =========================
# CONTENT TYPES
# =========================

CONTENT_TYPES = [
    "news",
    "news",
    "money",
    "investing",
    "income",
    "money",
    "news",
    "investing",
]


# =========================
# GET HISTORY
# =========================

def get_history():
    if os.path.exists("history.txt"):
        with open("history.txt", "r", encoding="utf-8") as f:
            return f.read().splitlines()

    return []


# =========================
# GET NEWS
# =========================

def get_news():
    print("🌍 Scanning financial news...")

    history = get_history()

    all_entries = []

    for rss_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                if entry.link not in history:
                    all_entries.append(entry)

        except Exception as e:
            print(f"⚠️ RSS Error: {e}")

    if not all_entries:
        print("ℹ️ No new news found.")
        return None

    # Remove duplicates
    unique_entries = {}

    for entry in all_entries:
        unique_entries[entry.link] = entry

    all_entries = list(unique_entries.values())

    # Pick a random fresh news item
    news = random.choice(all_entries)

    print(f"📰 Found: {news.title}")

    return news


# =========================
# GENERATE EDUCATIONAL TOPIC
# =========================

def generate_educational_topic():
    topics = [
        "how to manage personal money",
        "how to save money",
        "how to build an emergency fund",
        "how to avoid unnecessary debt",
        "how to increase income",
        "how to make money online realistically",
        "skills that can increase income",
        "how artificial intelligence can help people earn money",
        "how to start investing responsibly",
        "what diversification means",
        "what compound interest means",
        "how inflation affects ordinary people",
        "common financial mistakes",
        "how to create a personal budget",
        "how to control impulsive spending",
        "how to evaluate financial risks",
        "how to develop better money habits",
        "how to turn a skill into additional income",
        "how to negotiate a higher salary",
        "how to create additional sources of income",
    ]

    return random.choice(topics)


# =========================
# GENERATE AI CONTENT
# =========================

def generate_content(news_entry=None):
    print("🤖 AI is analyzing with Groq...")

    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY is not configured!")
        return None

    try:
        client = Groq(api_key=GROQ_API_KEY)

        content_type = random.choice(CONTENT_TYPES)

        # -------------------------
        # NEWS
        # -------------------------

        if content_type == "news" and news_entry:

            prompt = f"""
Ты — профессиональный русскоязычный редактор финансового Telegram-канала.

Твоя задача — объяснить финансовую новость обычному человеку простым языком.

Новость:

ЗАГОЛОВОК:
{news_entry.title}

ССЫЛКА:
{news_entry.link}

Напиши:

1. TELEGRAM — подробный пост на русском языке.
2. X_POST — короткий пост на русском языке.

Для Telegram:
- 3-6 небольших абзацев.
- Используй подходящие эмодзи.
- Объясни, что произошло.
- Объясни, почему это важно.
- Объясни возможное влияние на обычных людей.
- Добавь небольшой практический вывод.
- Можно добавить лёгкую шутку или иронию.
- Не выдумывай факты.
- Не выдавай предположения за факты.

Для X:
- Коротко.
- Интересно.
- Русский язык.
- 1-2 подходящих хэштега.
- Не используй кликбейт без причины.

В конце Telegram добавь:

⚠️ Материал носит информационный характер и не является индивидуальной финансовой рекомендацией.

Формат ответа должен быть строго:

TELEGRAM:
текст

X_POST:
текст
"""

        # -------------------------
        # EDUCATION / MONEY / INCOME
        # -------------------------

        else:

            topic = generate_educational_topic()

            prompt = f"""
Ты — автор современного русскоязычного финансового канала.

Тема:
{topic}

Создай полезный образовательный материал для обычного человека.

Основные направления:
- личные финансы;
- управление деньгами;
- инвестиционная грамотность;
- способы увеличения дохода;
- дополнительные источники дохода;
- финансовые привычки;
- предпринимательство;
- работа и навыки;
- использование ИИ для повышения продуктивности и дохода.

ВАЖНЫЕ ПРАВИЛА:

- Только русский язык.
- Объясняй простыми словами.
- Не обещай гарантированный заработок.
- Не говори, что человек гарантированно заработает деньги.
- Не рекламируй сомнительные схемы.
- Не придумывай статистику.
- Не выдавай инвестиционные предположения за факты.
- Не советуй конкретно покупать или продавать активы.
- Лёгкий юмор разрешён.
- Стиль должен быть современным и живым.

Для Telegram:
- 4-7 небольших абзацев.
- Эмодзи.
- Конкретные советы.
- В конце небольшой практический вывод.

Для X:
- Короткая полезная мысль.
- Русский язык.
- 1-2 хэштега.

В конце Telegram добавь:

⚠️ Материал носит информационный и образовательный характер и не является индивидуальной финансовой рекомендацией.

Формат ответа строго:

TELEGRAM:
текст

X_POST:
текст
"""

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты пишешь качественный русскоязычный "
                        "финансово-образовательный контент."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=800
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

        # X has a character limit
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        client_x.create_tweet(text=tweet_text)

        print("✅ Posted to X!")

    except Exception as e:
        print(f"❌ X Error: {e}")


# =========================
# SEND TELEGRAM
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

    print("🚀 Financial Bot started!")

    news = get_news()

    # 50/50:
    # If there is news, sometimes use it.
    # Otherwise generate educational content.

    if random.random() < 0.5 and news:
        ai_content = generate_content(news)
        history_link = news.link

    else:
        ai_content = generate_content(None)

        if news:
            history_link = news.link
        else:
            history_link = None

    if ai_content:

        # Telegram
        send_telegram(
            ai_content["telegram"],
            history_link if history_link else "Financial education"
        )

        # X
        if ai_content["x"]:
            post_to_x(ai_content["x"])

        # Save news to history
        if history_link:
            with open("history.txt", "a", encoding="utf-8") as f:
                f.write(history_link + "\n")

        print("✅ Content processed successfully!")

    else:
        print("❌ Content generation failed.")
