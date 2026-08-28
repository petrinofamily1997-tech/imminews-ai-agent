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
ASSETS_DIR = BASE_DIR / "assets"

AUDIO_FILE = WORK_DIR / "voice.mp3"
FINAL_VIDEO = OUTPUT_DIR / "video.mp4"
PHOTO_FILE = ASSETS_DIR / "photo.png"

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
PHOTO_DURATION = 3.0

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
    text = text.replace("**", "").replace("__", "").replace("```", "").replace("`", "")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_tts_text(text):
    text = clean_text(text)
    text = re.sub(r"(?m)^[ \t]*[-–—•]\s*", "", text)
    text = text.replace("—", ", ").replace("–", ", ").replace("−", "-")
    text = re.sub(r"\s*-\s*", " ", text)
    text = re.sub(r"\[(.*?)\]", "", text)
    text = re.sub(r"\((HOOK|PAUSE|CTA|INTRO|OUTRO|SFX|MUSIC|SCENE|ОЗВУЧКА).*?\)", "", text, flags=re.I)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:]){2,}", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
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
    
    missing = [name for name, value in required.items() if not value]
    
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
    
    if not PHOTO_FILE.exists():
        print(f"⚠️ Рекламное фото не найдено: {PHOTO_FILE}, продолжаем без него")
    
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("✅ Environment OK")
    return True


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
                print(f"⚠️ Could not delete {item}: {e}")
    WORK_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NEWS
# ============================================================

def fetch_free_news_topic():
    import xml.etree.ElementTree as ET
    
    feeds = FREE_NEWS_RSS[:]
    random.shuffle(feeds)
    headers = {"User-Agent": "Mozilla/5.0 FinancialVideoBot/3.0"}
    
    for feed_url in feeds:
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            candidates = []
            
            for item in items[:20]:
                title_node = item.find("title")
                link_node = item.find("link")
                title = clean_tts_text(title_node.text if title_node is not None and title_node.text else "")
                link = link_node.text.strip() if link_node is not None and link_node.text else ""
                
                if title and len(title) >= 20:
                    candidates.append((title, link))
            
            if candidates:
                title, link = random.choice(candidates)
                print(f"📰 News topic: {title}")
                return {"topic": title, "source_url": link}
                
        except Exception as e:
            print(f"⚠️ RSS error: {e}")
    
    return None


def choose_topic():
    if random.random() < 0.45:
        news = fetch_free_news_topic()
        if news:
            return news["topic"]
    
    history = []
    if TOPICS_HISTORY_FILE.exists():
        try:
            history = json.loads(TOPICS_HISTORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = []
        except Exception:
            history = []
    
    available = [topic for topic in MONEY_TOPICS if topic not in history]
    if not available:
        available = MONEY_TOPICS[:]
    
    topic = random.choice(available)
    history.append(topic)
    history = history[-TOPICS_HISTORY_SIZE:]
    
    try:
        TOPICS_HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"⚠️ Topic history error: {e}")
    
    print(f"🎯 Selected topic: {topic}")
    return topic


# ============================================================
# PARSE GROQ RESPONSE
# ============================================================

def parse_script_response(text):
    if not text:
        return None
    
    text = text.strip()
    text = re.sub(r"```(?:text|json)?", "", text, flags=re.I)
    text = text.replace("```", "")
    
    title_match = re.search(r"TITLE\s*:\s*(.*?)(?:\n|$)", text, flags=re.I)
    title = ""
    if title_match:
        title = clean_text(title_match.group(1))
    
    script_match = re.search(r"SCRIPT\s*:\s*(.*?)(?=\n\s*PEXELS\s*:|\Z)", text, flags=re.I | re.S)
    if not script_match:
        return None
    
    script = clean_tts_text(script_match.group(1))
    
    queries = []
    pexels_match = re.search(r"PEXELS\s*:\s*(.*)$", text, flags=re.I | re.S)
    if pexels_match:
        raw_queries = pexels_match.group(1)
        lines = raw_queries.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^\s*(?:\d+[\.\)]|-|•)\s*", "", line)
            line = clean_text(line)
            if line:
                queries.append(line)
    
    unique_queries = []
    seen = set()
    for query in queries:
        normalized = query.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_queries.append(query)
    queries = unique_queries
    
    if not script:
        return None
    
    return {
        "title": title,
        "script": script,
        "pexels_queries": queries
    }


