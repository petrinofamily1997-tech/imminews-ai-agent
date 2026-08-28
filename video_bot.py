import os
import re
import json
import random
import shutil
import subprocess
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from groq import Groq


# ============================================================
# ENV
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MUSIC_DIR = BASE_DIR / "assets" / "music"
WORK_DIR = BASE_DIR / "video_work"
OUTPUT_DIR = BASE_DIR / "output"

AUDIO_FILE = WORK_DIR / "voice.mp3"
FINAL_VIDEO = OUTPUT_DIR / "video.mp4"

TOPICS_HISTORY_FILE = BASE_DIR / "topics_history.json"


# ============================================================
# VIDEO SETTINGS
# ============================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

MUSIC_VOLUME = 0.055

MIN_CLIPS = 8
MAX_CLIPS = 14

MIN_CLIP_SECONDS = 1.6
MAX_CLIP_SECONDS = 3.0

VOICE_TAIL = 0.90

TOPICS_HISTORY_SIZE = 15


# ============================================================
# GROQ MODELS
# ============================================================

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]


# ============================================================
# TOPICS
# ============================================================

MONEY_TOPICS = [

    "почему зарплата не делает человека богатым",
    "ловушка потребительских кредитов",
    "как инфляция незаметно съедает сбережения",
    "психология импульсивных покупок",
    "почему высокий доход не гарантирует богатство",
    "разница между активом и пассивом простыми словами",
    "как банки зарабатывают на обычных клиентах",
    "что такое финансовая подушка",
    "почему люди постоянно живут от зарплаты до зарплаты",
    "как выйти из цикла от зарплаты до зарплаты",
    "почему скидка не всегда означает экономию",
    "как подписки незаметно съедают бюджет",
    "почему финансовый план лучше силы воли",
    "как эмоции влияют на финансовые решения",
    "почему люди покупают вещи, которые им не нужны",
    "как увеличить доход без второго полноценного рабочего дня",
    "какие навыки позволяют увеличить доход",
    "как использовать искусственный интеллект для работы",
    "как использовать ИИ для дополнительного заработка",
    "почему деньги любят учет",
    "что происходит с деньгами во время экономической неопределенности",
    "как центральные банки влияют на стоимость денег",
    "как изменение процентной ставки влияет на кредиты",
    "почему цены растут не одинаково на все товары",
    "как компании зарабатывают на комиссиях",
    "почему рынок может падать даже при хороших новостях",
    "как паника влияет на финансовые решения",
    "почему инвестировать страшно",
    "разница между инвестированием и спекуляцией",
    "что такое диверсификация",
    "как не потерять деньги на импульсивных инвестиционных решениях",
    "почему высокий кредитный рейтинг не означает финансовую свободу",
    "как повышение зарплаты может привести к росту расходов",
    "почему богатые считают стоимость времени",
    "как реклама заставляет нас тратить больше",
    "почему бесплатные сервисы тоже хотят заработать на пользователе",

]


# ============================================================
# FREE NEWS RSS
# ============================================================

FREE_NEWS_RSS = [

    "https://news.google.com/rss/search?q=деньги+экономика+финансы&hl=ru&gl=RU&ceid=RU:ru",

    "https://news.google.com/rss/search?q=инфляция+ставка+банки+рубль&hl=ru&gl=RU&ceid=RU:ru",

    "https://news.google.com/rss/search?q=акции+инвестиции+рынок&hl=ru&gl=RU&ceid=RU:ru",

    "https://news.google.com/rss/search?q=нефть+золото+валюта+экономика&hl=ru&gl=RU&ceid=RU:ru",

]


# ============================================================
# UTILS
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = str(text)

    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("```", "")
    text = text.replace("`", "")

    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def clean_tts_text(text):

    text = clean_text(text)

    text = re.sub(
        r"(?m)^[ \t]*[-–—•]\s*",
        "",
        text
    )

    text = text.replace("—", ", ")
    text = text.replace("–", ", ")
    text = text.replace("−", "-")

    text = re.sub(
        r"\s*-\s*",
        " ",
        text
    )

    text = re.sub(
        r"\[(.*?)\]",
        "",
        text
    )

    text = re.sub(
        r"\((HOOK|PAUSE|CTA|INTRO|OUTRO|SFX|MUSIC|SCENE|ОЗВУЧКА).*?\)",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        text
    )

    text = re.sub(
        r"([,.!?;:]){2,}",
        r"\1",
        text
    )

    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text
    )

    return text.strip()


# ============================================================
# ENVIRONMENT
# ============================================================

