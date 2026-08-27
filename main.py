import os
import random
import re
import base64
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

# Cloudflare
CLOUDFLARE_API_KEY = os.environ.get("CLOUDFLARE_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

# Pexels
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")


# ============================================================
# SETTINGS
# ============================================================

CLOUDFLARE_IMAGE_MODEL = (
    "@cf/black-forest-labs/flux-1-schnell"
)

MAX_TELEGRAM_LENGTH = 3900


# ============================================================
# NEWS RSS
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

    with open(
        "history.txt",
        "r",
        encoding="utf-8"
    ) as f:

        return set(
            line.strip()
            for line in f
            if line.strip()
        )


# ============================================================
# GET NEWS
# ============================================================

def get_news():

    print("🌍 Scanning financial news...")

    history = get_history()

    entries = []

    for rss_url in RSS_FEEDS:

        try:

            feed = feedparser.parse(
                rss_url
            )

            for entry in feed.entries:

                link = getattr(
                    entry,
                    "link",
                    ""
                )

                if (
                    link
                    and link not in history
                ):

                    entries.append(
                        entry
                    )

        except Exception as e:

            print(
                f"⚠️ RSS error: {e}"
            )

    if not entries:

        print(
            "ℹ️ No new news found."
        )

        return None

    unique = {}

    for entry in entries:

        unique[entry.link] = entry

    entries = list(
        unique.values()
    )

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

        "как планировать крупные покупки",

        "как создать несколько источников дохода",

        "как повысить свою ценность на рынке труда",

        "как попросить повышение зарплаты",

        "как превратить навык в дополнительный доход",

        "как экономить деньги без постоянных ограничений",

        "как научиться правильно обращаться с деньгами"

    ]

    return random.choice(
        topics
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.replace(
        "`",
        ""
    )

    text = text.replace(
        "~~",
        ""
    )

    # Убираем Markdown-заголовки
    lines = []

    for line in text.splitlines():

        line = line.strip()

        while line.startswith("#"):

            line = line[1:].strip()

        lines.append(line)

    text = "\n".join(
        lines
    )

    # Убираем URL
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
# AI RESPONSE PARSER
# ============================================================

def parse_ai_response(text):

    if not text:
        return None

    text = clean_text(
        text
    )

    if "TELEGRAM:" in text:

        text = text.split(
            "TELEGRAM:",
            1
        )[1]

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
# TEXT CHECK
# ============================================================

def good_text(text):

    if not text:
        return False

    if len(text) < 250:
        return False

    if text[-1] in ",:;—-(":
        return False

    return True


# ============================================================
# GROQ
# ============================================================

def ask_groq(
    client,
    prompt
):

    for attempt in range(1, 4):

        print(
            f"🤖 Groq request {attempt}/3..."
        )

        try:

            completion = client.chat.completions.create(

                model="openai/gpt-oss-20b",

                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты профессиональный автор "
                            "русскоязычного финансового "
                            "Telegram-канала. "
                            "Пиши живо, интересно "
                            "и понятно."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0.65,

                max_completion_tokens=4096,

                reasoning_effort="low"
            )

            if not completion.choices:

                continue

            choice = (
                completion.choices[0]
            )

            finish_reason = (
                choice.finish_reason
            )

            print(
                f"📡 Groq finish reason: "
                f"{finish_reason}"
            )

            content = (
                choice.message.content
            )

            if not content:
                continue

            result = parse_ai_response(
                content
            )

            if not result:
                continue

            if good_text(
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

    return None


# ============================================================
# GENERATE CONTENT
# ============================================================

def generate_content(
    news=None
):

    if not GROQ_API_KEY:

        print(
            "❌ GROQ_API_KEY is missing!"
        )

        return None

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

        # ----------------------------------------------------
        # NEWS
        # ----------------------------------------------------

        if news:

            prompt = f"""
Создай очень интересный пост для
русскоязычного финансового Telegram-канала.

НОВОСТЬ:

{news.title}

Пиши так, чтобы человек захотел дочитать
публикацию до конца.

Используй много, но уместно, эмодзи.

СТРУКТУРА:

🔥 ВАЖНОЕ ЗА СЕГОДНЯ

Заголовок должен быть коротким
и цепляющим.

📰 ЧТО ПРОИЗОШЛО

Простыми словами объясни событие.

📊 ПОЧЕМУ ЭТО ВАЖНО

Объясни значение новости.

👀 ЧТО ЭТО ЗНАЧИТ ДЛЯ ЛЮДЕЙ

Объясни возможное влияние
на обычного человека.

💡 ГЛАВНЫЙ ВЫВОД

Дай короткий практический вывод.

Используй дополнительные эмодзи:
💰 📈 📉 💡 📊 👀 🎯 🚀 ⚠️ 🔥

Не ставь эмодзи после каждого слова.
Они должны улучшать внешний вид.

Не выдумывай факты.

Не добавляй ссылку.

Не используй Markdown.

Не используй **.

Не используй *.

Не используй __.

Не используй обратные кавычки.

Пост должен быть полностью закончен.

Объём примерно 150-250 слов.

В самом конце:

⚠️ Материал носит информационный характер
и не является индивидуальной финансовой рекомендацией.

После этого:

X_POST:

Короткая версия новости для X.
До 280 символов.
Русский язык.
Можно использовать эмодзи.
Без ссылок.
"""

        # ----------------------------------------------------
        # EDUCATIONAL
        # ----------------------------------------------------

        else:

            topic = (
                get_educational_topic()
            )

            prompt = f"""
Создай интересный образовательный пост
для русского финансового Telegram-канала.

ТЕМА:

{topic}

Пост должен быть полезным,
понятным и увлекательным.

СТРУКТУРА:

💰 ЦЕПЛЯЮЩИЙ ЗАГОЛОВОК

Начни с интересной мысли,
вопроса или неожиданного факта.

🧠 В ЧЁМ СУТЬ?

Объясни тему простыми словами.

📌 ЧТО МОЖНО СДЕЛАТЬ?

Дай конкретные действия.

💡 ПРОСТОЙ ПРИМЕР

Приведи понятный жизненный пример.

🚀 ГЛАВНАЯ МЫСЛЬ

Сделай сильный итоговый вывод.

Используй уместные эмодзи:

💰 💡 📌 🧠 🚀 🎯 📈 📊 👀 ⚠️ 🔥

Не ставь эмодзи после каждого предложения.

Не обещай гарантированный заработок.

Не рекламируй сомнительные схемы.

Не придумывай статистику.

Не давай персональных инвестиционных
рекомендаций.

Не советуй конкретно покупать
или продавать активы.

Не добавляй ссылки.

Не используй Markdown.

Не используй **.

Не используй *.

Не используй __.

Не используй обратные кавычки.

Пост должен быть полностью закончен.

Объём примерно 150-250 слов.

В конце:

⚠️ Материал носит информационный
и образовательный характер и не является
индивидуальной финансовой рекомендацией.

После этого:

X_POST:

Короткая полезная мысль для X.
До 280 символов.
Русский язык.
Можно использовать эмодзи.
Без ссылок.
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
# IMAGE PROMPT
# ============================================================

def create_image_prompt(
    news,
    content
):

    if news:

        subject = news.title

    else:

        subject = content[
            "telegram"
        ][:800]

    return f"""
Create a professional editorial financial
illustration for a Russian finance news channel.

Topic:
{subject}

Style:

modern financial magazine,
professional editorial photography,
realistic,
cinematic lighting,
clean composition,
premium business aesthetic,
financial markets,
money and economy symbolism,
no text,
no letters,
no logos,
no watermark,
no numbers,
no readable signs.

The image should look attractive
as a Telegram channel cover image.
"""


# ============================================================
# CLOUDFLARE AI IMAGE
# ============================================================

def generate_cloudflare_image(
    prompt
):

    if not CLOUDFLARE_API_KEY:

        print(
            "⚠️ CLOUDFLARE_API_KEY missing."
        )

        return None

    if not CLOUDFLARE_ACCOUNT_ID:

        print(
            "⚠️ CLOUDFLARE_ACCOUNT_ID missing."
        )

        return None

    print(
        "🎨 Trying Cloudflare FLUX..."
    )

    url = (
        "https://api.cloudflare.com/client/v4/"
        f"accounts/{CLOUDFLARE_ACCOUNT_ID}"
        "/ai/run/"
        "@cf/black-forest-labs/flux-1-schnell"
    )

    try:

        response = requests.post(

            url,

            headers={
                "Authorization":
                    f"Bearer {CLOUDFLARE_API_KEY}",

                "Content-Type":
                    "application/json"
            },

            json={
                "prompt": prompt,
                "steps": 4
            },

            timeout=120
        )

        if response.status_code != 200:

            print(
                "⚠️ Cloudflare image error:"
                f" {response.status_code}"
            )

            print(
                response.text[:500]
            )

            return None

        data = response.json()

        result = data.get(
            "result"
        )

        if not result:

            print(
                "⚠️ Cloudflare returned "
                "no result."
            )

            return None

        image_base64 = result.get(
            "image"
        )

        if not image_base64:

            print(
                "⚠️ Cloudflare returned "
                "no image."
            )

            return None

        image_bytes = base64.b64decode(
            image_base64
        )

        filename = "generated_image.jpg"

        with open(
            filename,
            "wb"
        ) as f:

            f.write(
                image_bytes
            )

        print(
            "✅ Cloudflare image generated!"
        )

        return filename

    except Exception as e:

        print(
            f"⚠️ Cloudflare image error: {e}"
        )

        return None


# ============================================================
# PEXELS SEARCH
# ============================================================

def get_pexels_query(
    news,
    content
):

    text = (
        news.title
        if news
        else content["telegram"]
    )

    text = text.lower()

    keywords = {

        "inflation": "inflation economy",

        "economy": "economy business",

        "market": "stock market",

        "stocks": "stock market",

        "bank": "bank finance",

        "banks": "bank finance",

        "money": "money finance",

        "investment": "investment finance",

        "investing": "investment finance",

        "bitcoin": "bitcoin cryptocurrency",

        "crypto": "cryptocurrency",

        "dollar": "dollar money",

        "euro": "euro money",

        "salary": "salary work",

        "income": "business income",

        "business": "business office",

        "job": "career business",

        "ai": "artificial intelligence technology",

    }

    for word, query in keywords.items():

        if word in text:

            return query

    return "finance business money"


# ============================================================
# PEXELS IMAGE
# ============================================================

def get_pexels_image(
    news,
    content
):

    if not PEXELS_API_KEY:

        print(
            "⚠️ PEXELS_API_KEY missing."
        )

        return None

    query = get_pexels_query(
        news,
        content
    )

    print(
        f"📸 Searching Pexels: {query}"
    )

    url = (
        "https://api.pexels.com/v1/search"
    )

    try:

        response = requests.get(

            url,

            headers={
                "Authorization":
                    PEXELS_API_KEY
            },

            params={
                "query": query,
                "per_page": 10,
                "orientation": "portrait"
            },

            timeout=30
        )

        if response.status_code != 200:

            print(
                "⚠️ Pexels error:"
                f" {response.status_code}"
            )

            return None

        data = response.json()

        photos = data.get(
            "photos",
            []
        )

        if not photos:

            print(
                "⚠️ Pexels found no photos."
            )

            return None

        # Берём случайное из первых результатов
        photo = random.choice(
            photos[:5]
        )

        image_url = (
            photo
            .get("src", {})
            .get("large2x")
        )

        if not image_url:

            return None

        image_response = requests.get(
            image_url,
            timeout=60
        )

        image_response.raise_for_status()

        filename = "pexels_image.jpg"

        with open(
            filename,
            "wb"
        ) as f:

            f.write(
                image_response.content
            )

        print(
            "✅ Pexels image downloaded!"
        )

        return filename

    except Exception as e:

        print(
            f"⚠️ Pexels error: {e}"
        )

        return None


# ============================================================
# GET IMAGE
# ============================================================

def get_image(
    news,
    content
):

    prompt = create_image_prompt(
        news,
        content
    )

    # First: AI
    image = generate_cloudflare_image(
        prompt
    )

    if image:

        return image

    # Backup: Pexels
    print(
        "🔄 AI image failed. "
        "Trying Pexels..."
    )

    image = get_pexels_image(
        news,
        content
    )

    if image:

        return image

    print(
        "⚠️ No image available."
    )

    return None


# ============================================================
# TELEGRAM TEXT
# ============================================================

def send_telegram_text(
    text
):

    if not TELEGRAM_BOT_TOKEN:
        return False

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    try:

        response = requests.post(

            url,

            data={
                "chat_id":
                    TELEGRAM_CHAT_ID,

                "text":
                    text
            },

            timeout=30
        )

        response.raise_for_status()

        return True

    except Exception as e:

        print(
            f"❌ Telegram text error: {e}"
        )

        return False


# ============================================================
# TELEGRAM PHOTO
# ============================================================

def send_telegram_photo(
    image_path,
    text
):

    if not TELEGRAM_BOT_TOKEN:
        return False

    url = (
        "https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    )

    try:

        with open(
            image_path,
            "rb"
        ) as photo:

            response = requests.post(

                url,

                data={
                    "chat_id":
                        TELEGRAM_CHAT_ID,

                    "caption":
                        text
                },

                files={
                    "photo":
                        photo
                },

                timeout=90
            )

        response.raise_for_status()

        print(
            "✅ Telegram photo sent!"
        )

        return True

    except Exception as e:

        print(
            f"⚠️ Telegram photo error: {e}"
        )

        return False


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(
    text,
    image_path=None
):

    # Telegram caption has a lower limit
    # than a normal message.
    if image_path and len(text) <= 1024:

        success = send_telegram_photo(
            image_path,
            text
        )

        if success:
            return True

    # If caption is too long or photo failed,
    # send photo separately and then text.
    if image_path:

        photo_sent = send_telegram_photo(
            image_path,
            ""
        )

        if photo_sent:

            return send_telegram_text(
                text
            )

    return send_telegram_text(
        text
    )


# ============================================================
# X
# ============================================================

def post_to_x(
    text
):

    if not all([
        X_API_KEY,
        X_API_SECRET,
        X_ACCESS_TOKEN,
        X_ACCESS_SECRET
    ]):

        print(
            "⚠️ X credentials missing."
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
            f"❌ X error: {e}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "🚀 Financial Bot started!"
    )

    news = get_news()

    # 50/50 NEWS / EDUCATIONAL
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

    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    image_path = get_image(
        news if use_news else None,
        content
    )

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    telegram_success = send_telegram(
        content["telegram"],
        image_path
    )

    # --------------------------------------------------------
    # X
    # --------------------------------------------------------

    if content["x"]:

        post_to_x(
            content["x"]
        )

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

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
