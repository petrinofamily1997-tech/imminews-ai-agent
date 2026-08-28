import os
import re
import json
import random
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv
from groq import Groq


load_dotenv()


# ============================================================
# CONFIG
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")


BASE_DIR = Path(__file__).resolve().parent

MUSIC_DIR = BASE_DIR / "assets" / "music"
WORK_DIR = BASE_DIR / "video_work"
OUTPUT_DIR = BASE_DIR / "output"

AUDIO_FILE = WORK_DIR / "voice.mp3"
FINAL_VIDEO = OUTPUT_DIR / "video.mp4"

MUSIC_VOLUME = 0.06

# Небольшой запас после окончания речи.
# Голос никогда не должен упираться в конец видео.
VOICE_TAIL_SECONDS = 1.0

# Минимальная длина ролика.
MIN_VIDEO_SECONDS = 15

# Максимальная длина ролика.
MAX_VIDEO_SECONDS = 120

TOPICS_HISTORY_FILE = BASE_DIR / "topics_history.json"
TOPICS_HISTORY_SIZE = 12


# ============================================================
# GROQ MODELS
# ============================================================

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
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

NEWS_TIMEOUT = 15

# Вероятность использовать свежую новость.
NEWS_TOPIC_CHANCE = 0.45


# ============================================================
# TOPICS
# ============================================================

MONEY_TOPICS = [

    "почему зарплата не делает человека богатым",

    "ловушка потребительских кредитов",

    "как инфляция незаметно съедает сбережения",

    "психология импульсивных покупок",

    "почему богатые думают о времени, а не только о деньгах",

    "разница между активом и пассивом простыми словами",

    "почему откладывать фиксированный процент зарплаты подходит не всем",

    "как банки зарабатывают на обычных клиентах",

    "иллюзия финансовой безопасности",

    "почему высокий доход не гарантирует богатство",

    "ошибка мышления: заработаю больше и решу все проблемы",

    "как реклама заставляет нас тратить больше",

    "почему кредитная карта не является бесплатными деньгами",

    "финансовая грамотность, которой часто не учат в школе",

    "почему сравнение себя с другими портит финансовые решения",

    "ловушка рассрочки с нулевой переплатой",

    "что такое финансовая подушка и зачем она нужна",

    "почему инвестировать страшно и какие ошибки делают новички",

    "как страх упущенной выгоды толкает на плохие сделки",

    "почему богатство связано с привычками",

    "разница между ценой и реальной ценностью",

    "как маленькие ежедневные траты превращаются в крупную сумму",

    "почему откладывать деньги на потом часто не получается",

    "почему держать все деньги в одном месте рискованно",

    "почему высокий кредитный рейтинг не означает финансовую свободу",

    "как выйти из цикла от зарплаты до зарплаты",

    "почему статусные покупки стоят дороже их цены",

    "инфляция образа жизни и как не попасть в эту ловушку",

    "почему деньги любят учет",

    "разница между инвестированием и спекуляцией",

    "как эмоции влияют на финансовые решения",

    "почему быстрый пассивный доход почти всегда требует осторожности",

    "как соцсети искажают представление о зарплатах и богатстве",

    "почему наличные и деньги на счете ощущаются по-разному",

    "как подписки незаметно съедают бюджет",

    "почему скидка не всегда означает экономию",

    "как повышение зарплаты может привести к росту расходов",

    "почему богатые считают стоимость времени",

    "как процентная ставка меняет реальную стоимость кредита",

    "почему финансовый план лучше надежды на силу воли",

    "что происходит с деньгами во время экономической неопределенности",

    "как центральные банки влияют на стоимость денег",

    "почему курс валюты меняется даже без очевидной причины",

    "как изменение ставки влияет на кредиты и накопления",

    "почему цены растут не одинаково на все товары",

    "как компании зарабатывают на комиссиях",

    "почему бесплатные финансовые сервисы все равно могут приносить доход",

    "как новости о крупных компаниях влияют на настроение рынка",

    "почему рынок может падать даже при хороших новостях",

    "как паника заставляет инвесторов продавать в неподходящий момент",

]


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
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = str(text)

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


