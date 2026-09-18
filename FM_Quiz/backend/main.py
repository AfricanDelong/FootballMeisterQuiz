from pathlib import Path

import hashlib
import hmac
import json
import os
import time

from datetime import date
from urllib.parse import parse_qsl

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException,
)

from fastapi.responses import FileResponse

from pydantic import BaseModel

from backend.database import (
    init_database,
    create_or_update_user,
    get_user,
    get_quiz_progress,
    get_quiz_result,
    submit_quiz_answer,
    complete_quiz,
)

from backend.quiz_parser import (
    get_today_quiz,
)


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

WEBAPP_DIR = BASE_DIR / "webapp"


load_dotenv(
    BASE_DIR / ".env"
)


BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден. Проверь файл .env"
    )


app = FastAPI(
    title="FootballMeister Quiz API",
    version="1.0.0",
)


init_database()


class TelegramAuthRequest(BaseModel):
    init_data: str


class QuizAnswerRequest(BaseModel):
    init_data: str
    question_id: int
    answer: str


def validate_telegram_init_data(
    init_data: str,
) -> dict:

    if not init_data:
        raise ValueError(
            "Telegram initData отсутствует"
        )

    parsed_data = dict(
        parse_qsl(
            init_data,
            keep_blank_values=True,
        )
    )

    received_hash = parsed_data.pop(
        "hash",
        None,
    )

    if not received_hash:
        raise ValueError(
            "В initData отсутствует hash"
        )

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value
        in sorted(
            parsed_data.items()
        )
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=BOT_TOKEN.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        calculated_hash,
        received_hash,
    ):
        raise ValueError(
            "Неверная подпись Telegram"
        )

    auth_date = parsed_data.get(
        "auth_date"
    )

    if auth_date:

        try:
            auth_timestamp = int(
                auth_date
            )

        except ValueError:
            raise ValueError(
                "Некорректный auth_date"
            )

        current_timestamp = int(
            time.time()
        )

        if (
            current_timestamp
            - auth_timestamp
            > 86400
        ):
            raise ValueError(
                "Telegram initData устарел"
            )

    return parsed_data


def get_telegram_user(
    data: dict,
) -> dict:

    user_data = data.get(
        "user"
    )

    if not user_data:
        raise ValueError(
            "Данные пользователя Telegram отсутствуют"
        )

    try:
        return json.loads(
            user_data
        )

    except json.JSONDecodeError:
        raise ValueError(
            "Не удалось прочитать данные пользователя Telegram"
        )


def authenticate_user(
    init_data: str,
) -> dict:

    try:

        data = validate_telegram_init_data(
            init_data
        )

        user = get_telegram_user(
            data
        )

    except ValueError as error:

        raise HTTPException(
            status_code=401,
            detail=str(error),
        )

    telegram_id = user.get(
        "id"
    )

    if not telegram_id:

        raise HTTPException(
            status_code=401,
            detail="Telegram ID отсутствует",
        )

    first_name = (
        user.get("first_name")
        or "Пользователь"
    )

    last_name = user.get(
        "last_name"
    )

    username = user.get(
        "username"
    )

    create_or_update_user(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )

    return {
        "telegram_id": telegram_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
    }


@app.get("/")
async def webapp():

    return FileResponse(
        WEBAPP_DIR / "index.html"
    )


@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "FootballMeister Quiz API",
    }


@app.post("/api/auth")
async def telegram_auth(
    request: TelegramAuthRequest,
):

    user = authenticate_user(
        request.init_data
    )

    db_user = get_user(
        user["telegram_id"]
    )

    return {
        "success": True,

        "message": (
            "Telegram пользователь "
            "подтверждён"
        ),

        "user": {
            "telegram_id":
                db_user["telegram_id"],

            "first_name":
                db_user["first_name"],

            "last_name":
                db_user["last_name"],

            "username":
                db_user["username"],

            "points":
                db_user["points"],

            "quizzes_completed":
                db_user["quizzes_completed"],

            "correct_answers":
                db_user["correct_answers"],
        },
    }


