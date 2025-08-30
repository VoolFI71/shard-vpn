# Интеграция админ панели в основной бот
from aiogram import types, F
from aiogram.filters import Command
from datetime import datetime
from scripts.admin_handlers import (
    admin_command_handler,
    admin_stats_handler,
    admin_users_handler,
    admin_broadcast_handler,
    admin_manage_handler,
    is_admin
)

def register_admin_handlers(dp):
    """Регистрирует обработчики админ панели"""
    
    # Команда /admin
    @dp.message(Command("admin"))
    async def admin_command(message: types.Message):
        await admin_command_handler(message)
    
    # Обработчики callback'ов админ панели
    @dp.callback_query(F.data == "admin_stats")
    async def admin_stats_callback(callback: types.CallbackQuery):
        await admin_stats_handler(callback)
    
    @dp.callback_query(F.data == "admin_users")
    async def admin_users_callback(callback: types.CallbackQuery):
        await admin_users_handler(callback)
    
    @dp.callback_query(F.data == "admin_broadcast")
    async def admin_broadcast_callback(callback: types.CallbackQuery):
        await admin_broadcast_handler(callback)
    
    @dp.callback_query(F.data == "admin_manage")
    async def admin_manage_callback(callback: types.CallbackQuery):
        await admin_manage_handler(callback)
    
    @dp.callback_query(F.data == "admin_back_main")
    async def admin_back_main_callback(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        from scripts.admin_handlers import get_admin_main_keyboard, get_admin_stats
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
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await callback.message.delete()
        await callback.answer("Админ панель закрыта")
    
    # Поиск пользователя
    @dp.callback_query(F.data == "admin_find_user")
    async def admin_find_user_callback(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await callback.message.edit_text(
            text="<b>🔍 Поиск пользователя</b>\n\nОтправьте ID пользователя для поиска:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
            ])
        )
        
        # Здесь нужно добавить состояние для ожидания ID пользователя
    
    # Активные пользователи
    @dp.callback_query(F.data == "admin_active_users")
    async def admin_active_users_callback(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        import aiosqlite
        from config import DB_PATH
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute(
                """SELECT user_id, expiry_date FROM users 
                   WHERE subscribed = 1 AND datetime(expiry_date, 'localtime') > datetime('now', 'localtime')
                   ORDER BY expiry_date DESC LIMIT 10"""
            )
            active_users = await cursor.fetchall()
        
        if not active_users:
            text = "<b>👥 Активные пользователи</b>\n\nНет активных пользователей"
        else:
            text = "<b>👥 Активные пользователи (последние 10)</b>\n\n"
            for user_id, expiry_date in active_users:
                text += f"• ID: <code>{user_id}</code> до <code>{expiry_date}</code>\n"
        
        await callback.message.edit_text(
            text=text,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users")]
            ])
        )
    
    # Рассылка всем
    @dp.callback_query(F.data == "broadcast_all")
    async def broadcast_all_callback(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        await callback.message.edit_text(
            text="""<b>📢 Рассылка всем пользователям</b>

Отправьте сообщение, которое хотите разослать всем пользователям бота.

<blockquote><i>⚠️ Будьте осторожны! Сообщение получат ВСЕ пользователи.</i></blockquote>""",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
            ])
        )
        
        # Здесь нужно добавить состояние для ожидания текста рассылки

# Добавьте эту функцию в ваш основной bot.py файл