# ============================================================
# TTS TEXT CLEANING
# ============================================================

def clean_tts_text(text):

    """
    Подготавливает текст исключительно для ElevenLabs.

    Никаких субтитров здесь нет.
    Никакого alignment здесь нет.
    """

    text = clean_text(text)

    # Убираем списки.
    text = re.sub(
        r"(?m)^[ \t]*[-–—•]\s*",
        "",
        text
    )

    # Не даём TTS читать служебные конструкции.
    text = re.sub(
        r"\[(?:.*?)\]",
        "",
        text
    )

    text = re.sub(
        r"\((?:HOOK|PAUSE|CTA|INTRO|OUTRO|SFX|MUSIC).*?\)",
        "",
        text,
        flags=re.I
    )

    # Нормализуем тире.
    text = text.replace(
        "—",
        ", "
    )

    text = text.replace(
        "–",
        ", "
    )

    text = text.replace(
        "−",
        "-"
    )

    text = re.sub(
        r"\s*-\s*",
        " ",
        text
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
# FREE RSS NEWS
# ============================================================

def fetch_free_news_topic():

    print("🌍 Checking free financial news...")

    feeds = FREE_NEWS_RSS[:]

    random.shuffle(
        feeds
    )

    headers = {
        "User-Agent":
            "Mozilla/5.0 FinancialVideoBot/2.0"
    }

    for feed_url in feeds:

        try:

            response = requests.get(
                feed_url,
                headers=headers,
                timeout=NEWS_TIMEOUT
            )

            response.raise_for_status()

            root = ET.fromstring(
                response.content
            )

            items = root.findall(
                ".//item"
            )

            candidates = []

            for item in items[:15]:

                title_node = item.find(
                    "title"
                )

                link_node = item.find(
                    "link"
                )

                title = clean_tts_text(
                    title_node.text
                    if (
                        title_node is not None
                        and title_node.text
                    )
                    else ""
                )

                link = (
                    link_node.text.strip()
                    if (
                        link_node is not None
                        and link_node.text
                    )
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
                    f"📰 Free RSS news topic: {title}"
                )

                return {
                    "topic": title,
                    "source_url": link,
                }

        except Exception as e:

            print(
                f"⚠️ RSS news unavailable: {e}"
            )

    return None


# ============================================================
# CHOOSE TOPIC
# ============================================================

def choose_topic():

    if random.random() < NEWS_TOPIC_CHANCE:

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

        available = list(
            MONEY_TOPICS
        )

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
            f"⚠️ Could not save topic history: {e}"
        )

    print(
        f"🎯 Selected topic: {topic}"
    )

    return topic


# ============================================================
# GROQ SCRIPT GENERATION
# ============================================================

