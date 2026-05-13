# -*- coding: utf-8 -*-
import os
import math
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

# Стили фона — каждый раз разный
VISUAL_STYLES = [
    "cosmic",      # звёзды и туманности
    "particles",   # светящиеся частицы
    "runes",       # руны и символы
    "mandala",     # мандала-орнамент
    "fog",         # туманный мистический
]

MUSIC_TRACKS = [
    "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_91b32e02f1.mp3",
    "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3",
    "https://cdn.pixabay.com/download/audio/2022/08/02/audio_884fe92c21.mp3",
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


def generate_voice(text, out_path):
    """Генерирует женский голос через gTTS (бесплатно)"""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="ru", slow=False)
        tts.save(out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            print("✅ Voice generated (gTTS)")
            return True
    except Exception as e:
        print(f"⚠️ gTTS failed: {e}")

    # Fallback: espeak если gTTS не вышло
    try:
        result = subprocess.run([
            "espeak-ng", "-v", "ru", "-s", "140", "-p", "60",
            "-w", out_path, text
        ], capture_output=True, timeout=30)
        if result.returncode == 0 and os.path.exists(out_path):
            print("✅ Voice generated (espeak-ng)")
            return True
    except Exception as e:
        print(f"⚠️ espeak-ng failed: {e}")

    return False


def get_pexels_video(content_type):
    """Скачивает уникальное живое видео с Pexels"""
    queries = PEXELS_QUERIES.get(content_type, PEXELS_QUERIES["stars"])
    all_videos = []

    for query in queries:
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 30},
                timeout=10
            )
            if r.status_code == 200:
                videos = r.json().get("videos", [])
                videos = [v for v in videos if v.get("duration", 0) >= 10]
                all_videos.extend(videos)
                print(f"📹 Found {len(videos)} videos for '{query}'")
        except Exception as e:
            print(f"⚠️ Query '{query}' failed: {e}")

    if not all_videos:
        return None

    random.shuffle(all_videos)
    video = all_videos[0]
    files = video.get("video_files", [])
    portrait = [f for f in files if f.get("width", 0) <= f.get("height", 1) and f.get("height", 0) >= 720]
    if not portrait:
        portrait = [f for f in files if f.get("height", 0) >= 720]
    if not portrait:
        return None

    portrait.sort(key=lambda x: x.get("height", 0))
    best = portrait[len(portrait) // 2] if len(portrait) > 2 else portrait[0]
    url = best["link"]

    tmp = tempfile.mktemp(suffix=".mp4")
    try:
        with requests.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
        if os.path.getsize(tmp) < 50000:
            return None
        print(f"✅ Pexels: id={video['id']}, duration={video.get('duration')}s")
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


# ─────────────── ГЕНЕРАТОРЫ ФОНОВ ───────────────

def draw_cosmic_bg(draw, W, H, rng):
    """Космический фон: звёзды разных размеров + туманность"""
    # Тёмный фиолетово-синий фон
    for y in range(H):
        t = y / H
        r = int(5 + t * 10)
        g = int(0 + t * 5)
        b = int(20 + t * 30)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Туманность (большой мягкий круг)
    nebula_x = rng.randint(W // 4, 3 * W // 4)
    nebula_y = rng.randint(H // 4, 3 * H // 4)
    nebula_colors = [(80, 20, 120), (20, 40, 100), (60, 10, 80)]
    nc = rng.choice(nebula_colors)
    for radius in range(300, 50, -30):
        alpha = int(15 + (300 - radius) * 0.1)
        draw.ellipse([nebula_x - radius, nebula_y - radius,
                      nebula_x + radius, nebula_y + radius],
                     fill=(*nc, min(alpha, 60)))

    # Звёзды
    for _ in range(300):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        size = rng.choices([1, 2, 3], weights=[70, 25, 5])[0]
        brightness = rng.randint(150, 255)
        color_r = rng.choice([(brightness, brightness, brightness),
                               (brightness, brightness - 30, brightness + 20),
                               (brightness - 20, brightness - 20, brightness)])
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(*color_r, rng.randint(180, 255)))


def draw_particles_bg(draw, W, H, rng):
    """Светящиеся частицы на тёмном фоне"""
    for y in range(H):
        draw.line([(0, y), (W, y)], fill=(2, 0, 15, 255))

    # Большие светящиеся шары (bokeh)
    bokeh_colors = [(100, 0, 200), (0, 100, 200), (150, 0, 150), (50, 0, 180)]
    for _ in range(8):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        r = rng.randint(60, 180)
        bc = rng.choice(bokeh_colors)
        for dr in range(r, 0, -15):
            alpha = int(5 + (r - dr) * 0.3)
            draw.ellipse([x - dr, y - dr, x + dr, y + dr],
                         fill=(*bc, min(alpha, 40)))

    # Маленькие частицы
    for _ in range(200):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        size = rng.randint(1, 4)
        colors = [(180, 100, 255), (100, 180, 255), (255, 150, 255), (150, 255, 255)]
        c = rng.choice(colors)
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(*c, rng.randint(150, 230)))

    # Линии-связи между частицами
    points = [(rng.randint(0, W), rng.randint(0, H)) for _ in range(15)]
    for i, p1 in enumerate(points):
        for p2 in points[i + 1:]:
            dist = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
            if dist < 200:
                alpha = int(80 * (1 - dist / 200))
                draw.line([p1, p2], fill=(150, 100, 255, alpha), width=1)


def draw_runes_bg(draw, W, H, rng):
    """Руны и мистические символы"""
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=(int(8 + t * 5), int(3 + t * 3), int(15 + t * 10), 255))

    # Символы/руны по всему фону
    rune_symbols = ["ᚠ", "ᚢ", "ᚦ", "ᚨ", "ᚱ", "ᚲ", "ᚷ", "ᚹ", "ᚺ",
                    "ᚾ", "ᛁ", "ᛃ", "ᛇ", "ᛈ", "ᛉ", "ᛊ", "ᛏ", "ᛒ",
                    "ᛖ", "ᛗ", "ᛚ", "ᛜ", "ᛞ", "ᛟ",
                    "✦", "✧", "⬡", "⬢", "◈", "⊕"]

    try:
        font_rune = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        font_rune = ImageFont.load_default()

    for _ in range(40):
        x = rng.randint(20, W - 20)
        y = rng.randint(20, H - 20)
        sym = rng.choice(rune_symbols)
        alpha = rng.randint(30, 100)
        draw.text((x, y), sym, font=font_rune, fill=(180, 100, 255, alpha))

    # Пентаграмма в центре
    cx, cy = W // 2, H // 2
    for radius in [350, 300, 250]:
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     outline=(100, 40, 180, 60), width=2)