def check_environment():

    print("🔎 Checking environment...")

    required = {
        "GROQ_API_KEY": GROQ_API_KEY,
        "ELEVENLABS_API_KEY": ELEVENLABS_API_KEY,
        "ELEVENLABS_VOICE_ID": ELEVENLABS_VOICE_ID,
        "PEXELS_API_KEY": PEXELS_API_KEY,
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:

        print("❌ Missing secrets:")

        for name in missing:
            print(f"   - {name}")

        return False

    if not shutil.which("ffmpeg"):

        print("❌ FFmpeg is not installed.")

        return False

    if not shutil.which("ffprobe"):

        print("❌ FFprobe is not installed.")

        return False

    MUSIC_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("✅ Environment OK")

    return True


# ============================================================
# CLEAN WORK DIRECTORY
# ============================================================

def clean_work_directory():

    print("🧹 Cleaning temporary files...")

    if WORK_DIR.exists():

        for item in WORK_DIR.iterdir():

            try:

                if item.is_file():
                    item.unlink()

                elif item.is_dir():
                    shutil.rmtree(item)

            except Exception as e:

                print(
                    f"⚠️ Could not delete {item}: {e}"
                )

    WORK_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# NEWS
# ============================================================

def fetch_free_news_topic():

    import xml.etree.ElementTree as ET

    feeds = FREE_NEWS_RSS[:]

    random.shuffle(feeds)

    headers = {
        "User-Agent":
            "Mozilla/5.0 FinancialVideoBot/3.0"
    }

    for feed_url in feeds:

        try:

            response = requests.get(
                feed_url,
                headers=headers,
                timeout=15
            )

            response.raise_for_status()

            root = ET.fromstring(
                response.content
            )

            items = root.findall(
                ".//item"
            )

            candidates = []

            for item in items[:20]:

                title_node = item.find(
                    "title"
                )

                link_node = item.find(
                    "link"
                )

                title = clean_tts_text(
                    title_node.text
                    if title_node is not None
                    and title_node.text
                    else ""
                )

                link = (
                    link_node.text.strip()
                    if link_node is not None
                    and link_node.text
                    else ""
                )

                if title and len(title) >= 20:

                    candidates.append(
                        (
                            title,
                            link
                        )
                    )

            if candidates:

                title, link = random.choice(
                    candidates
                )

                print(
                    f"📰 News topic: {title}"
                )

                return {
                    "topic": title,
                    "source_url": link
                }

        except Exception as e:

            print(
                f"⚠️ RSS error: {e}"
            )

    return None


# ============================================================
# TOPIC SELECTION
# ============================================================

def choose_topic():

    if random.random() < 0.45:

        news = fetch_free_news_topic()

        if news:

            return news["topic"]

    history = []

    if TOPICS_HISTORY_FILE.exists():

        try:

            history = json.loads(
                TOPICS_HISTORY_FILE.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(
                history,
                list
            ):

                history = []

        except Exception:

            history = []

    available = [
        topic
        for topic in MONEY_TOPICS
        if topic not in history
    ]

    if not available:

        available = MONEY_TOPICS[:]

    topic = random.choice(
        available
    )

    history.append(
        topic
    )

    history = history[
        -TOPICS_HISTORY_SIZE:
    ]

    try:

        TOPICS_HISTORY_FILE.write_text(
            json.dumps(
                history,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    except Exception as e:

        print(
            f"⚠️ Topic history error: {e}"
        )

    print(
        f"🎯 Selected topic: {topic}"
    )

    return topic


# ============================================================
# PARSE GROQ PLAIN TEXT RESPONSE
# ============================================================

def parse_script_response(text):

    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"```(?:text|json)?",
        "",
        text,
        flags=re.I
    )

    text = text.replace(
        "```",
        ""
    )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title_match = re.search(
        r"TITLE\s*:\s*(.*?)(?:\n|$)",
        text,
        flags=re.I
    )

    title = ""

    if title_match:

        title = clean_text(
            title_match.group(1)
        )

    # --------------------------------------------------------
    # SCRIPT
    # --------------------------------------------------------

    script_match = re.search(
        r"SCRIPT\s*:\s*(.*?)(?=\n\s*PEXELS\s*:|\Z)",
        text,
        flags=re.I | re.S
    )

    if not script_match:

        return None

    script = clean_tts_text(
        script_match.group(1)
    )

    # --------------------------------------------------------
    # PEXELS
    # --------------------------------------------------------

    queries = []

    pexels_match = re.search(
        r"PEXELS\s*:\s*(.*)$",
        text,
        flags=re.I | re.S
    )

    if pexels_match:

        raw_queries = pexels_match.group(1)

        lines = raw_queries.splitlines()

        for line in lines:

            line = line.strip()

            if not line:
                continue

            line = re.sub(
                r"^\s*(?:\d+[\.\)]|-|•)\s*",
                "",
                line
            )

            line = clean_text(
                line
            )

            if line:

                queries.append(
                    line
                )

    # --------------------------------------------------------
    # CLEAN QUERY LIST
    # --------------------------------------------------------

    unique_queries = []

    seen = set()

    for query in queries:

        normalized = query.lower()

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        unique_queries.append(
            query
        )

    queries = unique_queries

    if not script:

        return None

    return {
        "title": title,
        "script": script,
        "pexels_queries": queries
    }


# ============================================================
# CTA
# ============================================================

def append_missing_cta(script):

    script = clean_tts_text(script)

    exact_question = "Что это значит для твоего кошелька?"

    telegram_cta = (
        "Такие разборы финансовых новостей, "
        "бизнеса и экономики, рекомендации "
        "по сохранению денег и идеи для увеличения "
        "дохода мы публикуем в нашем Telegram-канале. "
        "Переходи в Telegram, ссылка в шапке профиля."
    )

    lower = script.lower()

    # --------------------------------------------------------
    # If the exact question is missing,
    # add a natural transition first.
    # --------------------------------------------------------

    if exact_question.lower() not in lower:

        script = script.rstrip()

        if script and script[-1] not in ".!?":

            script += "."

        script += (
            " Поэтому важно понимать не только саму новость, "
            "но и то, как она может отразиться лично на тебе. "
            f"{exact_question}"
        )

        lower = script.lower()

    # --------------------------------------------------------
    # Add Telegram CTA if missing.
    # --------------------------------------------------------

    if (
        "telegram" not in lower
        and "телеграм" not in lower
    ):

        script = script.rstrip()

        if script and script[-1] not in ".!?":

            script += "."

        script += " " + telegram_cta

    else:

        if "в шапке профиля" not in lower:

            script = script.rstrip()

            if script and script[-1] not in ".!?":

                script += "."

            script += (
                " Переходи в Telegram, "
                "ссылка в шапке профиля."
            )

    return clean_tts_text(script)


def validate_cta(script):

    lower = script.lower()

    # --------------------------------------------------------
    # Exact main question
    # --------------------------------------------------------

    required_question = (
        "что это значит для твоего кошелька?"
    )

    if required_question not in lower:

        return False

    # --------------------------------------------------------
    # Telegram
    # --------------------------------------------------------

    if (
        "telegram" not in lower
        and "телеграм" not in lower
    ):

        return False

    # --------------------------------------------------------
    # Profile link
    # --------------------------------------------------------

    if "шапке профиля" not in lower:

        return False

    # --------------------------------------------------------
    # Natural lead-in
    # --------------------------------------------------------

    question_position = lower.find(
        required_question
    )

    if question_position < 1:

        return False

    before_question = lower[
        max(0, question_position - 180):
        question_position
    ]

    transition_words = [

        "поэтому",

        "важно понимать",

        "важнее понимать",

        "в итоге",

        "получается",

        "именно поэтому",

        "и вот здесь",

        "отсюда",

        "главное",

        "вопрос теперь",

        "важно понять",

        "для тебя",

        "для обычного человека",

    ]

    if not any(
        word in before_question
        for word in transition_words
    ):

        return False

    return True


# ============================================================
# SCRIPT GENERATION
# ============================================================

def generate_script():

    print(
        "🧠 Asking Groq to create a script..."
    )

    style = random.choice([
        "PROVOCATIVE",
        "INTELLECTUAL",
        "DARK",
        "PHILOSOPHICAL",
        "ANALYTICAL",
    ])

    topic = choose_topic()

    print(
        f"🎩 Selected style: {style}"
    )

    client = Groq(
        api_key=GROQ_API_KEY
    )

    system_prompt = """
Ты профессиональный сценарист коротких
финансовых видео для TikTok и YouTube Shorts.

Пиши на русском языке.

Темы:

деньги,
финансовая грамотность,
заработок,
экономика,
бизнес,
банки,
инвестиции,
инфляция,
финансовые ошибки,
психология денег,
сохранение денег.

Стиль:

умный,
спокойный,
уверенный,
слегка провокационный,
холодный,
аналитичный,
с лёгким сарказмом.

Не копируй конкретных блогеров.

СЦЕНАРИЙ:

Первые секунды должны сразу цеплять.

Не начинай со слов:

"Сегодня мы поговорим"

"В этом видео"

"Привет всем"

"Вы когда-нибудь задумывались"

Не используй клише.

Сначала создай интригу.

Затем раскрой проблему.

Затем объясни её простыми словами.

Добавь конкретный жизненный пример.

Дай неожиданный вывод.

После этого объясни,
как проблема или новость
может повлиять на деньги обычного человека.

ФИНАЛ СЦЕНАРИЯ ЯВЛЯЕТСЯ ОСОБЕННО ВАЖНЫМ.

Перед главным вопросом обязательно должен быть
естественный смысловой переход.

Нельзя просто внезапно сказать:

"Что это значит для твоего кошелька?"

Сначала нужно подвести зрителя к вопросу.

Например по смыслу:

"Поэтому важно понимать не только саму новость,
но и то, как она может отразиться лично на тебе.
Что это значит для твоего кошелька?"

Но НЕ копируй этот пример дословно.

После естественного подведения
ОБЯЗАТЕЛЬНО произнеси именно эту фразу:

"Что это значит для твоего кошелька?"

Не изменяй слова.

Не заменяй её другими словами.

Не убирай вопросительный знак.

Эта фраза должна быть отдельной
финальной смысловой точкой.

ПОСЛЕ ВОПРОСА ОБЯЗАТЕЛЬНО ДОЛЖЕН ИДТИ CTA.

CTA должен естественно продолжать мысль.

Обязательно упомяни:

наш Telegram-канал,

финансовые разборы,

финансовые новости,

новости бизнеса и экономики,

рекомендации,

способы сохранить деньги,

идеи и способы увеличить доход.

И ОБЯЗАТЕЛЬНО скажи,
что перейти в Telegram можно через ссылку
в шапке профиля.

Очень важно:

не говори "ссылка в описании".

не говори "ссылка ниже".

не говори "жми на ссылку".

не говори "переходи по ссылке".

Используй естественную формулировку
со смыслом:

"ссылка в шапке профиля"

CTA не должен выглядеть как агрессивная реклама.

Он должен ощущаться как логичное продолжение
финансового разбора.

Не используй:

"Подписывайся прямо сейчас!"

"Жми на ссылку!"

"Переходи по ссылке!"

"Не забудь подписаться!"

Лучше создать ощущение:

"Если хочешь понимать, что происходит
с твоими деньгами, подобные разборы
мы публикуем в нашем Telegram-канале.
Ссылка в шапке профиля."

Но НЕ копируй этот пример дословно.

ВАЖНАЯ СТРУКТУРА ФИНАЛА:

объяснение влияния на человека
→ естественный подвод
→ "Что это значит для твоего кошелька?"
→ спокойный переход к Telegram
→ что там публикуется
→ "ссылка в шапке профиля"

НЕ заканчивай сценарий сразу после вопроса.

Telegram CTA ОБЯЗАТЕЛЬНО должен находиться
после фразы "Что это значит для твоего кошелька?"

НЕ используй Markdown.

НЕ используй эмодзи.

НЕ используй URL.

НЕ используй хэштеги.

НЕ используй тире.

НЕ используй списки внутри SCRIPT.

НЕ используй служебные слова:

HOOK
CTA
INTRO
OUTRO
SCENE
SFX
MUSIC
ПАУЗА
ОЗВУЧКА

Они не должны попасть в SCRIPT.

Не давай персональных инвестиционных рекомендаций.

Не говори конкретно покупать или продавать
акции, криптовалюты или другие активы.

Не обещай гарантированный заработок.

Длина SCRIPT:

примерно 120–170 слов.

Текст должен естественно звучать
в глубокой мужской озвучке.

После сценария создай от 10 до 14
разнообразных поисковых запросов Pexels.

Каждый запрос должен описывать
отдельную визуальную сцену.

Очень важно:

не повторяй одинаковые сцены.

Запросы должны быть короткими,
на английском языке.

ПРИМЕРЫ:

bank interior

person checking bank account

stock market screens

business meeting

financial district

cash money

smartphone banking

office worker

luxury shopping

grocery shopping

city at night

entrepreneur working

Не используй текстовые надписи
или изображения с конкретными логотипами
в самих запросах.

ФОРМАТ ОТВЕТА:

TITLE: короткий заголовок

SCRIPT:
полный сценарий

PEXELS:
bank interior
person checking bank account
stock market screens
business meeting
financial district
cash money
smartphone banking
office worker
luxury shopping
grocery shopping

Очень важно:

Ответ должен быть ИМЕННО в таком формате.

Не используй JSON.

Не используй Markdown.

Не добавляй никакого текста
до TITLE или после списка PEXELS.
"""

    user_prompt = f"""
Создай короткий финансовый ролик.

СТИЛЬ:
{style}

ТЕМА:
{topic}

Главная задача:

сделать сценарий интересным настолько,
чтобы зритель не пролистал ролик.

Особенно хорошо раскрой,
как эта тема связана с деньгами
обычного человека.

В самом конце обязательно сделай:

естественный подвод к вопросу

"Что это значит для твоего кошелька?"

После этого обязательно объясни,
что подобные финансовые разборы,
новости бизнеса и экономики,
рекомендации по сохранению денег
и идеи по увеличению дохода
публикуются в нашем Telegram-канале.

В конце обязательно скажи:

"ссылка в шапке профиля"

Не используй агрессивную рекламу.

Не заканчивай сценарий на вопросе.
Telegram CTA должен идти ПОСЛЕ вопроса.

Создай минимум 10 разных визуальных сцен
для Pexels.

Ответ строго:

TITLE:
...

SCRIPT:
...

PEXELS:
...
"""

    for model in GROQ_MODELS:

        print(
            f"🤖 Trying Groq model: {model}"
        )

        try:

            response = client.chat.completions.create(

                model=model,

                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],

                temperature=0.72,

                max_completion_tokens=2200,

                reasoning_effort="low"
            )

            content = (
                response
                .choices[0]
                .message
                .content
                or ""
            )

            if not content.strip():

                print(
                    "⚠️ Groq returned empty response."
                )

                continue

            print(
                f"📡 Groq finish reason: "
                f"{response.choices[0].finish_reason}"
            )

            parsed = parse_script_response(
                content
            )

            if not parsed:

                print(
                    "⚠️ Could not parse Groq response."
                )

                print(
                    content[:3000]
                )

                continue

            script = parsed["script"]

            queries = parsed[
                "pexels_queries"
            ]

            # ------------------------------------------------
            # AUTOMATIC CTA SAFETY
            # ------------------------------------------------

            if not validate_cta(script):

                print(
                    "⚠️ CTA incomplete."
                )

                print(
                    "🔧 Automatically fixing CTA..."
                )

                script = append_missing_cta(
                    script
                )

            # ------------------------------------------------
            # FINAL CTA VALIDATION
            # ------------------------------------------------

            if not validate_cta(
                script
            ):

                print(
                    "❌ CTA validation failed "
                    "even after automatic repair."
                )

                continue

            # ------------------------------------------------
            # SCRIPT QUALITY
            # ------------------------------------------------

            if len(script) < 600:

                print(
                    f"⚠️ Script too short: "
                    f"{len(script)} chars"
                )

                continue

            if len(script) > 1700:

                print(
                    f"⚠️ Script too long: "
                    f"{len(script)} chars"
                )

                continue

            # ------------------------------------------------
            # VISUALS
            # ------------------------------------------------

            if len(queries) < MIN_CLIPS:

                print(
                    f"⚠️ Only {len(queries)} "
                    f"visual queries."
                )

                continue

            print(
                f"✅ Groq model working: {model}"
            )

            print()
            print(
                f"📝 Title: "
                f"{parsed['title']}"
            )

            print()
            print(
                "📜 SCRIPT:"
            )

            print(
                script
            )

            print()
            print(
                f"🎞️ Visual queries: "
                f"{len(queries)}"
            )

            return {
                "title": parsed["title"],
                "script": script,
                "pexels_queries": queries[
                    :MAX_CLIPS
                ]
            }

        except Exception as e:

            print(
                f"❌ Groq error with "
                f"{model}: {e}"
            )

    print(
        "❌ All Groq models failed."
    )

    return None


# ============================================================
# ELEVENLABS
# ============================================================

def generate_voice(script):

    print(
        "🎙️ Generating Russian voice..."
    )

    tts_script = clean_tts_text(
        script
    )

    url = (
        "https://api.elevenlabs.io/v1/"
        f"text-to-speech/{ELEVENLABS_VOICE_ID}"
    )

    headers = {
        "xi-api-key":
            ELEVENLABS_API_KEY,

        "Content-Type":
            "application/json",

        "Accept":
            "audio/mpeg"
    }

    payload = {

        "text":
            tts_script,

        "model_id":
            "eleven_multilingual_v2",

        "output_format":
            "mp3_44100_128",

        "voice_settings": {

            "stability":
                0.52,

            "similarity_boost":
                0.78,

            "style":
                0.32,

            "use_speaker_boost":
                True
        }
    }

    try:

        response = requests.post(

            url,

            headers=headers,

            json=payload,

            timeout=180
        )

        if response.status_code != 200:

            print(
                f"❌ ElevenLabs error "
                f"{response.status_code}"
            )

            print(
                response.text[:1500]
            )

            return False

        AUDIO_FILE.write_bytes(
            response.content
        )

        duration = get_duration(
            AUDIO_FILE
        )

        if duration <= 0:

            print(
                "❌ Invalid audio."
            )

            return False

        print(
            f"✅ Voice generated: "
            f"{duration:.2f}s"
        )

        return True

    except Exception as e:

        print(
            f"❌ ElevenLabs error: {e}"
        )

        return False


# ============================================================
# PEXELS SEARCH
# ============================================================

def search_pexels_video(query):

    print(
        f"🔎 Pexels: {query}"
    )

    url = (
        "https://api.pexels.com/videos/search"
    )

    headers = {
        "Authorization":
            PEXELS_API_KEY
    }

    params = {

        "query":
            query,

        "orientation":
            "portrait",

        "size":
            "medium",

        "per_page":
            15,

        "locale":
            "en-US"
    }

    try:

        response = requests.get(

            url,

            headers=headers,

            params=params,

            timeout=30
        )

        if response.status_code != 200:

            print(
                f"⚠️ Pexels error "
                f"{response.status_code}"
            )

            return None

        videos = response.json().get(
            "videos",
            []
        )

        if not videos:

            return None

        random.shuffle(
            videos
        )

        candidates = []

        for video in videos:

            video_files = video.get(
                "video_files",
                []
            )

            portrait = [

                f

                for f in video_files

                if f.get("width", 0)
                < f.get("height", 0)
            ]

            files = (
                portrait
                or video_files
            )

            for file in files:

                link = file.get(
                    "link"
                )

                width = file.get(
                    "width",
                    0
                )

                height = file.get(
                    "height",
                    0
                )

                if link:

                    candidates.append(
                        (
                            link,
                            width,
                            height
                        )
                    )

        if not candidates:

            return None

        candidates.sort(
            key=lambda item:
            abs(item[1] - 1080)
        )

        best = candidates[
            :min(7, len(candidates))
        ]

        selected = random.choice(
            best
        )

        return selected[0]

    except Exception as e:

        print(
            f"⚠️ Pexels exception: {e}"
        )

        return None


# ============================================================
# DOWNLOAD CLIP
# ============================================================

def download_video(
    url,
    destination
):

    print(
        f"⬇️ Downloading "
        f"{destination.name}"
    )

    try:

        response = requests.get(

            url,

            stream=True,

            timeout=120
        )

        response.raise_for_status()

        with open(
            destination,
            "wb"
        ) as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:

                    file.write(
                        chunk
                    )

        return destination.exists()

    except Exception as e:

        print(
            f"❌ Download error: {e}"
        )

        return False


# ============================================================
# GET MANY CLIPS
# ============================================================

def get_video_clips(
    queries
):

    fallback = [

        "money finance",

        "business office",

        "banking",

        "stock market",

        "financial district",

        "smartphone banking",

        "person checking phone",

        "business meeting",

        "shopping",

        "cash money",

        "office worker",

        "city night",

        "technology",

        "entrepreneur",

        "investment",

        "credit card",

        "grocery shopping",

        "salary payment",

        "business man",

        "modern office",

    ]

    all_queries = []

    all_queries.extend(
        queries
    )

    all_queries.extend(
        fallback
    )

    clips = []

    used_links = set()

    query_index = 0

    while (
        len(clips) < MAX_CLIPS
        and query_index < len(all_queries)
    ):

        query = all_queries[
            query_index
        ]

        query_index += 1

        link = search_pexels_video(
            query
        )

        if not link:

            continue

        if link in used_links:

            continue

        used_links.add(
            link
        )

        destination = (
            WORK_DIR /
            f"clip_{len(clips)+1}.mp4"
        )

        if download_video(
            link,
            destination
        ):

            clips.append(
                destination
            )

        time.sleep(
            0.3
        )

    print(
        f"✅ Downloaded "
        f"{len(clips)} visual clips."
    )

    return clips


# ============================================================
# MUSIC
# ============================================================

def get_music():

    tracks = list(
        MUSIC_DIR.glob(
            "*.mp3"
        )
    )

    if not tracks:

        print(
            "⚠️ No music found."
        )

        return None

    track = random.choice(
        tracks
    )

    print(
        f"🎵 Music: {track.name}"
    )

    return track


# ============================================================
# FFMPEG HELPERS
# ============================================================

def get_duration(
    file
):

    command = [

        "ffprobe",

        "-v",
        "error",

        "-show_entries",
        "format=duration",

        "-of",
        "default=noprint_wrappers=1:nokey=1",

        str(file)
    ]

    try:

        result = subprocess.run(

            command,

            capture_output=True,

            text=True,

            check=True
        )

        return float(
            result.stdout.strip()
        )

    except Exception:

        return 0.0


# ============================================================
# PREPARE CLIP
# ============================================================

def prepare_clip(
    input_file,
    output_file,
    duration
):

    command = [

        "ffmpeg",

        "-y",

        "-stream_loop",
        "-1",

        "-i",
        str(input_file),

        "-t",
        str(duration),

        "-vf",

        (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            "setsar=1"
        ),

        "-an",

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        str(output_file)
    ]

    try:

        subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            check=True
        )

        return True

    except subprocess.CalledProcessError as e:

        print(
            "❌ Clip preparation error:"
        )

        print(
            e.stderr[-2000:]
            if e.stderr
            else ""
        )

        return False


# ============================================================
# CREATE DYNAMIC VISUAL TRACK
# ============================================================

def create_visual_track(
    clips,
    duration
):

    print(
        "🎞️ Creating dynamic montage..."
    )

    if not clips:

        return None

    prepared = []

    for index, clip in enumerate(
        clips
    ):

        output = (
            WORK_DIR /
            f"prepared_{index}.mp4"
        )

        if prepare_clip(
            clip,
            output,
            MAX_CLIP_SECONDS + 1.0
        ):

            prepared.append(
                output
            )

    if not prepared:

        return None

    desired_count = int(
        duration /
        random.uniform(
            MIN_CLIP_SECONDS,
            MAX_CLIP_SECONDS
        )
    )

    desired_count = max(
        MIN_CLIPS,
        desired_count
    )

    desired_count = min(
        MAX_CLIPS,
        desired_count
    )

    visual_clips = []

    index = 0

    while len(visual_clips) < desired_count:

        candidate = prepared[
            index % len(prepared)
        ]

        if (
            visual_clips
            and candidate == visual_clips[-1]
            and len(prepared) > 1
        ):

            index += 1

            candidate = prepared[
                index % len(prepared)
            ]

        visual_clips.append(
            candidate
        )

        index += 1

    count = len(
        visual_clips
    )

    raw_lengths = []

    for _ in range(count):

        raw_lengths.append(
            random.uniform(
                MIN_CLIP_SECONDS,
                MAX_CLIP_SECONDS
            )
        )

    raw_total = sum(
        raw_lengths
    )

    segment_lengths = [

        x * duration / raw_total

        for x in raw_lengths

    ]

    segment_lengths = [

        max(
            1.25,
            x
        )

        for x in segment_lengths

    ]

    factor = (
        duration /
        sum(segment_lengths)
    )

    segment_lengths = [

        x * factor

        for x in segment_lengths

    ]

    filter_parts = []

    input_index = 0

    for i, segment in enumerate(
        segment_lengths
    ):

        zoom_mode = random.choice([
            "center",
            "left",
            "right",
        ])

        if zoom_mode == "left":

            crop_x = "0"

        elif zoom_mode == "right":

            crop_x = "(iw-ow)"

        else:

            crop_x = "(iw-ow)/2"

        filter_parts.append(

            f"[{input_index}:v]"
            f"trim=start=0:duration={segment:.6f},"
            "setpts=PTS-STARTPTS,"
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{crop_x}:(ih-oh)/2,"
            "setsar=1,"
            "format=yuv420p"
            f"[v{i}]"
        )

        input_index += 1

    joined = "".join(
        f"[v{i}]"
        for i in range(
            count
        )
    )

    filter_parts.append(

        f"{joined}"
        f"concat=n={count}:v=1:a=0,"
        "format=yuv420p[v]"
    )

    command = [
        "ffmpeg",
        "-y"
    ]

    for clip in visual_clips:

        command += [
            "-i",
            str(clip)
        ]

    command += [

        "-filter_complex",
        ";".join(
            filter_parts
        ),

        "-map",
        "[v]",

        "-t",
        f"{duration:.6f}",

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        str(
            WORK_DIR /
            "visual_track.mp4"
        )
    ]

    try:

        subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True,

            check=True
        )

    except subprocess.CalledProcessError as e:

        print(
            "❌ Visual montage error:"
        )

        print(
            e.stderr[-6000:]
            if e.stderr
            else ""
        )

        return None

    visual_track = (
        WORK_DIR /
        "visual_track.mp4"
    )

    if not visual_track.exists():

        return None

    actual_duration = get_duration(
        visual_track
    )

    print(
        f"🎞️ Visual duration: "
        f"{actual_duration:.3f}s"
    )

    print(
        f"🎬 Number of visual fragments: "
        f"{count}"
    )

    return visual_track


