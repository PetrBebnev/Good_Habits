# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, abort
from data import HABITS, APP_NAME, APP_DESCRIPTION

app = Flask(__name__)
app.secret_key = "super-secret-key-for-habits-tracker"  # для session


# ---------- Вспомогательные функции ----------
def get_completed_ids():
    """Возвращает список ID выполненных привычек из session."""
    return session.get("completed", [])


def save_completed_ids(ids):
    """Сохраняет список ID выполненных привычек в session."""
    session["completed"] = ids
    session.modified = True


def find_habit(habit_id):
    """Ищет привычку по id, иначе возвращает None."""
    for h in HABITS:
        if h["id"] == habit_id:
            return h
    return None


# ---------- Маршруты ----------
@app.route("/")
def index():
    """Главная страница."""
    return render_template(
        "index.html",
        app_name=APP_NAME,
        description=APP_DESCRIPTION,
        total=len(HABITS),
        completed_count=len(get_completed_ids()),
    )


@app.route("/app", methods=["GET", "POST"])
def app_page():
    """Основной экран со списком привычек."""
    completed = get_completed_ids()
    error = None

    if request.method == "POST":
        action = request.form.get("action")

        # --- Отметить выполненной ---
        if action == "complete":
            raw_id = request.form.get("habit_id", "").strip()

            # защита от "глупостей": пустой/нечисловой id
            if not raw_id or not raw_id.isdigit():
                error = "Не выбрана привычка. Попробуйте ещё раз."
            else:
                habit_id = int(raw_id)
                habit = find_habit(habit_id)
                if habit is None:
                    error = "Такой привычки не существует."
                elif habit_id in completed:
                    error = f"Привычка «{habit['title']}» уже отмечена как выполненная."
                else:
                    completed.append(habit_id)
                    save_completed_ids(completed)

        # --- Снять отметку ---
        elif action == "uncomplete":
            raw_id = request.form.get("habit_id", "").strip()
            if raw_id.isdigit():
                habit_id = int(raw_id)
                if habit_id in completed:
                    completed.remove(habit_id)
                    save_completed_ids(completed)

        # --- Сбросить всё ---
        elif action == "reset":
            save_completed_ids([])
            completed = []

        else:
            error = "Неизвестное действие."

        return redirect(url_for("app_page", error=error) if error else url_for("app_page"))

    # GET: показываем возможную ошибку из query-строки
    error = request.args.get("error") or error
    return render_template(
        "app.html",
        app_name=APP_NAME,
        habits=HABITS,
        completed=completed,
        error=error,
    )


@app.route("/progress")
def progress():
    """Страница прогресса/результатов."""
    completed = get_completed_ids()
    total = len(HABITS)
    done = len(completed)
    percent = round((done / total) * 100) if total else 0

    # статистика по категориям
    categories = {}
    for h in HABITS:
        cat = h["category"]
        categories.setdefault(cat, {"total": 0, "done": 0})
        categories[cat]["total"] += 1
        if h["id"] in completed:
            categories[cat]["done"] += 1

    completed_habits = [h for h in HABITS if h["id"] in completed]

    # мотивационное сообщение
    if percent == 100:
        message = "Потрясающе! Ты выполнил все привычки! 🏆"
    elif percent >= 70:
        message = "Отличный результат! Ты почти у цели! 💪"
    elif percent >= 40:
        message = "Хорошее начало! Продолжай в том же духе. 🌟"
    elif percent > 0:
        message = "Ты уже сделал первый шаг — не останавливайся! 🚀"
    else:
        message = "Начни отмечать привычки — и здесь появится твой прогресс."

    return render_template(
        "progress.html",
        app_name=APP_NAME,
        total=total,
        done=done,
        percent=percent,
        categories=categories,
        completed_habits=completed_habits,
        message=message,
    )


# ---------- Обработчики ошибок ----------
@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "base.html",
        app_name=APP_NAME,
        error_title="404 — Страница не найдена",
        error_text="Кажется, такой страницы не существует. Проверьте адрес или вернитесь на главную.",
    ), 404


@app.errorhandler(500)
def server_error(e):
    return render_template(
        "base.html",
        app_name=APP_NAME,
        error_title="500 — Внутренняя ошибка",
        error_text="Что-то пошло не так на сервере. Попробуйте позже.",
    ), 500


if __name__ == "__main__":
    app.run(debug=True)