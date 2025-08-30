import logging
import asyncio
from keyboards import get_user_keyboard
from aiogram import types, F
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardMarkup,
    LabeledPrice,
    Message
)
from datetime import datetime
from config import (
    TOKEN, 
    CHANNEL_ID, 
    WELCOME_GIF_URL,
    ADMIN_ID,
    PRICES,
    STARS_PROVIDER_TOKEN,
    ADMIN_IDS,
    MINIAPP_BASE_URL
)
from database import (
    init_db,
    check_user_payment,
    add_payment,
    get_user_data,
    get_vpn_config,
    add_bot_user,
    give_trial_subscription,
    has_trial
)
from payment import create_payment, check_payment_status
from yookassa import Payment
from keyboards import (
    create_main_keyboard,
    get_subscription_keyboard,
    get_payment_check_keyboard
)
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
from admin_panel import register_admin_handlers
dp = Dispatcher()
register_admin_handlers(dp)

def get_price_for_period(period: str) -> int:
    """Возвращает цену для указанного периода"""
    return PRICES.get(period, PRICES['1']) // 100

# Стоимость подписки в звёздах (приблизительная, при необходимости скорректируйте)
STARS_PRICES = {
    '1': 1,   # ~149₽
    '3': 1,   # ~399₽
    '6': 1,   # ~699₽
    '12': 1   # ~999₽
}

def get_stars_price(period: str) -> int:
    """Возвращает количество звёзд для указанного периода"""
    return STARS_PRICES.get(period, STARS_PRICES['1'])

async def check_subscription(user_id: int) -> bool:
    """Проверяет подписку пользователя на канал"""
    try:
        if user_id in ADMIN_IDS:
            return True
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Единственный обработчик команды /start"""
    user = message.from_user
    
    success = await add_bot_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    if success:
        logging.info(f"Пользователь {user.id} ({user.first_name}) добавлен в базу бота")
    else:
        logging.error(f"Ошибка добавления пользователя {user.id} в базу бота")
    
    welcome_text = f"""🌐 <b>Добро Пожаловать в Shard VPN — твой быстрый и надёжный доступ в интернет без границ!</b>

<blockquote><i>Я здесь, чтобы обеспечить тебе свободу в сети и защиту данных.</i></blockquote>
"""
    
    # Триал не выдаем автоматически. Фиксируем только, что триала ещё не было
    try:
        already_has_trial = await has_trial(user.id)
    except Exception:
        already_has_trial = True

    await message.answer_animation(
        animation=WELCOME_GIF_URL,
        caption=welcome_text,
        reply_markup=create_main_keyboard()
    )

    # Для триала всегда показываем оффер с требованием подписки (если триал ещё не выдавался)
    if not already_has_trial:
        await ask_for_subscription(message)

async def ask_for_subscription(message: Message):
    """Показывает предложение получить 14 дней после подписки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data='check_sub')]
    ])
    
    await message.answer(
        text=(
            "<b>🎁 Получите 14 дней бесплатно</b>\n\n"
            "Подпишитесь на наш канал и нажмите «✅ Проверить подписку» — мы автоматически выдадим пробный доступ."
        ),
        reply_markup=keyboard
    )

@dp.callback_query(F.data == 'check_sub')
async def check_subscription_callback(callback: types.CallbackQuery):
    """Проверяет подписку и обновляет интерфейс"""
    if await check_subscription(callback.from_user.id):
        # Выдаем пробную подписку на 14 дней
        try:
            success = await give_trial_subscription(callback.from_user.id, 14)
        except Exception as e:
            success = False
        await callback.message.delete()
        text = "<b>Спасибо за подписку!</b>\n\n"
        if success:
            text += "<b>🎁 Вам выдана пробная подписка на 14 дней.</b>"
        else:
            text += "<b>Не удалось автоматически выдать пробный доступ.</b> Обратитесь в поддержку."
        await callback.message.answer(
            text=text,
            reply_markup=create_main_keyboard(),
            message_effect_id="5046509860389126442"
        )
    else:
        await callback.answer("Вы ещё не подписались на канал!", show_alert=True)

# Стоимость подписки в звёздах (приблизительная, при необходимости скорректируйте)
STARS_PRICES = {
    '1': 1,   # ~149₽
    '3': 1,   # ~399₽
    '6': 1,   # ~699₽
    '12': 1   # ~999₽
}

def get_stars_price(period: str) -> int:
    """Возвращает количество звёзд для указанного периода"""
    return STARS_PRICES.get(period, STARS_PRICES['1'])

