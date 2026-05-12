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

# ── ENV ───────────────────────────────────────────────────────────────────────
GROQ_API_KEY          = os.environ["GROQ_API_KEY"]
PEXELS_API_KEY        = os.environ["PEXELS_API_KEY"]
YOUTUBE_TOKEN         = os.environ["YOUTUBE_TOKEN"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
YOUTUBE_CLIENT_ID     = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
CONTENT_TYPE          = os.environ.get("CONTENT_TYPE", "tarot")

TAROT_CARDS = [
    "Шут","Маг","Верховная Жрица","Императрица","Император",
    "Иерофант","Влюблённые","Колесница","Сила","Отшельник",
    "Колесо Фортуны","Справедливость","Повешенный","Смерть",
    "Умеренность","Дьявол","Башня","Звезда","Луна","Солнце","Суд","Мир"
]

HOOKS = [
    "Это послание пришло именно для тебя...",
    "Вселенная шепчет тебе кое-что важное",
    "Стоп. Это не случайно что ты это видишь",
    "Это знак. Читай до конца",
    "Ты это видишь — значит тебе это нужно",
    "Суд