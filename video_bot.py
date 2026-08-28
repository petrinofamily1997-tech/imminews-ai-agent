import os
import re
import json
import random
import shutil
import subprocess
import wave
import math
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
MAX_VIDEO_SECONDS = 40


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

Не используй URL.

Не используй хэштеги.

Не используй эмодзи внутри сценария.

Не обещай гарантированную прибыль.

Не давай персональных инвестиционных рекомендаций.

Длина сценария:
примерно 100–150 слов.

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

            script = clean_text(
                data.get("script", "")
            )

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

def get_audio_duration(audio_file):
    """Get exact audio duration using ffprobe."""
    command = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_file)
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )

    return float(result.stdout.strip())


def make_subtitles(script, duration):
    """
    Create subtitles from the actual narration duration.
    Text is split into short chunks and distributed according to word count,
    so captions follow the voice much more closely than equal-time captions.
    """

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", script.strip())
        if s.strip()
    ]

    chunks = []

    for sentence in sentences:
        words = sentence.split()

        while len(words) > 6:
            chunks.append(words[:6])
            words = words[6:]

        if words:
            chunks.append(words)

    if not chunks:
        return None

    total_words = sum(len(c) for c in chunks)

    # Small pause compensation: punctuation naturally takes a little longer.
    weights = []
    for chunk in chunks:
        weight = len(chunk)

        joined = " ".join(chunk)
        if joined.endswith((",", ";", ":")):
            weight += 0.25
        if joined.endswith((".", "!", "?")):
            weight += 0.45

        weights.append(weight)

    total_weight = sum(weights)

    subtitle_file = WORK_DIR / "subtitles.ass"

    def ass_time(seconds):
        total_cs = max(0, int(seconds * 100))
        h = total_cs // 360000
        m = (total_cs % 360000) // 6000
        s = (total_cs % 6000) // 100
        cs = total_cs % 100
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    with open(subtitle_file, "w", encoding="utf-8") as file:

        file.write(
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, "
            "SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, "
            "Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&H99000000,1,0,0,0,100,100,0,0,1,5,2,5,"
            "70,70,760,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, "
            "MarginR, MarginV, Effect, Text\n"
        )

        current = 0.0

        for index, chunk in enumerate(chunks):
            chunk_duration = duration * (weights[index] / total_weight)
            start_time = current
            end_time = min(current + chunk_duration, duration)
            current = end_time

            parts = list(chunk)

            # Red + bold final word.
            if len(parts) >= 2:
                caption = (
                    " ".join(parts[:-1])
                    + " "
                    + r"{\b1\c&H0000FF&}"
                    + parts[-1]
                    + r"{\b0\c&H00FFFFFF&}"
                )
            else:
                caption = parts[0]

            # Two readable lines for longer captions.
            if len(parts) >= 4:
                midpoint = len(parts) // 2
                left = " ".join(parts[:midpoint])
                right = " ".join(parts[midpoint:])

                if len(parts) >= 2:
                    last = parts[-1]
                    if right.endswith(last):
                        right = (
                            " ".join(parts[midpoint:-1])
                            + " "
                            + r"{\b1\c&H0000FF&}"
                            + last
                            + r"{\b0\c&H00FFFFFF&}"
                        )

                caption = left + r"\N" + right

            file.write(
                f"Dialogue: 0,{ass_time(start_time)},{ass_time(end_time)},"
                f"Default,,0,0,0,,{caption}\n"
            )

    print(
        f"📝 Subtitles synced to audio: {len(chunks)} caption blocks."
    )

    return subtitle_file


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_video(clips, subtitle_file, duration):

    if not clips:
        print("❌ No video clips available.")
        return False

    print(f"🎬 Building final video for exact narration duration: {duration:.2f}s")

    clip_duration = duration / len(clips)

    prepared = []

    for index, clip in enumerate(clips):
        output = WORK_DIR / f"prepared_{index}.mp4"

        if prepare_clip(
            clip,
            output,
            clip_duration + 0.25
        ):
            prepared.append(output)

    if not prepared:
        print("❌ Could not prepare video clips.")
        return False

    concat_file = WORK_DIR / "concat.txt"

    with open(concat_file, "w", encoding="utf-8") as file:
        for clip in prepared:
            file.write(
                f"file '{clip.resolve()}'\n"
            )

    video_filter = None

    if subtitle_file:
        subtitle_path = str(
            subtitle_file.resolve()
        ).replace("\\", "/").replace(":", "\\:")

        video_filter = f"ass='{subtitle_path}'"

    command = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-i", str(AUDIO_FILE),
    ]

    if MUSIC_FILE.exists():
        command += [
            "-stream_loop", "-1",
            "-i", str(MUSIC_FILE)
        ]

    command += [
        "-t", str(duration),
        "-map", "0:v:0",
        "-map", "1:a:0",
    ]

    if MUSIC_FILE.exists():
        command += [
            "-map", "2:a:0",
            "-filter_complex",
            (
                "[1:a]volume=1.0[voice];"
                f"[2:a]volume={MUSIC_VOLUME}[music];"
                "[voice][music]amix=inputs=2:"
                "duration=first:dropout_transition=2[aout]"
            ),
            "-map", "[aout]"
        ]
    else:
        command += [
            "-map", "1:a:0"
        ]

    if video_filter:
        command += [
            "-vf", video_filter
        ]

    command += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(OUTPUT_FILE)
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print("❌ FFmpeg failed.")
            print(result.stderr[-3000:])
            return False

        print("✅ Final video created.")
        return True

    except Exception as e:
        print(f"❌ Video creation failed: {e}")
        return False


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