async def check_subscription(user_id: int) -> bool:
    """Проверяет подписку пользователя на канал"""
    try:
        if user_id in ADMIN_IDS:
            return True
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = message.from_user
    
    # Записываем пользователя в базу всех пользователей бота
    success = await add_bot_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    if success:
        logging.info(f"Пользователь {user.id} ({user.first_name}) добавлен в базу бота")
    else:
        logging.error(f"Ошибка добавления пользователя {user.id} в базу бота")

    welcome_text = f"""
<b>Привет, {user.first_name}! 👋</b>

<b>🌍 Добро пожаловать в Shard VPN</b> – твой личный защитник от блокировок, слежки и тормозов в сети. С нами ты получаешь свободу, скорость и безопасность каждый день
"""
    
    if await check_subscription(user.id):
        await message.answer_animation(
            animation=WELCOME_GIF_URL,
            caption=welcome_text,
            reply_markup=create_main_keyboard()
        )
    else:
        await message.answer_animation(
            animation=WELCOME_GIF_URL,
            caption=welcome_text
        )
        await ask_for_subscription(message)

async def ask_for_subscription(message: Message):
    """Запрашивает подписку на канал"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_ID[1:]}")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data='check_sub')]
    ])
    
    await message.answer(
        text=(
            "<b>🎁 Получите 14 дней бесплатно</b>\n\n"
            "Подпишитесь на наш канал и нажмите «✅ Проверить подписку» — мы автоматически выдадим пробный доступ."
        ),
        reply_markup=keyboard
    )

@dp.callback_query(F.data == 'check_sub')
async def check_subscription_callback(callback: types.CallbackQuery):
    """Проверяет подписку и обновляет интерфейс"""
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer(
            text="<b>Спасибо за подписку! Приятного пользования!</b>",
            reply_markup=create_main_keyboard(),
            message_effect_id="5046509860389126442"
        )
    else:
        await callback.answer("Вы ещё не подписались на канал!", show_alert=True)

@dp.message(F.text == "🌐Активировать VPN")
async def connect_vpn(message: Message):
    user_id = message.from_user.id
    
    if await check_user_payment(user_id):
        user_data = await get_user_data(user_id)
        if user_data:
            expiry_date, config = user_data
            config_clean = str(config).strip('\"\'')
            vpn_config = f"vless://{config_clean}@146.103.102.21:443?type=tcp&security=reality&pbk=vouH_-SzPyt9HyyX7IuL0QTFppA1F8zkfWUUpLa2NEE&fp=chrome&sni=google.com&sid=47&flow=xtls-rprx-vision#1-a"
            # Кастомная ссылка с конфигом внутри (URL-encoding обязателен)
            encoded_config = quote(vpn_config, safe='')
            miniapp_link = f"{MINIAPP_BASE_URL}/u/{user_id}?config={encoded_config}"
            
            await message.answer(
                text=f"""
<b>🌐 Shard VPN</b>

<b>🔗 Мини-приложение:</b>
<a href="{miniapp_link}">{miniapp_link}</a>

<b>Срок действия:</b> <code>{expiry_date}</code>
<b>Статус:</b> <code>Активна ✅</code>

<blockquote><i>💡 Нажмите "Инструкция" для подключения.</i></blockquote>
""",
                reply_markup=get_user_keyboard(True)  # Используем новую клавиатуру
            )
        else:
            await message.answer("Ошибка получения данных. Попробуйте позже.")
    else:
        await show_subscription_options(message)
                                                
async def show_subscription_options(message: Message):
    """Показывает варианты подписки"""
    await message.answer(
        text="""<b>👨🏻‍💻Чтобы подключиться — выбери подписку:</b>

<blockquote><i>🔐 Быстрый, стабильный и защищённый VPN.</i></blockquote>
""",
        reply_markup=get_subscription_keyboard(),
    )

@dp.callback_query(F.data.startswith('sub_'))
async def subscription_callback(callback: types.CallbackQuery):
    """Обработчик выбора подписки"""
    try:
        period = callback.data.split('_')[1]
        
        payment_info = await create_payment(period, callback.from_user.id)
        if not payment_info:
            await callback.answer("Ошибка при создании платежа", show_alert=True)
            return
        
        # Формируем данные для проверки платежа в виде словаря
        payment_data = {
            'payment_id': payment_info['payment_id'],
            'user_id': callback.from_user.id,
            'message_id': callback.message.message_id,
            'chat_id': callback.message.chat.id,
            'period': payment_info['period']
        }
        
        # Правильный вызов функции с 2 аргументами
        asyncio.create_task(check_payment_status(payment_data, bot))
        
        pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Оплатить ЮKassa",
                url=payment_info['confirmation_url']
            )],
            [InlineKeyboardButton(
                text="🌟 Оплатить Stars",
                callback_data=f"pay_stars_{period}"
            )]
        ])

        await callback.message.edit_text(
            text=f'''<b>Вы выбрали подписку на {period} мес.</b>

<b>Сумма к оплате:</b><code> {get_price_for_period(period)}₽</code>

<blockquote><i>Нажмите кнопку ниже для перехода к оплате:</i></blockquote>

            ''',
            reply_markup=pay_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике подписки: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)

@dp.callback_query(F.data == 'back')
async def back_to_subscriptions(callback: types.CallbackQuery):
    """Возврат к выбору подписки"""
    try:
        await callback.message.edit_text(
            text="""<b>👨🏻‍💻Чтобы подключиться — выбери подписку:</b>

