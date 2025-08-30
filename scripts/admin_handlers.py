import logging
import asyncio
from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import ADMIN_ID, DB_PATH
from database import get_all_users, get_user_stats, delete_user, extend_user_subscription
import aiosqlite
from datetime import datetime, timedelta

# Список ID администраторов (можно расширить)
ADMIN_IDS = [ADMIN_ID, 2057750889]  # Добавьте нужные ID

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

def get_user_management_keyboard():
    """Клавиатура управления пользователями"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_find_user"),
            InlineKeyboardButton(text="📋 Список активных", callback_data="admin_active_users")
        ],
        [
            InlineKeyboardButton(text="⏰ Истекающие подписки", callback_data="admin_expiring"),
            InlineKeyboardButton(text="❌ Заблокированные", callback_data="admin_blocked")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")
        ]
    ])

def get_management_keyboard():
    """Клавиатура управления системой"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Перезапуск бота", callback_data="admin_restart"),
            InlineKeyboardButton(text="🧹 Очистка логов", callback_data="admin_clear_logs")
        ],
        [
            InlineKeyboardButton(text="💾 Бэкап БД", callback_data="admin_backup"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_main")
        ]
    ])

async def admin_command_handler(message: Message):
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

async def admin_stats_handler(callback: types.CallbackQuery):
    """Обработчик статистики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    stats = await get_detailed_stats()
    
    stats_text = f"""
<b>📊 Подробная статистика</b>

<b>👥 Пользователи:</b>
• Всего зарегистрировано: <code>{stats['total_users']}</code>
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

async def admin_users_handler(callback: types.CallbackQuery):
    """Обработчик управления пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        text="<b>👥 Управление пользователями</b>\n\nВыберите действие:",
        reply_markup=get_user_management_keyboard()
    )

async def admin_broadcast_handler(callback: types.CallbackQuery):
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

<blockquote><i>⚠️ После выбора отправьте текст сообщения для рассылки</i></blockquote>
""",
        reply_markup=broadcast_keyboard
    )

async def admin_manage_handler(callback: types.CallbackQuery):
    """Обработчик управления системой"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        text="<b>🔧 Управление системой</b>\n\nВыберите действие:",
        reply_markup=get_management_keyboard()
    )

# Вспомогательные функции для работы с БД

async def get_admin_stats():
    """Получает базовую статистику для админ панели"""
    async with aiosqlite.connect(DB_PATH) as conn:
        # Всего пользователей
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # Активные подписки
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE subscribed = 1 AND datetime(expiry_date, 'localtime') > datetime('now', 'localtime')"
        )
        active_subs = (await cursor.fetchone())[0]
        
        # Новые за сегодня
        today = datetime.now().strftime('%d.%m.%Y')
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(payment_date) = DATE('now')"
        )
        new_today = (await cursor.fetchone())[0]
        
        return {
            'total_users': total_users,
            'active_subs': active_subs,
            'monthly_revenue': 0,  # Можно добавить подсчет из платежей
            'new_today': new_today
        }

async def get_detailed_stats():
    """Получает подробную статистику"""
    async with aiosqlite.connect(DB_PATH) as conn:
        stats = {}
        
        # Всего пользователей
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = (await cursor.fetchone())[0]
        
        # Активные подписки
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE subscribed = 1 AND datetime(expiry_date, 'localtime') > datetime('now', 'localtime')"
        )
        stats['active_subs'] = (await cursor.fetchone())[0]
        
        # Истекшие подписки
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE subscribed = 1 AND datetime(expiry_date, 'localtime') <= datetime('now', 'localtime')"
        )
        stats['expired_subs'] = (await cursor.fetchone())[0]
        
        # Новые за сегодня
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(payment_date) = DATE('now')"
        )
        stats['new_today'] = (await cursor.fetchone())[0]
        
        # Новые за неделю
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(payment_date) >= DATE('now', '-7 days')"
        )
        stats['new_week'] = (await cursor.fetchone())[0]
        
        # Заглушки для финансовой статистики
        stats.update({
            'revenue_today': 0,
            'revenue_week': 0,
            'revenue_month': 0,
            'avg_payment': 0,
            'subs_1m': 0,
            'subs_3m': 0,
            'subs_6m': 0,
            'subs_12m': 0
        })
        
        return stats

async def get_all_users():
    """Получает всех пользователей"""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT user_id, subscribed, payment_date, expiry_date FROM users ORDER BY payment_date DESC"
        )
        return await cursor.fetchall()

async def extend_user_subscription(user_id: int, days: int):
    """Продлевает подписку пользователя"""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT expiry_date FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if row and row[0]:
            try:
                current_expiry = datetime.strptime(row[0], '%d.%m.%Y %H:%M')
                new_expiry = current_expiry + timedelta(days=days)
                
                await conn.execute(
                    "UPDATE users SET expiry_date = ? WHERE user_id = ?",
                    (new_expiry.strftime('%d.%m.%Y %H:%M'), user_id)
                )
                await conn.commit()
                return True
            except ValueError:
                return False
        return False

async def delete_user(user_id: int):
    """Удаляет пользователя из БД"""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await conn.commit()
        return True

async def extend_vpn_config(user_id: int, days: int) -> bool:
    """Продлевает конфигурацию VPN на сервере"""
    import asyncio  # Добавьте этот импорт
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute(
                "SELECT config FROM users WHERE user_id=?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row or not row[0]:
                logging.error(f"Не найден конфиг для user_id={user_id}")
                return False
                
            config_id = row[0].strip('"\'')  # Удаляем лишние кавычки
            
        import aiohttp  # Добавьте этот импорт тоже
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://89.111.142.122:8080/extendconfig",
                json={
                    "time": days, 
                    "uid": config_id  # Используем правильное имя параметра
                },
                headers={"x-api-key": "999999999999"},
                timeout=10
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logging.error(f"Ошибка продления: {resp.status} - {error}")
                    return False
                return True
                
    except asyncio.TimeoutError:
        logging.error("Таймаут при продлении конфига")
        return False
    except Exception as e:
        logging.error(f"Ошибка в extend_vpn_config: {str(e)}", exc_info=True)
        return False
