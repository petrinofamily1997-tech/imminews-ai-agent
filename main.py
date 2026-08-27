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
# HISTORY
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

    # Убираем дубликаты
    unique_entries = {}

    for entry in all_entries:
        unique_entries[entry.link] = entry

    all_entries = list(unique_entries.values())

    news = random.choice(all_entries)

    print(f"📰 Found: {news.title}")

    return news


# =========================
# EDUCATIONAL TOPICS
# =========================

def generate_educational_topic():

    topics = [
        "как правильно вести личный бюджет",
        "как начать откладывать деньги",
        "как создать финансовую подушку",
        "как избавиться от ненужных расходов",
        "как правильно пользоваться кредитами",
        "как избежать долговой ямы",
        "как увеличить свой доход",
        "как найти дополнительный источник дохода",
        "как начать зарабатывать в интернете без мошеннических схем",
        "какие навыки могут увеличить доход",
        "как использовать искусственный интеллект для работы",
        "как использовать ИИ для дополнительного заработка",
        "как начать разбираться в инвестициях",
        "что такое диверсификация",
        "что такое сложный процент",
        "как инфляция влияет на деньги",
        "какие финансовые ошибки совершают люди",
        "как контролировать импульсивные покупки",
        "как правильно планировать крупные покупки",
        "как создать несколько источников дохода",
        "как повысить свою стоимость на рынке труда",
        "как просить повышение зарплаты",
        "как превратить свой навык в дополнительный доход",
        "как экономить деньги без постоянных ограничений",
        "как научиться обращаться с деньгами",
    ]

    return random.choice(topics)


# =========================
# CLEAN TEXT
# =========================

def clean_text(text):

    if not text:
        return ""

    # Убираем Markdown
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("```", "")
    text = text.replace("`", "")
    text = text.replace("~~", "")

    # Убираем возможные заголовочные символы
    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line.startswith("#"):
            line = line.lstrip("#").strip()

        lines.append(line)

    text = "\n".join(lines)

    return text.strip()


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

        # =========================
        # NEWS
        # =========================

        if content_type == "news" and news_entry:

            prompt = f"""
Ты — редактор современного русскоязычного финансового канала.

Проанализируй эту финансовую новость:

ЗАГОЛОВОК:
{news_entry.title}

ИСТОЧНИК:
{news_entry.link}

Создай пост для Telegram и короткую версию для X.

Telegram:

Напиши 3-6 небольших абзацев.

Обязательно:
- русский язык;
- простое объяснение;
- объясни, что произошло;
- объясни, почему это важно;
- объясни возможное влияние на обычных людей;
- добавь практический вывод;
- можно использовать эмодзи;
- разрешён лёгкий юмор и ирония;
- не выдумывай факты.

Очень важно:

НЕ используй Markdown.

НЕ используй символы **

НЕ используй символы *

НЕ используй символы __

НЕ используй обратные кавычки.

НЕ используй заголовки с #.

Пиши обычным чистым текстом.

Не добавляй ссылку на источник в Telegram.

X:

Создай короткий пост на русском языке.
Максимум 280 символов.
Можно использовать 1-2 хэштега.

Также не используй Markdown.

В конце Telegram добавь:

⚠️ Материал носит информационный характер и не является индивидуальной финансовой рекомендацией.

Формат:

TELEGRAM:
текст

X_POST:
текст
"""

        # =========================
        # EDUCATIONAL CONTENT
        # =========================

        else:

            topic = generate_educational_topic()

            prompt = f"""
Ты — автор современного русскоязычного финансового канала.

Тема:
{topic}

Создай полезный материал для обычного человека.

Направления:
- личные финансы;
- управление деньгами;
- инвестиционная грамотность;
- увеличение дохода;
- дополнительные источники дохода;
- финансовые привычки;
- предпринимательство;
- работа и навыки;
- использование ИИ для повышения продуктивности и дохода.

Стиль:

Пиши как умный друг, который хорошо разбирается в деньгах.

Информация должна быть серьёзной и полезной, но текст должен быть живым.

Можно использовать лёгкий юмор и иронию.

Не обещай гарантированный заработок.

Не рекламируй сомнительные схемы.

Не придумывай статистику.

Не советуй конкретно покупать или продавать финансовые активы.

Telegram:

4-7 небольших абзацев.

Используй подходящие эмодзи.

Дай конкретные и понятные советы.

В конце сделай небольшой практический вывод.

Очень важно:

НЕ используй Markdown.

НЕ используй символы **

НЕ используй символы *

НЕ используй символы __

НЕ используй обратные кавычки.

НЕ используй заголовки с #.

Пиши обычным чистым текстом.

Не добавляй ссылки.

В конце добавь:

⚠️ Материал носит информационный и образовательный характер и не является индивидуальной финансовой рекомендацией.

X:

Короткая полезная мысль на русском языке.

Максимум 280 символов.

Можно использовать 1-2 хэштега.

Без Markdown.

Формат:

TELEGRAM:
текст

X_POST:
текст
"""

        # =========================
        # GROQ REQUEST
        # =========================

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты качественный русскоязычный "
                        "финансово-образовательный редактор. "
                        "Никогда не используй Markdown."
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

        # Дополнительная очистка
        telegram_text = clean_text(telegram_text)
        x_text = clean_text(x_text)

        return {
            "telegram": telegram_text,
            "x": x_text
        }

    except Exception as e:

        print(f"❌ Groq Error: {e}")

        return None


# =========================
# TELEGRAM
# =========================

def send_telegram(text):

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
                "text": text
            },
            timeout=30
        )

        response.raise_for_status()

        print("✅ Sent to Telegram!")

    except Exception as e:

        print(f"❌ Telegram Error: {e}")


# =========================
# X
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

        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        client_x.create_tweet(text=tweet_text)

        print("✅ Posted to X!")

    except Exception as e:

        print(f"❌ X Error: {e}")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("🚀 Financial Bot started!")

    news = get_news()

    # 50/50:
    # 50% новости
    # 50% образовательный контент

    if random.random() < 0.5 and news:

        print("📰 Content type: NEWS")

        ai_content = generate_content(news)

        history_link = news.link

    else:

        print("💡 Content type: EDUCATIONAL")

        ai_content = generate_content(None)

        history_link = None

    if ai_content:

        # Отправляем только текст.
        # Ссылка больше НЕ добавляется.

        send_telegram(
            ai_content["telegram"]
        )

        # X
        if ai_content["x"]:

            post_to_x(
                ai_content["x"]
            )

        # Записываем новость в историю
        if history_link:

            with open(
                "history.txt",
                "a",
                encoding="utf-8"
            ) as f:

                f.write(history_link + "\n")

        print("✅ Content processed successfully!")

    else:

        print("❌ Content generation failed.")