def draw_mandala_bg(draw, W, H, rng):
    """Мандала — повторяющийся геометрический орнамент"""
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=(int(3 + t * 8), int(0 + t * 5), int(18 + t * 15), 255))

    cx, cy = W // 2, H // 2
    colors = [(120, 40, 220), (80, 20, 180), (160, 60, 255), (200, 100, 255)]

    # Концентрические узоры
    for i, r in enumerate(range(80, 500, 60)):
        c = colors[i % len(colors)]
        alpha = max(20, 80 - i * 8)
        # Основной круг
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*c, alpha), width=2)
        # Лепестки
        petals = 8 + (i % 3) * 4
        for j in range(petals):
            angle = (2 * math.pi * j) / petals
            x1 = cx + int((r - 30) * math.cos(angle))
            y1 = cy + int((r - 30) * math.sin(angle))
            x2 = cx + int(r * math.cos(angle))
            y2 = cy + int(r * math.sin(angle))
            draw.line([x1, y1, x2, y2], fill=(*c, alpha), width=2)

    # Звёздный орнамент (второй центр — смещённый)
    cx2, cy2 = W // 2, H // 4
    for r in range(40, 200, 40):
        draw.ellipse([cx2 - r, cy2 - r, cx2 + r, cy2 + r],
                     outline=(200, 150, 255, 40), width=1)


