# Исправленная админ панель для VPN бота с поддержкой медиа в рассылке
import logging
import asyncio
from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import ADMIN_ID, DB_PATH
import aiosqlite
from datetime import datetime, timedelta
from database import (
    get_user_stats, 
    get_payment_stats, 
    get_users_by_status, 
    find_user_by_id,
    extend_user_subscription,
    delete_user,
    block_user,
    unblock_user,
    give_user_subscription,
    deactivate_user_subscription,
    activate_user_subscription
)

# Список ID администраторов
ADMIN_IDS = [ADMIN_ID, 2057750889]  # Добавьте нужные ID

# Состояния для админ панели
admin_states = {}

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

def get_admin_main_keyboard():
    """Главная клавиатура админ панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="🔧 Управление", callback_data="admin_manage"),
            InlineKeyboardButton(text="📋 Логи", callback_data="admin_logs")
        ],
        [
            InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")
        ]
    ])

async def get_admin_stats():
    """Получает базовую статистику для админ панели"""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            # Всего пользователей бота (кто запускал /start)
            cursor = await conn.execute("SELECT COUNT(*) FROM bot_users")
            result = await cursor.fetchone()
            total_users = result[0] if result else 0
            
            # Получаем всех пользователей с подписками
            cursor = await conn.execute(
                "SELECT user_id, subscribed, expiry_date FROM users"
            )
            all_vpn_users = await cursor.fetchall()
            
            active_subs = 0
            
            # Программно проверяем активные подписки
            if all_vpn_users:
                for user_id, subscribed, expiry_date in all_vpn_users:
                    if subscribed and expiry_date and is_subscription_active_check(expiry_date):
                        active_subs += 1
            
            # Новые за сегодня (кто запустил бота)
            today = datetime.now().strftime('%d.%m.%Y')
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM bot_users WHERE first_interaction LIKE ?",
                (f"{today}%",)
            )
            result = await cursor.fetchone()
            new_today = result[0] if result else 0
            
            # Доход за месяц
            try:
                payment_stats = await get_payment_stats()
                monthly_revenue = payment_stats.get('revenue_month', 0)
            except:
                monthly_revenue = 0
        
        return {
            'total_users': total_users,
            'active_subs': active_subs,
            'monthly_revenue': monthly_revenue,
            'new_today': new_today
        }
    except Exception as e:
        logging.error(f"Ошибка получения статистики: {e}")
        return {
            'total_users': 0,
            'active_subs': 0,
            'monthly_revenue': 0,
            'new_today': 0
        }

async def get_detailed_stats():
    """Получает подробную статистику"""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            # Всего пользователей бота
            cursor = await conn.execute("SELECT COUNT(*) FROM bot_users")
            result = await cursor.fetchone()
            total_users = result[0] if result else 0
            
            # Получаем всех пользователей с подписками для программной проверки
            cursor = await conn.execute(
                "SELECT user_id, subscribed, payment_date, expiry_date FROM users"
            )
            all_vpn_users = await cursor.fetchall()
            
            active_subs = 0
            expired_subs = 0
            
            if all_vpn_users:
                for user_id, subscribed, payment_date, expiry_date in all_vpn_users:
                    # Проверяем активность подписки
                    if subscribed and expiry_date:
                        if is_subscription_active_check(expiry_date):
                            active_subs += 1
                        else:
                            expired_subs += 1
            
            # Новые за сегодня (кто запустил бота)
            today = datetime.now().strftime('%d.%m.%Y')
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM bot_users WHERE first_interaction LIKE ?",
                (f"{today}%",)
            )
            result = await cursor.fetchone()
            new_today = result[0] if result else 0
            
            # Новые за неделю (кто запустил бота)
            cursor = await conn.execute("SELECT user_id, first_interaction FROM bot_users")
            all_bot_users = await cursor.fetchall()
            
            new_week = 0
            if all_bot_users:
                week_ago = datetime.now() - timedelta(days=7)
                
                for user_id, first_interaction in all_bot_users:
                    if first_interaction:
                        try:
                            formats = ['%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
                            for fmt in formats:
                                try:
                                    interaction_date = datetime.strptime(first_interaction, fmt)
                                    if interaction_date >= week_ago:
                                        new_week += 1
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
        
        # Получаем статистику платежей
        try:
            payment_stats = await get_payment_stats()
        except:
            payment_stats = {
                'revenue_today': 0,
                'revenue_week': 0,
                'revenue_month': 0,
                'avg_payment': 0,
                'subs_1m': 0,
                'subs_3m': 0,
                'subs_6m': 0,
                'subs_12m': 0
            }
        
        return {
            'total_users': total_users,
            'active_subs': active_subs,
            'expired_subs': expired_subs,
            'new_today': new_today,
            'new_week': new_week,
            'revenue_today': payment_stats.get('revenue_today', 0),
            'revenue_week': payment_stats.get('revenue_week', 0),
            'revenue_month': payment_stats.get('revenue_month', 0),
            'avg_payment': payment_stats.get('avg_payment', 0),
            'subs_1m': payment_stats.get('subs_1m', 0),
            'subs_3m': payment_stats.get('subs_3m', 0),
            'subs_6m': payment_stats.get('subs_6m', 0),
            'subs_12m': payment_stats.get('subs_12m', 0)
        }
    except Exception as e:
        logging.error(f"Ошибка получения детальной статистики: {e}")
        return {
            'total_users': 0,
            'active_subs': 0,
            'expired_subs': 0,
            'new_today': 0,
            'new_week': 0,
            'revenue_today': 0,
            'revenue_week': 0,
            'revenue_month': 0,
            'avg_payment': 0,
            'subs_1m': 0,
            'subs_3m': 0,
            'subs_6m': 0,
            'subs_12m': 0
        }

def is_subscription_active_check(expiry_date_str: str) -> bool:
    """Проверяет активность подписки с поддержкой разных форматов"""
    if not expiry_date_str:
        return False
    
    try:
        formats = ['%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
        for fmt in formats:
            try:
                expiry_date = datetime.strptime(expiry_date_str, fmt)
                return datetime.now() < expiry_date
            except ValueError:
                continue
        return False
    except Exception as e:
        logging.error(f"Ошибка проверки даты {expiry_date_str}: {e}")
        return False

async def send_broadcast_message(bot, message_text: str = None, target_type: str = "all", photo_url: str = None):
    """Отправляет рассылку пользователям с поддержкой фото"""
    try:
        # Получаем список пользователей в зависимости от типа
        if target_type == "all":
            query = "SELECT user_id FROM bot_users"  # Всем пользователям бота
        elif target_type == "active":
            query = """SELECT user_id FROM users 
                       WHERE subscribed = 1"""
        elif target_type == "inactive":
            query = """SELECT user_id FROM bot_users 
                       WHERE user_id NOT IN (
                           SELECT user_id FROM users WHERE subscribed = 1
                       )"""
        elif target_type == "expiring":
            query = """SELECT user_id FROM users 
                       WHERE subscribed = 1"""
        else:
            return {"success": 0, "failed": 0, "blocked": 0}
        
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute(query)
            users = await cursor.fetchall()
        
        # Дополнительная фильтрация для активных и истекающих
        if target_type == "active":
            filtered_users = []
            for (user_id,) in users:
                # Проверяем активность подписки
                cursor = await conn.execute(
                    "SELECT expiry_date FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                if row and row[0] and is_subscription_active_check(row[0]):
                    filtered_users.append((user_id,))
            users = filtered_users
        elif target_type == "expiring":
            filtered_users = []
            for (user_id,) in users:
                cursor = await conn.execute(
                    "SELECT expiry_date FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                if row and row[0]:
                    try:
                        formats = ['%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
                        for fmt in formats:
                            try:
                                exp_date = datetime.strptime(row[0], fmt)
                                days_left = (exp_date - datetime.now()).days
                                if 0 <= days_left <= 3:
                                    filtered_users.append((user_id,))
                                break
                            except ValueError:
                                continue
                    except:
                        pass
            users = filtered_users
        
        success_count = 0
        failed_count = 0
        blocked_count = 0
        
        for (user_id,) in users:
            try:
                if photo_url:
                    # Отправляем фото с подписью
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=photo_url,
                        caption=message_text,
                        parse_mode="HTML"
                    )
                else:
                    # Отправляем только текст
                    await bot.send_message(
                        chat_id=user_id,
                        text=message_text,
                        parse_mode="HTML"
                    )
                success_count += 1
                
                # Небольшая задержка чтобы не превысить лимиты API
                await asyncio.sleep(0.05)
                
            except Exception as e:
                if "blocked" in str(e).lower() or "forbidden" in str(e).lower():
                    blocked_count += 1
                else:
                    failed_count += 1
                logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        
        return {
            "success": success_count,
            "failed": failed_count,
            "blocked": blocked_count,
            "total": len(users)
        }
    except Exception as e:
        logging.error(f"Ошибка рассылки: {e}")
        return {"success": 0, "failed": 0, "blocked": 0}

def register_admin_handlers(dp):
    """Регистрирует обработчики админ панели"""
    
    @dp.message(Command("admin"))
    async def admin_command(message: Message):
        """Обработчик команды /admin"""
        if not is_admin(message.from_user.id):
            await message.answer("❌ У вас нет прав доступа к админ панели.")
            return
        
        stats = await get_admin_stats()
        
        admin_text = f"""
