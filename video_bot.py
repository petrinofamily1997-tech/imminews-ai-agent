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

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Optional WhisperX fallback for subtitle alignment.
# Install with: pip install whisperx
WHISPERX_ENABLED = os.getenv("WHISPERX_ENABLED", "true").lower() not in ("0", "false", "no")
WHISPERX_MODEL = os.getenv("WHISPERX_MODEL", "small")
WHISPERX_DEVICE = os.getenv("WHISPERX_DEVICE", "cpu")
WHISPERX_COMPUTE_TYPE = os.getenv("WHISPERX_COMPUTE_TYPE", "int8")

# Alignment quality checks.
ALIGNMENT_MAX_END_GAP = 0.80
ALIGNMENT_MAX_COVERAGE_GAP = 1.20
ALIGNMENT_MAX_WORD_DURATION = 3.50
ALIGNMENT_MIN_WORDS = 3
SUBTITLE_MAX_WORDS = 6
SUBTITLE_MAX_CHARS = 44
SUBTITLE_MAX_DURATION = 3.80
SUBTITLE_MIN_DURATION = 0.70
SUBTITLE_LEAD_IN = 0.03
SUBTITLE_TAIL = 0.06

BASE_DIR = Path(__file__).resolve().parent

MUSIC_DIR = BASE_DIR / "assets" / "music"
WORK_DIR = BASE_DIR / "video_work"
OUTPUT_DIR = BASE_DIR / "output"

AUDIO_FILE = WORK_DIR / "voice.mp3"
FINAL_VIDEO = OUTPUT_DIR / "video.mp4"

MUSIC_VOLUME = 0.06

MIN_VIDEO_SECONDS = 15
MAX_VIDEO_SECONDS = 9999

# Remembers the last N topics used, so the bot doesn't
# generate the same subject over and over between runs.
TOPICS_HISTORY_FILE = BASE_DIR / "topics_history.json"
TOPICS_HISTORY_SIZE = 12

# Subtitle pacing: how long a caption chunk must stay on
# screen at minimum, so fast speech doesn't flash by unreadably.
MIN_SUBTITLE_SECONDS = 1.25
MAX_SUBTITLE_SECONDS = 3.8
MAX_WORDS_PER_GROUP = 7
MAX_CHARS_PER_GROUP = 52

# Subtitles are now word-by-word using ElevenLabs timestamps.
# These group settings remain only for backwards compatibility.


# ============================================================
# CURRENT GROQ MODELS
# ============================================================

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
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
# CLEAN
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


# ============================================================
# TOPIC POOL (for variety, at zero cost — no paid news API)
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


# Бесплатные RSS-источники: никакого платного news API.
# Google News RSS собирает свежие публикации по заданному запросу.
FREE_NEWS_RSS = [
    "https://news.google.com/rss/search?q=деньги+экономика+финансы&hl=ru&gl=RU&ceid=RU:ru",
    "https://news.google.com/rss/search?q=инфляция+ставка+банки+рубль&hl=ru&gl=RU&ceid=RU:ru",
    "https://news.google.com/rss/search?q=акции+инвестиции+рынок&hl=ru&gl=RU&ceid=RU:ru",
    "https://news.google.com/rss/search?q=нефть+золото+валюта+экономика&hl=ru&gl=RU&ceid=RU:ru",
]

NEWS_TIMEOUT = 15
NEWS_TOPIC_CHANCE = 0.45