def validate_cta(script):
    lower = script.lower()
    required_phrases = ["что это значит", "твоего кошелька", "telegram"]
    for phrase in required_phrases:
        if phrase.lower() not in lower:
            return False
    telegram_variants = ["телеграм", "telegram"]
    if not any(x in lower for x in telegram_variants):
        return False
    return True


# ============================================================
# SCRIPT GENERATION
# ============================================================

def generate_script():
    print("🧠 Asking Groq to create a script...")
    
    style = random.choice(["PROVOCATIVE", "INTELLECTUAL", "DARK", "PHILOSOPHICAL", "ANALYTICAL"])
    topic = choose_topic()
    print(f"🎩 Selected style: {style}")
    
    client = Groq(api_key=GROQ_API_KEY)
    
    system_prompt = """
Ты профессиональный сценарист коротких финансовых видео для TikTok и YouTube Shorts.
Пиши на русском языке.

Темы: деньги, финансовая грамотность, заработок, экономика, бизнес, банки, инвестиции, инфляция, финансовые ошибки, психология денег, сохранение денег.

Стиль: умный, спокойный, уверенный, слегка провокационный, холодный, аналитичный, с лёгким сарказмом.

Не копируй конкретных блогеров.

СЦЕНАРИЙ:
Первые секунды должны сразу цеплять.
Не начинай со слов: "Сегодня мы поговорим", "В этом видео", "Привет всем", "Вы когда-нибудь задумывались"
Не используй клише.

Сначала создай интригу. Затем раскрой проблему. Затем объясни её простыми словами. Добавь конкретный жизненный пример. Дай неожиданный вывод.

После этого естественно свяжи тему с деньгами самого зрителя.

В ФИНАЛЕ обязательно должна быть логическая цепочка:
проблема или новость → влияние на обычного человека → деньги зрителя → фраза "Что это значит для твоего кошелька?" → объяснение, что подобные разборы доступны в нашем Telegram-канале.

Фраза "Что это значит для твоего кошелька?" должна звучать естественно и быть отдельной финальной смысловой точкой.

После неё обязательно скажи, что в нашем Telegram-канале можно узнать: финансовые разборы, финансовые новости, новости бизнеса и экономики, рекомендации, способы сохранить деньги, идеи и способы увеличить доход.

НЕ делай резкую рекламу.
НЕ говори: "Подписывайся прямо сейчас!", "Жми на ссылку!", "Переходи по ссылке!", "Не забудь подписаться!"

НЕ используй Markdown, эмодзи, URL, хэштеги, тире, списки внутри SCRIPT.
НЕ используй служебные слова: HOOK, CTA, INTRO, OUTRO, SCENE, SFX, MUSIC, ПАУЗА, ОЗВУЧКА.

Не давай персональных инвестиционных рекомендаций.
Не обещай гарантированный заработок.

Длина SCRIPT: примерно 120-170 слов.

После сценария создай от 10 до 14 разнообразных поисковых запросов Pexels на английском языке.

ФОРМАТ ОТВЕТА:
TITLE: короткий заголовок
SCRIPT:
полный сценарий
PEXELS:
bank interior
person checking bank account
...
"""
    
    user_prompt = f"""
Создай короткий финансовый ролик.

СТИЛЬ: {style}
ТЕМА: {topic}

Главная задача: сделать сценарий интересным.

В самом конце обязательно подведи к вопросу "Что это значит для твоего кошелька?".

После вопроса скажи, что подобные финансовые разборы, новости бизнеса и экономики, рекомендации по сохранению денег и идеи по увеличению дохода есть в нашем Telegram-канале.

Создай минимум 10 разных визуальных сцен для Pexels.

Ответ строго:
TITLE:
...
SCRIPT:
...
PEXELS:
...
"""
    
    for model in GROQ_MODELS:
        print(f"🤖 Trying Groq model: {model}")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.72,
                max_completion_tokens=2200,
                reasoning_effort="low"
            )
            
            content = response.choices[0].message.content or ""
            if not content.strip():
                print("⚠️ Groq returned empty response.")
                continue
            
            print(f"📡 Groq finish reason: {response.choices[0].finish_reason}")
            
            parsed = parse_script_response(content)
            if not parsed:
                print("⚠️ Could not parse Groq response.")
                print(content[:3000])
                continue
            
            script = parsed["script"]
            queries = parsed["pexels_queries"]
            
            if len(script) < 600:
                print(f"⚠️ Script too short: {len(script)} chars")
                continue
            
            if len(script) > 1500:
                print(f"⚠️ Script too long: {len(script)} chars")
                continue
            
            if not validate_cta(script):
                print("⚠️ CTA validation failed.")
                continue
            
            if len(queries) < MIN_CLIPS:
                print(f"⚠️ Only {len(queries)} visual queries.")
                continue
            
            print(f"✅ Groq model working: {model}")
            print(f"📝 Title: {parsed['title']}")
            print("📜 SCRIPT:", script, sep="\n")
            print(f"🎞️ Visual queries: {len(queries)}")
            
            return {
                "title": parsed["title"],
                "script": script,
                "pexels_queries": queries[:MAX_CLIPS]
            }
            
        except Exception as e:
            print(f"❌ Groq error with {model}: {e}")
    
    print("❌ All Groq models failed.")
    return None