<b>🔧 Админ панель Shard VPN</b>

<b>📊 Быстрая статистика:</b>
• Всего пользователей: <code>{stats['total_users']}</code>
• Активных подписок: <code>{stats['active_subs']}</code>
• Доход за месяц: <code>{stats['monthly_revenue']}₽</code>
• Новых за сегодня: <code>{stats['new_today']}</code>

<b>🕐 Время:</b> <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>
"""
        
        await message.answer(
            text=admin_text,
            reply_markup=get_admin_main_keyboard()
        )
    
    @dp.callback_query(F.data == "admin_stats")
    async def admin_stats_callback(callback: types.CallbackQuery):
        """Обработчик статистики"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        stats = await get_detailed_stats()
        
        stats_text = f"""
<b>📊 Подробная статистика</b>

<b>👥 Пользователи:</b>
• Всего пользователей бота: <code>{stats['total_users']}</code>
• Активных подписок: <code>{stats['active_subs']}</code>
• Истекших подписок: <code>{stats['expired_subs']}</code>
• Новых за сегодня: <code>{stats['new_today']}</code>
• Новых за неделю: <code>{stats['new_week']}</code>

<b>💰 Финансы:</b>
• Доход за сегодня: <code>{stats['revenue_today']}₽</code>
• Доход за неделю: <code>{stats['revenue_week']}₽</code>
• Доход за месяц: <code>{stats['revenue_month']}₽</code>
• Средний чек: <code>{stats['avg_payment']}₽</code>

<b>📈 Подписки по периодам:</b>
• 1 месяц: <code>{stats['subs_1m']}</code>
• 3 месяца: <code>{stats['subs_3m']}</code>
• 6 месяцев: <code>{stats['subs_6m']}</code>
• 12 месяцев: <code>{stats['subs_12m']}</code>
"""
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")]
        ])
        
        await callback.message.edit_text(
            text=stats_text,
            reply_markup=back_keyboard
        )
    
    @dp.callback_query(F.data == "admin_users")
    async def admin_users_callback(callback: types.CallbackQuery):
        """Обработчик управления пользователями"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        user_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_find_user"),
                InlineKeyboardButton(text="🎁 Выдать подписку", callback_data="admin_give_subscription")
            ],
            [
                InlineKeyboardButton(text="📋 Список активных", callback_data="admin_active_users"),
                InlineKeyboardButton(text="⏰ Истекающие подписки", callback_data="admin_expiring")
            ],
            [
                InlineKeyboardButton(text="❌ Истекшие подписки", callback_data="admin_expired"),
                InlineKeyboardButton(text="👥 Все пользователи бота", callback_data="admin_all_bot_users")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")
            ]
        ])
        
        await callback.message.edit_text(
            text="<b>👥 Управление пользователями</b>\n\nВыберите действие:",
            reply_markup=user_keyboard
        )
    
    @dp.callback_query(F.data == "admin_find_user")
    async def admin_find_user_callback(callback: types.CallbackQuery):
        """Поиск пользователя"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        admin_states[callback.from_user.id] = "waiting_user_id"
        
        await callback.message.edit_text(
            text="<b>🔍 Поиск пользователя</b>\n\nОтправьте ID пользователя для поиска:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
            ])
        )
    
    # ИСПРАВЛЕННЫЙ обработчик - только для админов и только в состоянии поиска
    @dp.message(F.text.regexp(r'^\d+$') & F.from_user.id.in_(ADMIN_IDS))
    async def handle_user_id_input(message: Message):
        """Обработка ввода ID пользователя - ТОЛЬКО для админов"""
        state_value = admin_states.get(message.from_user.id)
        if state_value not in ("waiting_user_id", "waiting_user_id_for_subscription"):
            # Не в нужном состоянии — просто выходим, чтобы отработали обычные хендлеры бота
            return
        if state_value == "waiting_user_id":
            user_id = int(message.text)
            user_data = await find_user_by_id(user_id)
            
            if user_data:
                user_id, subscribed, payment_date, expiry_date, config, last_update = user_data
                
                # Проверяем активность подписки
                is_active = False
                if expiry_date:
                    try:
                        formats = ['%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
                        for fmt in formats:
                            try:
                                exp_date = datetime.strptime(expiry_date, fmt)
                                is_active = exp_date > datetime.now()
                                break
                            except ValueError:
                                continue
                    except:
                        pass
                
                status = "🟢 Активна" if is_active else "🔴 Неактивна"
                
                user_info = f"""
<b>👤 Информация о пользователе</b>

<b>ID:</b> <code>{user_id}</code>
<b>Подписка:</b> {status}
<b>Дата платежа:</b> <code>{payment_date or 'Не указана'}</code>
<b>Дата окончания:</b> <code>{expiry_date or 'Не указана'}</code>
<b>Конфиг:</b> <code>{config[:20] + '...' if config else 'Отсутствует'}</code>
<b>Последнее обновление:</b> <code>{last_update or 'Не указано'}</code>
"""
                
                # Определяем доступные действия в зависимости от статуса пользователя
                if user_data:
                    # Пользователь с подпиской
                    if is_active:
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="➕ Продлить на 7 дней", callback_data=f"extend_user_{user_id}_7"),
                                InlineKeyboardButton(text="➕ Продлить на 30 дней", callback_data=f"extend_user_{user_id}_30")
                            ],
                            [
                                InlineKeyboardButton(text="🚫 Деактивировать", callback_data=f"deactivate_user_{user_id}"),
                                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_user_{user_id}")
                            ],
                            [
                                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")
                            ]
                        ])
                    else:
                        # Неактивная подписка
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="🔄 Активировать", callback_data=f"activate_user_{user_id}"),
                                InlineKeyboardButton(text="➕ Продлить на 30 дней", callback_data=f"extend_user_{user_id}_30")
                            ],
                            [
                                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_user_{user_id}"),
                                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")
                            ]
                        ])
                else:
                    # Пользователь без подписки - проверяем, есть ли он в bot_users
                    async with aiosqlite.connect(DB_PATH) as conn:
                        cursor = await conn.execute(
                            "SELECT user_id, first_name FROM bot_users WHERE user_id = ?",
                            (user_id,)
                        )
                        bot_user = await cursor.fetchone()
                    
                    if bot_user:
                        user_info = f"""
<b>👤 Информация о пользователе</b>

<b>ID:</b> <code>{user_id}</code>
<b>Имя:</b> <code>{bot_user[1] or 'Не указано'}</code>
<b>Статус:</b> 🔴 Нет подписки
<b>Взаимодействие с ботом:</b> ✅ Есть

<i>Пользователь запускал бота, но не имеет VPN подписки</i>
"""
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="🎁 Выдать 7 дней", callback_data=f"give_subscription_{user_id}_7"),
                                InlineKeyboardButton(text="🎁 Выдать 30 дней", callback_data=f"give_subscription_{user_id}_30")
                            ],
                            [
                                InlineKeyboardButton(text="🎁 Выдать 90 дней", callback_data=f"give_subscription_{user_id}_90"),
                                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")
                            ]
                        ])
                        
                        await message.answer(user_info, reply_markup=keyboard)
                        admin_states.pop(message.from_user.id, None)
                        return
                
                await message.answer(user_info, reply_markup=keyboard)
            else:
                await message.answer(
                    f"❌ Пользователь с ID <code>{user_id}</code> не найден.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
                    ])
                )
            
            # Сбрасываем состояние
            admin_states.pop(message.from_user.id, None)
        elif state_value == "waiting_user_id_for_subscription":
            user_id = int(message.text)
            
            # Проверяем, есть ли пользователь в bot_users
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.execute(
                    "SELECT user_id, first_name FROM bot_users WHERE user_id = ?",
                    (user_id,)
                )
                bot_user = await cursor.fetchone()
                
                # Проверяем, есть ли уже подписка
                cursor = await conn.execute(
                    "SELECT user_id FROM users WHERE user_id = ?",
                    (user_id,)
                )
                has_subscription = await cursor.fetchone()
            
            if not bot_user:
                await message.answer(
                    f"❌ Пользователь с ID <code>{user_id}</code> не найден в базе бота.\n\n<i>Пользователь должен сначала запустить бота командой /start</i>",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
                    ])
                )
            elif has_subscription:
                await message.answer(
                    f"⚠️ У пользователя <code>{user_id}</code> уже есть подписка.\n\n<i>Используйте поиск пользователя для управления существующей подпиской.</i>",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
                    ])
                )
            else:
                user_name = bot_user[1] or "Без имени"
                subscription_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🎁 7 дней", callback_data=f"give_subscription_{user_id}_7"),
                        InlineKeyboardButton(text="🎁 30 дней", callback_data=f"give_subscription_{user_id}_30")
                    ],
                    [
                        InlineKeyboardButton(text="🎁 90 дней", callback_data=f"give_subscription_{user_id}_90"),
                        InlineKeyboardButton(text="🎁 365 дней", callback_data=f"give_subscription_{user_id}_365")
                    ],
                    [
                        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")
                    ]
                ])
                
                await message.answer(
                    f"<b>🎁 Выдача подписки</b>\n\n<b>Пользователь:</b> {user_name} (<code>{user_id}</code>)\n\nВыберите период подписки:",
                    reply_markup=subscription_keyboard
                )
            
            # Сбрасываем состояние
            admin_states.pop(message.from_user.id, None)
            return
    
    @dp.callback_query(F.data.startswith("extend_user_"))
    async def extend_user_callback(callback: types.CallbackQuery):
        """Продление подписки пользователя"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            _, _, user_id, days = callback.data.split("_")
            user_id = int(user_id)
            days = int(days)
            
            success = await extend_user_subscription(user_id, days)
            
            if success:
                await callback.answer(f"✅ Подписка пользователя {user_id} продлена на {days} дней", show_alert=True)
            else:
                await callback.answer(f"❌ Ошибка продления подписки пользователя {user_id}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка продления подписки: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)
    
    @dp.callback_query(F.data.startswith("block_user_"))
    async def block_user_callback(callback: types.CallbackQuery):
        """Блокировка пользователя"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            _, _, user_id = callback.data.split("_")
            user_id = int(user_id)
            
            success = await block_user(user_id)
            
            if success:
                await callback.answer(f"✅ Пользователь {user_id} заблокирован", show_alert=True)
            else:
                await callback.answer(f"❌ Ошибка блокировки пользователя {user_id}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка блокировки пользователя: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)
    
    @dp.callback_query(F.data.startswith("delete_user_"))
    async def delete_user_callback(callback: types.CallbackQuery):
        """Удаление пользователя"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            _, _, user_id = callback.data.split("_")
            user_id = int(user_id)
            
            success = await delete_user(user_id)
            
            if success:
                await callback.answer(f"✅ Пользователь {user_id} удален", show_alert=True)
            else:
                await callback.answer(f"❌ Ошибка удаления пользователя {user_id}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка удаления пользователя: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)
    
    @dp.callback_query(F.data.startswith("give_subscription_"))
    async def give_subscription_callback(callback: types.CallbackQuery):
        """Выдача подписки пользователю"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            _, _, user_id, days = callback.data.split("_")
            user_id = int(user_id)
            days = int(days)
            
            success = await give_user_subscription(user_id, days)
            
            if success:
                await callback.answer(f"✅ Пользователю {user_id} выдана подписка на {days} дней", show_alert=True)
            else:
                await callback.answer(f"❌ Ошибка выдачи подписки пользователю {user_id}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка выдачи подписки: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)

    @dp.callback_query(F.data.startswith("deactivate_user_"))
    async def deactivate_user_callback(callback: types.CallbackQuery):
        """Деактивация подписки пользователя"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            _, _, user_id = callback.data.split("_")
            user_id = int(user_id)
            
            success = await deactivate_user_subscription(user_id)
            
            if success:
                await callback.answer(f"✅ Подписка пользователя {user_id} деактивирована", show_alert=True)
            else:
                await callback.answer(f"❌ Ошибка деактивации подписки пользователя {user_id}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка деактивации подписки: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)

    @dp.callback_query(F.data.startswith("activate_user_"))
    async def activate_user_callback(callback: types.CallbackQuery):
        """Активация подписки пользователя"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            _, _, user_id = callback.data.split("_")
            user_id = int(user_id)
            
            success = await activate_user_subscription(user_id)
            
            if success:
                await callback.answer(f"✅ Подписка пользователя {user_id} активирована", show_alert=True)
            else:
                await callback.answer(f"❌ Ошибка активации подписки пользователя {user_id}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка активации подписки: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)
    
    @dp.callback_query(F.data == "admin_active_users")
    async def admin_active_users_callback(callback: types.CallbackQuery):
        """Активные пользователи"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            active_users = await get_users_by_status("active", 15)
            
            if not active_users:
                text = "<b>👥 Активные пользователи</b>\n\nНет активных пользователей"
            else:
                text = "<b>👥 Активные пользователи (последние 15)</b>\n\n"
                for user_id, expiry_date in active_users:
                    text += f"• ID: <code>{user_id}</code> до <code>{expiry_date}</code>\n"
            
            await callback.message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка получения активных пользователей: {e}")
            await callback.answer("Ошибка получения данных", show_alert=True)
    
    @dp.callback_query(F.data == "admin_expiring")
    async def admin_expiring_callback(callback: types.CallbackQuery):
        """Истекающие подписки"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            expiring_users = await get_users_by_status("expiring", 15)
            
            if not expiring_users:
                text = "<b>⏰ Истекающие подписки</b>\n\nНет истекающих подписок в ближайшие 3 дня"
            else:
                text = "<b>⏰ Истекающие подписки (ближайшие 3 дня)</b>\n\n"
                for user_id, expiry_date in expiring_users:
                    text += f"• ID: <code>{user_id}</code> истекает <code>{expiry_date}</code>\n"
            
            await callback.message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка получения истекающих подписок: {e}")
            await callback.answer("Ошибка получения данных", show_alert=True)
    
    @dp.callback_query(F.data == "admin_expired")
    async def admin_expired_callback(callback: types.CallbackQuery):
        """Истекшие подписки"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            expired_users = await get_users_by_status("expired", 15)
            
            if not expired_users:
                text = "<b>❌ Истекшие подписки</b>\n\nНет истекших подписок"
            else:
                text = "<b>❌ Истекшие подписки (последние 15)</b>\n\n"
                for user_id, expiry_date in expired_users:
                    text += f"• ID: <code>{user_id}</code> истекла <code>{expiry_date}</code>\n"
            
            await callback.message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка получения истекших подписок: {e}")
            await callback.answer("Ошибка получения данных", show_alert=True)
    
    @dp.callback_query(F.data == "admin_give_subscription")
    async def admin_give_subscription_callback(callback: types.CallbackQuery):
        """Выдача подписки пользователю"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        admin_states[callback.from_user.id] = "waiting_user_id_for_subscription"
        
        await callback.message.edit_text(
            text="<b>🎁 Выдача подписки</b>\n\nОтправьте ID пользователя, которому хотите выдать подписку:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
            ])
        )

    @dp.callback_query(F.data == "admin_all_bot_users")
    async def admin_all_bot_users_callback(callback: types.CallbackQuery):
        """Все пользователи бота"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                cursor = await conn.execute(
                    """SELECT bu.user_id, bu.first_name, bu.first_interaction,
                          CASE WHEN u.user_id IS NOT NULL THEN 1 ELSE 0 END as has_subscription
                   FROM bot_users bu
                   LEFT JOIN users u ON bu.user_id = u.user_id
                   ORDER BY bu.first_interaction DESC LIMIT 15"""
                )
                all_bot_users = await cursor.fetchall()
            
            if not all_bot_users:
                text = "<b>👥 Все пользователи бота</b>\n\nНет пользователей"
            else:
                text = "<b>👥 Все пользователи бота (последние 15)</b>\n\n"
                for user_id, first_name, first_interaction, has_subscription in all_bot_users:
                    status = "💎" if has_subscription else "👤"
                    name = first_name or "Без имени"
                    text += f"{status} <code>{user_id}</code> - {name}\n"
                
                text += "\n💎 - есть подписка\n👤 - только запускал бота"
            
            await callback.message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка получения всех пользователей бота: {e}")
            await callback.answer("Ошибка получения данных", show_alert=True)
    
    @dp.callback_query(F.data == "admin_payments")
    async def admin_payments_callback(callback: types.CallbackQuery):
        """Статистика платежей"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        try:
            payment_stats = await get_payment_stats()
            
            payments_text = f"""
<b>💰 Статистика платежей</b>

<b>📊 Доходы:</b>
• За сегодня: <code>{payment_stats['revenue_today']}₽</code>
• За неделю: <code>{payment_stats['revenue_week']}₽</code>
• За месяц: <code>{payment_stats['revenue_month']}₽</code>
• Средний чек: <code>{payment_stats['avg_payment']}₽</code>

<b>📈 Подписки по периодам:</b>
• 1 месяц: <code>{payment_stats['subs_1m']}</code> шт.
• 3 месяца: <code>{payment_stats['subs_3m']}</code> шт.
• 6 месяцев: <code>{payment_stats['subs_6m']}</code> шт.
• 12 месяцев: <code>{payment_stats['subs_12m']}</code> шт.
"""
            
            await callback.message.edit_text(
                text=payments_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка получения статистики платежей: {e}")
            await callback.answer("Ошибка получения данных", show_alert=True)
    
    @dp.callback_query(F.data == "admin_broadcast")
    async def admin_broadcast_callback(callback: types.CallbackQuery):
        """Обработчик рассылки"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        broadcast_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Всем пользователям", callback_data="broadcast_all"),
                InlineKeyboardButton(text="💎 Только активным", callback_data="broadcast_active")
            ],
            [
                InlineKeyboardButton(text="⏰ Истекающим подпискам", callback_data="broadcast_expiring"),
                InlineKeyboardButton(text="❌ Неактивным", callback_data="broadcast_inactive")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")
            ]
        ])
        
        await callback.message.edit_text(
            text="""
<b>📢 Рассылка сообщений</b>

Выберите целевую аудиторию для рассылки:

<blockquote><i>⚠️ После выбора отправьте текст сообщения или фото с подписью для рассылки</i></blockquote>
""",
            reply_markup=broadcast_keyboard
        )
    
    @dp.callback_query(F.data == "admin_manage")
    async def admin_manage_callback(callback: types.CallbackQuery):
        """Обработчик управления системой"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        manage_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Очистить БД", callback_data="admin_clear_db"),
                InlineKeyboardButton(text="💾 Бэкап БД", callback_data="admin_backup_db")
            ],
            [
                InlineKeyboardButton(text="🔄 Перезапуск бота", callback_data="admin_restart_bot"),
                InlineKeyboardButton(text="📊 Пересчет статистики", callback_data="admin_recalc_stats")
            ],
            [
                InlineKeyboardButton(text="🧹 Очистка логов", callback_data="admin_clear_logs"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")
            ]
        ])
    
        await callback.message.edit_text(
            text="<b>🔧 Управление системой</b>\n\nВыберите действие:",
            reply_markup=manage_keyboard
        )

    @dp.callback_query(F.data == "admin_clear_db")
    async def admin_clear_db_callback(callback: types.CallbackQuery):
        """Очистка базы данных"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, очистить", callback_data="admin_clear_db_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage")
            ]
        ])
    
        await callback.message.edit_text(
            text="""<b>⚠️ ВНИМАНИЕ!</b>

