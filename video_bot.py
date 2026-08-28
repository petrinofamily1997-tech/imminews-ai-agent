import os
import base64
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

GROQ_MODELS = ["qwen/qwen3.8-27b"]


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

    print("🎙️ Generating Russian voice with ElevenLabs...")

    tts_script = script.replace("стоит", "стоИ́т").replace("Стоит", "СтоИ́т")

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
        "money finance", "banking", "credit card payment",
        "stock market", "business meeting", "smartphone banking",
        "office computer", "person thinking", "city night",
        "calculator money", "financial chart", "cash close up",
    ]

    all_queries = []
    for q in list(queries) + fallback:
        q = str(q).strip()
        if q and q not in all_queries:
            all_queries.append(q)

    clips = []

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

    alignment_file = WORK_DIR / "alignment.json"

    with open(alignment_file, "r", encoding="utf-8") as f:
        alignment = json.load(f)

    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    durations = alignment.get("character_durations_seconds", [])

    if not chars or not starts or not durations:
        raise ValueError("ElevenLabs timestamps are missing.")

    n = min(len(chars), len(starts), len(durations))

    words = []
    current = []
    word_start = None
    word_end = None

    for i in range(n):
        ch = chars[i]
        st = float(starts[i])
        en = st + float(durations[i])

        if ch.isspace():
            if current:
                words.append(("".join(current), word_start, word_end))
                current = []
                word_start = None
                word_end = None
        else:
            if word_start is None:
                word_start = st
            current.append(ch)
            word_end = en

    if current:
        words.append(("".join(current), word_start, word_end))

    subtitle_file = WORK_DIR / "subtitles.ass"

    def ts(x):
        x = max(0, min(float(x), duration))
        cs = int(round(x * 100))
        h = cs // 360000
        m = (cs % 360000) // 6000
        sec = (cs % 6000) // 100
        cent = cs % 100
        return f"{h}:{m:02d}:{sec:02d}.{cent:02d}"

    groups = [words[i:i+4] for i in range(0, len(words), 4)]

    with open(subtitle_file, "w", encoding="utf-8") as f:
        f.write(
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\nPlayResY: 1920\n"
            "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,76,&H00FFFFFF,&H00FFFFFF,&H00000000,"
            "&H99000000,1,0,0,0,100,100,0,0,1,5,2,5,60,60,680,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text\n"
        )

        for group in groups:
            start_t = group[0][1]
            end_t = min(group[-1][2], duration)

            if len(group) > 1:
                caption = (
                    " ".join(x[0] for x in group[:-1]) + " "
                    + r"{\b1\c&H0000FF&}" + group[-1][0]
                    + r"{\b0\c&H00FFFFFF&}"
                )
            else:
                caption = (
                    r"{\b1\c&H0000FF&}" + group[0][0]
                    + r"{\b0\c&H00FFFFFF&}"
                )

            if len(group) == 4:
                caption = (
                    " ".join(x[0] for x in group[:2]) + r"\N"
                    + " ".join(x[0] for x in group[2:-1]) + " "
                    + r"{\b1\c&H0000FF&}" + group[-1][0]
                    + r"{\b0\c&H00FFFFFF&}"
                )

            f.write(
                f"Dialogue: 0,{ts(start_t)},{ts(end_t)},Default,,0,0,0,,"
                f"{caption}\n"
            )

    print(f"📝 Exact word-timed subtitles: {len(groups)} blocks.")
    return subtitle_file


# ============================================================
# CREATE FINAL VIDEO
# ============================================================

def create_video(clips, subtitle_file, music_file):

    if not clips:
        return False

    duration = get_duration(AUDIO_FILE)

    if duration <= 0:
        print("❌ Could not determine voice duration.")
        return False

    print(f"🎬 Voice duration: {duration:.2f}s")

    clip_duration = duration / len(clips)
    prepared = []

    for i, clip in enumerate(clips):
        dst = WORK_DIR / f"prepared_{i}.mp4"
        if prepare_clip(clip, dst, clip_duration + 0.5):
            prepared.append(dst)

    if not prepared:
        return False

    concat_file = WORK_DIR / "concat.txt"

    with open(concat_file, "w", encoding="utf-8") as f:
        for clip in prepared:
            f.write(f"file '{clip.resolve()}'\n")

    subtitle_path = (
        str(subtitle_file.resolve())
        .replace("\\", "/")
        .replace(":", "\\:")
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-i", str(AUDIO_FILE),
    ]

    has_music = bool(music_file and Path(music_file).exists())

    if has_music:
        cmd += ["-stream_loop", "-1", "-i", str(music_file)]

        cmd += [
            "-filter_complex",
            f"[1:a]aresample=44100[voice];"
            f"[2:a]aresample=44100,volume={MUSIC_VOLUME}[music];"
            "[voice][music]amix=inputs=2:duration=first:"
            "dropout_transition=2[aout]",
            "-map", "0:v:0",
            "-map", "[aout]",
        ]
    else:
        cmd += [
            "-map", "0:v:0",
            "-map", "1:a:0",
        ]

    cmd += [
        "-vf", f"ass='{subtitle_path}'",
        "-t", f"{duration:.3f}",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-movflags", "+faststart",
        str(FINAL_VIDEO),
    ]

    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    if result.returncode != 0:
        print("❌ FFmpeg failed:")
        print(result.stderr[-4000:])
        return False

    print(f"✅ Final video created: {get_duration(FINAL_VIDEO):.2f}s")
    return True


def main():

    print()
    print("======================================")
    print("🎬 FINANCIAL VIDEO BOT")
    print("======================================")
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
    print(f"🎙️ Exact voice duration: {voice_duration:.2f}s")

    clips = get_video_clips(content["pexels_queries"])

    if not clips:
        print("❌ Could not find video footage.")
        return 1

    subtitle_file = make_subtitles(
        content["script"],
        voice_duration
    )

    music = get_music()

    if not create_video(
        clips,
        subtitle_file,
        music
    ):
        print("❌ Video rendering failed.")
        return 1

    print()
    print("======================================")
    print("🎉 VIDEO BOT FINISHED")
    print("======================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

