import time
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === НАСТРОЙКИ ===
TOKEN = "8559767612:AAEOvbHr-an5N8XNhEPsFTcrnLWV-KvuWkM"
SOURCE_CHANNEL_ID = -1003667504372
DEST_CHANNEL_ID = -1002240056200
ADMIN_ID = 7190057517

QUEUE_FILE = "queue.json"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

paused = False
DELAY_SECONDS = 60
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

def is_publish_time():
    return True

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
@dp.channel_post_handler(chat_id=SOURCE_CHANNEL_ID, content_types=types.ContentType.ANY)
async def grab_post(message: types.Message):
    publish_at = time.time() + DELAY_SECONDS

    if message.text:
        queue.append({
            "type": "text",
            "text": message.text,
            "publish_at": publish_at
        })
        print("📥 Текст добавлен")

    elif message.photo:
        queue.append({
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption or "",
            "publish_at": publish_at
        })
        print("📥 Фото добавлено")

    elif message.video:
        queue.append({
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption or "",
            "publish_at": publish_at
        })
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
    asyncio.create_task(publisher())

# === ЗАПУСК ===
if __name__ == "__main__":
    print("🚀 Бот запускается")
    load_queue()
    executor.start_polling(dp, on_startup=on_startup)







