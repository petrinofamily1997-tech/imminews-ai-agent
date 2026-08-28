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

    # В озвучку уходит только очищенный сценарий.
    # Никаких служебных слов, тире и Markdown, которые ElevenLabs
    # потенциально может интерпретировать как часть текста.
    tts_script = clean_tts_text(script)

    url = (
        "https://api.elevenlabs.io/v1/"
        f"text-to-speech/{ELEVENLABS_VOICE_ID}/with-timestamps"
    )

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "text": tts_script,
        "model_id": "eleven_multilingual_v2",
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
            print(f"❌ ElevenLabs error {response.status_code}")
            print(response.text[:1500])
            return False

        data = response.json()
        audio_b64 = data.get("audio_base64")
        alignment = data.get("alignment") or data.get("normalized_alignment")

        if not audio_b64 or not alignment:
            print("❌ ElevenLabs did not return audio + timestamps.")
            return False

        import base64
        AUDIO_FILE.write_bytes(base64.b64decode(audio_b64))

        with open(WORK_DIR / "alignment.json", "w", encoding="utf-8") as f:
            json.dump(alignment, f, ensure_ascii=False)

        print("✅ Voice generated with exact timestamps.")
        return True

    except Exception as e:
        print(f"❌ ElevenLabs error: {e}")
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

