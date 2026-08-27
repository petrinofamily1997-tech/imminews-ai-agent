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
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

BASE_DIR = Path(__file__).resolve().parent

MUSIC_DIR = BASE_DIR / "assets" / "music"
WORK_DIR = BASE_DIR / "video_work"
OUTPUT_DIR = BASE_DIR / "output"

AUDIO_FILE = WORK_DIR / "voice.mp3"
FINAL_VIDEO = OUTPUT_DIR / "video.mp4"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

MUSIC_VOLUME = 0.06

MIN_VIDEO_SECONDS = 15
MAX_VIDEO_SECONDS = 35


# ============================================================
# GROQ MODEL SETTINGS
# ============================================================

# Приоритет моделей.
# Сначала пытаемся использовать более мощную.
# Если модель недоступна — пробуем следующую.

PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
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

    missing = []

    for name, value in required.items():
        if not value:
            missing.append(name)

    if missing:

        print("❌ Missing secrets:")

        for item in missing:
            print(f"   - {item}")

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
# CLEAN WORK
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
# GET AVAILABLE GROQ MODELS
# ============================================================

def get_available_groq_models():

    print("🔎 Checking available Groq models...")

    url = "https://api.groq.com/openai/v1/models"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        models = data.get("data", [])

        model_ids = []

        for model in models:

            model_id = model.get("id")

            if model_id:
                model_ids.append(model_id)

        print(
            f"✅ Groq reports "
            f"{len(model_ids)} available models."
        )

        return model_ids

    except Exception as e:

        print(
            f"⚠️ Could not retrieve Groq models: {e}"
        )

        return []


# ============================================================
# SELECT GROQ MODEL
# ============================================================

def select_groq_models():

    available = get_available_groq_models()

    selected = []

    # Сначала наши предпочтительные модели

    for model in PREFERRED_MODELS:

        if model in available:

            selected.append(model)

    # Если ничего не найдено,
    # ищем текстовые instruct/chat модели.

    if not selected:

        for model in available:

            model_lower = model.lower()

            if any(
                x in model_lower
                for x in [
                    "gpt-oss",
                    "qwen",
                    "llama"
                ]
            ):

                selected.append(model)

    # Убираем дубликаты

    selected = list(dict.fromkeys(selected))

    print("🧠 Models selected for fallback:")

    for model in selected:

        print(f"   → {model}")

    return selected


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


def clean_search_query(text):

    text = clean_text(text)

    text = text.replace(",", " ")

    words = text.split()

    return " ".join(words[:6])


# ============================================================
# GENERATE SCRIPT
# ============================================================

