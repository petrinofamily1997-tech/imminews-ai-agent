````python
import os
import re
import json
import random
import shutil
import subprocess
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

# Minimum number of visual fragments.
MIN_CLIPS = 8

# Maximum number of visual fragments.
MAX_CLIPS = 14

# Average clip length.
MIN_CLIP_SECONDS = 1.8
MAX_CLIP_SECONDS = 3.2

# Extra time after voice.
VOICE_TAIL = 0.90

# Maximum topic history.
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
        r"\((HOOK|PAUSE|CTA|INTRO|OUTRO|SFX|MUSIC).*?\)",
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
            "Mozilla/5.0 FinancialVideoBot/2.0"
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

    # 45% chance of fresh news.
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

Твоя задача — создавать сценарии, которые
удерживают внимание зрителя до конца.

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

Стиль рассказчика:

умный,
спокойный,
уверенный,
слегка провокационный,
холодный,
аналитичный,
с лёгким сарказмом.

Не копируй конкретных блогеров,
персонажей или известных людей.

СТРУКТУРА:

1. Очень сильный HOOK в первых секундах.

2. Развитие интриги.

3. Неочевидный факт или интересная идея.

4. Объяснение простыми словами.

5. Неожиданный вывод.

6. Естественный переход к деньгам самого зрителя.

7. CTA в Telegram.

ВАЖНО:

Последняя часть сценария ОБЯЗАТЕЛЬНО должна
логически подвести зрителя к названию
Telegram-канала:

"Что это значит для твоего кошелька?"

После этой фразы нужно сказать, что подобные
разборы, финансовые новости, рекомендации,
идеи по сохранению денег и способы увеличения
дохода можно узнать в нашем Telegram-канале.

Пример логики:

"Но знать саму новость недостаточно.
Гораздо важнее понять, как она может
повлиять лично на тебя и твои деньги.

Что это значит для твоего кошелька?

Об этом, а также о финансовых новостях,
способах сохранить деньги и увеличить доход,
мы рассказываем в нашем Telegram-канале."

НЕ КОПИРУЙ пример дословно.
Создавай собственный естественный переход.

Последняя часть должна звучать
как продолжение мысли ролика,
а не как внезапная реклама.

Не говори:

"Подписывайся прямо сейчас!"

Не используй агрессивный рекламный стиль.

Не начинай:

"Сегодня мы поговорим..."

"В этом видео..."

"Привет всем..."

Не используй Markdown.

Не используй эмодзи.

Не используй URL.

Не используй хэштеги.

Не используй слова:

HOOK,
CTA,
ПАУЗА,
СЦЕНА,
МУЗЫКА,
ОЗВУЧКА.

Они не должны попасть в озвучку.

Не используй тире или списки.

Не обещай гарантированный заработок.

Не давай персональных инвестиционных
рекомендаций.

Не говори зрителю конкретно покупать
или продавать активы.

Длина:

примерно 120–170 слов.

Текст должен естественно звучать
в глубокой мужской озвучке.

Кроме сценария необходимо создать
8–12 разнообразных поисковых запросов
для Pexels.

Каждый запрос должен описывать отдельную
визуальную сцену.

Например:

bank interior

person checking bank account

stock market screens

business meeting

city financial district

cash money

smartphone banking

office worker

luxury shopping

inflation shopping

Не повторяй одну и ту же сцену.

Ответ ТОЛЬКО JSON:

{
  "title": "...",
  "script": "...",
  "pexels_queries": [
    "...",
    "...",
    "...",
    "...",
    "...",
    "...",
    "...",
    "..."
  ]
}
"""

    user_prompt = f"""
Создай сценарий короткого финансового видео.

Стиль:

{style}

ТЕМА:

{topic}

Раскрой именно эту тему.

Видео должно быть динамичным,
интересным и понятным обычному человеку.

Особое внимание удели тому,
как тема может повлиять на деньги
обычного человека.

В конце обязательно сделай
логическое подступление к фразе:

"Что это значит для твоего кошелька?"

После неё объясни, что подобные разборы,
новости бизнеса и экономики,
рекомендации по сохранению денег
и идеи по увеличению дохода
есть в нашем Telegram-канале.

Сделай переход естественным.

Создай минимум 8 разных визуальных
сцен для монтажа.

