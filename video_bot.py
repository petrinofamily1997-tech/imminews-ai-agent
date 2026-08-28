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

MUSIC_VOLUME = 0.045

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

    print(f"🎩 Selected style: {style}")

    client = Groq(api_key=GROQ_API_KEY)

    # Для обычной генерации текста используем Qwen в instruct-режиме.
    # Это специально сделано вместо GPT-OSS: GPT-OSS в предыдущих
    # запусках возвращал пустой message.content.
    models = [
        ("qwen/qwen3.8-27b", {
            "reasoning_effort": "none",
            "temperature": 0.7,
            "top_p": 0.8,
        }),
        ("qwen/qwen3.6-27b", {
            "reasoning_effort": "none",
            "temperature": 0.7,
            "top_p": 0.8,
        }),
        ("openai/gpt-oss-20b", {
            "include_reasoning": False,
            "temperature": 0.7,
        }),
    ]

    prompt = f"""
Напиши готовый сценарий для финансового TikTok/YouTube Shorts
на русском языке.

Стиль: {style}.

Требования:
- 90–130 слов.
- Сильный провокационный hook в первом предложении.
- Тема: деньги, финансовые ошибки, психология денег,
  инфляция, банки, инвестиции, заработок или экономика.
- После hook раскрой одну конкретную мысль.
- Добавь неожиданный вывод.
- В конце коротко предложи подписаться.
- Текст должен звучать естественно при мужской озвучке.
- Не начинай с «Привет», «Сегодня мы поговорим» или
  «В этом видео».
- Не используй Markdown, **, URL или хэштеги.
- Не обещай гарантированную прибыль.
- Не давай персональных инвестиционных рекомендаций.

Верни ТОЛЬКО текст сценария.
Никакого JSON.
Никакого заголовка.
Никаких пояснений.
"""

    for model, params in models:

        print()
        print(f"🤖 Trying Groq model: {model}")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=1000,
                **params,
            )

            choice = response.choices[0]
            message = choice.message
            content = getattr(message, "content", None)

            print(
                f"📡 Groq finish reason: "
                f"{getattr(choice, 'finish_reason', 'unknown')}"
            )

            if content is None:
                content = ""

            # SDK обычно возвращает строку. Оставляем обработку
            # списка блоков как дополнительную защиту.
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("text"):
                            parts.append(str(item["text"]))
                    elif getattr(item, "text", None):
                        parts.append(str(item.text))
                content = "\n".join(parts)

            content = str(content).strip()

            if not content:
                print("⚠️ Empty final text from Groq.")
                continue

            content = clean_text(content)
            content = re.sub(
                r"(?im)^\s*(TITLE|SCRIPT|QUERY|END)\s*:?\s*",
                "",
                content
            ).strip()

            words = content.split()

            if len(words) < 45:
                print(
                    f"⚠️ Script too short ({len(words)} words). "
                    "Trying next model..."
                )
                continue

            if len(words) > 145:
                content = " ".join(words[:145])
                content = content.rstrip(".,!?;:") + "."

            title = "Что происходит с твоими деньгами на самом деле"

            queries = [
                "money finance business",
                "banking money",
                "business person thinking",
            ]

            print(f"✅ Groq model working: {model}")
            print(f"📝 Title: {title}")
            print(f"🔎 Pexels query: {queries[0]}")
            print()
            print("📜 SCRIPT:")
            print(content)
            print()

            return {
                "title": title,
                "script": content,
                "pexels_queries": queries,
            }

        except Exception as e:
            print(f"❌ Groq error with {model}:")
            print(str(e)[:1500])

    print("❌ All Groq models failed.")
    return None


# ============================================================
# ELEVENLABS
# ============================================================

def normalize_tts_text(script):
    """Correct a few Russian stress patterns for ElevenLabs."""
    replacements = {
        "стоит": "стоИ́т",
        "Стоит": "СтоИ́т",
        "СТОИТ": "СТОИ́Т",
    }
    for old, new in replacements.items():
        script = script.replace(old, new)
    return script