Вы собираетесь полностью очистить базу данных!

Это действие удалит:
• Всех пользователей
• Все платежи
• Всю статистику

<b>Это действие НЕОБРАТИМО!</b>

Вы уверены?""",
            reply_markup=confirm_keyboard
        )

    @dp.callback_query(F.data == "admin_clear_db_confirm")
    async def admin_clear_db_confirm_callback(callback: types.CallbackQuery):
        """Подтверждение очистки БД"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        try:
            async with aiosqlite.connect(DB_PATH) as conn:
                await conn.execute("DELETE FROM users")
                await conn.execute("DELETE FROM bot_users")
                await conn.execute("DELETE FROM payments")
                await conn.commit()
        
            await callback.message.edit_text(
                text="✅ <b>База данных успешно очищена!</b>\n\nВся статистика обнулена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back_main")]
                ])
            )
        
            await callback.answer("База данных очищена!", show_alert=True)
        
        except Exception as e:
            logging.error(f"Ошибка очистки БД: {e}")
            await callback.answer("❌ Ошибка при очистке БД", show_alert=True)

    @dp.callback_query(F.data == "admin_backup_db")
    async def admin_backup_db_callback(callback: types.CallbackQuery):
        """Создание бэкапа БД"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        await callback.answer("🔄 Создание бэкапа... (функция в разработке)", show_alert=True)

    @dp.callback_query(F.data == "admin_restart_bot")
    async def admin_restart_bot_callback(callback: types.CallbackQuery):
        """Перезапуск бота"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        await callback.answer("🔄 Перезапуск... (функция в разработке)", show_alert=True)

    @dp.callback_query(F.data == "admin_recalc_stats")
    async def admin_recalc_stats_callback(callback: types.CallbackQuery):
        """Пересчет статистики"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        await callback.answer("📊 Статистика пересчитана!", show_alert=True)
    
        # Возвращаемся в главное меню с обновленной статистикой
        stats = await get_admin_stats()
    
        admin_text = f"""