def generate_script():

    print(
        "🧠 Asking Groq to create a script..."
    )

    style = random.choice(
        [
            "PROVOCATIVE",
            "INTELLECTUAL",
            "DARK",
            "PHILOSOPHICAL",
            "ANALYTICAL",
        ]
    )

    topic = choose_topic()

    print(
        f"🎩 Selected style: {style}"
    )

    client = Groq(
        api_key=GROQ_API_KEY
    )

    system_prompt = """
Ты профессиональный сценарист коротких
финансовых видео на русском языке.

Создавай оригинальный образ рассказчика:

умный,
спокойный,
холодный,
уверенный,
слегка провокационный,
философский,
с лёгким сарказмом.

Темы:

деньги,
финансовые ошибки,
заработок,
инвестиции,
экономика,
банки,
инфляция,
психология денег,
богатство,
расходы,
финансовая грамотность.

Структура:

1. Очень сильный HOOK.
2. Интрига.
3. Неочевидный факт или идея.
4. Неожиданный вывод.
5. Мягкий призыв подписаться.

Не начинай словами:

"Сегодня мы поговорим..."
"В этом видео..."
"Привет всем..."

Не используй Markdown.

Не используй **.

Не используй тире, длинное тире
или списки с дефисами внутри сценария.

Используй обычные предложения
с запятыми и точками.

Не добавляй в script слова:

"HOOK",
"ПАУЗА",
"CTA",
"SFX",
"музыка",
"озвучка",
"сцена".

Они не должны попадать в озвучку.

Не используй URL.

Не используй хэштеги.

Не используй эмодзи внутри сценария.

Не обещай гарантированную прибыль.

Не давай персональных инвестиционных рекомендаций.

Длина сценария:

примерно 110–160 слов.

Пиши естественным темпом
для глубокой мужской озвучки.

Ответ должен быть только JSON:

{
  "title": "...",
  "script": "...",
  "pexels_queries": [
    "...",
    "...",
    "..."
  ]
}
"""

    user_prompt = f"""
Создай сценарий финансового видео.

Стиль:

{style}

Конкретная тема ролика:

{topic}

Видео должно быть интересным,
необычным и удерживать внимание.

Тема должна заставлять зрителя
задуматься о собственных деньгах.

Сделай текст естественным
для мужской глубокой озвучки.

Ответь только JSON.
"""

    for model in GROQ_MODELS:

        print()
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

                max_tokens=1200,

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

                print(
                    "⚠️ Empty Groq response."
                )

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
                clean_text(query)
                for query in queries
                if str(query).strip()
            ]

            if not script:

                print(
                    "⚠️ Empty script."
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
            print(
                "📜 SCRIPT:"
            )

            print(
                script
            )

            print()

            return {
                "title": title,
                "script": script,
                "pexels_queries": queries[:5],
            }

        except Exception as e:

            print(
                f"❌ Groq error with {model}:"
            )

            print(
                str(e)[:1000]
            )

    print(
        "❌ All Groq models failed."
    )

    return None


# ============================================================
# FFPROBE DURATION
# ============================================================

def get_duration(file):

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file),
    ]

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        value = result.stdout.strip()

        if not value:

            return 0.0

        duration = float(
            value
        )

        if duration < 0:

            return 0.0

        return duration

    except Exception as e:

        print(
            f"⚠️ Could not read duration of {file}: {e}"
        )

        return 0.0


# ============================================================
# ELEVENLABS VOICE
# ============================================================

def generate_voice(script):

    print(
        "🎙️ Generating Russian voice with ElevenLabs..."
    )

    tts_script = clean_tts_text(
        script
    )

    if not tts_script:

        print(
            "❌ TTS script is empty."
        )

        return False

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
            "audio/mpeg",
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
                True,
        },
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
                f"❌ ElevenLabs TTS error "
                f"{response.status_code}"
            )

            print(
                response.text[:2000]
            )

            return False

        AUDIO_FILE.write_bytes(
            response.content
        )

        if not AUDIO_FILE.exists():

            print(
                "❌ Audio file was not created."
            )

            return False

        voice_duration = get_duration(
            AUDIO_FILE
        )

        if voice_duration <= 0:

            print(
                "❌ ElevenLabs returned "
                "an invalid audio file."
            )

            return False

        print(
            f"✅ Voice generated!"
        )

        print(
            f"🎙️ REAL voice duration: "
            f"{voice_duration:.3f}s"
        )

        print(
            "🚫 No subtitle generation."
        )

        print(
            "🚫 No forced alignment."
        )

        print(
            "🚫 No WhisperX."
        )

        return True

    except Exception as e:

        print(
            f"❌ ElevenLabs TTS error: {e}"
        )

        return False


# ============================================================
# PEXELS VIDEO SEARCH
# ============================================================

