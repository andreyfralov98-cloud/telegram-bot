import time
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from collections import defaultdict

# === НАСТРОЙКИ ===
TOKEN = "8559767612:AAEOvbHr-an5N8XNhEPsFTcrnLWV-KvuWkM"
SOURCE_CHANNEL_ID = -1003667504372
DEST_CHANNEL_ID = -1002240056200
ADMIN_ID = 7190057517

QUEUE_FILE = "queue.json"

queue = []

def save_queue():
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f)


def load_queue():
    global queue

    if os.path.exists(QUEUE_FILE):

        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)

    else:
        queue = []
        
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

paused = False
PUBLISH_HOURS = [6, 9, 12, 15, 18, 21]
DELAY_SECONDS = 10800
PUBLISH_START_HOUR = 6   # с 06:00
PUBLISH_END_HOUR = 24    # до 00:00

# === ЗАГРУЗКА / СОХРАНЕНИЕ ОЧЕРЕДИ ===
def load_queue():
    global queue
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)
            print(f"📂 Очередь загружена: {len(queue)}")
    except FileNotFoundError:
        queue = []
        print("📂 Очередь пуста")

    return queue

def save_queue():
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

queue = load_queue()
print(f"📂 Очередь загружена: {len(queue)}")
media_groups = defaultdict(list)

from datetime import datetime, timedelta

def is_publish_time():
    now = datetime.utcnow() + timedelta(hours=5)
    return 6 <= now.hour < 24

def is_publish_time():
    now = datetime.utcnow() + timedelta(hours=5)
    return 6 <= now.hour < 24


from datetime import datetime, timedelta

def get_next_publish_time():

    now = datetime.utcnow() + timedelta(hours=5)

    for hour in PUBLISH_HOURS:
        publish_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)

        if publish_time > now:
            return publish_time.timestamp()

    next_day = now + timedelta(days=1)
    publish_time = next_day.replace(hour=PUBLISH_HOURS[0], minute=0, second=0, microsecond=0)

    return publish_time.timestamp()

# === МЕНЮ ===
def control_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⏸️ Пауза", callback_data="pause"),
        InlineKeyboardButton("▶️ Продолжить", callback_data="resume"),
        InlineKeyboardButton("📊 Статус", callback_data="status"),
        InlineKeyboardButton("🗑 Очистить очередь", callback_data="clear"),
        InlineKeyboardButton("⏱️ 2 часа", callback_data="delay_2"),
        InlineKeyboardButton("⏱️ 3 часа", callback_data="delay_3"),
        InlineKeyboardButton("⏱️ 4 часа", callback_data="delay_4"),
    )
    return kb

# === ЗАХВАТ ПОСТОВ ===
from collections import defaultdict
media_groups = defaultdict(list)
media_captions = {}

@dp.channel_post_handler(chat_id=SOURCE_CHANNEL_ID, content_types=types.ContentType.ANY)
async def grab_post(message: types.Message):

    publish_at = get_next_publish_time()

    # --- ТЕКСТ ---
    if message.text:
        queue.append({
            "type": "text",
            "text": message.text,
            "publish_at": publish_at
        })

        save_queue()
        print("📥 Текст добавлен")

    elif message.media_group_id:

        media_groups[message.media_group_id].append(message.photo[-1].file_id)

        caption = message.caption if message.caption else ""

    if len(media_groups[message.media_group_id]) >= 2:
        
        queue.append({
            "type": "album",
            "files": media_groups[message.media_group_id],
            "caption": caption,
            "publish_at": publish_at
        })

        save_queue()

        print("📸 Альбом добавлен")

        del media_groups[message.media_group_id]
        
    elif message.photo:

        queue.append({
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption or "",
            "publish_at": publish_at
        })

        save_queue()

        print("📥 Фото добавлено")

    elif message.video:
        queue.append({
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption or "",
            "publish_at": publish_at
        })

        save_queue()
        
        print("📥 Видео добавлено")

    save_queue()

# === ПУБЛИКАТОР (ВАРИАНТ B) ===
async def publisher():
    print("🚀 Публикатор запущен")

    while True:

        if paused:
            await asyncio.sleep(5)
            continue

        if not is_publish_time():
            await asyncio.sleep(300)  # 5 минут
            continue

        now = time.time()
        idx = None

        for i, post in enumerate(queue):
            if post["publish_at"] <= now:
                idx = i
                break

        if idx is not None:
            post = queue.pop(idx)
            save_queue()

            try:
                if post["type"] == "text":
                    await bot.send_message(DEST_CHANNEL_ID, post["text"])

                elif post["type"] == "photo":
                    await bot.send_photo(
                        DEST_CHANNEL_ID,
                        post["file_id"],
                        caption=post.get("caption")
                    )

                elif post["type"] == "video":
                    await bot.send_video(
                        DEST_CHANNEL_ID,
                        post["file_id"],
                        caption=post.get("caption")
                    )
                elif post["type"] == "album":

                    media = []

                    for i, file_id in enumerate(post["files"]):

                        if i == 0:
                            media.append(types.InputMediaPhoto(file_id, caption=post["caption"]))
                        else:
                            media.append(types.InputMediaPhoto(file_id))

                    await bot.send_media_group(DEST_CHANNEL_ID, media)

                print(f"✅ Опубликовано ({post['type']})")

            except Exception as e:
                print("❌ Ошибка публикации:", e)

        await asyncio.sleep(5)

# === МЕНЮ КОМАНДА ===
@dp.message_handler(commands=["menu"])
async def cmd_menu(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.reply("⚙️ Управление:", reply_markup=control_menu())

# === ОБРАБОТКА КНОПОК ===
@dp.callback_query_handler(
    lambda c: c.data in ["pause", "resume", "status"]
)
async def process_menu(callback: types.CallbackQuery):
    global paused

    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    if callback.data == "pause":
        paused = True
        await callback.message.edit_text(
            "⏸️ Пауза",
            reply_markup=control_menu()
        )

    elif callback.data == "resume":
        paused = False
        await callback.message.edit_text(
            "▶️ Продолжено",
            reply_markup=control_menu()
        )

    elif callback.data == "status":
        state = "⏸️ Пауза" if paused else "▶️ Работает"
        await callback.message.edit_text(
            f"📊 Статус: {state}",
            reply_markup=control_menu()
        )

    await callback.answer()

async def on_startup(dp):
    load_queue()
    print(f"📂 Очередь загружена: {len(queue)}")
    asyncio.create_task(publisher())
    await bot.delete_webhook(drop_pending_updates=True)

# === ЗАПУСК ===
if __name__ == "__main__":
    print("🚀 Бот запускается")
    executor.start_polling(dp, on_startup=on_startup)