# ============================================================
# ELEVENLABS
# ============================================================

def generate_voice(script):
    print("🎙️ Generating Russian voice...")
    
    tts_script = clean_tts_text(script)
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": tts_script,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128",
        "voice_settings": {
            "stability": 0.52,
            "similarity_boost": 0.78,
            "style": 0.32,
            "use_speaker_boost": True
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)
        if response.status_code != 200:
            print(f"❌ ElevenLabs error {response.status_code}")
            print(response.text[:1500])
            return False
        
        AUDIO_FILE.write_bytes(response.content)
        duration = get_duration(AUDIO_FILE)
        if duration <= 0:
            print("❌ Invalid audio.")
            return False
        
        print(f"✅ Voice generated: {duration:.2f}s")
        return True
        
    except Exception as e:
        print(f"❌ ElevenLabs error: {e}")
        return False


# ============================================================
# PEXELS
# ============================================================

def search_pexels_video(query):
    print(f"🔎 Pexels: {query}")
    
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 15,
        "locale": "en-US"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            print(f"⚠️ Pexels error {response.status_code}")
            return None
        
        videos = response.json().get("videos", [])
        if not videos:
            return None
        
        random.shuffle(videos)
        candidates = []
        for video in videos:
            video_files = video.get("video_files", [])
            portrait = [f for f in video_files if f.get("width", 0) < f.get("height", 0)]
            files = portrait or video_files
            for file in files:
                link = file.get("link")
                if link:
                    candidates.append(link)
        
        if not candidates:
            return None
        
        return random.choice(candidates)
        
    except Exception as e:
        print(f"⚠️ Pexels exception: {e}")
        return None


