import os
import sys
import random
import tempfile
import subprocess
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

GROQ_API_KEY          = os.environ["GROQ_API_KEY"]
PEXELS_API_KEY        = os.environ["PEXELS_API_KEY"]
YOUTUBE_TOKEN         = os.environ["YOUTUBE_TOKEN"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
YOUTUBE_CLIENT_ID     = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
CONTENT_TYPE          = os.environ.get("CONTENT_TYPE", "tarot")

TAROT_RU = [
    "Shut", "Mag", "Verkhovnaya Zhritsa", "Imperatritsa", "Imperator",
    "Ierofant", "Vlyublennye", "Kolesnitsa", "Sila", "Otshelnikh",
    "Koleso Fortuny", "Spravedlivost", "Poveshennyy", "Smert",
    "Umerennost", "Dyavol", "Bashnya", "Zvezda", "Luna", "Solntse",
    "Itogovaya karta", "Mir"
]

HOOKS = [
    "Eto poslanie prishlo imenno dlya tebya...",
    "Vselennaya shepchет tebe koe-chto vazhnoe",
    "Stop. Eto ne sluchayno chto ty eto vidish",
    "Eto znak. Chitay do kontsa",
    "Ty eto vidish — znachit tebe eto nuzhno",
    "Sudba otpravila tebe soobshchenie",
    "Ne listay dalshe. Eto vazhno",
    "Chto skryvaet ot tebya Vselennaya?",
    "Sekret tvoey sudby raskryt",
    "Kosmos poslal tebe eto segodnya",
    "Ostanovis. Vselennaya khochet tebe skazat",
    "Tvoya sudba razvorachivaetsya pryamo seychas",
    "Preduprezhdenie ot zvezd imenno tebe",
    "Portal otkryt. Tvoyo poslanie vnutri",
    "Karty nikogda ne lgut. Osobenno segodnya",
    "Vysshie sily govoryat imenno s toboy",
    "Etot den izmenit vsyo. Smotri vnimatelno",
    "Magiya etogo dnya raskryvaetsya zdes",
    "Arkhangely shepchut tvoyo imya segodnya",
    "Energiya etogo dnya prinadlezhit tebe",
]

PEXELS_QUERIES = {
    "card":       ["tarot cards candles dark", "fortune telling mystical", "magic ritual fog"],
    "numerology": ["sacred geometry light", "mystical numbers universe", "cosmic energy glow"],
    "tarot":      ["tarot reading mystic", "crystal ball magic dark", "witch forest night"],
    "stars":      ["galaxy stars purple", "nebula universe dark", "aurora night sky"],
}

TITLES = {
    "card":       "Karta dnya",
    "numerology": "Numerologiya dnya",
    "tarot":      "Rasklad Taro",
    "stars":      "Poslanie zvezd",
}

TITLE_EMOJIS = {
    "card":       "Karta dnya",
    "numerology": "Numerologiya",
    "tarot":      "Rasklad Taro",
    "stars":      "Poslanie zvezd",
}

MUSIC_TRACKS = [
    "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8c8a73467.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_91b32e02f1.mp3",
    "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bab.mp3",
]


def ask_groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + GROQ_API_KEY,
            "Content-Type": "application/json"
        },
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
    queries = PEXELS_QUERIES.get(content_type, PEXELS_QUERIES["stars"])
    query = random.choice(queries)
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 15}
    )
    videos = r.json().get("videos", [])
    if not videos:
        raise Exception("Pexels: 0 videos for: " + query)
    video = random.choice(videos)
    files = video.get("video_files", [])
    portrait = [f for f in files if f.get("width", 0) < f.get("height", 1)]
    pool = portrait if portrait else files
    pool.sort(key=lambda x: x.get("width", 0))
    url = pool[0]["link"]
    print("Pexels OK: id=" + str(video["id"]) + " query=" + query)
    tmp = tempfile.mktemp(suffix=".mp4")
    with requests.get(url, stream=True, timeout=60) as resp:
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(65536):
                f.write(chunk)
    return tmp