def clean_tts_text(text):
    """Убирает из текста символы/конструкции, которые не должны озвучиваться."""
    text = clean_text(text)

    # Убираем markdown-подобные конструкции и служебные тире.
    text = re.sub(r"(?m)^[ \t]*[-–—•]\s*", "", text)
    text = text.replace("—", ", ")
    text = text.replace("–", ", ")
    text = text.replace("−", "-")
    text = re.sub(r"\s*-\s*", " ", text)

    # Не даем TTS читать возможные служебные подписи/сценические ремарки.
    text = re.sub(r"\[(?:.*?)\]", "", text)
    text = re.sub(r"\((?:HOOK|PAUSE|CTA|INTRO|OUTRO|SFX|MUSIC).*?\)", "", text, flags=re.I)

    # Убираем лишние пробелы вокруг пунктуации.
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:]){2,}", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def fetch_free_news_topic():
    """Пробует бесплатно получить свежую финансовую новость через RSS."""
    import xml.etree.ElementTree as ET

    feeds = FREE_NEWS_RSS[:]
    random.shuffle(feeds)

    headers = {
        "User-Agent": "Mozilla/5.0 (FinancialVideoBot/1.0)"
    }

    for feed_url in feeds:
        try:
            response = requests.get(
                feed_url,
                headers=headers,
                timeout=NEWS_TIMEOUT,
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            items = root.findall(".//item")

            candidates = []
            for item in items[:15]:
                title_node = item.find("title")
                link_node = item.find("link")

                title = clean_tts_text(
                    title_node.text if title_node is not None and title_node.text else ""
                )
                link = (
                    link_node.text.strip()
                    if link_node is not None and link_node.text
                    else ""
                )

                if title and len(title) >= 20:
                    candidates.append((title, link))

            if candidates:
                title, link = random.choice(candidates)
                print(f"📰 Free RSS news topic: {title}")
                return {
                    "topic": title,
                    "source_url": link,
                }

        except Exception as e:
            print(f"⚠️ RSS news unavailable: {e}")

    return None


def choose_topic():
    # Примерно 45% роликов могут быть про свежую финансовую новость.
    # Если RSS временно недоступен, автоматически используется обычная тема.
    if random.random() < NEWS_TOPIC_CHANCE:
        news = fetch_free_news_topic()
        if news:
            return news["topic"]

    history = []

    if TOPICS_HISTORY_FILE.exists():
        try:
            history = json.loads(
                TOPICS_HISTORY_FILE.read_text(encoding="utf-8")
            )

            if not isinstance(history, list):
                history = []

        except Exception:
            history = []

    available = [
        t for t in MONEY_TOPICS
        if t not in history
    ] or list(MONEY_TOPICS)

    topic = random.choice(available)

    history.append(topic)
    history = history[-TOPICS_HISTORY_SIZE:]

    try:
        TOPICS_HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"⚠️ Could not save topic history: {e}")

    print(f"🎯 Selected topic: {topic}")

    return topic


# ============================================================
# GROQ
# ============================================================

def generate_script():

    print("🧠 Asking Groq to create a script...")

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
финансовых видео на русском языке.

Создавай оригинальный образ рассказчика:

умный,
спокойный,
холодный,
уверенный,
слегка провокационный,
философский,
с лёгким сарказмом.

Не копируй конкретных персонажей,
актеров, блогеров или их голоса.

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

Не используй тире, длинное тире или списки с дефисами внутри сценария. Используй обычные предложения с запятыми и точками.

Не добавляй в script слова вроде "HOOK", "ПАУЗА", "CTA", "SFX", "музыка", "озвучка", "сцена" или любые служебные пометки. Они не должны попадать в озвучку.

Не используй URL.

Не используй хэштеги.

Не используй эмодзи внутри сценария.

Не обещай гарантированную прибыль.

Не давай персональных инвестиционных рекомендаций.

Длина сценария:
примерно 110–160 слов. Пиши в естественном темпе для глубокой мужской озвучки, без коротких обрывочных фраз, чтобы субтитры не приходилось переключать слишком часто.

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