def generate_script():

    print("🧠 Asking Groq to create a script...")

    models = select_groq_models()

    if not models:

        print(
            "❌ No compatible Groq models found."
        )

        return None

    styles = [
        "PROVOCATIVE",
        "ANALYTICAL",
        "INTELLECTUAL",
        "DARK",
        "PHILOSOPHICAL",
    ]

    style = random.choice(styles)

    print(
        f"🎩 Selected style: {style}"
    )

    system_prompt = """
Ты — сценарист коротких вирусных финансовых видео.

Пиши исключительно на русском языке.

Стиль рассказчика:

- умный;
- холодный;
- спокойный;
- уверенный;
- слегка провокационный;
- философский;
- иногда саркастичный;
- без дешёвого кликбейта;
- говорит прямо со зрителем.

Создавай полностью оригинальный образ рассказчика.

НЕ копируй конкретных персонажей,
актёров, блогеров или их голоса.

Не упоминай:
Мориарти,
Мистера Фримена,
других персонажей или авторов.

Видео должно ощущаться как монолог умного человека,
который показывает зрителю то,
что тот обычно не замечает.

Тема:

Финансы.
Деньги.
Привычки.
Инвестиции.
Заработок.
Психология денег.
Расходы.
Инфляция.
Банки.
Финансовые ошибки.
Богатство.
Личные финансы.

Структура:

HOOK
↓
ИНТРИГА
↓
ФАКТ / ИДЕЯ
↓
НЕОЖИДАННЫЙ ВЫВОД
↓
МЯГКИЙ CTA

Первые слова должны заставлять
человека перестать листать видео.

Не начинай:

"Сегодня мы поговорим..."
"В этом видео..."
"Привет всем..."

Не используй:

Markdown.
**
Ссылки.
URL.
Хэштеги.
Служебные комментарии.

Не используй эмодзи внутри сценария.

Не обещай гарантированную прибыль.

Не давай персональных инвестиционных рекомендаций.

Длина:
80–130 слов.

Верни ТОЛЬКО JSON.

Формат:

{
    "title": "...",
    "style": "...",
    "script": "...",
    "pexels_queries": [
        "...",
        "...",
        "..."
    ]
}
"""

    user_prompt = f"""
Создай сценарий одного короткого видео.

Стиль:
{style}

Нужна необычная финансовая тема,
которая вызывает желание досмотреть ролик.

Сделай текст естественным для озвучки.

Не перегружай фактами.

Главное:
интерес,
напряжение,
любопытство,
сильный финальный вывод.

Верни только JSON.
"""

    client = Groq(
        api_key=GROQ_API_KEY
    )

    for model in models:

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

                temperature=0.85,

                max_tokens=1200,

                response_format={
                    "type": "json_object"
                }
            )

            text = (
                response.choices[0]
                .message.content
                or ""
            )

            if not text.strip():

                print(
                    "⚠️ Empty response."
                )

                continue

            data = json.loads(text)

            script = clean_text(
                data.get("script", "")
            )

            title = clean_text(
                data.get("title", "")
            )

            generated_style = clean_text(
                data.get(
                    "style",
                    style
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
                clean_search_query(q)
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

            print(
                f"🎩 Style: {generated_style}"
            )

            print()
            print("📜 SCRIPT:")
            print(script)
            print()

            return {
                "title": title,
                "style": generated_style,
                "script": script,
                "pexels_queries": queries[:5],
                "model": model,
            }

        except Exception as e:

            error_text = str(e)

            print(
                f"⚠️ Model failed: {error_text[:500]}"
            )

            continue

    print()
    print(
        "❌ All Groq models failed."
    )

    return None


# ============================================================
# ELEVENLABS
# ============================================================

def generate_voice(script):

    print(
        "🎙️ Generating Russian voice with ElevenLabs..."
    )

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

        "text": script,

        "model_id":
            "eleven_multilingual_v2",

        "voice_settings": {

            "stability": 0.52,

            "similarity_boost": 0.78,

            "style": 0.32,

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
                f"{response.status_code}"
            )

            print(
                response.text[:1000]
            )

            return False

        if not response.content:

            print(
                "❌ Empty ElevenLabs response."
            )

            return False

        with open(
            AUDIO_FILE,
            "wb"
        ) as file:

            file.write(
                response.content
            )

        print(
            "✅ Voice generated."
        )

        return True

    except Exception as e:

        print(
            f"❌ ElevenLabs error: {e}"
        )

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
        "Authorization":
            PEXELS_API_KEY
    }

    params = {

        "query": query,

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
                f"⚠️ Pexels error "
                f"{response.status_code}"
            )

            return None

        data = response.json()

        videos = data.get(
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

                f for f in files

                if (
                    f.get("width", 0)
                    <
                    f.get("height", 0)
                )
            ]

            candidates = (
                portrait or files
            )

            if not candidates:
                continue

            candidates.sort(
                key=lambda x:
                    abs(
                        (
                            x.get(
                                "width",
                                0
                            )
                            or 0
                        ) - 1080
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

                    file.write(
                        chunk
                    )

        if destination.stat().st_size < 10000:

            return False

        return True

    except Exception as e:

        print(
            f"❌ Download error: {e}"
        )

        return False


def get_video_clips(queries):

    print(
        "🎥 Searching for video footage..."
    )

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
        queries +
        fallback
    )

    clips = []

    used = set()

    for query in all_queries:

        if len(clips) >= 3:
            break

        link = search_pexels_video(
            query
        )

        if not link:
            continue

        if link in used:
            continue

        used.add(link)

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
        f"✅ Downloaded "
        f"{len(clips)} clips."
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
# DURATION
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

    except:

        return 0


# ============================================================
# PREPARE CLIPS
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

    except:

        return False


# ============================================================
# SUBTITLES
# ============================================================

def make_subtitles(
    script,
    duration
):

    words = script.split()

    chunks = []

    current = []

    for word in words:

        current.append(word)

        if len(current) >= 6:

            chunks.append(
                " ".join(current)
            )

            current = []

    if current:

        chunks.append(
            " ".join(current)
        )

    if not chunks:

        return None

    subtitle_file = (
        WORK_DIR /
        "subtitles.srt"
    )

    chunk_duration = (
        duration /
        len(chunks)
    )

    def timestamp(seconds):

        hours = int(
            seconds // 3600
        )

        minutes = int(
            (seconds % 3600) // 60
        )

        secs = int(
            seconds % 60
        )

        millis = int(
            (seconds -
             int(seconds)) * 1000
        )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d},"
            f"{millis:03d}"
        )

    with open(
        subtitle_file,
        "w",
        encoding="utf-8"
    ) as file:

        for i, chunk in enumerate(
            chunks
        ):

            start = (
                i *
                chunk_duration
            )

            end = min(
                (i + 1) *
                chunk_duration,
                duration
            )

            file.write(
                f"{i+1}\n"
            )

            file.write(
                f"{timestamp(start)} --> "
                f"{timestamp(end)}\n"
            )

            file.write(
                chunk
            )

            file.write(
                "\n\n"
            )

    return subtitle_file