def search_pexels_video(query):

    print(
        f"🔎 Pexels search: {query}"
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
            10,

        "locale":
            "en-US",
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
                f"⚠️ Pexels status: "
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

        for video in videos:

            files = video.get(
                "video_files",
                []
            )

            portrait = [
                item
                for item in files
                if item.get("width", 0)
                < item.get("height", 0)
            ]

            candidates = (
                portrait
                or files
            )

            if not candidates:

                continue

            # Предпочитаем разрешение около 1080p.
            candidates.sort(
                key=lambda item:
                    abs(
                        item.get(
                            "width",
                            0
                        )
                        - 1080
                    )
            )

            link = candidates[0].get(
                "link"
            )

            if link:

                return link

        return None

    except Exception as e:

        print(
            f"⚠️ Pexels error: {e}"
        )

        return None


# ============================================================
# DOWNLOAD VIDEO
# ============================================================

def download_video(
    url,
    destination
):

    print(
        "⬇️ Downloading video..."
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
# GET VIDEO CLIPS
# ============================================================

def get_video_clips(queries):

    fallback = [

        "money finance",

        "business",

        "banking",

        "stock market",

        "city night",

        "smartphone",

        "office",

        "person thinking",

    ]

    all_queries = (
        queries
        + fallback
    )

    clips = []

    used_links = set()

    for query in all_queries:

        if len(clips) >= 4:

            break

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
            WORK_DIR
            / f"clip_{len(clips) + 1}.mp4"
        )

        if download_video(
            link,
            destination
        ):

            clips.append(
                destination
            )

    print(
        f"✅ Downloaded "
        f"{len(clips)} clips."
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
# PREPARE VIDEO CLIP
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
        f"{duration:.6f}",

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1"
        ),

        "-an",

        "-r",
        "30",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        str(output_file),
    ]

    try:

        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True
        )

        if result.returncode != 0:

            print(
                "⚠️ Failed to prepare clip:"
            )

            print(
                result.stderr[-2000:]
            )

            return False

        return True

    except Exception as e:

        print(
            f"⚠️ prepare_clip error: {e}"
        )

        return False


# ============================================================
# BUILD VISUAL TRACK
# ============================================================

