from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
def get_user_keyboard(has_subscription: bool):
    """Клавиатура для пользователя с учетом статуса подписки"""
    if has_subscription:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Инструкция", callback_data='instruction')],
            [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data='renew_sub')]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оформить подписку", callback_data='subscribe')]
        ])
def create_main_keyboard():
    """Основная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌐Активировать VPN")],
            [KeyboardButton(text="👾Аккаунт"), KeyboardButton(text="🔒О VPN")]
        ],
        resize_keyboard=True
    )

def get_subscription_keyboard():
    """Клавиатура выбора подписки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 месяц - 149₽", callback_data="sub_1")
            ],
            [
                InlineKeyboardButton(text="3 месяца - 399₽", callback_data="sub_3")
            ],
            [
                InlineKeyboardButton(text="6 месяцев - 699₽", callback_data="sub_6")
            ],
            [
                InlineKeyboardButton(text="12 месяцев - 999₽", callback_data="sub_12")
            ]
        ]
    )

def get_payment_check_keyboard(payment_id: str):
    """Клавиатура для проверки платежа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Проверить оплату",
                callback_data=f"check_pay:{payment_id}"
            )],
            [InlineKeyboardButton(
                text="📞 Поддержка",
                url="https://t.me/xmakedon"
            )]
        ]
    )