Ответ только JSON.
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

                temperature=0.8,

                max_tokens=1800,

                response_format={
                    "type": "json_object"
                }
            )

            content = (
                response
                .choices[0]
                .message
                .content
                or ""
            )

            if not content.strip():

                continue

            data = json.loads(
                content
            )

            script = clean_tts_text(
                data.get(
                    "script",
                    ""
                )
            )

            title = clean_text(
                data.get(
                    "title",
                    ""
                )
            )

            queries = data.get(
                "pexels_queries",
                []
            )

            if not isinstance(
                queries,
                list
            ):

                queries = []

            queries = [
                clean_text(q)
                for q in queries
                if str(q).strip()
            ]

            if not script:

                continue

            # Make sure CTA exists.
            cta_words = [
                "Что это значит",
                "твоего кошелька",
                "Telegram",
                "телеграм"
            ]

            if not all(
                word.lower() in script.lower()
                for word in cta_words
            ):

                print(
                    "⚠️ CTA missing. "
                    "Regenerating..."
                )

                continue

            # We need many visual queries.
            if len(queries) < MIN_CLIPS:

                print(
                    "⚠️ Not enough visual queries."
                )

                continue

            print(
                f"✅ Groq model working: {model}"
            )

            print()
            print(
                f"📝 Title: {title}"
            )

            print()
            print("📜 SCRIPT:")
            print(script)

            print()
            print(
                f"🎞️ Visual queries: {len(queries)}"
            )

            return {
                "title": title,
                "script": script,
                "pexels_queries": queries[
                    :MAX_CLIPS
                ]
            }

        except Exception as e:

            print(
                f"❌ Groq error: {e}"
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

        # Prefer vertical videos around 720-1080 width.
        candidates.sort(
            key=lambda item:
            abs(item[1] - 1080)
        )

        # Randomize among the best candidates.
        best = candidates[
            :min(5, len(candidates))
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

    ]

    all_queries = []

    # First use AI-generated queries.
    all_queries.extend(
        queries
    )

    # Then fallback queries.
    all_queries.extend(
        fallback
    )

    clips = []

    used_links = set()

    query_index = 0

    # Keep searching until we have enough footage.
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

        # Prevent same Pexels file.
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

        # Small delay to avoid hammering API.
        import time
        time.sleep(0.3)

    print(
        f"✅ Downloaded "
        f"{len(clips)} visual clips."
    )

    if len(clips) < MIN_CLIPS:

        print(
            f"⚠️ Only {len(clips)} "
            f"clips available."
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

    # Prepare all clips.
    for index, clip in enumerate(
        clips
    ):

        output = (
            WORK_DIR /
            f"prepared_{index}.mp4"
        )

        # Give each clip enough source duration.
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

    # If fewer clips than needed,
    # cycle through them.
    required_count = max(
        MIN_CLIPS,
        len(prepared)
    )

    visual_clips = []

    index = 0

    while (
        sum(
            get_duration(x)
            for x in visual_clips
        ) < duration
        and len(visual_clips) < 30
    ):

        visual_clips.append(
            prepared[
                index % len(prepared)
            ]
        )

        index += 1

    # Calculate exact segment duration.
    segment = (
        duration /
        len(visual_clips)
    )

    filter_parts = []

    for i in range(
        len(visual_clips)
    ):

        # Small zoom effect.
        filter_parts.append(

            f"[{i}:v]"
            f"trim=start=0:duration={segment:.6f},"
            "setpts=PTS-STARTPTS,"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1,"
            "format=yuv420p"
            f"[v{i}]"
        )

    joined = "".join(
        f"[v{i}]"
        for i in range(
            len(visual_clips)
        )
    )

    filter_parts.append(

        f"{joined}"
        f"concat=n={len(visual_clips)}:v=1:a=0,"
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

    # IMPORTANT:
    # Voice is the master clock.
    #
    # We NEVER make the video shorter
    # than the actual generated voice.
    #
    # Add a small safety tail so the final
    # consonant is never cut.
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
    # FINAL AUDIO + VIDEO
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
                f"atrim=0:{target_duration:.6f},"
                "[voice];"

                "[2:a]"
                "aresample=44100,"
                f"volume={MUSIC_VOLUME},"
                "apad,"
                f"atrim=0:{target_duration:.6f},"
                "[music];"

                "[voice][music]"
                "amix=inputs=2:"
                "duration=first:"
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

    # HARD SAFETY CHECK.
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

        # We can still continue if at least
        # a few clips exist because the montage
        # can reuse them.
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


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
````