def build_visual_track(
    clips,
    duration
):

    print(
        "🎞️ Building visual track..."
    )

    prepared = []

    # Даём исходным клипам небольшой запас.
    preparation_duration = (
        duration
        + 2.0
    )

    for index, clip in enumerate(
        clips
    ):

        output = (
            WORK_DIR
            / f"prepared_{index}.mp4"
        )

        success = prepare_clip(

            clip,

            output,

            preparation_duration
        )

        if success:

            prepared.append(
                output
            )

    if not prepared:

        print(
            "❌ No prepared clips."
        )

        return None

    # Каждый клип получает одинаковый кусок времени.
    segment_duration = (
        duration
        / len(prepared)
    )

    filter_parts = []

    for index in range(
        len(prepared)
    ):

        filter_parts.append(

            f"[{index}:v]"
            f"trim=start=0:"
            f"duration={segment_duration:.6f},"
            f"setpts=PTS-STARTPTS"
            f"[v{index}]"
        )

    joined = "".join(

        f"[v{index}]"
        for index in range(
            len(prepared)
        )
    )

    filter_parts.append(

        f"{joined}"
        f"concat=n={len(prepared)}:"
        f"v=1:a=0,"
        f"format=yuv420p"
        f"[v]"
    )

    merged = (
        WORK_DIR
        / "merged.mp4"
    )

    command = [
        "ffmpeg",
        "-y"
    ]

    for clip in prepared:

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
        "30",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-an",

        str(merged),
    ]

    try:

        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True
        )

        if result.returncode != 0:

            print(
                "❌ Visual track creation failed:"
            )

            print(
                result.stderr[-5000:]
            )

            return None

    except Exception as e:

        print(
            f"❌ Visual track error: {e}"
        )

        return None

    if not merged.exists():

        print(
            "❌ merged.mp4 was not created."
        )

        return None

    merged_duration = get_duration(
        merged
    )

    print(
        f"🎞️ Visual track duration: "
        f"{merged_duration:.3f}s"
    )

    if merged_duration + 0.05 < duration:

        print(
            "❌ Visual track is shorter "
            "than target duration."
        )

        return None

    return merged


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_video(
    clips,
    script,
    music
):

    print()
    print(
        "🎬 Creating final video..."
    )

    # ========================================================
    # IMPORTANT:
    # THE VOICE IS THE MASTER CLOCK.
    # ========================================================

    voice_duration = get_duration(
        AUDIO_FILE
    )

    if voice_duration <= 0:

        print(
            "❌ Invalid voice duration."
        )

        return False

    print(
        f"🎙️ REAL voice duration: "
        f"{voice_duration:.3f}s"
    )

    # Добавляем хвост после речи.
    target_duration = (
        voice_duration
        + VOICE_TAIL_SECONDS
    )

    # Минимальная длина.
    if target_duration < MIN_VIDEO_SECONDS:

        target_duration = (
            MIN_VIDEO_SECONDS
        )

    # Защита от слишком длинного ролика.
    if target_duration > MAX_VIDEO_SECONDS:

        print(
            f"⚠️ Voice is longer than "
            f"{MAX_VIDEO_SECONDS}s."
        )

        print(
            "❌ Video creation aborted."
        )

        return False

    print(
        f"🎬 Target video duration: "
        f"{target_duration:.3f}s"
    )

    print(
        "🚫 Subtitles: DISABLED"
    )

    print(
        "🚫 WhisperX: DISABLED"
    )

    print(
        "🚫 Forced Alignment: DISABLED"
    )

    print(
        "🚫 ASS subtitles: DISABLED"
    )

    # ========================================================
    # VISUAL TRACK
    # ========================================================

    merged = build_visual_track(
        clips,
        target_duration
    )

    if not merged:

        return False

    # ========================================================
    # FINAL AUDIO + VIDEO
    # ========================================================

    print(
        "🎧 Building final audio..."
    )

    if music:

        filter_complex = (

            "[1:a]"
            "aresample=44100,"
            "apad,"
            f"atrim=0:{target_duration:.6f},"
            "asetpts=N/SR/TB"
            "[voice];"

            "[2:a]"
            "aresample=44100,"
            f"volume={MUSIC_VOLUME},"
            "apad,"
            f"atrim=0:{target_duration:.6f},"
            "asetpts=N/SR/TB"
            "[music];"

            "[voice][music]"
            "amix=inputs=2:"
            "duration=first:"
            "dropout_transition=0,"
            "aresample=44100"
            "[finalaudio]"
        )

        command = [

            "ffmpeg",

            "-y",

            "-i",
            str(merged),

            "-i",
            str(AUDIO_FILE),

            "-stream_loop",
            "-1",

            "-i",
            str(music),

            "-filter_complex",
            filter_complex,

            "-map",
            "0:v:0",

            "-map",
            "[finalaudio]",

            # ВАЖНО:
            # НЕТ -vf subtitles.
            # НЕТ ASS.
            # НЕТ WhisperX.
            # НЕТ forced alignment.

            "-t",
            f"{target_duration:.6f}",

            "-r",
            "30",

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

            str(FINAL_VIDEO),
        ]

    else:

        command = [

            "ffmpeg",

            "-y",

            "-i",
            str(merged),

            "-i",
            str(AUDIO_FILE),

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            "-t",
            f"{target_duration:.6f}",

            "-r",
            "30",

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

            str(FINAL_VIDEO),
        ]

    print(
        "✂️ Rendering final MP4..."
    )

    try:

        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True
        )

        if result.returncode != 0:

            print(
                "❌ FFmpeg final render error:"
            )

            print(
                result.stderr[-7000:]
            )

            return False

    except Exception as e:

        print(
            f"❌ Final render exception: {e}"
        )

        return False

    # ========================================================
    # FINAL FILE CHECK
    # ========================================================

    if not FINAL_VIDEO.exists():

        print(
            "❌ Final video was not created."
        )

        return False

    final_duration = get_duration(
        FINAL_VIDEO
    )

    final_audio_duration = get_audio_duration(
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
        f"🎬 Target: "
        f"{target_duration:.3f}s"
    )

    print(
        f"🎞️ Final video: "
        f"{final_duration:.3f}s"
    )

    print(
        f"🔊 Final audio: "
        f"{final_audio_duration:.3f}s"
    )

    print(
        "======================================"
    )

    # ========================================================
    # HARD SAFETY CHECK #1
    # VIDEO >= VOICE
    # ========================================================

    if final_duration + 0.05 < voice_duration:

        print()
        print(
            "❌❌❌ CRITICAL:"
        )

        print(
            "Final video is SHORTER "
            "than the voice!"
        )

        print(
            f"Voice: {voice_duration:.3f}s"
        )

        print(
            f"Video: {final_duration:.3f}s"
        )

        print(
            "❌ Video will NOT be accepted."
        )

        return False

    # ========================================================
    # HARD SAFETY CHECK #2
    # AUDIO >= VOICE
    # ========================================================

    if final_audio_duration + 0.05 < voice_duration:

        print()
        print(
            "❌❌❌ CRITICAL:"
        )

        print(
            "Final audio is SHORTER "
            "than the original voice!"
        )

        print(
            f"Voice: {voice_duration:.3f}s"
        )

        print(
            f"Final audio: "
            f"{final_audio_duration:.3f}s"
        )

        print(
            "❌ Video will NOT be accepted."
        )

        return False

    # ========================================================
    # SAFETY CHECK #3
    # VIDEO HAS A TAIL
    # ========================================================

    tail = (
        final_duration
        - voice_duration
    )

    print(
        f"🛡️ Voice safety tail: "
        f"{tail:.3f}s"
    )

    if tail < 0.20:

        print(
            "⚠️ Safety tail is very small."
        )

        print(
            "The video is technically valid, "
            "but this is unusual."
        )

    print(
        f"📦 Size: "
        f"{FINAL_VIDEO.stat().st_size / 1024 / 1024:.2f} MB"
    )

    print(
        "✅ Final video passed "
        "voice-duration safety checks."
    )

    return True


