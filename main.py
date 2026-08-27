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
    "https://news.google.com/rss/search?q=business+economy&hl=en-US&gl=US&ceid=US:en",
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
                link = getattr(entry, "link", "")

                if link and link not in history:
                    all_entries.append(entry)

        except Exception as e:
            print(f"⚠️ RSS Error: {e}")

    if not all_entries:
        print("ℹ️ No new news found.")
        return None

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

    replacements = [
        ("**", ""),
        ("__", ""),
        ("```", ""),
        ("`", ""),
        ("~~", ""),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    cleaned_lines = []

    for line in text.splitlines():

        line = line.strip()

        if line.startswith("#"):
            line = line.lstrip("#").strip()

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


# =========================
# GROQ REQUEST
# =========================

def ask_groq(client, prompt):

    for attempt in range(1, 3):

        print(f"🤖 Groq request attempt {attempt}/2...")

        try:

            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты профессиональный русскоязычный "
                            "финансовый редактор. "
                            "Отвечай только на русском языке. "
                            "Не используй Markdown."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_completion_tokens=1000
            )

            # Диагностика
            print(f"📡 Groq finish reason: {completion.choices[0].finish_reason}")

            message = completion.choices[0].message

            text = message.content

            if text and text.strip():

                print("✅ Groq returned text!")

                return text.strip()

            print("⚠️ Groq returned empty content.")

        except Exception as e:

            print(f"⚠️ Groq attempt {attempt} error: {e}")

    print("❌ Groq failed after 2 attempts.")

    return None


# =========================
# GENERATE CONTENT
# =========================

def generate_content(news_entry=None):

    print("🤖 AI is analyzing with Groq...")

    if not GROQ_API_KEY:

        print("❌ GROQ_API_KEY is not configured!")

        return None

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

        # =========================
        # NEWS
        # =========================

        if news_entry:

            prompt = f"""
Ты ведёшь русскоязычный финансовый канал.

Проанализируй новость:

Заголовок:
{news_entry.title}

Источник:
{news_entry.link}

Создай качественный пост для Telegram и короткую версию для X.

TELEGRAM:

Напиши 3-6 небольших абзацев.

Объясни:
1. Что произошло.
2. Почему это важно.
3. Как это может повлиять на обычных людей.
4. Какой можно сделать практический вывод.

Можно использовать эмодзи.

Можно использовать лёгкий юмор или иронию.

НЕ выдумывай факты.

НЕ добавляй информацию, которой нет в предоставленной новости.

НЕ добавляй ссылку.

НЕ используй Markdown.

НЕ используй **.

НЕ используй *.

НЕ используй __.

НЕ используй `.

НЕ используй #.

X_POST:

Напиши короткий пост максимум 280 символов.

Русский язык.

Можно использовать 1-2 хэштега.

Без Markdown.

В конце Telegram:

⚠️ Материал носит информационный характер и не является индивидуальной финансовой рекомендацией.

Формат ответа:

TELEGRAM:
текст

X_POST:
текст
"""

        # =========================
        # EDUCATION
        # =========================

        else:

            topic = generate_educational_topic()

            prompt = f"""
Создай полезный пост для современного русскоязычного финансового канала.

Тема:
{topic}

Направления канала:

личные финансы;
управление деньгами;
финансовая грамотность;
инвестиции;
увеличение дохода;
дополнительный заработок;
работа;
полезные навыки;
ИИ и заработок;
предпринимательство.

Стиль:

Умный друг, который хорошо разбирается в деньгах.

Текст должен быть серьёзным и полезным, но живым.

Можно использовать лёгкий юмор.

Не обещай гарантированный заработок.

Не рекламируй сомнительные схемы.

Не придумывай статистику.

Не советуй конкретно покупать или продавать активы.

TELEGRAM:

4-7 небольших абзацев.

Используй эмодзи.

Дай конкретный практический совет.

НЕ добавляй ссылки.

НЕ используй Markdown.

НЕ используй **.

НЕ используй *.

НЕ используй __.

НЕ используй `.

НЕ используй #.

В конце:

⚠️ Материал носит информационный и образовательный характер и не является индивидуальной финансовой рекомендацией.

X_POST:

Короткая полезная мысль.

Максимум 280 символов.

Русский язык.

Можно 1-2 хэштега.

Без Markdown.

Формат:

TELEGRAM:
текст

X_POST:
текст
"""

        text = ask_groq(
            client,
            prompt
        )

        if not text:

            return None

        parts = text.split(
            "X_POST:",
            1
        )

        telegram_text = (
            parts[0]
            .replace("TELEGRAM:", "")
            .strip()
        )

        if len(parts) > 1:

            x_text = parts[1].strip()

        else:

            x_text = ""

        telegram_text = clean_text(
            telegram_text
        )

        x_text = clean_text(
            x_text
        )

        if not telegram_text:

            print("❌ Telegram content is empty.")

            return None

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

    if not TELEGRAM_BOT_TOKEN:

        print("❌ TELEGRAM_BOT_TOKEN is missing!")

        return False

    if not TELEGRAM_CHAT_ID:

        print("❌ TELEGRAM_CHAT_ID is missing!")

        return False

    try:

        url = (
            "https://api.telegram.org/"
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

        return True

    except Exception as e:

        print(f"❌ Telegram Error: {e}")

        return False


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

        print(
            "⚠️ X API credentials are not configured. "
            "Skipping X."
        )

        return

    try:

        client_x = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_SECRET
        )

        if len(tweet_text) > 280:

            tweet_text = (
                tweet_text[:277]
                + "..."
            )

        client_x.create_tweet(
            text=tweet_text
        )

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
    # NEWS / EDUCATIONAL CONTENT

    if random.random() < 0.5 and news:

        print("📰 Content type: NEWS")

        ai_content = generate_content(
            news
        )

        history_link = news.link

    else:

        print("💡 Content type: EDUCATIONAL")

        ai_content = generate_content(
            None
        )

        history_link = None

    if ai_content:

        telegram_success = send_telegram(
            ai_content["telegram"]
        )

        if ai_content["x"]:

            post_to_x(
                ai_content["x"]
            )

        if telegram_success and history_link:

            with open(
                "history.txt",
                "a",
                encoding="utf-8"
            ) as f:

                f.write(
                    history_link + "\n"
                )

        print(
            "✅ Content processed successfully!"
        )

    else:

        print(
            "❌ Content generation failed."
        )