def download_video(url, destination):
    print(f"⬇️ Downloading {destination.name}")
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        with open(destination, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
        return destination.exists()
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False


def get_video_clips(queries):
    fallback = [
        "money finance", "business office", "banking", "stock market",
        "financial district", "smartphone banking", "person checking phone",
        "business meeting", "shopping", "cash money", "office worker",
        "city night", "technology", "entrepreneur", "investment",
        "credit card", "grocery shopping", "salary payment"
    ]
    
    all_queries = queries + fallback
    clips = []
    used_links = set()
    query_index = 0
    
    while len(clips) < MAX_CLIPS and query_index < len(all_queries):
        query = all_queries[query_index]
        query_index += 1
        
        link = search_pexels_video(query)
        if not link or link in used_links:
            continue
        
        used_links.add(link)
        destination = WORK_DIR / f"clip_{len(clips)+1}.mp4"
        
        if download_video(link, destination):
            clips.append(destination)
        
        time.sleep(0.3)
    
    print(f"✅ Downloaded {len(clips)} visual clips.")
    return clips


# ============================================================
# MUSIC
# ============================================================

def get_music():
    tracks = list(MUSIC_DIR.glob("*.mp3"))
    if not tracks:
        print("⚠️ No music found.")
        return None
    track = random.choice(tracks)
    print(f"🎵 Music: {track.name}")
    return track


# ============================================================
# FFMPEG HELPERS
# ============================================================

def get_duration(file):
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file)
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


# ============================================================
# CREATE VIDEO - УПРОЩЕННАЯ ВЕРСИЯ
# ============================================================

def create_photo_clip(photo_path, output_path, duration):
    """Создает видео из фото"""
    print(f"🖼️ Создание рекламного кадра...")
    
    command = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(photo_path),
        "-c:v", "libx264",
        "-t", str(duration),
        "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,format=yuv420p",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(output_path)
    ]
    
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print(f"✅ Рекламный кадр создан")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка создания рекламного кадра: {e}")
        return False