# ============================================================
# AUDIO DURATION
# ============================================================

def get_audio_duration(file):

    command = [

        "ffprobe",

        "-v",
        "error",

        "-select_streams",
        "a:0",

        "-show_entries",
        "stream=duration",

        "-of",
        "default=noprint_wrappers=1:nokey=1",

        str(file),
    ]

    try:

        result = subprocess.run(

            command,

            capture_output=True,

            text=True,

            check=True
        )

        value = result.stdout.strip()

        if not value:

            return 0.0

        return float(
            value
        )

    except Exception as e:

        print(
            f"⚠️ Could not read audio duration: {e}"
        )

        return 0.0


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

    # ========================================================
    # ENVIRONMENT
    # ========================================================

    if not check_environment():

        return 1

    # ========================================================
    # CLEAN
    # ========================================================

    clean_work_directory()

    # ========================================================
    # GENERATE SCRIPT
    # ========================================================

    content = generate_script()

    if not content:

        print(
            "❌ Content generation failed."
        )

        return 1

    # ========================================================
    # GENERATE VOICE
    # ========================================================

    if not generate_voice(
        content["script"]
    ):

        print(
            "❌ Voice generation failed."
        )

        return 1

    # ========================================================
    # GET FOOTAGE
    # ========================================================

    clips = get_video_clips(
        content["pexels_queries"]
    )

    if not clips:

        print(
            "❌ Could not find video footage."
        )

        return 1

    # ========================================================
    # MUSIC
    # ========================================================

    music = get_music()

    # ========================================================
    # CREATE VIDEO
    # ========================================================

    if not create_video(

        clips,

        content["script"],

        music
    ):

        print(
            "❌ Video rendering failed."
        )

        return 1

    # ========================================================
    # FINISHED
    # ========================================================

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

    print(
        f"📁 Output: {FINAL_VIDEO}"
    )

    print(
        "🚫 Embedded subtitles: NO"
    )

    print(
        "🎙️ Voice: FULL"
    )

    print(
        "🛡️ Duration protection: ON"
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )