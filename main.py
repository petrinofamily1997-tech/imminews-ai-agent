import os
import random
import re
import feedparser
import requests
import tweepy
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# KEYS
# ============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")


# ============================================================
# NEWS
# ============================================================

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=finance+economy+markets&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=personal+finance+money&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=investing+stocks+economy&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=business+economy&hl=en-US&gl=US&ceid=US:en",
]


# ============================================================
# HISTORY
# ============================================================

def get_history():
    if not os.path.exists("history.txt"):
        return set()

    with open("history.txt", "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


# ============================================================
# GET NEWS
# ============================================================

def get_news():
    print("🌍 Scanning financial news...")

    history = get_history()
    entries = []

    for rss_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                link = getattr(entry, "link", "")

                if link and link not in history:
                    entries.append(entry)

        except Exception as e:
            print(f"⚠️ RSS error: {e}")

    if not entries:
        print("ℹ️ No new news found.")
        return None

    # Remove duplicates
    unique = {}

    for entry in entries:
        unique[entry.link] = entry

    entries = list(unique.values())

    # Prefer newer entries when possible
    entries.sort(
        key=lambda x: getattr(x, "published_parsed", None) or (0,),
        reverse=True
    )

    news = entries[0]

    print(f"📰 Found: {news.title}")

    return news


# ============================================================
# EDUCATIONAL TOPICS
# ============================================================

def get_educational_topic():

    topics = [
        "как правильно вести личный бюджет",
        "как начать откладывать деньги",
        "как создать финансовую подушку",
        "как перестать тратить деньги на ненужные покупки",
        "как правильно пользоваться кредитами",
        "как избежать долгов",
        "как увеличить свой доход",
        "как найти дополнительный источник дохода",
        "как заработать дополнительные деньги с помощью полезного навыка",
        "какие навыки сегодня помогают увеличить доход",
        "как использовать искусственный интеллект для работы",
        "как использовать ИИ для дополнительного заработка",
        "как начать разбираться в инвестициях",
        "что такое диверсификация",
        "что такое сложный процент",
        "как инфляция влияет на личные финансы",
        "самые распространённые финансовые ошибки",
        "как контролировать импульсивные покупки",
        "как планировать крупные покупки",
        "как создать несколько источников дохода",
        "как повысить свою ценность на рынке труда",
        "как попросить повышение зарплаты",
        "как превратить хобби или навык в дополнительный доход",
        "как экономить деньги без постоянных ограничений",
        "как научиться правильно обращаться с деньгами",
    ]

    return random.choice(topics)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    # Remove markdown
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("```", "")
    text = text.replace("`", "")
    text = text.replace("~~", "")

    # Remove markdown headings
    lines = []

    for line in text.splitlines():

        line = line.strip()

        while line.startswith("#"):
            line = line[1:].strip()

        lines.append(line)

    text = "\n".join(lines)

    # Remove accidental links
    text = re.sub(
        r'https?://\S+',
        '',
        text
    )

    # Remove excessive empty lines
    text = re.sub(
        r'\n{3,}',
        '\n\n',
        text
    )

    return text.strip()


# ============================================================
# CHECK IF TEXT IS COMPLETE
# ============================================================

def is_complete_text(text):

    if not text:
        return False

    text = text.strip()

    # Too short
    if len(text) < 100:
        return False

    # Obvious unfinished ending
    bad_endings = [
        "и",
        "а",
        "но",
        "что",
        "как",
        "если",
        "когда",
        "потому что",
        "который",
        "которая",
        "которые",
        "повыс",
        "увелич",
        "сниз",
        "помог",
        "позвол",
        "мож",
        "важн",
        "поэтому",
        "например",
        "также",
        "однако",
    ]

    last_word = text.split()[-1].lower()

    for ending in bad_endings:
        if last_word.startswith(ending):
            return False

    # Must end with punctuation
    if text[-1] not in ".!?…»”\"":
        return False

    return True


# ============================================================
# GROQ REQUEST
# ============================================================

def ask_groq(client, prompt):

    for attempt in range(1, 4):

        print(f"🤖 Groq request {attempt}/3...")

        try:

            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты профессиональный редактор "
                            "русскоязычного финансового канала. "
                            "Пиши только на русском языке. "
                            "Никогда не используй Markdown."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_completion_tokens=1800
            )

            if not completion.choices:
                print("⚠️ Groq returned no choices.")
                continue

            text = completion.choices[0].message.content

            finish_reason = completion.choices[0].finish_reason

            print(
                f"📡 Groq finish reason: {finish_reason}"
            )

            if not text or not text.strip():
                print("⚠️ Empty Groq response.")
                continue

            text = clean_text(text)

            if is_complete_text(text):
                print("✅ Complete Groq response!")
                return text

            print("⚠️ Text appears incomplete.")

        except Exception as e:

            print(
                f"⚠️ Groq attempt {attempt} error: {e}"
            )

    return None


# ============================================================
# GENERATE CONTENT
# ============================================================

