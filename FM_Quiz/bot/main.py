
import logging
import os
import sys

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ============================================================
# ENV
# ============================================================

load_dotenv(
    os.path.join(
        BASE_DIR,
        ".env",
    )
)


BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден. Проверь файл .env"
    )


if not WEBAPP_URL:
    raise RuntimeError(
        "WEBAPP_URL не найден. Проверь файл .env"
    )


# ============================================================
# PYTHON PATH
# ============================================================

if BASE_DIR not in sys.path:
    sys.path.insert(
        0,
        BASE_DIR,
    )


# ============================================================
# DATABASE
# ============================================================

from backend.database import (
    init_database,
    get_user,
    get_leaderboard,
    get_user_rank,
)


# ============================================================
# KEYBOARDS
# ============================================================

from bot.keyboards import (
    main_menu,
    inline_back_button,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE INIT
# ============================================================

init_database()


# ============================================================
# INLINE WEB APP BUTTON
# ============================================================

def quiz_webapp_button() -> InlineKeyboardMarkup:
    """
    Inline-кнопка для запуска Telegram Mini App.

    В отличие от кнопки нижнего ReplyKeyboard,
    здесь Web App запускается непосредственно
    через InlineKeyboardButton.
    """

    keyboard = [
        [
            InlineKeyboardButton(
                text="🎯 Открыть сегодняшний квиз",
                web_app=WebAppInfo(
                    url=WEBAPP_URL,
                ),
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    logger.info(
        "START: telegram_id=%s username=%s",
        user.id,
        user.username,
    )

    logger.info(
        "WEBAPP_URL: %s",
        WEBAPP_URL,
    )

    text = (
        "⚽ <b>FootballMeister Quiz</b>\n\n"
        f"Привет, {user.first_name}!\n\n"
        "Здесь тебя ждут ежедневные "
        "футбольные квизы.\n"
        "Проверяй свои знания и "
        "зарабатывай очки.\n\n"
        "Нажми кнопку ниже, чтобы открыть "
        "сегодняшний квиз 👇"
    )

    # Первое сообщение — отдельная inline-кнопка Web App.
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=quiz_webapp_button(),
    )

    # Второе сообщение — обычное нижнее меню.
    await update.message.reply_text(
        "Основные разделы:",
        reply_markup=main_menu(
            WEBAPP_URL
        ),
    )


# ============================================================
# PROFILE
# ============================================================

async def show_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    db_user = get_user(user.id)

    if db_user is None:

        await update.message.reply_text(
            (
                "👤 <b>Профиль</b>\n\n"
                "Ты ещё не проходил квизы.\n"
                "Открой сегодняшний квиз, "
                "чтобы создать профиль."
            ),
            parse_mode="HTML",
            reply_markup=main_menu(
                WEBAPP_URL
            ),
        )

        return

    first_name = (
        db_user["first_name"]
        or "Пользователь"
    )

    username = db_user["username"]

    username_text = (
        f"@{username}"
        if username
        else "не указан"
    )

    points = db_user["points"]
    correct_answers = db_user["correct_answers"]
    quizzes_completed = db_user["quizzes_completed"]

    rank = get_user_rank(user.id)

    rank_text = (
        f"#{rank}"
        if rank is not None
        else "—"
    )

    text = (
        "👤 <b>Профиль</b>\n\n"
        f"Имя: {first_name}\n"
        f"Username: {username_text}\n\n"
        f"🏆 Очки: <b>{points}</b>\n"
        f"📊 Место в лидерборде: "
        f"<b>{rank_text}</b>\n"
        f"✅ Правильных ответов: "
        f"<b>{correct_answers}</b>\n"
        f"🎯 Квизов пройдено: "
        f"<b>{quizzes_completed}</b>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(
            WEBAPP_URL
        ),
    )


# ============================================================
# LEADERBOARD
# ============================================================

async def show_leaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    leaders = get_leaderboard(10)

    if not leaders:

        await update.message.reply_text(
            (
                "🏆 <b>Лидерборд</b>\n\n"
                "Пока никто не набрал очков."
            ),
            parse_mode="HTML",
            reply_markup=main_menu(
                WEBAPP_URL
            ),
        )

        return

    user_rank = get_user_rank(user.id)

    lines = [
        "🏆 <b>Лидерборд</b>",
        "",
    ]

    for index, leader in enumerate(leaders):

        telegram_id = leader["telegram_id"]
        points = leader["points"]

        if index == 0:
            medal = "🥇"

        elif index == 1:
            medal = "🥈"

        elif index == 2:
            medal = "🥉"

        else:
            medal = f"{index + 1}."

        name = (
            leader["first_name"]
            or "Пользователь"
        )

        if telegram_id == user.id:
            name = f"<b>{name}</b>"

        lines.append(
            f"{medal} {name} — "
            f"<b>{points}</b> очков"
        )

    if user_rank is not None:

        lines.extend(
            [
                "",
                "━━━━━━━━━━━━━━",
                (
                    f"👤 Твоё место: "
                    f"<b>#{user_rank}</b>"
                ),
            ]
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=main_menu(
            WEBAPP_URL
        ),
    )


# ============================================================
# HELP
# ============================================================

async def show_help(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "👤 <b>Профиль</b>\n"
        "Твои очки, место в лидерборде и "
        "статистика прохождения.\n\n"
        "🏆 <b>Лидерборд</b>\n"
        "Топ игроков по количеству набранных очков.\n\n"
        "📝 <b>Как проходить квиз?</b>\n"
        "Открывай сегодняшний квиз, отвечай "
        "на вопросы и получай очки за правильные ответы.\n\n"
        "Каждый вопрос можно ответить только один раз."
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(
            WEBAPP_URL
        ),
    )


# ============================================================
# TEXT BUTTONS
# ============================================================

async def text_button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text

    if text == "👤 Профиль":

        await show_profile(
            update,
            context,
        )

    elif text == "🏆 Лидерборд":

        await show_leaderboard(
            update,
            context,
        )

    elif text == "ℹ️ Помощь":

        await show_help(
            update,
            context,
        )


# ============================================================
# CALLBACK BUTTONS
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    if query.data == "profile":

        await query.message.reply_text(
            (
                "Используй кнопку "
                "👤 <b>Профиль</b> "
                "в нижнем меню."
            ),
            parse_mode="HTML",
            reply_markup=main_menu(
                WEBAPP_URL
            ),
        )

    elif query.data == "leaderboard":

        await query.message.reply_text(
            (
                "Используй кнопку "
                "🏆 <b>Лидерборд</b> "
                "в нижнем меню."
            ),
            parse_mode="HTML",
            reply_markup=main_menu(
                WEBAPP_URL
            ),
        )

    elif query.data == "back_to_menu":

        await query.message.reply_text(
            "Главное меню 👇",
            reply_markup=main_menu(
                WEBAPP_URL
            ),
        )


# ============================================================
# WEB APP DATA
# ============================================================

async def web_app_data_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not update.message:
        return

    if not update.message.web_app_data:
        return

    data = update.message.web_app_data.data

    logger.info(
        "WEB APP DATA: telegram_id=%s data=%s",
        user.id if user else None,
        data,
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.exception(
        "Ошибка Telegram Bot:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "========================================"
    )

    logger.info(
        "FootballMeister Quiz Bot запускается..."
    )

    logger.info(
        "WEBAPP_URL = %s",
        WEBAPP_URL,
    )

    logger.info(
        "========================================"
    )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # /start
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # --------------------------------------------------------
    # Кнопки нижнего меню
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_button_handler,
        )
    )

    # --------------------------------------------------------
    # Callback-кнопки
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # --------------------------------------------------------
    # Данные от Telegram Web App
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            web_app_data_handler,
        )
    )

    # --------------------------------------------------------
    # Общий обработчик ошибок
    # --------------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "FootballMeister Quiz Bot запущен."
    )

    application.run_polling()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()