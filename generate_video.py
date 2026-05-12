# -*- coding: utf-8 -*-
import os
import random
import tempfile
import subprocess
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
YOUTUBE_TOKEN = os.environ["YOUTUBE_TOKEN"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
YOUTUBE_CLIENT_ID = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
CONTENT_TYPE = os.environ.get("CONTENT_TYPE", "tarot")

TAROT_CARDS = [
    "Шут", "Маг", "Верховная Жрица", "Императрица", "Император",
    "Иерофант", "Влюблённые", "Колесница", "Сила", "Отшельник",
    "Колесо Фортуны", "Справедливость", "Повешенный", "Смерть",
    "Умеренность", "Дьявол", "Башня", "Звезда", "Луна", "Солнце",
    "Суд", "Мир"
]

HOOKS = [
    "Это послание пришло именно для тебя...",
    "Вселенная шепчет тебе кое-что важное",
    "Стоп. Это не случайно что ты это видишь",
    "Это знак. Читай до конца",
    "Ты это видишь — значит тебе это нужно",
    "Судьба отправила тебе сообщение",
    "Не листай дальше. Это важно",
    "Что скрывает от тебя Вселенная?",
    "Секрет твоей судьбы раскрыт",
    "Космос послал тебе это сегодня",
    "Остановись. Вселенная хочет тебе сказать",
    "Твоя судьба разворачивается прямо сейчас",
    "Предупреждение от звёзд именно тебе",
    "Портал открыт. Твоё послание внутри",
    "Карты никогда не лгут. Особенно сегодня",
    "Высшие силы говорят именно с тобой",
    "Энергия этого дня принадлежит тебе",
    "Архангелы шепчут твоё имя сегодня",
    "Магия этого дня раскрывается здесь",
    "Знаешь ли ты что ждёт тебя впереди?",
]

TITLES = {
    "card": "🃏 Карта дня 🃏",
    "numerology": "🔢 Нумерология 🔢",
    "tarot": "🔮 Расклад Таро 🔮",
    "stars": "⭐ Послание звёзд ⭐",
}

PEXELS_QUERIES = {
    "card": ["tarot cards candles dark", "fortune telling mystical", "magic ritual fog"],
    "numerology": ["sacred geometry light", "mystical numbers universe", "cosmic energy glow"],
    "tarot": ["tarot reading mystic", "crystal ball magic dark", "witch forest night"],
    "stars": ["galaxy stars purple", "nebula universe dark", "aurora night sky"],
}

# Ambient мистическая музыка (Pixabay Free Music)
MUSIC_TRACKS = [
    "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3",  # Mystical
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_91b32e02f1.mp3",  # Ambient Space
    "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3",  # Ethereal
    "https://cdn.pixabay.com/download/audio/2022/08/02/audio_884fe92c21.mp3",  # Dark Ambient
]


def ask_groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.9
        }
    )
    data = r.json()
    if "choices" not in data:
        raise Exception(str(data.get("error", data)))
    return data["choices"][0]["message"]["content"]


