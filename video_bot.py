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
# CONFIG
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# Можно указать конкретный Voice ID ElevenLabs через GitHub Secret.
# Если секрет не задан, попробуем получить первый доступный голос.
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()

# Модель Groq
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

# Папки
BASE_DIR = Path(__file__).resolve().parent

MUSIC_DIR = BASE_DIR / "assets" / "music"
WORK_DIR = BASE_DIR / "video_work"
OUTPUT_DIR = BASE_DIR / "output"

AUDIO_FILE = WORK_DIR / "voice.mp3"
MUSIC_FILE = WORK_DIR / "music.mp3"
FINAL_VIDEO = OUTPUT_DIR / "video.mp4"

# Вертикальное видео
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Музыка
MUSIC_VOLUME = 0.07

# Продолжительность
MIN_VIDEO_SECONDS = 15
MAX_VIDEO_SECONDS = 28


# ============================================================
# VALIDATION
# ============================================================

def check_environment():
    print("🔎 Checking environment...")

    missing = []

    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")

    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")

    if not PEXELS_API_KEY:
        missing.append("PEXELS_API_KEY")

    if missing:
        print("❌ Missing API keys:")
        for key in missing:
            print(f"   - {key}")
        return False

    if not shutil.which("ffmpeg"):
        print("❌ FFmpeg is not installed or not available in PATH.")
        return False

    if not shutil.which("ffprobe"):
        print("❌ FFprobe is not installed or not available in PATH.")
        return False

    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("✅ Environment OK")
    return True


# ============================================================
# CLEANUP
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
                print(f"⚠️ Could not delete {item}: {e}")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# GROQ
# ============================================================