def generate_voice(script):

    print(
        "🎙️ Generating Russian voice with ElevenLabs..."
    )

    
    # Stress fixes are used only for speech; subtitles keep the normal spelling.
    tts_script = normalize_tts_text(script)
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
        "banking",
        "credit card payment",
        "stock market",
        "business meeting",
        "person thinking",
        "smartphone banking",
        "city night",
        "office computer",
        "calculator money",
        "cash close up",
        "financial chart",
    ]

    all_queries = []
    for q in queries + fallback:
        if q not in all_queries:
            all_queries.append(q)

    clips = []

    # 8 different clips gives a much more dynamic Short than 2-3 slides.
    for query in all_queries:

        if len(clips) >= 8:
            break

        link = search_pexels_video(query)

        if not link:
            continue

        destination = WORK_DIR / f"clip_{len(clips)+1}.mp4"

        if download_video(link, destination):
            clips.append(destination)

    print(f"✅ Downloaded {len(clips)} clips.")

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


def prepare_clip(input_file, output_file, duration):

    # Gentle animated zoom prevents stock footage from feeling static.
    vf = (
        "scale=1200:2133:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0008,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:s=1080x1920:fps=30,"
        "setsar=1"
    )

    command = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(input_file),
        "-t", str(duration),
        "-vf", vf,
        "-an",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
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

    # Split by punctuation first so captions follow the spoken rhythm.
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", script.strip())
        if s.strip()
    ]

    chunks = []
    for sentence in sentences:
        words = sentence.split()

        # Break long sentences into compact 3-6 word caption blocks.
        while len(words) > 6:
            chunks.append(" ".join(words[:6]))
            words = words[6:]

        if words:
            chunks.append(" ".join(words))

    if not chunks:
        return None

    subtitle_file = WORK_DIR / "subtitles.ass"

    chunk_duration = duration / len(chunks)

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
            "Style: Default,Arial,58,&H00FFFFFF,&H00FFFFFF,"
            "&H00000000,&H99000000,1,0,0,0,100,100,0,0,1,4,2,2,"
            "80,80,330,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, "
            "MarginR, MarginV, Effect, Text\n"
        )

        for i, chunk in enumerate(chunks):
            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, duration)

            # Highlight the last word for stronger visual rhythm.
            parts = chunk.split()
            if len(parts) >= 2:
                caption = " ".join(parts[:-1]) + " " + r"{\b1\c&H0000FF&}" + parts[-1] + r"{\b0\c&H00FFFFFF&}"
            else:
                caption = chunk

            # Keep captions to two lines when possible.
            if len(caption.split()) > 3:
                p = caption.split()
                midpoint = len(p) // 2
                caption = " ".join(p[:midpoint]) + r"\N" + " ".join(p[midpoint:])

            file.write(
                f"Dialogue: 0,{ass_time(start_time)},{ass_time(end_time)},"
                f"Default,,0,0,0,,{caption}\n"
            )

    return subtitle_file


# ============================================================
# CREATE FINAL VIDEO
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

    prepared = []

    # Use enough clips to cover the whole voice track.
    clip_duration = duration / len(clips)

    for i, clip in enumerate(clips):

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

    try:

        subprocess.run(
            [
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
                str(merged),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

    except:

        return False

    subtitle_file = make_subtitles(
        script,
        duration
    )

    if not subtitle_file:
        return False

    subtitle_path = str(subtitle_file.resolve()).replace("\\", "/")
    subtitle_path = subtitle_path.replace(":", "\\:")

    # Burn ASS captions directly into the video.
    video_filter = f"ass='{subtitle_path}'"

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

            str(FINAL_VIDEO),
        ]

    print(
        "✂️ Rendering MP4..."
    )

    try:

        subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        if not FINAL_VIDEO.exists():

            print(
                "❌ Video was not created."
            )

            return False

        size = (
            FINAL_VIDEO.stat().st_size
            / 1024
            / 1024
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
        print("❌ Could not find video footage.")
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