# ============================================================
# FINAL VIDEO
# ============================================================

def create_video(
    clips,
    music
):

    print(
        "🎬 Creating final video..."
    )

    voice_duration = get_duration(
        AUDIO_FILE
    )

    if voice_duration <= 0:

        print(
            "❌ Invalid voice duration."
        )

        return False

    target_duration = (
        voice_duration
        + VOICE_TAIL
    )

    print(
        f"🎙️ Voice: "
        f"{voice_duration:.3f}s"
    )

    print(
        f"🎬 Target video: "
        f"{target_duration:.3f}s"
    )

    visual_track = create_visual_track(
        clips,
        target_duration
    )

    if not visual_track:

        print(
            "❌ Could not create visual track."
        )

        return False

    # --------------------------------------------------------
    # FINAL AUDIO
    # --------------------------------------------------------

    if music:

        command = [

            "ffmpeg",

            "-y",

            "-i",
            str(visual_track),

            "-i",
            str(AUDIO_FILE),

            "-stream_loop",
            "-1",

            "-i",
            str(music),

            "-filter_complex",

            (
                "[1:a]"
                "aresample=44100,"
                "apad,"
                f"atrim=0:{voice_duration:.6f},"
                "asetpts=N/SR/TB,"
                "[voice];"

                "[2:a]"
                "aresample=44100,"
                f"volume={MUSIC_VOLUME},"
                "apad,"
                f"atrim=0:{target_duration:.6f},"
                "asetpts=N/SR/TB,"
                "[music];"

                "[voice][music]"
                "amix=inputs=2:"
                "duration=longest:"
                "dropout_transition=0"
                "[finalaudio]"
            ),

            "-map",
            "0:v:0",

            "-map",
            "[finalaudio]",

            "-t",
            f"{target_duration:.6f}",

            "-r",
            str(FPS),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "22",

            "-pix_fmt",
            "yuv420p",

            "-c:a",
            "aac",

            "-b:a",
            "192k",

            "-ar",
            "44100",

            "-movflags",
            "+faststart",

            str(FINAL_VIDEO)
        ]

    else:

        command = [

            "ffmpeg",

            "-y",

            "-i",
            str(visual_track),

            "-i",
            str(AUDIO_FILE),

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            "-t",
            f"{target_duration:.6f}",

            "-r",
            str(FPS),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "22",

            "-pix_fmt",
            "yuv420p",

            "-c:a",
            "aac",

            "-b:a",
            "192k",

            "-ar",
            "44100",

            "-movflags",
            "+faststart",

            str(FINAL_VIDEO)
        ]

    print(
        "✂️ Rendering final MP4..."
    )

    try:

        subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True,

            check=True
        )

    except subprocess.CalledProcessError as e:

        print(
            "❌ FFmpeg final render error:"
        )

        print(
            e.stderr[-7000:]
            if e.stderr
            else ""
        )

        return False

    if not FINAL_VIDEO.exists():

        print(
            "❌ Final video was not created."
        )

        return False

    final_duration = get_duration(
        FINAL_VIDEO
    )

    print()
    print(
        "======================================"
    )

    print(
        "🎉 VIDEO CREATED"
    )

    print(
        "======================================"
    )

    print(
        f"🎙️ Voice: "
        f"{voice_duration:.3f}s"
    )

    print(
        f"🎬 Video: "
        f"{final_duration:.3f}s"
    )

    print(
        f"📦 Size: "
        f"{FINAL_VIDEO.stat().st_size / 1024 / 1024:.2f} MB"
    )

    # --------------------------------------------------------
    # HARD SAFETY CHECK
    # --------------------------------------------------------

    if final_duration + 0.05 < voice_duration:

        print(
            "❌ SAFETY CHECK FAILED!"
        )

        print(
            "Video is shorter than voice."
        )

        return False

    print(
        "✅ Voice is fully contained inside video."
    )

    print(
        "🚫 NO SUBTITLES WERE ADDED."
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "======================================"
    )

    print(
        "🎬 FINANCIAL VIDEO BOT"
    )

    print(
        "======================================"
    )

    print()

    if not check_environment():

        return 1

    clean_work_directory()

    # --------------------------------------------------------
    # SCRIPT
    # --------------------------------------------------------

    content = generate_script()

    if not content:

        print(
            "❌ Content generation failed."
        )

        return 1

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

    if not generate_voice(
        content["script"]
    ):

        print(
            "❌ Voice generation failed."
        )

        return 1

    # --------------------------------------------------------
    # VISUALS
    # --------------------------------------------------------

    clips = get_video_clips(
        content["pexels_queries"]
    )

    if len(clips) < MIN_CLIPS:

        print(
            "⚠️ Not enough clips."
        )

        print(
            f"Required: {MIN_CLIPS}"
        )

        print(
            f"Found: {len(clips)}"
        )

        if not clips:

            return 1

    # --------------------------------------------------------
    # MUSIC
    # --------------------------------------------------------

    music = get_music()

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    if not create_video(
        clips,
        music
    ):

        print(
            "❌ Video rendering failed."
        )

        return 1

    print()

    print(
        "======================================"
    )

    print(
        "🎉 VIDEO BOT FINISHED"
    )

    print(
        "======================================"
    )

    print()

    print(
        "📹 Video ready:"
    )

    print(
        FINAL_VIDEO
    )

    print()

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )