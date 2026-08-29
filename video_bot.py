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
from gtts import gTTS

# ============================================================
# ENV
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MUSIC_DIR = BASE_DIR / "assets" / "music"
WORK_DIR = BASE_DIR / "video_work"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"

AUDIO_FILE = WORK_DIR / "voiceover.mp3"
FINAL_VIDEO = OUTPUT_DIR / "video.mp4"
PHOTO_FILE = ASSETS_DIR / "photo.png"

TOPICS_HISTORY_FILE = BASE_DIR / "topics_history.json"


# ============================================================
# VIDEO SETTINGS
# ============================================================

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
MUSIC_VOLUME = 0.15

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
# ТЕМЫ
# ============================================================

MONEY_TOPICS = [
    "Почему богатые инвестируют, а бедные копят",
    "Как инфляция в 2026 году съедает сбережения",
    "Налоговые лазейки, о которых молчат банки",
    "Криптовалюты: новый пузырь или будущее денег?",
    "Как заработать на росте цен на недвижимость",
    "Почему вклады в банках больше не спасают от инфляции",
    "Как использовать ИИ для пассивного дохода",
    "Инвестиции в стартапы: как не потерять деньги",
    "Почему доллар больше не защита от кризиса",
    "Как начать инвестировать с 1000 рублей в 2026 году",
    "Золото или биткоин: что надежнее?",
    "Как эмоции мешают зарабатывать на бирже",
    "Что делать с деньгами во время рецессии",
    "Диверсификация портфеля для начинающих",
    "Как работают ETF и стоит ли в них вкладывать",
    "Почему большинство трейдеров теряют деньги",
    "Как пассивный доход может сделать вас богатым",
    "Инвестиции в себя: лучший вклад в 2026 году",
    "Как не попасть на финансовые пирамиды",
    "Почему криптозима — лучшее время для покупки",
]


# ============================================================
# RSS ЛЕНТЫ
# ============================================================

FREE_NEWS_RSS = [
    "https://news.google.com/rss/search?q=инвестиции+экономика+финансы&hl=ru&gl=RU&ceid=RU:ru",
    "https://news.google.com/rss/search?q=банки+ставка+инфляция&hl=ru&gl=RU&ceid=RU:ru",
    "https://news.google.com/rss/search?q=криптовалюта+биткоин+рынок&hl=ru&gl=RU&ceid=RU:ru",
    "https://news.google.com/rss/search?q=недвижимость+цены+инвестиции&hl=ru&gl=RU&ceid=RU:ru",
]


# ============================================================
# UTILS
# ============================================================

def clean_text(text):
    if not text:
        return ""
    text = str(text)
    for ch in ["**", "__", "```", "`"]:
        text = text.replace(ch, "")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_tts_text(text):
    text = clean_text(text)
    text = re.sub(r"(?m)^[ \t]*[-–—•]\s*", "", text)
    for old, new in [("—", ", "), ("–", ", "), ("−", "-")]:
        text = text.replace(old, new)
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
        "PEXELS_API_KEY": PEXELS_API_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print("❌ Missing secrets:", missing)
        return False

    if not shutil.which("ffmpeg"):
        print("❌ FFmpeg is not installed.")
        return False

    if not shutil.which("ffprobe"):
        print("❌ FFprobe is not installed.")
        return False

    if not shutil.which("hyperframes"):
        print("❌ HyperFrames is not installed.")
        print("   Run: npm install -g hyperframes")
        return False

    if not PHOTO_FILE.exists():
        print(f"⚠️ Рекламное фото не найдено: {PHOTO_FILE}")

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
            except Exception:
                pass
    WORK_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# NEWS AND TOPICS
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
# SCRIPT GENERATION
# ============================================================

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
        "pexels_queries": queries[:MAX_CLIPS]
    }