# ============================================================
# CREATE VIDEO
# ============================================================

def create_video(
    clips,
    script,
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

    duration = max(
        MIN_VIDEO_SECONDS,
        min(
            voice_duration + 0.5,
            MAX_VIDEO_SECONDS
        )
    )

    if voice_duration > MAX_VIDEO_SECONDS:

        duration = voice_duration

    print(
        f"⏱️ Duration: "
        f"{duration:.2f}s"
    )

    prepared = []

    clip_duration = (
        duration /
        len(clips)
    )

    for i, clip in enumerate(
        clips
    ):

        output = (
            WORK_DIR /
            f"prepared_{i}.mp4"
        )

        if prepare_clip(
            clip,
            output,
            clip_duration
        ):

            prepared.append(
                output
            )

    if not prepared:

        return False

    concat = (
        WORK_DIR /
        "concat.txt"
    )

    with open(
        concat,
        "w",
        encoding="utf-8"
    ) as file:

        for clip in prepared:

            file.write(
                f"file '{clip.resolve()}'\n"
            )

    merged = (
        WORK_DIR /
        "merged.mp4"
    )

    merge_command = [

        "ffmpeg",

        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        str(concat),

        "-c",
        "copy",

        str(merged)
    ]

    try:

        subprocess.run(

            merge_command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            check=True
        )

    except Exception as e:

        print(
            f"❌ Merge error: {e}"
        )

        return False

    subtitle_file = make_subtitles(
        script,
        duration
    )

    if not subtitle_file:

        return False

    subtitle_path = (
        str(
            subtitle_file.resolve()
        )
        .replace("\\", "/")
        .replace(":", "\\:")
    )

    video_filter = (

        f"subtitles='{subtitle_path}':"

        "force_style='"

        "FontName=Arial,"
        "FontSize=20,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=3,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=420"

        "'"
    )

    if music:

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

            (
                "[1:a]"
                "volume=1.0"
                "[voice];"

                "[2:a]"
                f"volume={MUSIC_VOLUME}"
                "[music];"

                "[voice][music]"
                "amix=inputs=2:"
                "duration=first:"
                "dropout_transition=2"
                "[audio]"
            ),

            "-vf",
            video_filter,

            "-map",
            "0:v:0",

            "-map",
            "[audio]",

            "-t",
            str(duration),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "22",

            "-c:a",
            "aac",

            "-b:a",
            "192k",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            str(FINAL_VIDEO)
        ]

    else:

        command = [

            "ffmpeg",

            "-y",

            "-i",
            str(merged),

            "-i",
            str(AUDIO_FILE),

            "-vf",
            video_filter,

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            "-t",
            str(duration),

            "-c:v",
            "libx264",

            "-preset",
            "medium",

            "-crf",
            "22",

            "-c:a",
            "aac",

            "-b:a",
            "192k",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            str(FINAL_VIDEO)
        ]

    print(
        "✂️ Rendering MP4..."
    )

    try:

        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            check=True
        )

        if not FINAL_VIDEO.exists():

            print(
                "❌ Video not created."
            )

            return False

        size = (
            FINAL_VIDEO.stat().st_size
            /
            1024
            /
            1024
        )

        print(
            f"✅ VIDEO CREATED"
        )

        print(
            f"📦 Size: {size:.2f} MB"
        )

        return True

    except subprocess.CalledProcessError as e:

        print(
            "❌ FFmpeg error:"
        )

        print(
            e.stderr.decode(
                errors="ignore"
            )[-5000:]
        )

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

    # --------------------------------
    # GROQ
    # --------------------------------

    content = generate_script()

    if not content:

        print(
            "❌ Content generation failed."
        )

        return 1

    # --------------------------------
    # ELEVENLABS
    # --------------------------------

    if not generate_voice(
        content["script"]
    ):

        print(
            "❌ Voice generation failed."
        )

        return 1

    # --------------------------------
    # PEXELS
    # --------------------------------

    clips = get_video_clips(
        content["pexels_queries"]
    )

    if not clips:

        print(
            "❌ Could not find video footage."
        )

        return 1

    # --------------------------------
    # MUSIC
    # --------------------------------

    music = get_music()

    # --------------------------------
    # VIDEO
    # --------------------------------

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

    raise SystemExit(
        main()
    )