<blockquote><i>🔐 Быстрый, стабильный и защищённый VPN.</i></blockquote>
""",
            reply_markup=get_subscription_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при возврате к подпискам: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
        
@dp.callback_query(F.data.startswith('check_pay:'))
async def check_payment_callback(callback: types.CallbackQuery):
    """Ручная проверка платежа"""
    payment_id = callback.data.split(':')[1]
    
    try:
        payment = await Payment.find_one(payment_id)
        
        if payment.status == "succeeded":
            await callback.answer("Оплата уже подтверждена!", show_alert=True)
        elif payment.status == "pending":
            await callback.answer(
                "Оплата еще не прошла. Попробуйте позже.",
                show_alert=True
            )
        else:
            await callback.answer(
                f"Статус платежа: {payment.status}",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Ошибка проверки платежа: {e}")
        await callback.answer(
            "Ошибка при проверке платежа",
            show_alert=True
        )

@dp.message(F.text == "👾Аккаунт")
async def profile(message: Message):
    """Показывает профиль пользователя"""
    user_id = message.from_user.id
    has_paid = await check_user_payment(user_id)
    status = "активна" if has_paid else "не активна"
    
    if has_paid:
        user_data = await get_user_data(user_id)
        if user_data:
            expiry_date, _ = user_data
            text = f"""
<b>👾 Ваш профиль</b>

<b>Статус подписки:</b><code> активна 🟢</code>
<b>Дата окончания:</b><code> {expiry_date}</code>
"""
        else:
            text = "Ошибка получения данных подписки"
    else:
        text = f"""
<b>👾 Ваш профиль</b>

<b>Статус подписки:</b> <code>не активна 🔴</code>

<blockquote><i>Для подключения VPN оформите подписку.</i></blockquote>
"""
    
    # Создаем клавиатуру с кнопками
    buttons = []
    if not has_paid:
        buttons.append([InlineKeyboardButton(text="💳 Оформить подписку", callback_data='subscribe_from_profile')])
    
    # Добавляем кнопку акции в любом случае
    buttons.append([InlineKeyboardButton(text="🔥 Акция", callback_data='promo_action')])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(text, reply_markup=reply_markup)

@dp.callback_query(F.data == 'promo_action')
async def promo_action_callback(callback: types.CallbackQuery):
    """Обработчик кнопки акции"""
    promo_text = """
🔥 <b>Получите 14 дней VPN бесплатно за сторис в Telegram!</b>

<b>Что нужно сделать:</b>
1. Опубликуйте сторис с нашей реф-ссылкой и одной из готовых картинок.
2. Пришлите скрин в поддержку.
3. Получите 2 недели премиум-доступа бесплатно! 🎁

🔗 <b>Ссылка для сторис:</b> t.me/SHARDPROB_bot

<blockquote><i>📌 Участвовать можно один раз.</i></blockquote>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Получить картинки", callback_data='get_promo_images')],
        [InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/xmakedon")]
    ])
    
    await callback.message.answer(
        text=promo_text,
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == 'get_promo_images')
async def get_promo_images_callback(callback: types.CallbackQuery):
    """Отправляет промо-картинки как файлы для акции"""
    try:
        # Здесь должны быть URL или file_id ваших промо-картинок
        image_urls = [
            "https://wallpapercat.com/w/full/d/c/9/126712-1080x1920-iphone-1080p-game-of-thrones-background.jpg",  # Замените на реальные URL
            "https://wallpapercat.com/w/full/d/c/9/126712-1080x1920-iphone-1080p-game-of-thrones-background.jpg",
            "https://wallpapercat.com/w/full/d/c/9/126712-1080x1920-iphone-1080p-game-of-thrones-background.jpg"
        ]
        
        # Отправляем каждую картинку как документ (файл)
        for i, url in enumerate(image_urls, 1):
            await callback.message.answer_document(
                document=url,
                caption=f"Картинка {i} для акции",
            )
        
        await callback.answer("Файлы с промо-материалами отправлены!")
    except Exception as e:
        logger.error(f"Ошибка отправки промо-файлов: {e}")
        await callback.answer("Произошла ошибка при отправке файлов", show_alert=True)