def generate_content(news=None):

    if not GROQ_API_KEY:

        print("❌ GROQ_API_KEY is missing!")

        return None

    print("🤖 AI is analyzing with Groq...")

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

        # ====================================================
        # NEWS
        # ====================================================

        if news:

            prompt = f"""
Создай полноценный пост для русскоязычного финансового Telegram-канала.

ФИНАНСОВАЯ НОВОСТЬ:

Заголовок:
{news.title}

Источник:
{news.link}

Твоя задача:

Объяснить новость обычному человеку.

Структура Telegram-поста:

📰 Короткий заголовок

Затем 3-6 небольших абзацев.

Обязательно объясни:

Что произошло.

Почему это важно.

Как это может повлиять на обычных людей.

Что читателю стоит понимать или учитывать.

В конце сделай короткий практический вывод.

Можно использовать эмодзи.

Можно использовать лёгкий юмор.

Не выдумывай факты.

Не добавляй информацию, которой нет в новости или которую невозможно разумно вывести из неё.

Не давай персональных финансовых рекомендаций.

Не обещай заработок.

НЕ добавляй ссылку на источник.

НЕ используй Markdown.

НЕ используй символы **

НЕ используй символы *

НЕ используй символы __

НЕ используй обратные кавычки.

НЕ используй #.

Пиши обычным текстом.

Очень важно:

Пост должен быть полностью закончен.

Последнее предложение обязательно должно быть завершено.

Нельзя заканчивать текст посреди слова или предложения.

После написания проверь текст перед ответом.

В конце:

⚠️ Материал носит информационный характер и не является индивидуальной финансовой рекомендацией.

После этого напиши:

X_POST:

Короткий пост для X на русском языке.

Максимум 280 символов.

Без Markdown.

Можно использовать 1-2 хэштега.

Формат:

TELEGRAM:
текст

X_POST:
текст
"""

        # ====================================================
        # EDUCATIONAL
        # ====================================================

        else:

            topic = get_educational_topic()

            prompt = f"""
Создай полноценный образовательный пост для современного
русскоязычного финансового Telegram-канала.

ТЕМА:
{topic}

Пост должен быть полезным обычному человеку.

Направления:

личные финансы;
экономия;
финансовая грамотность;
инвестиции;
увеличение дохода;
дополнительный заработок;
работа;
полезные навыки;
искусственный интеллект;
предпринимательство.

Стиль:

Умный друг, который хорошо разбирается в деньгах.

Пиши понятно и живо.

Можно использовать лёгкий юмор.

Структура:

💰 Короткий заголовок

4-7 небольших абзацев.

Объясни проблему.

Дай конкретные советы.

Приведи простой пример.

В конце сделай практический вывод.

Не обещай гарантированный заработок.

Не рекламируй сомнительные схемы.

Не придумывай статистику.

Не советуй конкретно покупать или продавать активы.

НЕ добавляй ссылки.

НЕ используй Markdown.

НЕ используй **

НЕ используй *

НЕ используй __

НЕ используй обратные кавычки.

НЕ используй #.

Пиши обычным текстом.

Очень важно:

Пост должен быть полностью закончен.

Последнее предложение обязательно должно быть завершено.

Нельзя заканчивать текст посреди слова или предложения.

После написания проверь текст перед ответом.

В конце:

⚠️ Материал носит информационный и образовательный характер и не является индивидуальной финансовой рекомендацией.

После этого:

X_POST:

Короткая полезная мысль для X.

Максимум 280 символов.

Без Markdown.

Можно использовать 1-2 хэштега.

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
            print("❌ Groq failed to create content.")
            return None

        # ====================================================
        # SPLIT TELEGRAM / X
        # ====================================================

        if "X_POST:" in text:

            telegram_text, x_text = text.split(
                "X_POST:",
                1
            )

        else:

            telegram_text = text
            x_text = ""

        telegram_text = telegram_text.replace(
            "TELEGRAM:",
            ""
        ).strip()

        x_text = x_text.strip()

        telegram_text = clean_text(
            telegram_text
        )

        x_text = clean_text(
            x_text
        )

        # Final safety check
        if not is_complete_text(
            telegram_text
        ):

            print(
                "❌ Telegram text failed "
                "completion check."
            )

            return None

        return {
            "telegram": telegram_text,
            "x": x_text
        }

    except Exception as e:

        print(
            f"❌ Groq Error: {e}"
        )

        return None


# ============================================================
# TELEGRAM
# ============================================================

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

        print(
            f"❌ Telegram Error: {e}"
        )

        return False


# ============================================================
# X
# ============================================================

def post_to_x(text):

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

        if len(text) > 280:
            text = text[:277] + "..."

        client_x.create_tweet(
            text=text
        )

        print("✅ Posted to X!")

    except Exception as e:

        print(
            f"❌ X Error: {e}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("🚀 Financial Bot started!")

    news = get_news()

    # 50/50 NEWS / EDUCATIONAL
    use_news = (
        news is not None
        and random.random() < 0.5
    )

    if use_news:

        print("📰 Content type: NEWS")

        content = generate_content(
            news
        )

    else:

        print("💡 Content type: EDUCATIONAL")

        content = generate_content(
            None
        )

    if not content:

        print(
            "❌ Content generation failed."
        )

        raise SystemExit(1)

    # ========================================================
    # TELEGRAM
    # ========================================================

    telegram_success = send_telegram(
        content["telegram"]
    )

    # ========================================================
    # X
    # ========================================================

    if content["x"]:

        post_to_x(
            content["x"]
        )

    # ========================================================
    # SAVE NEWS ONLY AFTER SUCCESS
    # ========================================================

    if telegram_success and use_news:

        with open(
            "history.txt",
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                news.link + "\n"
            )

    print(
        "✅ Content processed successfully!"
    )