def generate_script():
    print("🧠 Asking Groq to create a script...")

    client = Groq(api_key=GROQ_API_KEY)

    styles = [
        "PROVOCATIVE",
        "ANALYTICAL",
        "INTELLECTUAL",
    ]

    style = random.choice(styles)

    print(f"🎩 Selected style: {style}")

    system_prompt = """
Ты — сценарист коротких вирусных финансовых видео.

Создавай оригинальные сценарии на русском языке.

Образ рассказчика:
- интеллектуальный;
- холодный;
- наблюдательный;
- уверенный;
- немного ироничный;
- иногда провокационный;
- философский, но без лишней воды;
- говорит со зрителем напрямую;
- создаёт ощущение, что показывает скрытую сторону обычной вещи.

ВАЖНО:
Не копируй конкретных персонажей, блогеров, актёров или их голоса.
Не упоминай профессора Мориарти, Мистера Фримена или других персонажей.
Создавай самостоятельный образ.

Структура:
1. Очень сильный hook на первые 1–2 секунды.
2. Интрига.
3. Основная мысль.
4. Неожиданный вывод.
5. Мягкий переход к Telegram.

Сценарий должен звучать естественно при озвучке.

Не используй:
- markdown;
- **;
- ссылки;
- эмодзи внутри текста сценария;
- длинные списки;
- фразы вроде "сегодня мы поговорим";
- "подпишись на канал" в каждом ролике;
- обещания гарантированного заработка;
- финансовые гарантии.

Если речь идёт об инвестициях, обязательно избегай утверждений о гарантированной прибыли.

Длина:
примерно 70–110 слов.

Верни строго JSON:
{
  "title": "...",
  "style": "...",
  "script": "...",
  "pexels_queries": ["...", "...", "..."]
}
"""

    user_prompt = f"""
Создай один короткий финансовый ролик.

Выбранный стиль:
{style}

Темы должны быть связаны с:
- деньгами;
- личными финансами;
- психологией денег;
- финансовыми привычками;
- инвестиционной грамотностью;
- банковскими продуктами;
- заработком;
- расходами;
- инфляцией;
- финансовыми ошибками.

Не делай слишком банальную тему.

Нужна идея, которая заставит человека остановить прокрутку.

Верни только JSON.
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
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
            temperature=0.85,
            max_tokens=900,
            response_format={"type": "json_object"},
        )

        text = response.choices[0].message.content or ""

        if not text.strip():
            print("❌ Groq returned empty response.")
            return None

        data = json.loads(text)

        script = clean_text(data.get("script", ""))
        title = clean_text(data.get("title", ""))
        style = clean_text(data.get("style", style))

        queries = data.get("pexels_queries", [])

        if not isinstance(queries, list):
            queries = []

        queries = [
            clean_search_query(str(q))
            for q in queries
            if str(q).strip()
        ]

        if not script:
            print("❌ Groq generated an empty script.")
            return None

        print(f"📝 Title: {title}")
        print(f"🎩 Style: {style}")
        print(f"🎥 Pexels queries: {queries}")
        print()
        print("📜 SCRIPT:")
        print(script)
        print()

        return {
            "title": title,
            "style": style,
            "script": script,
            "pexels_queries": queries[:5],
        }

    except Exception as e:
        print(f"❌ Groq error: {e}")
        return None


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = str(text)

    # Убираем markdown
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("```", "")
    text = text.replace("`", "")

    # Убираем возможные ссылки
    text = re.sub(r"https?://\S+", "", text)

    # Убираем лишние пробелы
    text = re.sub(r"[ \t]+", " ", text)

    # Убираем слишком много пустых строк
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_search_query(text):
    text = clean_text(text)

    # Pexels лучше работает с короткими английскими запросами.
    text = text.replace(",", " ")

    words = text.split()

    if len(words) > 6:
        words = words[:6]

    return " ".join(words)


# ============================================================
# ELEVENLABS
# ============================================================

def get_elevenlabs_voice():
    if ELEVENLABS_VOICE_ID:
        return ELEVENLABS_VOICE_ID

    print("🎙️ No ELEVENLABS_VOICE_ID provided.")
    print("🎙️ Trying to get first available voice...")

    url = "https://api.elevenlabs.io/v1/voices"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        voices = data.get("voices", [])

        if not voices:
            print("❌ No ElevenLabs voices available.")
            return None

        voice_id = voices[0].get("voice_id")

        if voice_id:
            print(
                f"🎙️ Using ElevenLabs voice: "
                f"{voices[0].get('name', 'Unknown')}"
            )

        return voice_id

    except Exception as e:
        print(f"❌ ElevenLabs voice error: {e}")
        return None


def generate_voice(script):
    print("🎙️ Generating Russian voice with ElevenLabs...")

    voice_id = get_elevenlabs_voice()

    if not voice_id:
        return False

    url = (
        f"https://api.elevenlabs.io/v1/"
        f"text-to-speech/{voice_id}"
    )

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.78,
            "style": 0.30,
            "use_speaker_boost": True
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            print(
                f"❌ ElevenLabs error "
                f"{response.status_code}: "
                f"{response.text[:1000]}"
            )
            return False

        if not response.content:
            print("❌ ElevenLabs returned empty audio.")
            return False

        with open(AUDIO_FILE, "wb") as f:
            f.write(response.content)

        print(
            f"✅ Voice generated: "
            f"{AUDIO_FILE}"
        )

        return True

    except Exception as e:
        print(f"❌ ElevenLabs request error: {e}")
        return False


# ============================================================
# PEXELS
# ============================================================

def search_pexels_video(query):
    print(f"🔎 Pexels search: {query}")

    url = "https://api.pexels.com/videos/search"

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
            print(
                f"⚠️ Pexels error "
                f"{response.status_code}: "
                f"{response.text[:500]}"
            )
            return None

        data = response.json()

        videos = data.get("videos", [])

        if not videos:
            print("⚠️ No videos found.")
            return None

        # Выбираем случайное видео из результатов
        video = random.choice(videos)

        files = video.get("video_files", [])

        if not files:
            return None

        # Предпочитаем вертикальное видео
        portrait_files = [
            f for f in files
            if f.get("width", 0) < f.get("height", 0)
        ]

        candidates = portrait_files or files

        # Ищем файл разумного качества
        candidates = sorted(
            candidates,
            key=lambda x: (
                abs(
                    (x.get("width", 0) or 0)
                    - 1080
                ),
                -(x.get("height", 0) or 0)
            )
        )

        chosen = candidates[0]

        link = chosen.get("link")

        if not link:
            return None

        print(
            f"🎥 Selected Pexels video "
            f"{chosen.get('width')}x"
            f"{chosen.get('height')}"
        )

        return link

    except Exception as e:
        print(f"⚠️ Pexels request error: {e}")
        return None


def download_file(url, destination):
    print(f"⬇️ Downloading: {url[:100]}...")

    try:
        response = requests.get(
            url,
            stream=True,
            timeout=120
        )

        response.raise_for_status()

        with open(destination, "wb") as f:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    f.write(chunk)

        if destination.stat().st_size < 10_000:
            print("⚠️ Downloaded file is suspiciously small.")
            return False

        return True

    except Exception as e:
        print(f"❌ Download error: {e}")
        return False


def get_video_clips(queries):
    """
    Скачиваем до 3 коротких видео.
    Если один запрос не работает, пробуем следующий.
    """

    clips = []

    fallback_queries = [
        "money finance",
        "business finance",
        "bank money",
        "city business",
        "person using smartphone",
    ]

    all_queries = queries + fallback_queries

    used_links = set()

    for query in all_queries:

        if len(clips) >= 3:
            break

        link = search_pexels_video(query)

        if not link:
            continue

        if link in used_links:
            continue

        used_links.add(link)

        destination = (
            WORK_DIR /
            f"clip_{len(clips) + 1}.mp4"
        )

        if download_file(link, destination):
            clips.append(destination)

    if not clips:
        print("❌ Could not download any Pexels video.")
        return []

    print(f"✅ Downloaded {len(clips)} video clip(s).")

    return clips


# ============================================================
# MUSIC
# ============================================================

def get_music():
    print("🎵 Looking for music...")

    if not MUSIC_DIR.exists():
        print(f"⚠️ Music directory does not exist: {MUSIC_DIR}")
        return None

    tracks = list(MUSIC_DIR.glob("*.mp3"))

    if not tracks:
        print("⚠️ No MP3 files found.")
        return None

    selected = random.choice(tracks)

    print(f"🎵 Selected: {selected.name}")

    return selected


# ============================================================
# VIDEO INFORMATION
# ============================================================

def get_duration(file_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        return float(result.stdout.strip())

    except Exception as e:
        print(f"⚠️ Could not read duration: {e}")
        return 0


# ============================================================
# VIDEO PREPARATION
# ============================================================

def prepare_clip(input_file, output_file, duration):
    """
    Приводим любой Pexels ролик к 1080x1920.
    Видео центрируется и заполняет вертикальный кадр.
    """

    command = [
        "ffmpeg",
        "-y",
        "-stream_loop", "-1",
        "-i", str(input_file),
        "-t", str(duration),
        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1"
        ),
        "-an",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
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
            "❌ FFmpeg clip error:"
        )
        print(e.stderr.decode(errors="ignore")[-2000:])
        return False


# ============================================================
# SUBTITLES
# ============================================================

def make_subtitle_file(script, duration):
    """
    Создаём простой SRT.

    Текст разбиваем на короткие фразы.
    """

    words = script.split()

    if not words:
        return None

    # Примерно 5–8 слов на экран
    chunks = []

    current = []

    for word in words:
        current.append(word)

        if len(current) >= 7:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    if not chunks:
        return None

    chunk_duration = duration / len(chunks)

    srt_file = WORK_DIR / "subtitles.srt"

    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d},"
            f"{millis:03d}"
        )

    with open(
        srt_file,
        "w",
        encoding="utf-8"
    ) as f:

        for i, chunk in enumerate(chunks):

            start = i * chunk_duration
            end = min(
                (i + 1) * chunk_duration,
                duration
            )

            f.write(f"{i + 1}\n")
            f.write(
                f"{format_time(start)} --> "
                f"{format_time(end)}\n"
            )
            f.write(chunk)
            f.write("\n\n")

    return srt_file


# ============================================================
# CREATE VIDEO
# ============================================================

def create_video(clips, script, music):
    print("🎬 Creating final video...")

    if not clips:
        print("❌ No video clips.")
        return False

    voice_duration = get_duration(AUDIO_FILE)

    if voice_duration <= 0:
        print("❌ Could not determine voice duration.")
        return False

    # Ограничиваем длительность
    duration = max(
        MIN_VIDEO_SECONDS,
        min(
            voice_duration + 0.5,
            MAX_VIDEO_SECONDS
        )
    )

    print(f"⏱️ Target duration: {duration:.2f}s")

    # Если голос длиннее лимита, пока оставляем его полностью.
    if voice_duration > MAX_VIDEO_SECONDS:
        duration = voice_duration

    prepared_clips = []

    # Длительность каждого куска
    clip_duration = duration / len(clips)

    for index, clip in enumerate(clips):

        prepared = (
            WORK_DIR /
            f"prepared_{index + 1}.mp4"
        )

        if prepare_clip(
            clip,
            prepared,
            clip_duration
        ):
            prepared_clips.append(prepared)

    if not prepared_clips:
        print("❌ Could not prepare clips.")
        return False

    # Создаём concat-файл
    concat_file = WORK_DIR / "concat.txt"

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as f:

        for clip in prepared_clips:
            # FFmpeg concat требует безопасный путь.
            absolute_path = clip.resolve()
            f.write(
                f"file '{absolute_path}'\n"
            )

    merged_video = WORK_DIR / "merged.mp4"

    command_merge = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(merged_video)
    ]

    try:
        subprocess.run(
            command_merge,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("❌ Could not merge video clips.")
        print(
            e.stderr.decode(errors="ignore")[-3000:]
        )
        return False

    # Субтитры
    subtitle_file = make_subtitle_file(
        script,
        duration
    )

    # Музыка может отсутствовать — это допустимо.
    if music:
        music_input = str(music)
    else:
        music_input = None

    # --------------------------------------------------------
    # FINAL FFMPEG
    # --------------------------------------------------------

    # Используем ASS-подобный стиль через subtitles filter.
    # SRT будет отображаться крупно по центру/ниже центра.
    subtitle_path = str(
        subtitle_file.resolve()
    ).replace("\\", "/").replace(":", "\\:")

    video_filter = (
        f"subtitles='{subtitle_path}':"
        "force_style="
        "'FontName=Arial,"
        "FontSize=20,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=3,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=420'"
    )

    if music_input:

        command = [
            "ffmpeg",
            "-y",

            "-i", str(merged_video),
            "-i", str(AUDIO_FILE),
            "-stream_loop", "-1",
            "-i", music_input,

            "-filter_complex",

            (
                "[0:a]"
                "volume=1.0"
                "[voice];"

                "[2:a]"
                f"volume={MUSIC_VOLUME},"
                f"atrim=0:{duration},"
                "asetpts=N/SR/TB"
                "[music];"

                "[voice][music]"
                "amix=inputs=2:"
                "duration=first:"
                "dropout_transition=2"
                "[audio]"
            ),

            "-vf", video_filter,

            "-map", "0:v:0",
            "-map", "[audio]",

            "-t", str(duration),

            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",

            "-c:a", "aac",
            "-b:a", "192k",

            "-pix_fmt", "yuv420p",

            "-movflags", "+faststart",

            str(FINAL_VIDEO)
        ]

    else:

        command = [
            "ffmpeg",
            "-y",

            "-i", str(merged_video),
            "-i", str(AUDIO_FILE),

            "-vf", video_filter,

            "-map", "0:v:0",
            "-map", "1:a:0",

            "-t", str(duration),

            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",

            "-c:a", "aac",
            "-b:a", "192k",

            "-pix_fmt", "yuv420p",

            "-movflags", "+faststart",

            str(FINAL_VIDEO)
        ]

    print("✂️ Rendering final MP4...")

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        if not FINAL_VIDEO.exists():
            print("❌ Final video was not created.")
            return False

        size_mb = (
            FINAL_VIDEO.stat().st_size
            / 1024
            / 1024
        )

        print(
            f"✅ VIDEO CREATED: "
            f"{FINAL_VIDEO}"
        )
        print(
            f"📦 Size: {size_mb:.2f} MB"
        )

        return True

    except subprocess.CalledProcessError as e:
        print("❌ Final FFmpeg error:")
        print(
            e.stderr.decode(errors="ignore")[-5000:]
        )
        return False


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

    # --------------------------------------------------------
    # 1. Generate script
    # --------------------------------------------------------

    content = generate_script()

    if not content:
        print("❌ Content generation failed.")
        return 1

    # --------------------------------------------------------
    # 2. Generate voice
    # --------------------------------------------------------

    if not generate_voice(content["script"]):
        print("❌ Voice generation failed.")
        return 1

    # --------------------------------------------------------
    # 3. Pexels
    # --------------------------------------------------------

    clips = get_video_clips(
        content["pexels_queries"]
    )

    if not clips:
        print("❌ Video generation failed: no clips.")
        return 1

    # --------------------------------------------------------
    # 4. Music
    # --------------------------------------------------------

    music = get_music()

    if not music:
        print(
            "⚠️ No music found. "
            "Video will be created without background music."
        )

    # --------------------------------------------------------
    # 5. Render
    # --------------------------------------------------------

    if not create_video(
        clips,
        content["script"],
        music
    ):
        print("❌ Video rendering failed.")
        return 1

    print()
    print("======================================")
    print("🎉 VIDEO BOT FINISHED")
    print("======================================")
    print()
    print(f"🎬 {FINAL_VIDEO}")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