def generate_script():
    print("🧠 Asking Groq to create a script...")

    style = random.choice(["PROVOCATIVE", "INTELLECTUAL", "DARK", "PHILOSOPHICAL", "ANALYTICAL"])
    topic = choose_topic()
    print(f"🎩 Selected style: {style}")

    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = """
Ты профессиональный сценарист коротких финансовых видео для TikTok и YouTube Shorts.
Пиши на русском языке.

Ты создаешь ВИРАЛЬНЫЙ контент. Твоя задача — сделать видео, которое наберет миллионы просмотров.

Правила виральности:
1. ПЕРВЫЕ 3 СЕКУНДЫ — ХУК! Это самое важное. Начни с шокирующего факта, провокационного вопроса или неожиданного утверждения.
2. Используй ЭМОЦИИ: страх упустить выгоду (FOMO), удивление, надежду на разбогатеть.
3. Добавь КОНКРЕТНЫЕ ЦИФРЫ: проценты, суммы, даты.
4. Сделай ЛИЧНЫМ: обращайся к зрителю на "ты", говори о его деньгах.
5. Добавь ИНТРИГУ: "Большинство не знает...", "Банки скрывают...", "Вот почему..."
6. Используй ПРОСТОЙ ЯЗЫК: без сложных терминов, объясняй как для друга.

Темы: деньги, финансовая грамотность, заработок, инвестиции, криптовалюты, инфляция, экономика.

Структура сценария:
1. ХУК (первые 3-5 секунд): шокирующий факт или вопрос
2. ПРОБЛЕМА: что происходит в экономике/финансах прямо сейчас
3. ВЛИЯНИЕ: как это влияет на деньги зрителя
4. РЕШЕНИЕ: что можно сделать (не давай конкретных инвестиционных советов!)
5. ПРИЗЫВ: "Что это значит для твоего кошелька?" → переход на Telegram-канал

В ФИНАЛЕ обязательно скажи, что в нашем Telegram-канале можно узнать: свежие финансовые разборы, новости экономики, рекомендации по сохранению денег и идеи для увеличения дохода.

НЕ используй Markdown, эмодзи, URL, хэштеги, тире, списки внутри SCRIPT.
НЕ используй служебные слова: HOOK, CTA, INTRO, OUTRO.

Длина SCRIPT: примерно 100-150 слов.

После сценария создай от 10 до 14 разнообразных поисковых запросов Pexels на английском языке для визуального ряда.

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
Создай ВИРАЛЬНЫЙ короткий финансовый ролик.

СТИЛЬ: {style}
ТЕМА: {topic}

Главная задача: сделать видео, которое захочется переслать другу.
Обязательно используй ХУК в первых 3 секундах.

В конце: логически подведи к вопросу "Что это значит для твоего кошелька?" и скажи, что подобные разборы есть в нашем Telegram-канале.

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
                temperature=0.75,
                max_completion_tokens=2200,
                reasoning_effort="low"
            )

            content = response.choices[0].message.content or ""
            if not content.strip():
                print("⚠️ Groq returned empty response.")
                continue

            parsed = parse_script_response(content)
            if not parsed:
                print("⚠️ Could not parse Groq response.")
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
            print(f"🎞️ Visual queries: {len(queries)}")

            return parsed

        except Exception as e:
            print(f"❌ Groq error with {model}: {e}")

    print("❌ All Groq models failed.")
    return None


# ============================================================
# gTTS — БЕСПЛАТНАЯ ОЗВУЧКА
# ============================================================

def generate_voice(script):
    print("🎙️ Generating voice with gTTS...")

    tts_script = clean_tts_text(script)

    try:
        tts = gTTS(text=tts_script, lang='ru', slow=False)

        temp_mp3 = WORK_DIR / "temp_voice.mp3"
        tts.save(str(temp_mp3))

        if not temp_mp3.exists():
            print("❌ gTTS: File not created")
            return False

        shutil.copy(temp_mp3, AUDIO_FILE)
        temp_mp3.unlink()

        duration = get_duration(AUDIO_FILE)
        if duration <= 0:
            print("❌ Invalid audio duration")
            return False

        print(f"✅ Voice generated: {duration:.2f}s")
        return True

    except Exception as e:
        print(f"❌ gTTS error: {e}")
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
        "per_page": 10,
        "locale": "en-US"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            return None

        videos = response.json().get("videos", [])
        if not videos:
            return None

        random.shuffle(videos)
        for video in videos:
            video_files = video.get("video_files", [])
            portrait = [f for f in video_files if f.get("width", 0) < f.get("height", 0)]
            files = portrait or video_files
            for file in files:
                link = file.get("link")
                if link:
                    return link
        return None
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
# HYPERFRAMES
# ============================================================

def create_hyperframes_video(content, clips, voice_duration):
    """Создаёт видео через HyperFrames"""
    print("📄 Generating HyperFrames HTML...")

    title = content["title"]
    script = content["script"]

    sentences = re.split(r'[.!?]+\s*', script)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    total_duration = voice_duration + PHOTO_DURATION + 0.5
    time_per_sentence = voice_duration / len(sentences) if sentences else 3.0

    subtitles_html = []
    current_time = 0.3

    for i, sentence in enumerate(sentences[:15]):
        duration = min(time_per_sentence * 1.2, 4.5)
        subtitles_html.append(f'''
        <div class="subtitle" id="subtitle-{i}" data-start="{current_time:.2f}" data-duration="{duration:.2f}">
            {sentence}
        </div>
        ''')
        current_time += duration

    html_content = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    
    #stage {{
      width: 1080px;
      height: 1920px;
      position: relative;
      background: #0D0A1A;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      overflow: hidden;
    }}

    .clip-video {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      z-index: 1;
    }}

    .overlay {{
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 45%;
      background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, transparent 100%);
      z-index: 2;
      pointer-events: none;
    }}

    .title-text {{
      position: absolute;
      top: 100px;
      left: 40px;
      right: 40px;
      color: white;
      font-size: 52px;
      font-weight: 800;
      text-shadow: 0 4px 30px rgba(0,0,0,0.9);
      z-index: 3;
      text-align: center;
      line-height: 1.2;
      opacity: 0;
      transform: translateY(40px);
    }}

    .subtitle {{
      position: absolute;
      bottom: 200px;
      left: 40px;
      right: 40px;
      color: rgba(255,255,255,0.95);
      font-size: 48px;
      font-weight: 700;
      text-align: center;
      z-index: 4;
      text-shadow: 0 2px 30px rgba(0,0,0,0.95), 0 0 60px rgba(0,0,0,0.5);
      opacity: 0;
      transform: translateY(30px);
      line-height: 1.3;
      letter-spacing: 0.5px;
    }}

    .photo-ad {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      z-index: 5;
      opacity: 0;
      background: #0D0A1A;
    }}

    .ad-text {{
      position: absolute;
      bottom: 200px;
      left: 0;
      right: 0;
      color: white;
      font-size: 48px;
      font-weight: 700;
      text-align: center;
      z-index: 6;
      text-shadow: 0 4px 40px rgba(0,0,0,0.95);
      opacity: 0;
    }}

    .ad-text small {{
      display: block;
      font-size: 28px;
      font-weight: 400;
      margin-top: 15px;
      opacity: 0.8;
    }}
  </style>
</head>
<body>
  <div id="stage" data-composition-id="finance-video" data-width="1080" data-height="1920" data-fps="30" data-duration="{total_duration:.2f}">
'''

    for i, clip_path in enumerate(clips[:MAX_CLIPS]):
        duration_per_clip = min(voice_duration / len(clips[:MAX_CLIPS]) * 1.5, 5.0)
        start_time = i * (voice_duration / len(clips[:MAX_CLIPS]))
        html_content += f'''
    <video class="clip-video" data-start="{start_time:.2f}" data-duration="{duration_per_clip:.2f}" data-track-index="{i}" src="{clip_path.name}" muted playsinline></video>
'''

    html_content += '''
    <div class="overlay"></div>
'''

    html_content += f'''
    <div class="title-text" id="main-title" data-start="0.3" data-duration="3.5">
        {title}
    </div>
'''

    html_content += ''.join(subtitles_html)

    html_content += f'''
    <img class="photo-ad" id="ad-photo" data-start="{voice_duration + 0.5:.2f}" data-duration="{PHOTO_DURATION:.2f}" src="photo.png" />
    <div class="ad-text" id="ad-text" data-start="{voice_duration + 0.8:.2f}" data-duration="{PHOTO_DURATION - 0.5:.2f}">
        Telegram: @imminews_ai_agent
        <small>Финансовые разборы, новости, идеи для дохода</small>
    </div>
'''

    html_content += f'''
    <audio id="voiceover" data-start="0" data-duration="{voice_duration:.2f}" src="voiceover.mp3"></audio>
    <audio id="bg-music" data-start="0" data-duration="{total_duration:.2f}" data-volume="0.15" src="background.mp3" loop></audio>
  </div>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script>
    window.addEventListener('load', () => {{
      const tl = gsap.timeline();
      
      tl.fromTo("#main-title",
        {{ opacity: 0, y: 40, scale: 0.95 }},
        {{ opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power2.out" }},
        0.3
      );
      tl.to("#main-title",
        {{ opacity: 0, y: -20, duration: 0.5, ease: "power2.in" }},
        3.8
      );

      const subtitles = document.querySelectorAll('.subtitle');
      subtitles.forEach((el, i) => {{
        const start = parseFloat(el.dataset.start);
        const duration = parseFloat(el.dataset.duration);
        if (!isNaN(start) && !isNaN(duration)) {{
          tl.fromTo(el,
            {{ opacity: 0, y: 30 }},
            {{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }},
            start
          );
          tl.to(el,
            {{ opacity: 0, y: -20, duration: 0.3, ease: "power2.in" }},
            start + duration - 0.2
          );
        }}
      }});

      const adPhoto = document.getElementById('ad-photo');
      const adText = document.getElementById('ad-text');
      
      tl.fromTo(adPhoto,
        {{ opacity: 0 }},
        {{ opacity: 1, duration: 0.6, ease: "power2.out" }},
        {voice_duration + 0.5:.2f}
      );
      
      tl.fromTo(adText,
        {{ opacity: 0, y: 30 }},
        {{ opacity: 1, y: 0, duration: 0.5, ease: "power2.out" }},
        {voice_duration + 0.8:.2f}
      );
    }});
  </script>
</body>
</html>
'''

    html_path = WORK_DIR / "video_composition.html"
    html_path.write_text(html_content, encoding="utf-8")

    # ПРОВЕРКА: убеждаемся, что HTML-файл создан
    if not html_path.exists():
        print(f"❌ HTML file not created: {html_path}")
        return False
    print(f"✅ HTML file created: {html_path}")

    # Копируем фото, если оно есть
    if PHOTO_FILE.exists():
        shutil.copy(PHOTO_FILE, WORK_DIR / "photo.png")

    # Проверяем, что голосовой файл существует
    if not AUDIO_FILE.exists():
        print(f"❌ Voice file not found: {AUDIO_FILE}")
        return False

    # Копируем музыку, если она есть
    music_file = get_music()
    if music_file and music_file.exists():
        shutil.copy(music_file, WORK_DIR / "background.mp3")

    print("🎬 Rendering with HyperFrames...")
    
    # Переходим в WORK_DIR
    os.chdir(WORK_DIR)
    
    # ИСПРАВЛЕНИЕ: используем полный путь к файлу
    html_abs_path = html_path.absolute()
    print(f"📄 Rendering: {html_abs_path}")
    
    try:
        result = subprocess.run(
            ["hyperframes", "render", str(html_abs_path), "--output", "output.mp4"],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            print("✅ HyperFrames render completed")
        else:
            print("❌ HyperFrames render error:")
            print(result.stderr if result.stderr else result.stdout)
            os.chdir(BASE_DIR)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ HyperFrames render timeout")
        os.chdir(BASE_DIR)
        return False
    except Exception as e:
        print(f"❌ HyperFrames exception: {e}")
        os.chdir(BASE_DIR)
        return False

    os.chdir(BASE_DIR)

    output_video = WORK_DIR / "output.mp4"
    if output_video.exists():
        shutil.copy(output_video, FINAL_VIDEO)
        print(f"✅ Video created: {FINAL_VIDEO}")
        return True

    print("❌ Video not created")
    return False


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 38)
    print("🎬 FINANCIAL VIDEO BOT")
    print("=" * 38)
    print()

    if not check_environment():
        return 1

    clean_work_directory()

    content = generate_script()
    if not content:
        print("❌ Content generation failed.")
        return 1

    if not generate_voice(content["script"]):
        print("❌ Voice generation failed.")
        return 1

    voice_duration = get_duration(AUDIO_FILE)

    clips = get_video_clips(content["pexels_queries"])
    if len(clips) < MIN_CLIPS:
        print(f"⚠️ Not enough clips. Required: {MIN_CLIPS}, Found: {len(clips)}")
        if not clips:
            return 1

    if not create_hyperframes_video(content, clips, voice_duration):
        print("❌ Video creation failed.")
        return 1

    print()
    print("=" * 38)
    print("🎉 VIDEO BOT FINISHED")
    print("=" * 38)
    print()
    print("📹 Video ready:")
    print(FINAL_VIDEO)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())