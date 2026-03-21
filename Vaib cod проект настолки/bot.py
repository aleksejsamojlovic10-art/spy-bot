import asyncio
import random
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import aiogram.client.session.aiohttp
from aiogram.client.telegram import TelegramAPIServer
from dotenv import load_dotenv
from aiohttp import web

# Загрузка токена
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создаем сессию для бота
session = aiogram.client.session.aiohttp.AiohttpSession(
    timeout=130,
    api=TelegramAPIServer.from_base('https://api.telegram.org')
)

bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# Хранилище игр
games = {}

# Список локаций
LOCATIONS = [
    "Школа", "Больница", "Ресторан", "Самолет", "Кинотеатр",
    "Пляж", "Космос", "Библиотека", "Стадион", "Банк"
]

#  ВЕБ-СЕРВЕР ДЛЯ MINI APP 

async def handle_game(request):
    """Обрабатывает запрос к странице игры"""
    # Получаем параметры из URL
    chat_id = request.rel_url.query.get('chat_id')
    user_id = request.rel_url.query.get('user_id')
    
    print(f"📱 Открыта игра: chat_id={chat_id}, user_id={user_id}")
    
    html_file = open('templates/game.html', 'r', encoding='utf-8')
    html_content = html_file.read()
    html_file.close()
    return web.Response(text=html_content, content_type='text/html')

async def handle_data(request):
    """Получает данные от Mini App"""
    try:
        data = await request.json()
        print(f"📦 Получены данные от Mini App: {data}")
        return web.Response(text='{"status": "ok"}', content_type='application/json')
    except Exception as e:
        print(f"❌ Ошибка при получении данных: {e}")
        return web.Response(text='{"status": "error"}', content_type='application/json')

# Создаем веб-приложение
app = web.Application()
app.router.add_get('/game', handle_game)  # Страница игры
app.router.add_post('/data', handle_data) # Прием данных

# Функция запуска веб-сервера
async def start_web():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("✅ Веб-сервер запущен на http://localhost:8080")

#  КОМАНДЫ БОТА 

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🕵️ Добро пожаловать в игру Шпион с Mini App!\n\n"
        "Команды:\n"
        "/new_game - создать новую игру\n"
        "/join - присоединиться к игре\n"
        "/play - открыть игровой интерфейс"
    )

@dp.message(Command("new_game"))
async def cmd_new_game(message: types.Message):
    chat_id = message.chat.id
    
    if chat_id in games:
        await message.answer("Игра уже создана! Присоединяйся командой /join")
        return
    
    games[chat_id] = {
        "players": [{
            "id": message.from_user.id,
            "name": message.from_user.first_name,
            "role": None
        }],
        "creator": message.from_user.id,
        "location": None,
        "started": False
    }
    
    await message.answer(
        f"🎮 Игра создана!\n"
        f"Игрок 1: {message.from_user.first_name}\n\n"
        f"Присоединяйтесь: /join\n"
        f"Открыть интерфейс: /play"
    )

@dp.message(Command("join"))
async def cmd_join(message: types.Message):
    chat_id = message.chat.id
    
    if chat_id not in games:
        await message.answer("Сначала создай игру: /new_game")
        return
    
    game = games[chat_id]
    
    if game["started"]:
        await message.answer("Игра уже началась!")
        return
    
    # Проверка не в игре ли уже игрок
    for player in game["players"]:
        if player["id"] == message.from_user.id:
            await message.answer("Ты уже в игре!")
            return
    
    # Добавлить игрока
    game["players"].append({
        "id": message.from_user.id,
        "name": message.from_user.first_name,
        "role": None
    })
    
    await message.answer(
        f"✅ {message.from_user.first_name} присоединился!\n"
        f"Всего игроков: {len(game['players'])}"
    )

@dp.message(Command("play"))
async def cmd_play(message: types.Message):
    """Открывает Mini App"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # HTTPS ССЫЛКА ОТ SERVEO.NET
    web_app_url = f"https://8232de737e86da13-217-116-58-138.serveousercontent.com/game?chat_id={chat_id}&user_id={user_id}"
    
    # кнопка для открытия Web App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 ОТКРЫТЬ ИГРУ",
            web_app=WebAppInfo(url=web_app_url)
        )]
    ])
    
    await message.answer(
        "👇 **Нажми кнопку, чтобы открыть игру!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(Command("end_game"))
async def cmd_end_game(message: types.Message):
    chat_id = message.chat.id
    if chat_id in games:
        del games[chat_id]
        await message.answer("Игра завершена. Можно создать новую: /new_game")

# ЗАПУСК ВСЕГО ВМЕСТЕ 

async def main():
    # Запускаем веб-сервер
    await start_web()
    
    # Запускаем бота
    print("✅ Бот с Mini App запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())