<b>🔧 Админ панель Shard VPN</b>

<b>📊 Быстрая статистика:</b>
• Всего пользователей: <code>{stats['total_users']}</code>
• Активных подписок: <code>{stats['active_subs']}</code>
• Доход за месяц: <code>{stats['monthly_revenue']}₽</code>
• Новых за сегодня: <code>{stats['new_today']}</code>

<b>🕐 Время:</b> <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>
"""
    
        await callback.message.edit_text(
            text=admin_text,
            reply_markup=get_admin_main_keyboard()
        )

    @dp.callback_query(F.data == "admin_clear_logs")
    async def admin_clear_logs_callback(callback: types.CallbackQuery):
        """Очистка логов"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        await callback.answer("🧹 Логи очищены! (функция в разработке)", show_alert=True)

    @dp.callback_query(F.data == "admin_settings")
    async def admin_settings_callback(callback: types.CallbackQuery):
        """Настройки"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        await callback.answer("⚙️ Настройки (функция в разработке)", show_alert=True)

    @dp.callback_query(F.data == "admin_logs")
    async def admin_logs_callback(callback: types.CallbackQuery):
        """Просмотр логов"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
        logs_text = """
<b>📋 Системные логи</b>

<b>Последние события:</b>
• 15:30 - Новый пользователь: 123456789
• 15:25 - Платеж: 149₽ от 987654321
• 15:20 - Админ панель открыта
• 15:15 - Рассылка отправлена: 25 пользователей

<i>Полные логи доступны в файле bot.log</i>
"""
    
        await callback.message.edit_text(
            text=logs_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")]
            ])
        )
    
    @dp.callback_query(F.data == "admin_back_main")
    async def admin_back_main_callback(callback: types.CallbackQuery):
        """Возврат в главное меню админки"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        stats = await get_admin_stats()
        
        admin_text = f"""