Конкретная тема ролика (раскрой именно её,
не подменяй на другую и не будь общим):
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

            data = json.loads(content)

            script = clean_tts_text(data.get("script", ""))

            title = clean_text(
                data.get("title", "")
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
            print("📜 SCRIPT:")
            print(script)
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
# ELEVENLABS
# ============================================================

def generate_voice(script):

    print("🎙️ Generating Russian voice with ElevenLabs...")

    # IMPORTANT: do NOT trust the TTS endpoint's alignment for subtitles.
    # We generate the audio first, then independently force-align the
    # finished audio against the exact script. This gives us a second,
    # independent timing pass for subtitles.
    tts_script = clean_tts_text(script)

    url = (
        "https://api.elevenlabs.io/v1/"
        f"text-to-speech/{ELEVENLABS_VOICE_ID}"
    )

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": tts_script,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
        "voice_settings": {
            "stability": 0.52,
            "similarity_boost": 0.78,
            "style": 0.32,
            "use_speaker_boost": True,
        },
    }

    try:
        response = requests.post(
            url, headers=headers, json=payload, timeout=180
        )

        if response.status_code != 200:
            print(f"❌ ElevenLabs TTS error {response.status_code}")
            print(response.text[:1500])
            return False

        AUDIO_FILE.write_bytes(response.content)

        if get_duration(AUDIO_FILE) <= 0:
            print("❌ ElevenLabs returned an invalid audio file.")
            return False

        # ------------------------------------------------------------
        # SECOND PASS: forced alignment
        # ------------------------------------------------------------
        # This endpoint receives the ACTUAL generated audio + the EXACT
        # script and finds where every word is really spoken.
        align_url = "https://api.elevenlabs.io/v1/forced-alignment"
        align_headers = {"xi-api-key": ELEVENLABS_API_KEY}

        with open(AUDIO_FILE, "rb") as audio_file:
            files = {
                "file": (AUDIO_FILE.name, audio_file, "audio/mpeg"),
            }
            data = {"text": tts_script}
            align_response = requests.post(
                align_url,
                headers=align_headers,
                files=files,
                data=data,
                timeout=180,
            )

        if align_response.status_code != 200:
            print(f"❌ Forced alignment error {align_response.status_code}")
            print(align_response.text[:2000])
            return False

        alignment = align_response.json()

        words = alignment.get("words") or []
        if not words:
            print("❌ Forced alignment returned no words.")
            return False

        with open(WORK_DIR / "alignment.json", "w", encoding="utf-8") as f:
            json.dump(alignment, f, ensure_ascii=False, indent=2)

        print(
            f"✅ Voice generated. Forced alignment found {len(words)} timed words. "
            f"Alignment loss: {alignment.get('loss', 'n/a')}"
        )
        return True

    except Exception as e:
        print(f"❌ ElevenLabs TTS/alignment error: {e}")
        return False


# ============================================================
# PEXELS
# ============================================================