def get_music():
    url = random.choice(MUSIC_TRACKS)
    tmp = tempfile.mktemp(suffix=".mp3")
    try:
        r = requests.get(url, timeout=30, stream=True)
        if r.status_code == 200:
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
            print("Music downloaded OK")
            return tmp
    except Exception as e:
        print("Music download failed: " + str(e))
    print("Generating ambient music via ffmpeg...")
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "aevalsrc=0.3*sin(220*2*PI*t)+0.2*sin(330*2*PI*t)+0.1*sin(110*2*PI*t):s=44100",
        "-t", "32",
        "-af", "volume=0.3,aecho=0.8:0.88:80:0.5,lowpass=f=700",
        tmp
    ]
    r2 = subprocess.run(cmd, capture_output=True, timeout=30)
    if r2.returncode == 0:
        return tmp
    return None


def create_overlay(hook, text, title_text, emoji_label):
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), (8, 4, 22))
    draw = ImageDraw.Draw(img)

    for y in range(H):
        t = y / H
        r = int(8 + t * 25)
        g = int(4 + t * 10)
        b = int(22 + t * 35)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    rng = random.Random(datetime.now().day + datetime.now().month)
    for _ in range(220):
        x = rng.randint(0, W)
        y = rng.randint(0, H // 2)
        s = rng.randint(1, 3)
        br = rng.randint(100, 255)
        draw.ellipse([x - s, y - s, x + s, y + s], fill=(br, br, br))

    for radius in [350, 300, 250]:
        draw.ellipse(
            [W // 2 - radius, H // 2 - radius, W // 2 + radius, H // 2 + radius],
            outline=(80, 20, 120), width=1
        )

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    fp = next((p for p in candidates if os.path.exists(p)), None)

    def fnt(sz):
        if fp:
            return ImageFont.truetype(fp, sz)
        return ImageFont.load_default()

    def wrap(t, n=24):
        words = t.split()
        lines = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 <= n:
                cur = (cur + " " + w).strip()
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def shadow_text(xy, t, font, color, shadow=(0, 0, 0), off=4):
        x, y = xy
        draw.text((x + off, y + off), t, font=font, fill=shadow, anchor="mm")
        draw.text((x, y), t, font=font, fill=color, anchor="mm")

    y = 160
    for line in wrap(hook, 22):
        shadow_text((W // 2, y), line, fnt(70), (255, 220, 50))
        y += 88

    draw.line([(80, y + 15), (W - 80, y + 15)], fill=(180, 80, 255), width=3)
    full_title = emoji_label
    shadow_text((W // 2, y + 70), full_title, fnt(56), (210, 150, 255))
    draw.line([(80, y + 115), (W - 80, y + 115)], fill=(180, 80, 255), width=2)

    ty = y + 185
    for line in wrap(text, 28)[:7]:
        shadow_text((W // 2, ty), line, fnt(46), (255, 245, 255))
        ty += 63
        if ty > H - 430:
            break

    cy = H - 380
    draw.rounded_rectangle(
        [40, cy, W - 40, cy + 320],
        radius=28,
        fill=(10, 0, 38),
        outline=(170, 70, 255),
        width=3
    )
    shadow_text((W // 2, cy + 55), "Besplatnyy rasklad kazhdyy den", fnt(38), (190, 140, 255))
    shadow_text((W // 2, cy + 125), "Karta  Numerologiya  Taro", fnt(36), (220, 200, 255))
    shadow_text((W // 2, cy + 210), "@numer_taro_bot", fnt(48), (255, 215, 60))
    shadow_text((W // 2, cy + 285), "Ssylka v opisanii kanala", fnt(34), (170, 215, 255))

    out = tempfile.mktemp(suffix=".png")
    img.save(out, "PNG")
    return out


def build_video(bg_path, overlay_png, music_path, out_path):
    bg_fixed = tempfile.mktemp(suffix="_fixed.mp4")
    r1 = subprocess.run([
        "ffmpeg", "-y", "-i", bg_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-pix_fmt", "yuv420p", "-an", "-t", "30", bg_fixed
    ], capture_output=True, timeout=120)

    use_bg = r1.returncode == 0 and os.path.exists(bg_fixed) and os.path.getsize(bg_fixed) > 1000

    video_no_audio = tempfile.mktemp(suffix="_text.mp4")
    if use_bg:
        r2 = subprocess.run([
            "ffmpeg", "-y",
            "-i", bg_fixed,
            "-i", overlay_png,
            "-filter_complex",
            "[0:v]format=yuv420p[bg];[1:v]format=rgba[ov];[bg][ov]overlay=0:0,format=yuv420p[out]",
            "-map", "[out]",
            "-t", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "26",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
            video_no_audio
        ], capture_output=True, timeout=120)
        if r2.returncode != 0:
            use_bg = False

    if not use_bg:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x08041a:size=1080x1920:rate=24",
            "-i", overlay_png,
            "-filter_complex",
            "[0:v]format=yuv420p[bg];[1:v]format=rgba[ov];[bg][ov]overlay=0:0,format=yuv420p[out]",
            "-map", "[out]",
            "-t", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "26",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
            video_no_audio
        ], capture_output=True, timeout=120, check=True)

    if music_path and os.path.exists(music_path) and os.path.getsize(music_path) > 1000:
        r3 = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_no_audio,
            "-i", music_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "96k",
            "-af", "volume=0.35,afade=t=in:st=0:d=2,afade=t=out:st=27:d=3",
            "-shortest", "-movflags", "+faststart",
            out_path
        ], capture_output=True, timeout=60)
        if r3.returncode != 0:
            import shutil
            shutil.copy(video_no_audio, out_path)
    else:
        import shutil
        shutil.copy(video_no_audio, out_path)

    for f in [bg_fixed, video_no_audio]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass


def upload_youtube(video_path, title, description):
    creds = Credentials(
        token=YOUTUBE_TOKEN,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": [
                "taro", "numerologiya", "ezoterika", "goroskop",
                "rasklad", "shorts", "kartadnya", "mistika",
                "predskazanie", "selena", "tarolog"
            ],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    resp = yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    return "https://youtube.com/shorts/" + resp["id"]


def main():
    ct = CONTENT_TYPE
    title_text = TITLES.get(ct, "Rasklad Taro")
    emoji_label = TITLE_EMOJIS.get(ct, "Rasklad Taro")
    card = random.choice(TAROT_RU)
    today = datetime.now().strftime("%d.%m.%Y")

    prompts = {
        "card": (
            "Karta Taro dnya — " + card + ". "
            "Napishi misticheskoe poslanie na segodnya. "
            "Maksimum 3 korotkikh predlozheniya. Tolko russkiy yazyk."
        ),
        "numerology": (
            "Numerologicheskoe poslanie na " + today + ". "
            "Ukazi chislo dnya i ego energetiku. "
            "Maksimum 3 predlozheniya. Tolko russkiy yazyk."
        ),
        "tarot": (
            "Rasklad Taro: proshloe, nastoyashchee, budushchee. "
            "Po odnomu predlozheniyu na kazhdoe. "
            "Tolko russkiy yazyk. Mistichno i kratko."
        ),
        "stars": (
            "Energeticheskiy prognoz zvezd na " + today + ". "
            "Maksimum 3 predlozheniya. "
            "Tolko russkiy yazyk. Mistichno."
        ),
    }

    print("[1/5] Generating text...")
    text = ask_groq(prompts[ct])
    print("Text: " + text[:80] + "...")

    print("[2/5] Downloading Pexels video...")
    bg = get_pexels_video(ct)

    print("[3/5] Creating text overlay...")
    hook = random.choice(HOOKS)
    overlay = create_overlay(hook, text, title_text, emoji_label)

    print("[4/5] Getting music...")
    music = get_music()

    print("[5/5] Building video...")
    out = tempfile.mktemp(suffix=".mp4")
    build_video(bg, overlay, music, out)

    size_mb = os.path.getsize(out) / 1024 / 1024
    print("Video size: " + str(round(size_mb, 1)) + " MB")

    yt_title = title_text + " " + today + " shorts taro numerologiya"
    yt_desc = (
        title_text + " na segodnya\n\n"
        "Khochesh lichnyy rasklad?\n"
        "Karta dnya BESPLATNO\n"
        "Numerologiya BESPLATNO\n"
        "Natalnaya karta BESPLATNO\n\n"
        "Bot Seleny v Telegram: @numer_taro_bot\n"
        "Ssylka v opisanii kanala\n\n"
        "#taro #numerologiya #ezoterika #goroskop #rasklad "
        "#shorts #kartadnya #mistika #poslanie #selena #tarolog"
    )

    print("[YouTube] Uploading...")
    url = upload_youtube(out, yt_title, yt_desc)
    print("Uploaded: " + url)

    for f in [bg, overlay, out]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    if music and os.path.exists(music):
        try:
            os.remove(music)
        except Exception:
            pass


if __name__ == "__main__":
    main()