<b>🔧 Админ панель Shard VPN</b>

<b>📊 Быстрая статистика:</b>
• Всего пользователей: <code>{stats['total_users']}</code>
• Активных подписок: <code>{stats['active_subs']}</code>
• Доход за месяц: <code>{stats['monthly_revenue']}₽</code>
• Новых за сегодня: <code>{stats['new_today']}</code>

<b>🕐 Время:</b> <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>
"""
        
        await callback.message.edit_text(
            text=admin_text,
            reply_markup=get_admin_main_keyboard()
        )
    
    @dp.callback_query(F.data == "admin_close")
    async def admin_close_callback(callback: types.CallbackQuery):
        """Закрытие админ панели"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await callback.message.delete()
        await callback.answer("Админ панель закрыта")
    
    # Обработчики рассылки
    @dp.callback_query(F.data.startswith("broadcast_"))
    async def broadcast_callback(callback: types.CallbackQuery):
        """Обработчик выбора типа рассылки"""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        broadcast_type = callback.data.split("_")[1]
        
        type_names = {
            "all": "всем пользователям",
            "active": "активным пользователям",
            "inactive": "неактивным пользователям",
            "expiring": "пользователям с истекающими подписками"
        }
        
        admin_states[callback.from_user.id] = f"waiting_broadcast_{broadcast_type}"
        
        await callback.message.edit_text(
            text=f"""<b>📢 Рассылка {type_names.get(broadcast_type, 'выбранной группе')}</b>

Отправьте сообщение или фото с подписью, которое хотите разослать.

<blockquote><i>⚠️ Будьте осторожны! Отменить рассылку будет невозможно.</i></blockquote>""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
            ])
        )
    
    # ИСПРАВЛЕННЫЙ обработчик рассылки - только для админов и только в состоянии рассылки
    @dp.message((F.text | F.photo) & F.from_user.id.in_(ADMIN_IDS))
    async def handle_broadcast_message(message: Message):
        """Обработка сообщения для рассылки - ТОЛЬКО для админов"""
        state = admin_states.get(message.from_user.id, "")
        if not state.startswith("waiting_broadcast_"):
            # Не в режиме ожидания текста для рассылки — выходим
            return
        if state.startswith("waiting_broadcast_"):
            broadcast_type = state.split("_")[2]
            
            # Отправляем уведомление о начале рассылки
            await message.answer("📤 Начинаю рассылку...")
            
            # Определяем тип сообщения
            message_text = None
            photo_url = None
            
            if message.photo:
                # Если есть фото
                photo_url = message.photo[-1].file_id  # Берем фото наибольшего размера
                message_text = message.caption or ""
            else:
                # Если только текст
                message_text = message.text
            
            # Выполняем рассылку
            from bot import bot  # Импортируем бота
            result = await send_broadcast_message(bot, message_text, broadcast_type, photo_url)
            
            # Отправляем результат
            result_text = f"""
<b>📊 Результат рассылки</b>

<b>Успешно отправлено:</b> <code>{result['success']}</code>
<b>Ошибки отправки:</b> <code>{result['failed']}</code>
<b>Заблокировали бота:</b> <code>{result['blocked']}</code>
<b>Всего пользователей:</b> <code>{result.get('total', 0)}</code>
"""
            
            await message.answer(result_text)
            
            # Сбрасываем состояние
            admin_states.pop(message.from_user.id, None)