def search_pexels_video(query):

    print(
        f"🔎 Pexels search: {query}"
    )

    url = (
        "https://api.pexels.com/videos/search"
    )

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {

        "query": query,

        "orientation": "portrait",

        "size": "medium",

        "per_page": 10,

        "locale": "en-US",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return None

        videos = response.json().get(
            "videos",
            []
        )

        if not videos:
            return None

        random.shuffle(videos)

        for video in videos:

            files = video.get(
                "video_files",
                []
            )

            portrait = [
                f
                for f in files
                if f.get("width", 0)
                < f.get("height", 0)
            ]

            candidates = (
                portrait or files
            )

            if not candidates:
                continue

            candidates.sort(
                key=lambda f:
                abs(
                    f.get("width", 0)
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


def download_video(url, destination):

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
                    file.write(chunk)

        return destination.exists()

    except Exception as e:

        print(
            f"❌ Download error: {e}"
        )

        return False


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
        queries + fallback
    )

    clips = []

    for query in all_queries:

        if len(clips) >= 3:
            break

        link = search_pexels_video(
            query
        )

        if not link:
            continue

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

    print(
        f"✅ Downloaded {len(clips)} clips."
    )

    return clips


# ============================================================
# MUSIC
# ============================================================

def get_music():

    tracks = list(
        MUSIC_DIR.glob("*.mp3")
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
# VIDEO HELPERS
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

        return float(
            result.stdout.strip()
        )

    except:

        return 0


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

        subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        return True

    except:

        return False


# ============================================================
# SUBTITLES
# ============================================================

def _normalize_alignment_words(raw_words, duration):
    """Normalize ElevenLabs/WhisperX word objects to {text,start,end}."""
    words = []

    for item in raw_words or []:
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        # WhisperX uses start/end; ElevenLabs forced alignment also exposes
        # word-level start/end. Ignore non-word alignment entries.
        if item.get("type") not in (None, "word"):
            continue

        try:
            start = float(item["start"])
            end = float(item["end"])
        except (KeyError, TypeError, ValueError):
            continue

        if not (start >= 0 and end > start):
            continue

        start = min(start, duration)
        end = min(end, duration)

        if end <= start:
            continue

        words.append({
            "text": text,
            "start": start,
            "end": end,
        })

    words.sort(key=lambda x: (x["start"], x["end"]))
    return words


def _validate_alignment(words, duration):
    """
    Return (ok, diagnostics).

    The important check is not just whether timestamps exist. We verify:
    - enough words were aligned;
    - the alignment reaches close enough to the end of the audio;
    - no single word has an implausibly long duration;
    - timestamps are monotonic.
    """
    diagnostics = {}

    if duration <= 0:
        return False, {"reason": "invalid audio duration"}

    if len(words) < ALIGNMENT_MIN_WORDS:
        return False, {
            "reason": "too few aligned words",
            "word_count": len(words),
        }

    last_end = words[-1]["end"]
    first_start = words[0]["start"]
    end_gap = max(0.0, duration - last_end)
    coverage = max(0.0, last_end - first_start)

    diagnostics.update({
        "word_count": len(words),
        "first_start": first_start,
        "last_end": last_end,
        "audio_duration": duration,
        "end_gap": end_gap,
        "coverage": coverage,
    })

    previous_end = -1.0
    max_word_duration = 0.0

    for word in words:
        if word["start"] + 0.02 < previous_end:
            return False, {
                **diagnostics,
                "reason": "non-monotonic timestamps",
            }

        word_duration = word["end"] - word["start"]
        max_word_duration = max(max_word_duration, word_duration)
        previous_end = word["end"]

    diagnostics["max_word_duration"] = max_word_duration

    # Some natural silence after the last spoken word is normal.
    if end_gap > ALIGNMENT_MAX_END_GAP:
        return False, {
            **diagnostics,
            "reason": "alignment ends too early",
        }

    if max_word_duration > ALIGNMENT_MAX_WORD_DURATION:
        return False, {
            **diagnostics,
            "reason": "implausibly long word timestamp",
        }

    return True, diagnostics


def _load_elevenlabs_alignment(duration):
    """Load and validate the ElevenLabs forced-alignment result."""
    alignment_file = WORK_DIR / "alignment.json"

    if not alignment_file.exists():
        return None, {"reason": "alignment.json missing"}

    try:
        with open(alignment_file, "r", encoding="utf-8") as f:
            alignment = json.load(f)
    except Exception as e:
        return None, {"reason": f"invalid alignment.json: {e}"}

    words = _normalize_alignment_words(
        alignment.get("words") or [],
        duration,
    )

    ok, diagnostics = _validate_alignment(words, duration)
    diagnostics["source"] = "elevenlabs"

    if not ok:
        print(
            "⚠️ ElevenLabs alignment failed validation: "
            f"{diagnostics.get('reason', 'unknown reason')}"
        )
        return None, diagnostics

    print(
        "✅ ElevenLabs alignment passed: "
        f"{len(words)} words, "
        f"last word {words[-1]['end']:.3f}s, "
        f"audio {duration:.3f}s."
    )
    return words, diagnostics


def _run_whisperx_alignment(script, duration):
    """
    Fallback alignment using WhisperX on the actual generated voice.mp3.

    WhisperX is imported lazily so the normal ElevenLabs path does not require
    WhisperX to be installed. If WhisperX is unavailable, the function simply
    returns None and the caller can stop with a useful diagnostic.
    """
    if not WHISPERX_ENABLED:
        return None, {"reason": "WHISPERX_ENABLED=false"}

    try:
        import torch
        import whisperx
    except ImportError as e:
        return None, {
            "reason": "WhisperX is not installed",
            "error": str(e),
        }

    try:
        device = WHISPERX_DEVICE
        compute_type = WHISPERX_COMPUTE_TYPE

        # CPU/int8 is the safest default for a generic deployment.
        print(
            f"🧩 WhisperX fallback: model={WHISPERX_MODEL}, "
            f"device={device}, compute_type={compute_type}"
        )

        model = whisperx.load_model(
            WHISPERX_MODEL,
            device,
            compute_type=compute_type,
            language="ru",
        )

        audio = whisperx.load_audio(str(AUDIO_FILE))
        result = model.transcribe(audio, batch_size=8, language="ru")

        # Release the ASR model before loading the align model when possible.
        try:
            del model
            if device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        language_code = result.get("language") or "ru"

        metadata, align_model = whisperx.load_align_model(
            language_code=language_code,
            device=device,
        )

        aligned = whisperx.align(
            result.get("segments", []),
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )

        raw_words = []
        for segment in aligned.get("segments", []):
            for word in segment.get("words", []):
                if word.get("start") is None or word.get("end") is None:
                    continue
                raw_words.append({
                    "text": str(word.get("word", "")).strip(),
                    "start": word.get("start"),
                    "end": word.get("end"),
                })

        words = _normalize_alignment_words(raw_words, duration)
        ok, diagnostics = _validate_alignment(words, duration)
        diagnostics["source"] = "whisperx"

        # Save the fallback result so it is inspectable/debuggable.
        fallback_file = WORK_DIR / "alignment_whisperx.json"
        with open(fallback_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "source": "whisperx",
                    "words": words,
                    "diagnostics": diagnostics,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        if not ok:
            print(
                "❌ WhisperX alignment also failed validation: "
                f"{diagnostics.get('reason', 'unknown reason')}"
            )
            return None, diagnostics

        print(
            "✅ WhisperX alignment passed: "
            f"{len(words)} words, "
            f"last word {words[-1]['end']:.3f}s, "
            f"audio {duration:.3f}s."
        )

        return words, diagnostics

    except Exception as e:
        print(f"❌ WhisperX fallback error: {e}")
        return None, {
            "reason": "WhisperX exception",
            "error": str(e),
        }


def _build_subtitle_cues(words, duration):
    """
    Build readable cues from real word timestamps.

    Unlike the old implementation, a cue is allowed to occupy the natural
    silence before the next cue. We never invent a new speech timestamp, but
    we avoid making subtitles 'race' ahead because every cue ended exactly
    at the final phoneme of its last word.
    """
    if not words:
        return []

    cues = []
    current = []
    current_chars = 0

    def flush(next_start=None):
        nonlocal current, current_chars

        if not current:
            return

        start = current[0]["start"]
        spoken_end = current[-1]["end"]

        # Keep a tiny lead-in, but never before zero.
        start = max(0.0, start - SUBTITLE_LEAD_IN)

        # If there is a following word/cue, use a conservative part of the
        # silence as display tail. This prevents visual subtitles from
        # disappearing immediately after the last syllable.
        if next_start is not None and next_start > spoken_end:
            available_gap = next_start - spoken_end
            tail = min(SUBTITLE_TAIL, available_gap * 0.35)
            end = spoken_end + tail
        else:
            end = spoken_end + SUBTITLE_TAIL

        end = min(duration, end)

        # Never create a cue longer than the configured maximum.
        if end - start > SUBTITLE_MAX_DURATION:
            end = start + SUBTITLE_MAX_DURATION

        if end > start:
            cues.append({
                "text": " ".join(w["text"] for w in current),
                "start": start,
                "end": end,
            })

        current = []
        current_chars = 0

    for index, word in enumerate(words):
        next_word = words[index + 1] if index + 1 < len(words) else None

        proposed_chars = (
            current_chars
            + (1 if current else 0)
            + len(word["text"])
        )

        should_break = False

        if current and len(current) >= SUBTITLE_MAX_WORDS:
            should_break = True

        if current and proposed_chars > SUBTITLE_MAX_CHARS:
            should_break = True

        if current:
            current_duration = word["end"] - current[0]["start"]
            if current_duration > SUBTITLE_MAX_DURATION:
                should_break = True

        # A meaningful pause is a natural subtitle boundary.
        if current and next_word is not None:
            pause_before_current_next = word["start"] - current[-1]["end"]
            if pause_before_current_next >= 0.55:
                should_break = True

        if should_break:
            flush(next_start=word["start"])

        current.append(word)
        current_chars += (
            (1 if len(current) > 1 else 0)
            + len(word["text"])
        )

        # Prefer punctuation as a boundary, but only if the cue is not tiny.
        if (
            word["text"][-1:] in ".!?;:"
            and len(current) >= 2
        ):
            if next_word is not None:
                flush(next_start=next_word["start"])
            else:
                flush()

    flush()

    # Merge pathological micro-cues caused by punctuation or unusual ASR.
    merged = []
    for cue in cues:
        if (
            merged
            and cue["start"] - merged[-1]["end"] < 0.15
            and cue["end"] - merged[-1]["start"] <= SUBTITLE_MAX_DURATION
            and len((merged[-1]["text"] + " " + cue["text"])) <= SUBTITLE_MAX_CHARS
        ):
            merged[-1]["text"] += " " + cue["text"]
            merged[-1]["end"] = cue["end"]
        else:
            merged.append(cue)

    # Final safety: all subtitle timings remain inside the real audio.
    for cue in merged:
        cue["start"] = max(0.0, min(cue["start"], duration))
        cue["end"] = max(cue["start"], min(cue["end"], duration))

    return merged


def make_subtitles(script, duration):
    """
    Create ASS subtitles from validated word-level alignment.

    Primary source: ElevenLabs forced alignment.
    Fallback: WhisperX on the actual generated voice file.

    Crucially, subtitle timing is NEVER derived from character counts,
    script length, or an assumed speech rate.
    """
    words, diagnostics = _load_elevenlabs_alignment(duration)

    if words is None:
        print("🔄 Switching to WhisperX alignment fallback...")
        words, whisper_diagnostics = _run_whisperx_alignment(
            clean_tts_text(script),
            duration,
        )

        if words is None:
            raise RuntimeError(
                "Subtitle alignment failed. "
                f"ElevenLabs: {diagnostics}. "
                f"WhisperX: {whisper_diagnostics}"
            )

    cues = _build_subtitle_cues(words, duration)

    if not cues:
        raise RuntimeError("Could not build subtitle cues from alignment.")

    subtitle_file = WORK_DIR / "subtitles.ass"

    def ass_time(seconds):
        seconds = max(0.0, min(float(seconds), duration))
        total_cs = int(round(seconds * 100))
        h = total_cs // 360000
        m = (total_cs % 360000) // 6000
        s = (total_cs % 6000) // 100
        cs = total_cs % 100
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    with open(subtitle_file, "w", encoding="utf-8") as f:
        f.write(
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,82,&H00FFFFFF,&H00FFFFFF,&H00101010,"
            "&H99000000,1,0,0,0,100,100,0,0,1,5,2,5,60,60,650,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text\n"
        )

        for cue in cues:
            text = (
                cue["text"]
                .replace("{", "\\{")
                .replace("}", "\\}")
            )

            f.write(
                f"Dialogue: 0,{ass_time(cue['start'])},"
                f"{ass_time(cue['end'])},Default,,0,0,0,,"
                f"{{\\b1\\c&H00FFFFFF&}}{text}{{\\b0}}\n"
            )

    last_subtitle_end = cues[-1]["end"]

    print(
        f"📝 Subtitles created from {diagnostics.get('source', 'alignment')} "
        f"alignment: {len(cues)} cues; "
        f"last subtitle ends at {last_subtitle_end:.2f}s; "
        f"voice duration is {duration:.2f}s."
    )

    # Explicit diagnostic for the exact failure mode reported by the user.
    remaining_audio = max(0.0, duration - last_subtitle_end)
    if remaining_audio > ALIGNMENT_MAX_COVERAGE_GAP:
        print(
            f"⚠️ Subtitle/audio tail gap: {remaining_audio:.2f}s. "
            "The last subtitle does not cover the final spoken region."
        )
    else:
        print(
            f"✅ Subtitle/audio tail gap is only {remaining_audio:.2f}s."
        )

    return subtitle_file


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_video(clips, script, music):

    print("🎬 Creating final video...")

    voice_duration = get_duration(AUDIO_FILE)
    if voice_duration <= 0:
        print("❌ Invalid voice duration.")
        return False

    # The AUDIO is the absolute master clock. Add a small tail so the final
    # consonant is never cut off. The video track is explicitly constructed
    # to be at least this long; no concat-demuxer duration directives and no
    # stream-copy are used.
    duration = voice_duration + 0.80

    print(f"🎙️ Voice duration: {voice_duration:.3f}s")
    print(f"🎬 Target duration: {duration:.3f}s")

    prepared = []
    for i, clip in enumerate(clips):
        output = WORK_DIR / f"prepared_{i}.mp4"
        if prepare_clip(clip, output, duration + 1.0):
            prepared.append(output)

    if not prepared:
        print("❌ No prepared video clips.")
        return False

    # Build the visual track with FFmpeg's filter graph and re-encode it.
    # This guarantees that the video stream itself lasts exactly `duration`.
    segment = duration / len(prepared)
    filter_parts = []
    for i in range(len(prepared)):
        filter_parts.append(
            f"[{i}:v]trim=start=0:duration={segment:.6f},"
            f"setpts=PTS-STARTPTS[v{i}]"
        )
    joined_inputs = "".join(f"[v{i}]" for i in range(len(prepared)))
    filter_parts.append(
        f"{joined_inputs}concat=n={len(prepared)}:v=1:a=0,"
        "format=yuv420p[v]"
    )

    visual_command = ["ffmpeg", "-y"]
    for clip in prepared:
        visual_command += ["-i", str(clip)]
    visual_command += [
        "-filter_complex", ";".join(filter_parts),
        "-map", "[v]",
        "-t", f"{duration:.6f}",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        str(WORK_DIR / "merged.mp4"),
    ]

    merged = WORK_DIR / "merged.mp4"
    try:
        subprocess.run(
            visual_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("❌ Visual track creation failed:")
        print(e.stderr[-5000:])
        return False

    merged_duration = get_duration(merged)
    print(f"🎞️ Visual track duration: {merged_duration:.3f}s")
    if merged_duration + 0.05 < duration:
        print("❌ Visual track is still shorter than target. Aborting.")
        return False

    subtitle_file = make_subtitles(clean_tts_text(script), voice_duration)
    subtitle_path = (
        str(subtitle_file.resolve())
        .replace("\\", "/")
        .replace(":", "\\:")
    )

    video_filter = (
        f"subtitles='{subtitle_path}':"
        "force_style='"
        "FontName=Arial,FontSize=82,Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,"
        "BackColour=&H99000000,BorderStyle=1,Outline=5,Shadow=2,"
        "Alignment=5,MarginL=60,MarginR=60,MarginV=0'"
    )

    # Audio is also built independently. `-shortest` is intentionally NOT
    # used. The final duration is explicitly controlled by -t.
    if music:
        command = [
            "ffmpeg", "-y",
            "-i", str(merged),
            "-i", str(AUDIO_FILE),
            "-stream_loop", "-1",
            "-i", str(music),
            "-filter_complex",
            (
                "[1:a]aresample=44100,apad,atrim=0:" + f"{duration:.6f}" + ",[voice];"
                f"[2:a]aresample=44100,volume={MUSIC_VOLUME},"
                f"apad,atrim=0:{duration:.6f}[music];"
                "[voice][music]amix=inputs=2:duration=first:dropout_transition=0[finalaudio]"
            ),
            "-map", "0:v:0",
            "-map", "[finalaudio]",
            "-vf", video_filter,
            "-t", f"{duration:.6f}",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-movflags", "+faststart",
            str(FINAL_VIDEO),
        ]
    else:
        command = [
            "ffmpeg", "-y",
            "-i", str(merged),
            "-i", str(AUDIO_FILE),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-vf", video_filter,
            "-t", f"{duration:.6f}",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-movflags", "+faststart",
            str(FINAL_VIDEO),
        ]

    print("✂️ Rendering final MP4...")
    try:
        subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg final render error:")
        print(e.stderr[-6000:])
        return False

    if not FINAL_VIDEO.exists():
        print("❌ Final video was not created.")
        return False

    final_duration = get_duration(FINAL_VIDEO)
    print(f"✅ VIDEO CREATED")
    print(f"⏱️ Final duration: {final_duration:.3f}s")
    print(f"🎙️ Voice duration: {voice_duration:.3f}s")

    # HARD SAFETY CHECK: the final MP4 may NEVER be shorter than the voice.
    if final_duration + 0.05 < voice_duration:
        print("❌ SAFETY CHECK FAILED: final video is shorter than voice.")
        return False

    print(f"📦 Size: {FINAL_VIDEO.stat().st_size / 1024 / 1024:.2f} MB")
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

    content = generate_script()

    if not content:

        print(
            "❌ Content generation failed."
        )

        return 1

    if not generate_voice(
        content["script"]
    ):

        print(
            "❌ Voice generation failed."
        )

        return 1

    clips = get_video_clips(
        content["pexels_queries"]
    )

    if not clips:

        print(
            "❌ Could not find video footage."
        )

        return 1

    music = get_music()

    if not create_video(
        clips,
        content["script"],
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())