@app.post("/api/quiz/today")
async def today_quiz(
    request: TelegramAuthRequest,
):

    user = authenticate_user(
        request.init_data
    )

    today = date.today().isoformat()

    quiz = get_today_quiz(
        today
    )

    if quiz is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Квиз на дату "
                f"{today} не найден"
            ),
        )

    progress = get_quiz_progress(
        telegram_id=user["telegram_id"],
        quiz_date=today,
    )

    answered_ids = {
        row["question_id"]
        for row in progress
    }

    total_questions = len(
        quiz["questions"]
    )

    answered_count = len(
        answered_ids
    )

    completed = (
        answered_count
        >= total_questions
    )

    result = get_quiz_result(
        telegram_id=user["telegram_id"],
        quiz_date=today,
    )

    public_questions = []

    for index, question in enumerate(
        quiz["questions"]
    ):

        question_id = index + 1

        public_questions.append(
            {
                "id": question_id,

                "question":
                    question["question"],

                "points":
                    question["points"],

                "answered":
                    question_id
                    in answered_ids,
            }
        )

    return {
        "success": True,

        "title":
            quiz["title"],

        "date":
            quiz["date"],

        "completed":
            completed,

        "answered_questions":
            answered_count,

        "total_questions":
            total_questions,

        "points_earned":
            result["points_earned"],

        "questions":
            public_questions,
    }


@app.post("/api/quiz/answer")
async def answer_quiz_question(
    request: QuizAnswerRequest,
):

    if not request.answer.strip():

        raise HTTPException(
            status_code=400,
            detail="Ответ не может быть пустым",
        )

    user = authenticate_user(
        request.init_data
    )

    today = date.today().isoformat()

    quiz = get_today_quiz(
        today
    )

    if quiz is None:

        raise HTTPException(
            status_code=404,
            detail="Сегодняшний квиз не найден",
        )

    total_questions = len(
        quiz["questions"]
    )

    if (
        request.question_id < 1
        or request.question_id > total_questions
    ):

        raise HTTPException(
            status_code=400,
            detail="Некорректный номер вопроса",
        )

    progress = get_quiz_progress(
        telegram_id=user["telegram_id"],
        quiz_date=today,
    )

    answered_ids = {
        row["question_id"]
        for row in progress
    }

    if (
        len(answered_ids)
        >= total_questions
    ):

        raise HTTPException(
            status_code=409,
            detail="Сегодняшний квиз уже пройден",
        )

    question = quiz["questions"][
        request.question_id - 1
    ]

    result = submit_quiz_answer(
        telegram_id=user["telegram_id"],

        quiz_date=today,

        question_id=request.question_id,

        user_answer=request.answer,

        correct_answer=question["answer"],

        points=question["points"],
    )

    if result["already_answered"]:

        raise HTTPException(
            status_code=409,
            detail=(
                "На этот вопрос "
                "вы уже отвечали"
            ),
        )

    progress_after = get_quiz_progress(
        telegram_id=user["telegram_id"],
        quiz_date=today,
    )

    answered_count = len(
        progress_after
    )

    quiz_completed = (
        answered_count
        >= total_questions
    )

    points_earned_today = sum(
        row["points_earned"]
        for row in progress_after
    )

    if quiz_completed:

        complete_quiz(
            telegram_id=user["telegram_id"],

            quiz_date=today,

            points_earned=points_earned_today,
        )

    db_user = get_user(
        user["telegram_id"]
    )

    return {
        "success": True,

        "correct":
            result["correct"],

        "points_earned":
            result["points_earned"],

        "total_points":
            db_user["points"],

        "answered_questions":
            answered_count,

        "total_questions":
            total_questions,

        "quiz_completed":
            quiz_completed,
    }