def make_subtitles(script, duration):
    """
    Создаёт читаемые субтитры, используя реальные таймкоды ElevenLabs.

    ВАЖНО:
    Мы НЕ растягиваем субтитры искусственно и НЕ задаём им минимальную
    длительность. Иначе текст начинает появляться раньше голоса.

    Вместо одного слова на экран объединяем 3-5 соседних слов.
    Время группы = от начала первого слова до начала следующей группы.
    Поэтому субтитры всегда следуют за голосом и никогда не "убегают".
    """
    alignment_file = WORK_DIR / "alignment.json"

    if not alignment_file.exists():
        raise RuntimeError("alignment.json was not created by ElevenLabs.")

    with open(alignment_file, "r", encoding="utf-8") as f:
        alignment = json.load(f)

    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    char_durations = alignment.get("character_durations_seconds", [])

    if not chars or not starts or not char_durations:
        raise RuntimeError("ElevenLabs returned no usable character timestamps.")

    n = min(len(chars), len(starts), len(char_durations))

    # Восстанавливаем слова из character-level alignment.
    words = []
    current = []
    word_start = None
    word_end = None

    for i in range(n):
        ch = chars[i]
        st = float(starts[i])
        en = st + float(char_durations[i])

        if ch.isspace():
            if current:
                words.append({
                    "text": "".join(current),
                    "start": word_start,
                    "end": word_end,
                })
                current = []
                word_start = None
                word_end = None
        else:
            if word_start is None:
                word_start = st
            current.append(ch)
            word_end = en

    if current:
        words.append({
            "text": "".join(current),
            "start": word_start,
            "end": word_end,
        })

    if not words:
        raise RuntimeError("Could not reconstruct words from ElevenLabs timestamps.")

    # Исправляем границы слов: начало следующего слова является
    # надёжной границей предыдущего.
    timed_words = []
    for i, word in enumerate(words):
        start_time = max(0.0, float(word["start"]))

        if i + 1 < len(words):
            next_start = max(start_time, float(words[i + 1]["start"]))
            end_time = next_start
        else:
            end_time = float(word["end"])

        end_time = min(end_time, float(duration))

        if end_time <= start_time:
            continue

        timed_words.append({
            "text": word["text"],
            "start": start_time,
            "end": end_time,
        })

    if not timed_words:
        raise RuntimeError("Could not create timed subtitle words.")

    # ------------------------------------------------------------
    # Группируем слова.
    #
    # Например:
    # "Деньги любят тишину"
    # "но рынок любит"
    # "громкие новости"
    #
    # Группа НЕ получает искусственные 1.25-3.8 секунды.
    # Она живёт ровно по таймкодам голоса.
    # ------------------------------------------------------------
    MAX_WORDS = 5
    MAX_CHARS = 34

    groups = []
    current_group = []
    current_chars = 0

    def flush_group():
        nonlocal current_group, current_chars

        if not current_group:
            return

        groups.append({
            "text": " ".join(w["text"] for w in current_group),
            "start": current_group[0]["start"],
            "end": current_group[-1]["end"],
        })

        current_group = []
        current_chars = 0

    for i, word in enumerate(timed_words):
        word_text = word["text"]
        proposed_chars = (
            current_chars + len(word_text) +
            (1 if current_group else 0)
        )

        # Не делаем слишком длинную строку.
        if current_group and (
            len(current_group) >= MAX_WORDS or
            proposed_chars > MAX_CHARS
        ):
            flush_group()

        current_group.append(word)
        current_chars += len(word_text) + (1 if len(current_group) > 1 else 0)

        # После знака препинания лучше начать новую группу.
        if re.search(r"[.!?;:]$", word_text):
            flush_group()

    flush_group()

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
            "Style: Default,Arial,78,&H00FFFFFF,&H00FFFFFF,&H00101010,"
            "&H99000000,1,0,0,0,100,100,0,0,1,5,2,5,60,60,650,1\n\n"

            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text\n"
        )

        for group in groups:
            # ASS-экранирование.
            caption = (
                group["text"]
                .replace("\\", r"\\")
                .replace("{", r"\{")
                .replace("}", r"\}")
            )

            f.write(
                f"Dialogue: 0,{ass_time(group['start'])},{ass_time(group['end'])},"
                f"Default,,0,0,0,,{{\\b1}}{caption}{{\\b0}}\n"
            )

    print(
        f"📝 Synced subtitle groups: {len(groups)} "
        f"(3-5 words, exact ElevenLabs timing)."
    )

    return subtitle_file


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_video(clips, script, music):
    """
    Финальный рендер.

    ГОЛОС = MASTER CLOCK.
    Видео всегда минимум на 0.5 секунды длиннее голоса.
    FFmpeg не получает возможности закончить ролик раньше аудио.
    """
    print("🎬 Creating final video...")

    voice_duration = get_duration(AUDIO_FILE)

    if voice_duration <= 0:
        print("❌ Invalid voice duration.")
        return False

    # Небольшой запас после последнего слова.
    duration = voice_duration + 0.50

    print(f"🎙️ Voice duration: {voice_duration:.2f}s")
    print(f"🎬 Target video duration: {duration:.2f}s")

    prepared = []

    # Каждый клип готовим длиннее всего ролика.
    # Это исключает обрыв картинки в середине озвучки.
    for i, clip in enumerate(clips):
        output = WORK_DIR / f"prepared_{i}.mp4"

        if prepare_clip(
            clip,
            output,
            duration + 1.0
        ):
            prepared.append(output)

    if not prepared:
        print("❌ No prepared clips.")
        return False

    # ------------------------------------------------------------
    # Вместо concat demuxer + duration + -c copy используем
    # полноценный FFmpeg filter concat.
    #
    # Старый способ мог дать короткий merged.mp4 из-за особенностей
    # concat duration/keyframes. Теперь длительность контролируется
    # самим filter_complex.
    # ------------------------------------------------------------
    inputs = []
    filter_parts = []

    for i, clip in enumerate(prepared):
        inputs += ["-i", str(clip)]
        filter_parts.append(
            f"[{i}:v]trim=duration={duration:.3f},setpts=PTS-STARTPTS[v{i}]"
        )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(prepared)))

    filter_complex = (
        ";".join(filter_parts)
        + ";"
        + f"{concat_inputs}concat=n={len(prepared)}:v=1:a=0,"
          f"trim=duration={duration:.3f},setpts=PTS-STARTPTS[video]"
    )

    merged = WORK_DIR / "merged.mp4"

    merge_command = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[video]",
        "-an",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.3f}",
        str(merged),
    ]

    try:
        subprocess.run(
            merge_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("❌ Video merge failed:")
        print(e.stderr[-5000:])
        return False

    merged_duration = get_duration(merged)

    if merged_duration + 0.05 < voice_duration:
        print(
            f"❌ Merged video is too short: "
            f"{merged_duration:.2f}s < {voice_duration:.2f}s"
        )
        return False

    subtitle_file = make_subtitles(
        clean_tts_text(script),
        voice_duration
    )

    subtitle_path = (
        str(subtitle_file.resolve())
        .replace("\\", "/")
        .replace(":", "\\:")
    )

    video_filter = (
        f"subtitles='{subtitle_path}':"
        "force_style='"
        "FontName=Arial,"
        "FontSize=78,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,"
        "BackColour=&H99000000,"
        "BorderStyle=1,"
        "Outline=5,"
        "Shadow=2,"
        "Alignment=5,"
        "MarginL=60,"
        "MarginR=60,"
        "MarginV=0"
        "'"
    )

    # ------------------------------------------------------------
    # Голос остаётся главным аудиоисточником.
    # Музыка автоматически обрезается по длительности голоса.
    # ------------------------------------------------------------
    if music:
        command = [
            "ffmpeg", "-y",
            "-i", str(merged),
            "-i", str(AUDIO_FILE),
            "-stream_loop", "-1",
            "-i", str(music),
            "-filter_complex",
            (
                "[1:a]aresample=44100,asetpts=PTS-STARTPTS[voice];"
                f"[2:a]aresample=44100,volume={MUSIC_VOLUME},"
                "asetpts=PTS-STARTPTS[music];"
                "[voice][music]amix=inputs=2:duration=first:"
                "dropout_transition=0:normalize=0[finalaudio]"
            ),
            "-map", "0:v:0",
            "-map", "[finalaudio]",
            "-vf", video_filter,
            "-t", f"{duration:.3f}",
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
            "-t", f"{duration:.3f}",
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

    print("✂️ Rendering MP4...")

    try:
        subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        if not FINAL_VIDEO.exists():
            print("❌ Video was not created.")
            return False

        final_duration = get_duration(FINAL_VIDEO)
        print(f"✅ VIDEO CREATED")
        print(f"⏱️ Final video duration: {final_duration:.2f}s")
        print(f"🎙️ Voice duration: {voice_duration:.2f}s")

        # Жёсткая проверка: итоговый ролик не может быть короче голоса.
        if final_duration + 0.05 < voice_duration:
            print("❌ SAFETY CHECK FAILED: video is shorter than voice.")
            return False

        print(f"📦 Size: {FINAL_VIDEO.stat().st_size / 1024 / 1024:.2f} MB")
        return True

    except subprocess.CalledProcessError as e:
        print("❌ FFmpeg error:")
        print(e.stderr[-5000:])
        return False


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