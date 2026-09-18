
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


def main_menu(webapp_url: str) -> ReplyKeyboardMarkup:
    """
    Главное меню бота.

    Кнопка «Сегодняшний квиз» открывает Telegram Mini App
    непосредственно через Web App API.
    """

    profile_button = KeyboardButton(
        text="👤 Профиль",
    )

    leaderboard_button = KeyboardButton(
        text="🏆 Лидерборд",
    )

    help_button = KeyboardButton(
        text="ℹ️ Помощь",
    )

    keyboard = [
        [
            profile_button,
        ],
        [
            leaderboard_button,
            help_button,
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


def inline_back_button() -> InlineKeyboardMarkup:
    """
    Inline-кнопка возврата в главное меню.
    """

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="back_to_menu",
                )
            ]
        ]
    )