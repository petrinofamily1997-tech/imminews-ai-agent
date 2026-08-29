import os
import time
import random
import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YUMCUT_URL = os.getenv("YUMCUT_URL", "http://localhost:3000")

def choose_topic():
    topics = [
        "Как инфляция в 2026 году съедает сбережения",
        "Криптовалюты: новый пузырь или будущее денег?",
        "Как эмоции мешают зарабатывать на бирже",
        "Почему богатые инвестируют, а бедные копят",
        "Что делать с деньгами во время рецессии"
    ]
    return random.choice(topics)

def generate_script(topic):
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Ты сценарист коротких финансовых видео. Напиши сценарий на 60 секунд. Пиши на русском, с хайпом в начале."},
            {"role": "user", "content": f"Тема: {topic}"}
        ],
        temperature=0.75,
        max_completion_tokens=800
    )
    script = response.choices[0].message.content
    return {"title": topic, "script": script}

def create_video_with_yumcut(title, script):
    print("🎬 Отправляем в YumCut...")
    
    payload = {
        "prompt": f"{title}: {script[:300]}",
        "durationSeconds": 60,
        "languages": ["ru"],
        "captionsEnabled": True
    }
    
    try:
        resp = requests.post(
            f"{YUMCUT_URL}/api/user/v1/projects",
            json=payload,
            timeout=60
        )
        if resp.status_code != 200:
            print(f"❌ Ошибка: {resp.text}")
            return False
        project_id = resp.json()["id"]
        print(f"✅ Проект создан: {project_id}")
        
        print("⏳ Ждём генерации...")
        time.sleep(300)
        print("✅ Видео готово (условно)")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    topic = choose_topic()
    print(f"📌 Тема: {topic}")
    content = generate_script(topic)
    create_video_with_yumcut(content["title"], content["script"])

if __name__ == "__main__":
    main()