def draw_fog_bg(draw, W, H, rng):
    """Туманный мистический фон"""
    for y in range(H):
        t = y / H
        r = int(10 + t * 20)
        g = int(5 + t * 10)
        b = int(25 + t * 40)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

    # Слои тумана
    fog_colors = [(60, 20, 100), (40, 10, 80), (80, 30, 120), (30, 15, 70)]
    for layer in range(6):
        x = rng.randint(-200, W)
        y = rng.randint(0, H)
        rw = rng.randint(300, 700)
        rh = rng.randint(100, 300)
        fc = rng.choice(fog_colors)
        for dr in range(rh, 0, -20):
            alpha = int(5 + (rh - dr) * 0.15)
            scale = dr / rh
            draw.ellipse([x - int(rw * scale), y - dr, x + int(rw * scale), y + dr],
                         fill=(*fc, min(alpha, 35)))

    # Звёзды сквозь туман
    for _ in range(100):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H // 2)
        ss = rng.randint(1, 2)
        draw.ellipse([sx - ss, sy - ss, sx + ss, sy + ss],
                     fill=(200, 200, 255, rng.randint(100, 200)))


def create_background_image(style, W=1080, H=1920):
    """Создаёт уникальный фоновый PNG в заданном стиле"""
    rng = random.Random(datetime.now().timestamp())
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    if style == "cosmic":
        draw_cosmic_bg(draw, W, H, rng)
    elif style == "particles":
        draw_particles_bg(draw, W, H, rng)
    elif style == "runes":
        draw_runes_bg(draw, W, H, rng)
    elif style == "mandala":
        draw_mandala_bg(draw, W, H, rng)
    else:  # fog
        draw_fog_bg(draw, W, H, rng)

    out = tempfile.mktemp(suffix="_bg.png")
    img.save(out, "PNG")
    return out