@dp.callback_query(F.data == 'subscribe_from_profile')
async def subscribe_from_profile(callback: types.CallbackQuery):
    """Обработчик кнопки оформления подписки из профиля"""
    await show_subscription_options(callback.message)
    await callback.answer()

@dp.message(F.text == "🔒О VPN")
async def info(message: Message):
    """Показывает информацию о боте"""
    await message.answer(
        text="""🌐 <b>Shard VPN</b> — быстрый и безопасный интернет без ограничений.

<b>Преимущества:</b>
— ⚡️ Высокая скорость
— 🔒 Полное шифрование
— 🎯 Подключение в 1 клик

<blockquote><i>📩 Вопросы? Напиши в поддержку — мы всегда на связи.</i></blockquote>""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧑‍💻 Поддержка", url="https://t.me/xmakedon")]
        ])
    )

@dp.callback_query(F.data == 'instruction')
async def show_instructions(callback: types.CallbackQuery):
    """Показывает инструкцию по подключению с выбором устройства"""
    devices_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 iOS", callback_data='instruction_ios')],
        [InlineKeyboardButton(text="🤖 Android", callback_data='instruction_android')],
        [InlineKeyboardButton(text="💻 Windows", callback_data='instruction_win')],
        [InlineKeyboardButton(text="🍎 macOS", callback_data='instruction_mac')],
        [InlineKeyboardButton(text="🧑‍💻 Поддержка", url="https://t.me/xmakedon")]
    ])
    
    await callback.message.answer(
        text="""⚡️ <b>Инструкция по подключению</b>

Просто выберите устройство — мы сразу покажем, что делать.""",
        reply_markup=devices_keyboard
    )
    await callback.answer()

@dp.callback_query(F.data.startswith('instruction_'))
async def show_device_instructions(callback: types.CallbackQuery):
    """Показывает инструкцию для конкретного устройства"""
    device = callback.data.split('_')[1]
    user_id = callback.from_user.id
    
    # Получаем конфиг пользователя
    user_data = await get_user_data(user_id)
    if not user_data:
        await callback.answer("Ошибка получения конфигурации", show_alert=True)
        return
    
    expiry_date, config = user_data
    config_clean = str(config).strip('\"\'')
    vpn_config = f"vless://{config_clean}@89.111.142.122:443?security=reality&encryption=none&pbk=HCt07BSW3zdncQ4BFpr33wUxnZ7-WWhGNWHmXV-VsBA&headerType=none&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni=google.com&sid=92643cc23109a57d#ShardVPN"
    encoded_config = quote(vpn_config, safe='')
    miniapp_link = f"{MINIAPP_BASE_URL}/u/{user_id}?config={encoded_config}"
    
    # Создаем клавиатуру с кнопками для приложения
    buttons = []
    
    # Добавляем кнопку скачивания приложения
    if device in ['ios', 'android']:
        app_url = {
            'ios': 'https://apps.apple.com/ru/app/v2raytun/id6448898396',
            'android': 'https://play.google.com/store/apps/details?id=com.v2raytun.app'
        }.get(device)
        
        if app_url:
            buttons.append([InlineKeyboardButton(text="⬇️ Скачать V2RayTun", url=app_url)])
    
    # Добавляем кнопку "Установить VPN" с deep link для открытия приложения
    deep_links = {
        'ios': f"v2raytun://import/{vpn_config}",
        'android': f"v2raytun://import/{vpn_config}",
        'win': f"v2raytun://import/{vpn_config}",
        'mac': f"v2raytun://import/{vpn_config}"
    }
    buttons.append([InlineKeyboardButton(text="🔌 Установить VPN", url=deep_links.get(device, ''))])
    buttons.append([InlineKeyboardButton(text="🔗 Открыть миниапп", url=miniapp_link)])
    
    # Добавляем кнопку поддержки
    buttons.append([InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/xmakedon")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Инструкции для разных устройств
    instructions = {
        'ios': f"""
<b>📱 Инструкция для iOS:</b>

1. Скачайте приложение <b>V2RayTun</b> из App Store
2. Нажмите кнопку "Установить VPN" ниже
3. Разрешите приложению добавить VPN-конфигурацию
4. Включите соединение в приложении

<b>🔗 Мини-приложение:</b>
<a href="{miniapp_link}">{miniapp_link}</a>

<b>Срок действия:</b> <code>{expiry_date}</code>
""",
        'android': f"""
<b>🤖 Инструкция для Android:</b>

1. Скачайте приложение <b>V2RayTun</b> из Play Market
2. Нажмите кнопку "Установить VPN" ниже
3. Разрешите приложению добавить VPN-конфигурацию
4. Включите соединение в приложении

<b>🔗 Мини-приложение:</b>
<a href="{miniapp_link}">{miniapp_link}</a>

<b>Срок действия:</b> <code>{expiry_date}</code>
""",
        'win': f"""
<b>💻 Инструкция для Windows:</b>

1. Скачайте и установите <b>V2RayTun</b> с официального сайта
2. Нажмите кнопку "Установить VPN" ниже
3. Приложение автоматически добавит конфигурацию
4. Включите соединение в программе

<b>🔗 Мини-приложение:</b>
<a href="{miniapp_link}">{miniapp_link}</a>

<b>Срок действия:</b> <code>{expiry_date}</code>
""",
        'mac': f"""
<b>🍎 Инструкция для macOS:</b>

1. Скачайте и установите <b>V2RayTun</b> из App Store
2. Нажмите кнопку "Установить VPN" ниже
3. Приложение автоматически добавит конфигурацию
4. Включите соединение в программе

<b>Конфигурация:</b>
<code>{vpn_config}</code>

<b>🔗 Мини-приложение:</b>
<a href="{miniapp_link}">{miniapp_link}</a>

<b>Срок действия:</b> <code>{expiry_date}</code>
"""
    }
    
    if device in instructions:
        await callback.message.answer(
            text=instructions[device],
            reply_markup=reply_markup
        )
    else:
        await callback.answer("Устройство не найдено", show_alert=True)
    
    await callback.answer()

@dp.callback_query(F.data == 'renew_sub')
async def renew_subscription(callback: types.CallbackQuery):
    """Продление подписки"""
    user_id = callback.from_user.id
    
    # Проверяем, есть ли у пользователя активная подписка
    if await check_user_payment(user_id):
        # Показываем варианты продления
        await callback.message.answer(
            text="""<b>🔒Продли подписку и оставайся в безопасности!</b>

<blockquote><i>Выбери удобный вариант:</i></blockquote>
""",
            reply_markup=get_subscription_keyboard()
        )
    else:
        await callback.answer(
            "У вас нет активной подписки. Оформите новую подписку.",
            show_alert=True
        )
        await show_subscription_options(callback.message)
    
    await callback.answer()

# ----- Обработка оплаты через Telegram Stars -----
@dp.callback_query(F.data.startswith('pay_stars_'))
async def pay_stars_callback(callback: types.CallbackQuery):
    """Отправляет пользователю счёт на оплату в Telegram Stars"""
    period = callback.data.split('_')[2]
    stars_price = get_stars_price(period)
    prices = [LabeledPrice(label=f"{period} мес.", amount=stars_price)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Shard VPN подписка",
        description=f"{period} мес. подписки",
        payload=f"stars_sub_{period}_{callback.from_user.id}",
        provider_token=STARS_PROVIDER_TOKEN,
        currency="XTR",
        prices=prices,
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout: types.PreCheckoutQuery):
    """Подтверждаем подготовительный запрос перед оплатой звёздами"""
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешного платежа через Telegram Stars"""
    payload = message.successful_payment.invoice_payload
    if payload.startswith('stars_sub_'):
        try:
            _, _, period_str, user_id_str = payload.split('_')
            period = int(period_str)
            user_id = int(user_id_str)
        except ValueError:
            period = 1
            user_id = message.from_user.id

        # Определяем, была ли подписка активной до продления
        was_active = await check_user_payment(user_id)

        success = await add_payment(user_id, period)
        if not success:
            await message.answer("Ошибка активации подписки. Обратитесь в поддержку.")
            return

        user_data = await get_user_data(user_id)
        expiry_date = user_data[0] if user_data else "не определена"

        action_word = "продлена" if was_active else "активирована"
        await message.answer(
            text=f"""<b>✅ Оплата успешно выполнена</b>

<b>Ваша подписка на Shard VPN {action_word}!</b>

<b>Срок подписки:</b> {period} мес.
<b>Дата окончания:</b> <code>{expiry_date}</code>

<blockquote><i>🔹 Нажмите «Подключить VPN», чтобы начать пользоваться.</i></blockquote>""",
            message_effect_id="5046509860389126442"
        )
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
