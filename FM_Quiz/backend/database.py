import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "footballmeister.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT,
            username TEXT,
            points INTEGER NOT NULL DEFAULT 0,
            quizzes_completed INTEGER NOT NULL DEFAULT 0,
            correct_answers INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            quiz_date TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            points_earned INTEGER NOT NULL DEFAULT 0,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (
                telegram_id,
                quiz_date,
                question_id
            ),

            FOREIGN KEY (telegram_id)
            REFERENCES users (telegram_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            quiz_date TEXT NOT NULL,
            points_earned INTEGER NOT NULL DEFAULT 0,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE (
                telegram_id,
                quiz_date
            ),

            FOREIGN KEY (telegram_id)
            REFERENCES users (telegram_id)
        )
        """
    )

    connection.commit()
    connection.close()


def get_user(telegram_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    user = cursor.fetchone()

    connection.close()

    return user


def create_or_update_user(
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO users (
            telegram_id,
            first_name,
            last_name,
            username
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            username = excluded.username,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            telegram_id,
            first_name,
            last_name,
            username,
        ),
    )

    connection.commit()
    connection.close()

    return get_user(telegram_id)


def get_quiz_progress(
    telegram_id: int,
    quiz_date: str,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            question_id,
            answer,
            is_correct,
            points_earned
        FROM quiz_answers
        WHERE telegram_id = ?
          AND quiz_date = ?
        ORDER BY question_id
        """,
        (
            telegram_id,
            quiz_date,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


def get_quiz_result(
    telegram_id: int,
    quiz_date: str,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) AS answered_questions,
            COALESCE(
                SUM(points_earned),
                0
            ) AS points_earned
        FROM quiz_answers
        WHERE telegram_id = ?
          AND quiz_date = ?
        """,
        (
            telegram_id,
            quiz_date,
        ),
    )

    result = cursor.fetchone()

    connection.close()

    return result


def normalize_answer(answer: str) -> str:
    return " ".join(
        answer.strip().lower().split()
    )


def submit_quiz_answer(
    telegram_id: int,
    quiz_date: str,
    question_id: int,
    user_answer: str,
    correct_answer: str,
    points: int,
):
    normalized_user_answer = normalize_answer(
        user_answer
    )

    normalized_correct_answer = normalize_answer(
        correct_answer
    )

    is_correct = (
        normalized_user_answer
        == normalized_correct_answer
    )

    points_earned = (
        points
        if is_correct
        else 0
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO quiz_answers (
                telegram_id,
                quiz_date,
                question_id,
                answer,
                is_correct,
                points_earned
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                quiz_date,
                question_id,
                user_answer,
                1 if is_correct else 0,
                points_earned,
            ),
        )

        cursor.execute(
            """
            UPDATE users
            SET
                points = points + ?,
                correct_answers =
                    correct_answers + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            (
                points_earned,
                1 if is_correct else 0,
                telegram_id,
            ),
        )

        connection.commit()

    except sqlite3.IntegrityError:
        connection.rollback()

        cursor.execute(
            """
            SELECT
                is_correct,
                points_earned
            FROM quiz_answers
            WHERE telegram_id = ?
              AND quiz_date = ?
              AND question_id = ?
            """,
            (
                telegram_id,
                quiz_date,
                question_id,
            ),
        )

        existing = cursor.fetchone()

        connection.close()

        return {
            "already_answered": True,
            "correct": bool(
                existing["is_correct"]
            ) if existing else False,
            "points_earned": (
                existing["points_earned"]
                if existing
                else 0
            ),
        }

    connection.close()

    return {
        "already_answered": False,
        "correct": is_correct,
        "points_earned": points_earned,
    }


def complete_quiz(
    telegram_id: int,
    quiz_date: str,
    points_earned: int,
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO quiz_completions (
                telegram_id,
                quiz_date,
                points_earned
            )
            VALUES (?, ?, ?)
            """,
            (
                telegram_id,
                quiz_date,
                points_earned,
            ),
        )

        inserted = cursor.rowcount

        if inserted == 0:
            connection.rollback()
            connection.close()
            return False

        cursor.execute(
            """
            UPDATE users
            SET
                quizzes_completed =
                    quizzes_completed + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        connection.close()
        raise

    connection.close()

    return True


def is_quiz_completed(
    telegram_id: int,
    quiz_date: str,
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM quiz_completions
        WHERE telegram_id = ?
          AND quiz_date = ?
        LIMIT 1
        """,
        (
            telegram_id,
            quiz_date,
        ),
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


def get_leaderboard(limit: int = 10):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            telegram_id,
            first_name,
            last_name,
            username,
            points
        FROM users
        WHERE points > 0
        ORDER BY
            points DESC,
            updated_at ASC,
            telegram_id ASC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


def get_user_rank(telegram_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT points
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )

    user = cursor.fetchone()

    if user is None:
        connection.close()
        return None

    user_points = user["points"]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE points > ?
        """,
        (user_points,),
    )

    higher_count = cursor.fetchone()[0]

    connection.close()

    return higher_count + 1