def create_overlay(hook, text, title):
    """
    Создаёт прозрачный PNG с текстом.
    Фон почти полностью прозрачный — чтобы видео Pexels просвечивало.
    """
    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Лёгкий затемняющий градиент (НЕ непрозрачный)
    for y in range(H):
        t = y / H
        # Сильнее затемняем верх и низ (где текст), середину — светлее
        if t < 0.35 or t > 0.60:
            alpha = 140
        else:
            alpha = 50
        draw.line([(0, y), (W, y)], fill=(5, 0, 20, alpha))

    # Звёзды (немного)
    rng = random.Random(datetime.now().day + datetime.now().hour)
    for _ in range(80):
        x = rng.randint(0, W)
        y = rng.randint(0, H // 3)
        s = rng.randint(1, 2)
        br = rng.randint(180, 255)
        draw.ellipse([x - s, y - s, x + s, y + s], fill=(br, br, br, 180))

    # Декоративные круги (тонкие, не забивают видео)
    cx = W // 2
    for radius, alpha in [(380, 60), (330, 50), (280, 40)]:
        draw.ellipse([cx - radius, 550 - radius, cx + radius, 550 + radius],
                     outline=(150, 80, 255, alpha), width=2)

    # Шрифт
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    font_path = next((p for p in font_paths if os.path.exists(p)), None)

    def font(size):
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

    def wrap_text(t, max_chars=22):
        words = t.split()
        lines, current = [], ""
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

    def shadow_text(xy, txt, fnt, color, offset=4):
        x, y = xy
        # Тень
        draw.text((x + offset, y + offset), txt, font=fnt, fill=(0, 0, 0, 200), anchor="mm")
        # Основной текст
        draw.text((x, y), txt, font=fnt, fill=color, anchor="mm")

    # ХУК сверху (полупрозрачный блок)
    hook_lines = wrap_text(hook, 22)
    hook_h = len(hook_lines) * 85 + 40
    draw.rounded_rectangle([30, 60, W - 30, 60 + hook_h], radius=20,
                            fill=(5, 0, 30, 160), outline=(180, 80, 255, 180), width=2)
    y = 115
    for line in hook_lines:
        shadow_text((W // 2, y), line, font(64), (255, 220, 50, 255))
        y += 85

    # Разделитель
    draw.line([(80, y + 20), (W - 80, y + 20)], fill=(200, 100, 255, 200), width=3)

    # ЗАГОЛОВОК
    shadow_text((W // 2, y + 75), title, font(52), (220, 160, 255, 255))

    # Линия
    draw.line([(80, y + 120), (W - 80, y + 120)], fill=(200, 100, 255, 200), width=2)

    # ОСНОВНОЙ ТЕКСТ — светлый, читаемый, с тёмной подложкой
    text_lines = wrap_text(text, 24)[:5]
    ty_start = y + 160
    text_block_h = len(text_lines) * 80 + 30
    draw.rounded_rectangle([30, ty_start - 20, W - 30, ty_start + text_block_h],
                            radius=20, fill=(5, 0, 30, 150))
    ty = ty_start + 30
    for line in text_lines:
        shadow_text((W // 2, ty), line, font(54), (255, 250, 245, 255))
        ty += 80

    # CTA блок снизу
    cy = H - 490
    draw.rounded_rectangle([30, cy, W - 30, cy + 330],
                            radius=30, fill=(10, 0, 40, 210),
                            outline=(180, 80, 255, 200), width=3)
    shadow_text((W // 2, cy + 55), "✨ Бесплатный расклад каждый день", font(40), (200, 150, 255, 255))
    shadow_text((W // 2, cy + 125), "Карта • Нумерология • Таро", font(38), (220, 200, 255, 255))
    shadow_text((W // 2, cy + 210), "@numer_taro_bot", font(52), (255, 215, 60, 255))
    shadow_text((W // 2, cy + 280), "Ссылка в описании канала", font(34), (180, 220, 255, 255))

    out = tempfile.mktemp(suffix=".png")
    img.save(out, "PNG")
    return out


def build_video(bg_video_path, bg_image_path, overlay_png, music_path, voice_path, out_path):
    """
    Собирает финальное видео:
    - Если есть Pexels видео → оно фоном (живое)
    - Иначе → анимированный PNG фон (случайный стиль)
    - Поверх прозрачный оверлей с текстом
    - Женский голос + фоновая музыка
    """

    # ── 1. Подготавливаем видео-фон ──
    if bg_video_path and os.path.exists(bg_video_path):
        print("🎬 Processing Pexels video background...")
        bg_fixed = tempfile.mktemp(suffix="_bgfixed.mp4")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg_video_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-an", "-t", "32",
            bg_fixed
        ], capture_output=True, timeout=180)

        if result.returncode == 0 and os.path.exists(bg_fixed) and os.path.getsize(bg_fixed) > 10000:
            active_bg = bg_fixed
            bg_input_args = ["-i", active_bg]
            bg_filter = "[0:v]"
        else:
            print(f"⚠️ Pexels processing failed, using image background")
            bg_video_path = None

    if not bg_video_path:
        # Анимируем PNG — лёгкое движение (масштаб)
        bg_input_args = ["-loop", "1", "-i", bg_image_path]
        bg_filter = "[0:v]scale=1140:2030,zoompan=z='min(zoom+0.0005,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=750:s=1080x1920:fps=24,"

    # ── 2. Накладываем оверлей ──
    video_no_audio = tempfile.mktemp(suffix="_va.mp4")

    if bg_video_path:
        # Живой Pexels фон
        cmd = [
            "ffmpeg", "-y",
            "-i", active_bg,
            "-i", overlay_png,
            "-filter_complex", "[0:v][1:v]overlay=0:0,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-t", "30", "-an", video_no_audio
        ]
    else:
        # Анимированный PNG фон с зумом
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", bg_image_path,
            "-i", overlay_png,
            "-filter_complex",
            "[0:v]scale=1140:2030,zoompan=z='min(zoom+0.0005,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=750:s=1080x1920:fps=24[bgz];"
            "[bgz][1:v]overlay=0:0,format=yuv420p[out]",
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-t", "30", "-an", video_no_audio
        ]

    result = subprocess.run(cmd, capture_output=True, timeout=300)
    if result.returncode != 0:
        print(f"❌ Video overlay failed: {result.stderr.decode()[-500:]}")
        raise Exception("Video creation failed")

    # ── 3. Микшируем аудио: голос + музыка ──
    audio_inputs = []
    audio_filter = ""
    has_voice = voice_path and os.path.exists(voice_path) and os.path.getsize(voice_path) > 1000
    has_music = music_path and os.path.exists(music_path) and os.path.getsize(music_path) > 5000

    if has_voice and has_music:
        print("🎵🗣️ Mixing voice + music...")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_no_audio,
            "-stream_loop", "-1", "-i", music_path,
            "-i", voice_path,
            "-filter_complex",
            # Музыка тихо на фоне, голос громко
            "[1:a]volume=0.25,afade=t=in:st=0:d=1,afade=t=out:st=27:d=3[music];"
            "[2:a]volume=1.8,adelay=1500|1500[voice];"
            "[music][voice]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", out_path
        ], capture_output=True, timeout=120)

        if result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            print("✅ Video with voice + music ready!")
            return
        else:
            print(f"⚠️ Mix failed: {result.stderr.decode()[-300:]}")

    elif has_voice:
        print("🗣️ Adding voice only...")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_no_audio,
            "-i", voice_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-af", "volume=1.8,adelay=1500|1500",
            "-shortest", "-movflags", "+faststart", out_path
        ], capture_output=True, timeout=120)
        if result.returncode == 0:
            print("✅ Video with voice ready!")
            return

    elif has_music:
        print("🎵 Adding music only...")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_no_audio,
            "-stream_loop", "-1", "-i", music_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-af", "volume=0.5,afade=t=in:st=0:d=2,afade=t=out:st=27:d=3",
            "-shortest", "-movflags", "+faststart", out_path
        ], capture_output=True, timeout=120)
        if result.returncode == 0:
            print("✅ Video with music ready!")
            return

    # Без аудио
    import shutil
    shutil.copy(video_no_audio, out_path)
    print("✅ Video ready (no audio)")


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
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    response = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    ).execute()
    return f"https://youtube.com/shorts/{response['id']}"


def main():
    ct = CONTENT_TYPE
    title = TITLES.get(ct, "🔮 Расклад Таро 🔮")
    card = random.choice(TAROT_CARDS)
    today = datetime.now().strftime("%d.%m.%Y")

    # Случайный визуальный стиль — каждое видео уникально
    style = random.choice(VISUAL_STYLES)
    print(f"🎨 Visual style: {style}")

    prompts = {
        "card": f"Карта Таро дня — {card}. Напиши мистическое послание на русском. МАКСИМУМ 2 коротких предложения. Без вступлений.",
        "numerology": f"Нумерология на {today}. Укажи число дня и его мистическое значение. МАКСИМУМ 2 предложения. Только русский.",
        "tarot": "Расклад Таро: прошлое, настоящее, будущее. МАКСИМУМ 3 предложения по 8-10 слов. Только русский. Мистично.",
        "stars": f"Послание звёзд на {today}. МАКСИМУМ 2 предложения. Только русский. Мистично и загадочно.",
    }

    print("[1/6] 📝 Generating text...")
    text = ask_groq(prompts[ct])
    print(f"✅ Text: {text[:80]}...")

    print("[2/6] 🗣️ Generating voice...")
    voice_path = tempfile.mktemp(suffix=".mp3")
    voice_ok = generate_voice(text, voice_path)
    if not voice_ok:
        voice_path = None

    print("[3/6] 🎥 Downloading Pexels video...")
    bg_video = get_pexels_video(ct)

    print(f"[4/6] 🎨 Creating background (style: {style})...")
    bg_image = create_background_image(style)

    print("[5/6] 🖼️ Creating text overlay...")
    hook = random.choice(HOOKS)
    overlay = create_overlay(hook, text, title)

    print("[5b/6] 🎵 Downloading music...")
    music = get_music()

    print("[6/6] 🎬 Building final video...")
    out = tempfile.mktemp(suffix=".mp4")
    build_video(bg_video, bg_image, overlay, music, voice_path, out)

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
    for f in [bg_video, bg_image, overlay, out, music, voice_path]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass


if __name__ == "__main__":
    main()
