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
# API KEYS
# ============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET")


# ============================================================
# NEWS SOURCES
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
        return set(
            line.strip()
            for line in f
            if line.strip()
        )


# ============================================================
# NEWS
# ============================================================

def get_news():

    print("🌍 Scanning financial news...")

    history = get_history()
    entries = []

    for rss_url in RSS_FEEDS:

        try:

            feed = feedparser.parse(rss_url)

            for entry in feed.entries:

                link = getattr(
                    entry,
                    "link",
                    ""
                )

                if link and link not in history:

                    entries.append(entry)

        except Exception as e:

            print(f"⚠️ RSS Error: {e}")

    if not entries:

        print("ℹ️ No new news found.")

        return None

    unique = {}

    for entry in entries:

        unique[entry.link] = entry

    entries = list(unique.values())

    # Берём свежую новость
    entries.sort(
        key=lambda x:
        getattr(
            x,
            "published_parsed",
            None
        ) or (0,),
        reverse=True
    )

    news = entries[0]

    print(
        f"📰 Found: {news.title}"
    )

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

        "какие навыки помогают увеличить доход",

        "как использовать искусственный интеллект для работы",

        "как использовать ИИ для дополнительного заработка",

        "как начать разбираться в инвестициях",

        "что такое диверсификация",

        "что такое сложный процент",

        "как инфляция влияет на личные финансы",

        "самые распространённые финансовые ошибки",

        "как контролировать импульсивные покупки",

        "как правильно планировать крупные покупки",

        "как создать несколько источников дохода",

        "как повысить свою стоимость на рынке труда",

        "как попросить повышение зарплаты",

        "как превратить навык в дополнительный доход",

        "как экономить деньги без постоянных ограничений",

        "как научиться правильно обращаться с деньгами"

    ]

    return random.choice(topics)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:

        return ""

    # Убираем Markdown
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("```", "")
    text = text.replace("`", "")
    text = text.replace("~~", "")

    # Убираем заголовки Markdown
    lines = []

    for line in text.splitlines():

        line = line.strip()

        while line.startswith("#"):

            line = line[1:].strip()

        lines.append(line)

    text = "\n".join(lines)

    # Убираем ссылки
    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    # Убираем лишние пустые строки
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# CHECK TELEGRAM TEXT
# ============================================================

def telegram_text_is_good(text):

    if not text:

        return False

    text = text.strip()

    # Слишком короткий текст
    if len(text) < 250:

        return False

    # Если закончился на запятой/двоеточии/тире —
    # скорее всего предложение не закончено
    if text[-1] in ",:;—-(":

        return False

    return True


# ============================================================
# PARSE RESPONSE
# ============================================================

def parse_ai_response(text):

    if not text:

        return None

    text = clean_text(text)

    # Ищем Telegram
    if "TELEGRAM:" in text:

        text = text.split(
            "TELEGRAM:",
            1
        )[1]

    # Разделяем X
    if "X_POST:" in text:

        telegram_text, x_text = text.split(
            "X_POST:",
            1
        )

    else:

        telegram_text = text
        x_text = ""

    telegram_text = clean_text(
        telegram_text
    )

    x_text = clean_text(
        x_text
    )

    if not telegram_text:

        return None

    return {
        "telegram": telegram_text,
        "x": x_text
    }


# ============================================================
# GROQ
# ============================================================

def ask_groq(client, prompt):

    for attempt in range(1, 4):

        print(
            f"🤖 Groq request {attempt}/3..."
        )

        try:

            completion = client.chat.completions.create(

                model="openai/gpt-oss-20b",

                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.5,

                max_completion_tokens=4096,

                reasoning_effort="low"
            )

            if not completion.choices:

                print(
                    "⚠️ Groq returned no choices."
                )

                continue

            choice = completion.choices[0]

            finish_reason = choice.finish_reason

            print(
                f"📡 Groq finish reason: "
                f"{finish_reason}"
            )

            content = choice.message.content

            # Иногда reasoning-модель может вернуть пустой content
            if not content:

                print(
                    "⚠️ Groq content is empty."
                )

                continue

            content = content.strip()

            if not content:

                print(
                    "⚠️ Groq content is blank."
                )

                continue

            result = parse_ai_response(
                content
            )

            if not result:

                print(
                    "⚠️ Could not parse Groq response."
                )

                continue

            # Если модель нормально завершила ответ,
            # принимаем его.
            if finish_reason == "stop":

                if telegram_text_is_good(
                    result["telegram"]
                ):

                    print(
                        "✅ Groq response accepted!"
                    )

                    return result

            # Если ответ был обрезан,
            # пробуем ещё раз.
            if finish_reason == "length":

                print(
                    "⚠️ Groq response hit length limit."
                )

                continue

            # На всякий случай принимаем хороший ответ
            if telegram_text_is_good(
                result["telegram"]
            ):

                print(
                    "✅ Groq response accepted!"
                )

                return result

        except Exception as e:

            print(
                f"⚠️ Groq error: {e}"
            )

    print(
        "❌ Groq failed after 3 attempts."
    )

    return None


