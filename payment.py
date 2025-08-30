import uuid
import asyncio
import aiosqlite
import logging
from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, YOOKASSA_RETURN_URL, DB_PATH
from database import add_payment
from datetime import datetime
# Настройка ЮKассы
Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)

# Глобальный набор для отслеживания активных проверок
active_checks = set()

async def create_payment(period: str, user_id: int):
    """Создает платеж в ЮKассе"""
    periods = {
        '1': {'value': '149.00', 'description': '1 месяц'},
        '3': {'value': '399.00', 'description': '3 месяца'},
        '6': {'value': '699.00', 'description': '6 месяцев'},
        '12': {'value': '999.00', 'description': '12 месяцев'}
    }
    
    if period not in periods:
        logging.error(f"Неверный период подписки: {period}")
        return None
    
    try:
        payment = Payment.create({
            "amount": {
                "value": periods[period]['value'],
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": YOOKASSA_RETURN_URL
            },
            "capture": True,
            "description": f"Shard VPN: {periods[period]['description']}",
            "metadata": {
                "user_id": str(user_id),
                "period": period
            }
        }, str(uuid.uuid4()))
        
        return {
            'confirmation_url': payment.confirmation.confirmation_url,
            'payment_id': payment.id,
            'period': period
        }
    except Exception as e:
        logging.error(f"Ошибка создания платежа: {str(e)}", exc_info=True)
        return None

async def check_payment_status(payment_data: dict, bot):
    """Автоматически проверяет статус платежа"""
    payment_id = payment_data['payment_id']
    
    try:
        for _ in range(60):  # 10 минут (60 попыток * 10 секунд)
            try:
                payment = Payment.find_one(payment_id)
                
                if payment.status == "succeeded":
                    # Проверяем, была ли подписка активной ДО продления
                    was_active = False
                    try:
                        async with aiosqlite.connect(DB_PATH) as conn:
                            cursor = await conn.execute(
                                "SELECT expiry_date FROM users WHERE user_id=?",
                                (payment_data['user_id'],)
                            )
                            row_before = await cursor.fetchone()
                            if row_before and row_before[0]:
                                expiry_str = row_before[0]
                                from datetime import datetime
                                for fmt in ('%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                                    try:
                                        dt = datetime.strptime(expiry_str, fmt)
                                        was_active = datetime.now() < dt
                                        if was_active or True:
                                            break
                                    except ValueError:
                                        continue
                    except Exception:
                        was_active = False
                    # Добавляем оплату в БД
                    success = await add_payment(
                        payment_data['user_id'],
                        int(payment_data['period'])
                    )
                    
                    if not success:
                        logging.error("Не удалось обновить подписку в БД")
                        return False
                    
                    # Удаляем сообщение с платежом
                    try:
                        await bot.delete_message(
                            chat_id=payment_data['chat_id'],
                            message_id=payment_data['message_id']
                        )
                    except Exception as e:
                        logging.warning(f"Не удалось удалить сообщение: {e}")

                    # Получаем дату окончания и форматируем её
                    async with aiosqlite.connect(DB_PATH) as conn:
                        cursor = await conn.execute(
                            "SELECT expiry_date FROM users WHERE user_id=?",
                            (payment_data['user_id'],)
                        )
                        row = await cursor.fetchone()
                        if row and row[0]:
                            try:
                                expiry_date = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
                            except ValueError:
                                expiry_date = row[0]
                        else:
                            expiry_date = "не определена"

                    # Отправляем сообщение об успешной оплате
                    action_word = "продлена" if was_active else "активирована"
                    await bot.send_message(
                        chat_id=payment_data['chat_id'],
                        text=f"""
<b>✅ Оплата успешно выполнена</b>

<b>Ваша подписка на Shard VPN {action_word}!</b>

<b>Срок подписки:</b> {payment_data['period']} мес.
<b>Дата окончания:</b> <code>{expiry_date}</code>

<blockquote><i>🔹 Нажмите «Активировать VPN», чтобы начать пользоваться.</i></blockquote>
""",
                        message_effect_id="5046509860389126442"
                    )
                    return True
                    
                elif payment.status in ("canceled", "failed"):
                    return False
                    
            except Exception as e:
                logging.error(f"Ошибка проверки платежа: {str(e)}", exc_info=True)
            
            await asyncio.sleep(10)
        
        logging.warning(f"Платеж {payment_id} не завершился в течение 10 минут")
        return False
        
    except Exception as e:
        logging.error(f"Критическая ошибка в check_payment_status: {str(e)}", exc_info=True)
        return False