def create_video(clips, music):
    print("🎬 Creating final video...")
    
    voice_duration = get_duration(AUDIO_FILE)
    if voice_duration <= 0:
        print("❌ Invalid voice duration.")
        return False
    
    # Целевая длительность с рекламой
    target_duration = voice_duration + VOICE_TAIL + PHOTO_DURATION
    print(f"🎙️ Voice: {voice_duration:.3f}s")
    print(f"🎬 Target video: {target_duration:.3f}s")
    
    # --------------------------------------------------------
    # ШАГ 1: Создаем простой визуальный трек
    # --------------------------------------------------------
    
    print("🎞️ Creating visual track...")
    
    if not clips:
        print("❌ No clips available")
        return False
    
    # Берем первые 10 клипов
    selected_clips = clips[:MAX_CLIPS]
    
    # Создаем concat список
    concat_file = WORK_DIR / "concat_list.txt"
    with open(concat_file, "w") as f:
        for clip in selected_clips:
            f.write(f"file '{clip.absolute()}'\n")
    
    # Если есть фото, добавляем его в конец
    has_photo = PHOTO_FILE.exists()
    if has_photo:
        photo_video = WORK_DIR / "photo_clip.mp4"
        if create_photo_clip(PHOTO_FILE, photo_video, PHOTO_DURATION):
            with open(concat_file, "a") as f:
                f.write(f"file '{photo_video.absolute()}'\n")
    
    # Создаем визуальный трек
    visual_track = WORK_DIR / "visual_track.mp4"
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(visual_track)
    ]
    
    try:
        subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("✅ Visual track created")
    except Exception as e:
        print(f"❌ Error creating visual track: {e}")
        return False
    
    # Проверяем длительность
    visual_duration = get_duration(visual_track)
    print(f"📊 Visual duration: {visual_duration:.3f}s")
    
    # Если визуальный трек короче целевой длительности, зацикливаем
    if visual_duration < target_duration:
        print("🔄 Looping visual track...")
        looped_track = WORK_DIR / "looped_track.mp4"
        cmd_loop = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(visual_track),
            "-c", "copy",
            "-t", str(target_duration),
            str(looped_track)
        ]
        try:
            subprocess.run(cmd_loop, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            visual_track = looped_track
            print("✅ Loop created")
        except Exception as e:
            print(f"⚠️ Loop error: {e}")
    
    # --------------------------------------------------------
    # ШАГ 2: Добавляем голос
    # --------------------------------------------------------
    
    print("🎤 Adding voice...")
    with_voice = WORK_DIR / "with_voice.mp4"
    cmd_voice = [
        "ffmpeg", "-y",
        "-i", str(visual_track),
        "-i", str(AUDIO_FILE),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-shortest",
        str(with_voice)
    ]
    
    try:
        subprocess.run(cmd_voice, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("✅ Voice added")
    except Exception as e:
        print(f"❌ Error adding voice: {e}")
        return False
    
    # --------------------------------------------------------
    # ШАГ 3: Добавляем музыку (если есть)
    # --------------------------------------------------------
    
    final_file = FINAL_VIDEO
    
    if music and music.exists():
        print("🎵 Adding music...")
        
        # Конвертируем музыку
        music_aac = WORK_DIR / "music.aac"
        cmd_convert = [
            "ffmpeg", "-y",
            "-i", str(music),
            "-vn",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-t", str(target_duration),
            str(music_aac)
        ]
        
        try:
            subprocess.run(cmd_convert, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except:
            music_aac = None
        
        if music_aac and music_aac.exists():
            # Смешиваем аудио
            cmd_mix = [
                "ffmpeg", "-y",
                "-i", str(with_voice),
                "-i", str(music_aac),
                "-filter_complex",
                f"[1:a]volume={MUSIC_VOLUME}[music];[0:a][music]amix=inputs=2:duration=first[aout]",
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-movflags", "+faststart",
                str(final_file)
            ]
            
            try:
                subprocess.run(cmd_mix, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                print("✅ Music added")
            except Exception as e:
                print(f"⚠️ Music mix error: {e}")
                shutil.copy2(with_voice, final_file)
        else:
            shutil.copy2(with_voice, final_file)
    else:
        shutil.copy2(with_voice, final_file)
    
    # --------------------------------------------------------
    # ПРОВЕРКА РЕЗУЛЬТАТА
    # --------------------------------------------------------
    
    if not FINAL_VIDEO.exists():
        print("❌ Final video was not created.")
        return False
    
    final_duration = get_duration(FINAL_VIDEO)
    print()
    print("======================================")
    print("🎉 VIDEO CREATED")
    print("======================================")
    print(f"🎙️ Voice: {voice_duration:.3f}s")
    print(f"🎬 Video: {final_duration:.3f}s")
    print(f"📦 Size: {FINAL_VIDEO.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"🖼️ Реклама Telegram: {'добавлена' if has_photo else 'не добавлена (фото отсутствует)'}")
    
    if final_duration < voice_duration:
        print("⚠️ WARNING: Video is shorter than voice!")
        return False
    
    return True


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("======================================")
    print("🎬 FINANCIAL VIDEO BOT")
    print("======================================")
    print()
    
    if not check_environment():
        return 1
    
    clean_work_directory()
    
    # SCRIPT
    content = generate_script()
    if not content:
        print("❌ Content generation failed.")
        return 1
    
    # VOICE
    if not generate_voice(content["script"]):
        print("❌ Voice generation failed.")
        return 1
    
    # VISUALS
    clips = get_video_clips(content["pexels_queries"])
    if len(clips) < MIN_CLIPS:
        print(f"⚠️ Not enough clips. Required: {MIN_CLIPS}, Found: {len(clips)}")
        if not clips:
            return 1
    
    # MUSIC
    music = get_music()
    
    # VIDEO
    if not create_video(clips, music):
        print("❌ Video rendering failed.")
        return 1
    
    print()
    print("======================================")
    print("🎉 VIDEO BOT FINISHED")
    print("======================================")
    print()
    print("📹 Video ready:")
    print(FINAL_VIDEO)
    print()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())