# ============================================================
# GENERATE CONTENT
# ============================================================

def generate_content(news=None):

    print(
        "🤖 AI is analyzing with Groq..."
    )

    if not GROQ_API_KEY:

        print(
            "❌ GROQ_API_KEY is missing!"
        )

        return None

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

        # ====================================================
        # NEWS
        # ====================================================

        if news:

            prompt = f"""
Ты пишешь пост для русского финансового Telegram-канала.

НОВОСТЬ:

{news.title}

Задача:

Объясни эту новость обычному человеку.

Telegram-пост должен содержать:

📰 Заголовок

3-5 коротких абзацев.

Объясни:

Что произошло.

Почему это важно.

Как это может повлиять на обычных людей.

Что из этого следует.

Можно использовать эмодзи.

Можно добавить лёгкий юмор.

Не выдумывай факты.

Не добавляй ссылку.

Не используй Markdown.

Не используй **.

Не используй *.

Не используй __.

Не используй обратные кавычки.

Не используй символ # для заголовков.

Пиши обычным текстом.

Пост должен быть законченным.

Не заканчивай предложение на середине.

Объём Telegram-поста: примерно 120-250 слов.

В самом конце:

⚠️ Материал носит информационный характер и не является индивидуальной финансовой рекомендацией.

После Telegram напиши:

X_POST:

Короткий пост для X.

До 280 символов.

Русский язык.

Без Markdown.

Можно использовать 1-2 хэштега.
"""

        # ====================================================
        # EDUCATIONAL
        # ====================================================

        else:

            topic = get_educational_topic()

            prompt = f"""
Ты пишешь пост для современного русского финансового канала.

ТЕМА:

{topic}

Создай полезный материал для обычного человека.

Telegram:

🧠 Короткий заголовок

3-6 небольших абзацев.

Объясни тему простыми словами.

Дай конкретные советы.

Приведи простой пример.

В конце сделай практический вывод.

Можно использовать эмодзи.

Можно добавить лёгкий юмор.

Не обещай гарантированный заработок.

Не рекламируй сомнительные схемы.

Не придумывай статистику.

Не давай персональных инвестиционных рекомендаций.

Не советуй конкретно покупать или продавать активы.

Не добавляй ссылки.

Не используй Markdown.

Не используй **.

Не используй *.

Не используй __.

Не используй обратные кавычки.

Не используй # для заголовков.

Пиши обычным текстом.

Пост должен быть полностью закончен.

Не заканчивай предложение на середине.

Объём Telegram-поста: примерно 120-250 слов.

В самом конце:

⚠️ Материал носит информационный и образовательный характер и не является индивидуальной финансовой рекомендацией.

После Telegram:

X_POST:

Короткая полезная мысль для X.

До 280 символов.

Русский язык.

Без Markdown.

Можно использовать 1-2 хэштега.
"""

        return ask_groq(
            client,
            prompt
        )

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

        print(
            "❌ TELEGRAM_BOT_TOKEN is missing!"
        )

        return False

    if not TELEGRAM_CHAT_ID:

        print(
            "❌ TELEGRAM_CHAT_ID is missing!"
        )

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

        print(
            "✅ Sent to Telegram!"
        )

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

            text = (
                text[:277]
                + "..."
            )

        client_x.create_tweet(
            text=text
        )

        print(
            "✅ Posted to X!"
        )

    except Exception as e:

        print(
            f"❌ X Error: {e}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "🚀 Financial Bot started!"
    )

    news = get_news()

    # 50/50
    use_news = (
        news is not None
        and random.random() < 0.5
    )

    if use_news:

        print(
            "📰 Content type: NEWS"
        )

        content = generate_content(
            news
        )

    else:

        print(
            "💡 Content type: EDUCATIONAL"
        )

        content = generate_content()

    if not content:

        print(
            "❌ Content generation failed."
        )

        raise SystemExit(1)

    # Telegram
    telegram_success = send_telegram(
        content["telegram"]
    )

    # X
    if content["x"]:

        post_to_x(
            content["x"]
        )

    # Save news only after successful Telegram delivery
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