def get_pexels_video(content_type):
    """Скачивает уникальное ЖИВОЕ видео с Pexels"""
    queries = PEXELS_QUERIES.get(content_type, PEXELS_QUERIES["stars"])
    
    # Пробуем несколько запросов подряд для разнообразия
    all_videos = []
    
    for query in queries:
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={
                    "query": query,
                    "orientation": "portrait",
                    "size": "medium",
                    "per_page": 30  # берём больше видео
                },
                timeout=10
            )
            
            if r.status_code == 200:
                videos = r.json().get("videos", [])
                # Фильтруем только видео длиннее 10 секунд (чтобы были живые, не статичные)
                videos = [v for v in videos if v.get("duration", 0) >= 10]
                all_videos.extend(videos)
                print(f"📹 Found {len(videos)} videos for '{query}'")
        except Exception as e:
            print(f"⚠️ Query '{query}' failed: {e}")
            continue
    
    if not all_videos:
        print("❌ No Pexels videos found")
        return None
    
    # Берём случайное видео
    random.shuffle(all_videos)
    video = all_videos[0]
    
    files = video.get("video_files", [])
    
    # Ищем вертикальное HD видео
    portrait = [f for f in files if f.get("width", 0) <= f.get("height", 1) and f.get("height", 0) >= 720]
    if not portrait:
        # Если нет вертикальных, берём любое HD
        portrait = [f for f in files if f.get("height", 0) >= 720]
    
    if not portrait:
        print("⚠️ No suitable video files")
        return None
    
    # Берём файл среднего качества (не самое высокое — быстрее скачается)
    portrait.sort(key=lambda x: x.get("height", 0))
    best = portrait[len(portrait) // 2] if len(portrait) > 2 else portrait[0]
    
    url = best["link"]
    duration = video.get("duration", 0)
    
    print(f"✅ Pexels: id={video['id']}, duration={duration}s, quality={best.get('height')}p")
    
    tmp = tempfile.mktemp(suffix=".mp4")
    
    try:
        with requests.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
        
        if os.path.getsize(tmp) < 50000:
            print("⚠️ Downloaded file too small")
            return None
        
        return tmp
    
    except Exception as e:
        print(f"❌ Download failed: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return None


def get_music():
    """Скачивает ambient музыку"""
    url = random.choice(MUSIC_TRACKS)
    tmp = tempfile.mktemp(suffix=".mp3")
    
    try:
        r = requests.get(url, timeout=30, stream=True)
        if r.status_code == 200:
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
            
            if os.path.getsize(tmp) > 5000:
                print("✅ Music downloaded")
                return tmp
    except Exception as e:
        print(f"⚠️ Music download failed: {e}")
    
    return None


def create_overlay(hook, text, title):
    """Создаёт PNG оверлей с текстом"""
    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Полупрозрачный градиент
    for y in range(H):
        alpha = int(180 + (y / H) * 50)
        draw.line([(0, y), (W, y)], fill=(5, 0, 20, alpha))
    
    # Звёзды
    rng = random.Random(datetime.now().day + datetime.now().month)
    for _ in range(150):
        x = rng.randint(0, W)
        y = rng.randint(0, H // 2)
        s = rng.randint(1, 3)
        br = rng.randint(180, 255)
        draw.ellipse([x - s, y - s, x + s, y + s], fill=(br, br, br, 220))
    
    # Декоративные круги
    cx, cy = W // 2, H // 2
    for radius in [380, 340, 300]:
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=(120, 50, 200, 180), width=2)
    
    # Шрифты
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    font_path = next((p for p in font_paths if os.path.exists(p)), None)
    
    def font(size):
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
    
    def wrap_text(t, max_chars=24):
        words = t.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = (current + " " + word).strip()
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines
    
    def shadow_text(xy, txt, fnt, color, shadow=(0, 0, 0, 200), offset=4):
        x, y = xy
        draw.text((x + offset, y + offset), txt, font=fnt, fill=shadow, anchor="mm")
        draw.text((x, y), txt, font=fnt, fill=color, anchor="mm")
    
    # ХУК сверху
    y = 140
    for line in wrap_text(hook, 22):
        shadow_text((W // 2, y), line, font(68), (255, 220, 50, 255), offset=5)
        y += 85
    
    # Разделитель
    draw.line([(80, y + 20), (W - 80, y + 20)], fill=(200, 100, 255, 255), width=4)
    
    # ЗАГОЛОВОК
    shadow_text((W // 2, y + 80), title, font(56), (220, 160, 255, 255))
    
    # Разделитель
    draw.line([(80, y + 130), (W - 80, y + 130)], fill=(200, 100, 255, 255), width=3)
    
    # ОСНОВНОЙ ТЕКСТ — крупнее и короче
    ty = y + 200
    for line in wrap_text(text, 24)[:5]:  # макс 5 строк, 24 символа
        shadow_text((W // 2, ty), line, font(56), (255, 250, 255, 255))
        ty += 75
        if ty > H - 520:
            break
    
    # CTA блок снизу — поднят выше чтобы не налезать на панель YouTube
    cy = H - 500
    draw.rounded_rectangle([40, cy, W - 40, cy + 340],
                           radius=30, fill=(10, 0, 40, 230),
                           outline=(180, 80, 255, 255), width=3)
    
    shadow_text((W // 2, cy + 60), "✨ Бесплатный расклад каждый день", font(42), (200, 150, 255, 255))
    shadow_text((W // 2, cy + 135), "Карта • Нумерология • Таро", font(40), (220, 200, 255, 255))
    shadow_text((W // 2, cy + 220), "@numer_taro_bot", font(54), (255, 215, 60, 255))
    shadow_text((W // 2, cy + 295), "Ссылка в описании канала", font(36), (180, 220, 255, 255))
    
    out = tempfile.mktemp(suffix=".png")
    img.save(out, "PNG")
    return out


def build_video(bg_path, overlay_png, music_path, out_path):
    """Собирает финальное видео с фоном, текстом и музыкой"""
    
    # Обрабатываем фоновое видео
    if bg_path and os.path.exists(bg_path):
        print("🎬 Processing Pexels video...")
        bg_fixed = tempfile.mktemp(suffix="_bg.mp4")
        
        # Зацикливаем если видео короче 30 секунд
        result = subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",  # бесконечный loop
            "-i", bg_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-an", "-t", "32", bg_fixed
        ], capture_output=True, timeout=180)
        
        if result.returncode != 0 or not os.path.exists(bg_fixed) or os.path.getsize(bg_fixed) < 10000:
            print(f"⚠️ Pexels processing failed: {result.stderr.decode()[-300:]}")
            bg_fixed = None
        else:
            bg_path = bg_fixed
    else:
        bg_path = None
    
    # Накладываем текст
    video_no_audio = tempfile.mktemp(suffix="_video.mp4")
    
    if bg_path:
        # С живым фоном
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", overlay_png,
            "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-t", "30", "-an", video_no_audio
        ]
    else:
        # Тёмный статичный фон
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x05000f:size=1080x1920:rate=24",
            "-i", overlay_png,
            "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-t", "30", "-an", video_no_audio
        ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=180)
    if result.returncode != 0:
        print(f"❌ Video overlay failed: {result.stderr.decode()[-500:]}")
        raise Exception("Video creation failed")
    
    # Добавляем музыку
    if music_path and os.path.exists(music_path) and os.path.getsize(music_path) > 5000:
        print("🎵 Adding music...")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_no_audio,
            "-stream_loop", "-1",  # зацикливаем музыку если она короткая
            "-i", music_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-af", "volume=0.5,afade=t=in:st=0:d=2,afade=t=out:st=27:d=3",
            "-shortest", "-movflags", "+faststart",
            out_path
        ], capture_output=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print("✅ Video with music ready!")
            return
        else:
            print(f"⚠️ Music add failed: {result.stderr.decode()[-300:]}")
    
    # Без музыки
    import shutil
    shutil.copy(video_no_audio, out_path)
    print("✅ Video ready (no music)")


def upload_youtube(video_path, title, description):
    """Загружает на YouTube"""
    creds = Credentials(
        token=YOUTUBE_TOKEN,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    
    youtube = build("youtube", "v3", credentials=creds)
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["таро", "нумерология", "эзотерика", "гороскоп", "расклад",
                     "shorts", "мистика", "предсказание", "селена"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    response = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    ).execute()
    
    return f"https://youtube.com/shorts/{response['id']}"


def main():
    ct = CONTENT_TYPE
    title = TITLES.get(ct, "🔮 Расклад Таро 🔮")
    card = random.choice(TAROT_CARDS)
    today = datetime.now().strftime("%d.%m.%Y")
    
    prompts = {
        "card": f"Карта Таро дня — {card}. Напиши мистическое послание. МАКСИМУМ 2 КОРОТКИХ предложения. Только русский.",
        "numerology": f"Нумерология на {today}. Укажи число дня и его значение. МАКСИМУМ 2 предложения. Только русский.",
        "tarot": "Расклад Таро: прошлое, настоящее, будущее. МАКСИМУМ 3 предложения по 8-10 слов. Только русский. Мистично.",
        "stars": f"Прогноз звёзд на {today}. МАКСИМУМ 2 предложения. Только русский. Мистично.",
    }
    
    print("[1/5] 📝 Generating text...")
    text = ask_groq(prompts[ct])
    print(f"✅ Text: {text[:60]}...")
    
    print("[2/5] 🎥 Downloading Pexels video...")
    bg = get_pexels_video(ct)
    
    print("[3/5] 🎨 Creating overlay...")
    hook = random.choice(HOOKS)
    overlay = create_overlay(hook, text, title)
    
    print("[4/5] 🎵 Downloading music...")
    music = get_music()
    
    print("[5/5] 🎬 Building final video...")
    out = tempfile.mktemp(suffix=".mp4")
    build_video(bg, overlay, music, out)
    
    size_mb = round(os.path.getsize(out) / 1024 / 1024, 1)
    print(f"✅ Video ready: {size_mb} MB")
    
    yt_title = f"{title} {today} #shorts #таро #нумерология"
    yt_desc = (
        f"{title} на сегодня\n\n"
        "🔮 Хочешь личный расклад?\n"
        "✨ Карта дня БЕСПЛАТНО\n"
        "🔢 Нумерология БЕСПЛАТНО\n"
        "⭐ Натальная карта БЕСПЛАТНО\n\n"
        "👉 Бот Селены: @numer_taro_bot\n\n"
        "#таро #нумерология #эзотерика #гороскоп #расклад "
        "#shorts #мистика #селена"
    )
    
    print("📤 Uploading to YouTube...")
    url = upload_youtube(out, yt_title, yt_desc)
    print(f"🎉 Published: {url}")
    
    # Cleanup
    for f in [bg, overlay, out, music]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass


if __name__ == "__main__":
    main()
