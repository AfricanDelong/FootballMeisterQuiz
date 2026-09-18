from pathlib import Path


# ========================================
# PATHS
# ========================================

BASE_DIR = Path(__file__).resolve().parent.parent

QUIZZES_DIR = BASE_DIR / "quizzes"


# ========================================
# PARSER
# ========================================

def parse_quiz_file(
    file_path: Path,
) -> dict:

    text = file_path.read_text(
        encoding="utf-8"
    )

    blocks = text.split("---")

    title = ""
    date = ""

    questions = []


    # ========================================
    # PARSE BLOCKS
    # ========================================

    for block in blocks:

        lines = [
            line.strip()
            for line in block.splitlines()
        ]


        # Убираем пустые строки

        lines = [
            line
            for line in lines
            if line
        ]


        if not lines:
            continue


        # ====================================
        # TITLE
        # ====================================

        for line in lines:

            if line.startswith("TITLE:"):

                title = line[
                    len("TITLE:"):
                ].strip()


            elif line.startswith("DATE:"):

                date = line[
                    len("DATE:"):
                ].strip()


        # ====================================
        # QUESTION
        # ====================================

        question = None
        answer = None
        points = 0


        i = 0


        while i < len(lines):

            line = lines[i]


            # ==================================
            # QUESTION
            # ==================================

            if line == "QUESTION:":

                if i + 1 < len(lines):

                    question = lines[i + 1].strip()

                    i += 2

                    continue


            # ==================================
            # ANSWER
            # ==================================

            if line == "ANSWER:":

                if i + 1 < len(lines):

                    answer = lines[i + 1].strip()

                    i += 2

                    continue


            # ==================================
            # POINTS
            # ==================================

            if line == "POINTS:":

                if i + 1 < len(lines):

                    points_text = (
                        lines[i + 1].strip()
                    )


                    try:

                        points = int(
                            points_text
                        )

                    except ValueError:

                        points = 0


                    i += 2

                    continue


            # ==================================
            # SAME-LINE FORMAT
            # ==================================

            if line.startswith("QUESTION:"):

                question = line[
                    len("QUESTION:")
                ].strip()


            elif line.startswith("ANSWER:"):

                answer = line[
                    len("ANSWER:")
                ].strip()


            elif line.startswith("POINTS:"):

                points_text = line[
                    len("POINTS:")
                ].strip()


                try:

                    points = int(
                        points_text
                    )

                except ValueError:

                    points = 0


            i += 1


        # ====================================
        # ADD QUESTION
        # ====================================

        if question and answer:

            questions.append(
                {
                    "question": question,
                    "answer": answer,
                    "points": points,
                }
            )


    # ========================================
    # RESULT
    # ========================================

    return {

        "title": title,

        "date": date,

        "questions": questions,

    }


# ========================================
# TODAY QUIZ
# ========================================

def get_today_quiz(
    date: str,
) -> dict | None:

    file_path = (
        QUIZZES_DIR
        / f"{date}.txt"
    )


    if not file_path.exists():

        return None


    return parse_quiz_file(
        file_path
    )