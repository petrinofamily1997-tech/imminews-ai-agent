import os
import sys
import time
import random
import requests
from dotenv import load_dotenv
from groq import Groq


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YUMCUT_URL = os.getenv("YUMCUT_URL", "http://localhost:3000").rstrip("/")
YUMCUT_API_KEY = os.getenv("YUMCUT_API_KEY")

REQUEST_TIMEOUT = 60


# ============================================================
# VALIDATION
# ============================================================

def check_environment():
    print("======================================")
    print("🔎 CHECKING ENVIRONMENT")
    print("======================================")

    errors = []

    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY is missing")

    if not YUMCUT_API_KEY:
        errors.append("YUMCUT_API_KEY is missing")

    if not YUMCUT_URL:
        errors.append("YUMCUT_URL is missing")

    if errors:
        print("❌ Environment errors:")

        for error in errors:
            print(f"   - {error}")

        sys.exit(1)

    print("✅ GROQ_API_KEY found")
    print("✅ YUMCUT_API_KEY found")
    print(f"✅ YUMCUT_URL: {YUMCUT_URL}")
    print()


# ============================================================
# TOPIC
# ============================================================

def choose_topic():
    topics = [
        "Как инфляция в 2026 году съедает сбережения",
        "Криптовалюты: новый пузырь или будущее денег?",
        "Как эмоции мешают зарабатывать на бирже",
        "Почему богатые инвестируют, а бедные копят",
        "Что делать с деньгами во время рецессии",
    ]

    return random.choice(topics)


# ============================================================
# GROQ SCRIPT GENERATION
# ============================================================

def generate_script(topic):
    print("🧠 Asking Groq to create a script...")
    print(f"🎯 Selected topic: {topic}")

    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты профессиональный сценарист коротких финансовых "
                    "видео для TikTok, Reels и YouTube Shorts. "
                    "Напиши динамичный сценарий примерно на 60 секунд. "
                    "Пиши на русском языке. "
                    "Начни с сильного hook в первые 2-3 секунды. "
                    "Не используй приветствие. "
                    "Не добавляй заголовки вроде 'Сцена 1'. "
                    "Текст должен хорошо звучать при озвучке."
                ),
            },
            {
                "role": "user",
                "content": f"Тема видео: {topic}",
            },
        ],
        temperature=0.75,
        max_completion_tokens=800,
    )

    script = response.choices[0].message.content

    if not script:
        raise RuntimeError("Groq returned an empty script")

    script = script.strip()

    print()
    print("======================================")
    print("📝 GENERATED SCRIPT")
    print("======================================")
    print(script)
    print()

    return {
        "title": topic,
        "script": script,
    }


# ============================================================
# YUMCUT HEADERS
# ============================================================

def yumcut_headers():
    return {
        "Authorization": f"Bearer {YUMCUT_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ============================================================
# YUMCUT HEALTH CHECK
# ============================================================

def check_yumcut():
    print("======================================")
    print("🔎 CHECKING YUMCUT")
    print("======================================")

    try:
        response = requests.get(
            YUMCUT_URL,
            timeout=20,
        )

        print(f"YumCut HTTP status: {response.status_code}")

        if response.status_code >= 500:
            print("❌ YumCut returned a server error")
            print(response.text[:2000])
            return False

        print("✅ YumCut is reachable")
        print()

        return True

    except requests.RequestException as exc:
        print(f"❌ Cannot connect to YumCut: {exc}")
        return False


# ============================================================
# CREATE YUMCUT PROJECT
# ============================================================

def create_video_with_yumcut(title, script):
    print("======================================")
    print("🎬 SENDING PROJECT TO YUMCUT")
    print("======================================")

    # Keep the complete script if possible.
    # The previous version sent only script[:300],
    # which unnecessarily removed most of the generated script.
    payload = {
        "prompt": f"{title}\n\n{script}",
        "durationSeconds": 60,
        "languages": ["ru"],
        "captionsEnabled": True,
    }

    endpoint = f"{YUMCUT_URL}/api/user/v1/projects"

    print(f"POST {endpoint}")
    print()

    try:
        response = requests.post(
            endpoint,
            headers=yumcut_headers(),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:
        print(f"❌ YumCut request failed: {exc}")
        return None

    print(f"YumCut HTTP status: {response.status_code}")

    # --------------------------------------------------------
    # Successful response
    # --------------------------------------------------------

    if 200 <= response.status_code < 300:
        try:
            data = response.json()
        except ValueError:
            data = {
                "raw_response": response.text
            }

        print("✅ YumCut accepted the project")
        print()
        print("YumCut response:")

        print(data)
        print()

        project_id = data.get("id") if isinstance(data, dict) else None

        if project_id:
            print(f"✅ Project ID: {project_id}")

        return data

    # --------------------------------------------------------
    # Error response
    # --------------------------------------------------------

    print("❌ YumCut rejected the request")

    try:
        error_data = response.json()
        print("Response:")
        print(error_data)
    except ValueError:
        print("Response:")
        print(response.text[:5000])

    if response.status_code == 401:
        print()
        print("🔐 HTTP 401 Unauthorized")
        print("Check that YUMCUT_API_KEY is valid.")

    elif response.status_code == 403:
        print()
        print("🚫 HTTP 403 Forbidden")
        print("The API key may not have permission for this endpoint.")

    elif response.status_code == 404:
        print()
        print("❓ HTTP 404 Not Found")
        print("The YumCut API endpoint may be different in this version.")

    return None


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("======================================")
    print("🎬 FINANCIAL VIDEO BOT")
    print("======================================")
    print()

    # 1. Check environment
    check_environment()

    # 2. Check YumCut
    if not check_yumcut():
        sys.exit(1)

    # 3. Choose topic
    topic = choose_topic()

    print(f"📌 Topic: {topic}")
    print()

    # 4. Generate script
    try:
        content = generate_script(topic)
    except Exception as exc:
        print(f"❌ Groq error: {exc}")
        sys.exit(1)

    # 5. Create project in YumCut
    result = create_video_with_yumcut(
        content["title"],
        content["script"],
    )

    if not result:
        print()
        print("❌ Video project was not created.")
        sys.exit(1)

    print()
    print("======================================")
    print("✅ YUMCUT PROJECT CREATED")
    print("======================================")

    # --------------------------------------------------------
    # IMPORTANT
    #
    # We deliberately do NOT say:
    # "Video is ready"
    #
    # The previous version waited 300 seconds and then assumed
    # that the video was ready. That was not reliable.
    #
    # Until we confirm the exact status/download endpoint of
    # the installed YumCut API, we stop after successful
    # project creation and print the complete API response.
    # --------------------------------------------------------

    project_id = None

    if isinstance(result, dict):
        project_id = result.get("id")

    if project_id:
        print(f"📁 Project ID: {project_id}")

    print()
    print("ℹ️ YumCut accepted the project successfully.")
    print("ℹ️ The exact generation-status endpoint is not assumed.")
    print("ℹ️ Full response from YumCut was printed above.")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n❌ Unexpected error: {exc}")
        sys.exit(1)
