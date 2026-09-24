# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, abort
from data import HABITS, APP_NAME, APP_DESCRIPTION

app = Flask(__name__)
app.secret_key = "super-secret-key-for-habits-tracker"

# ---------- Вспомогательные функции ----------
def get_completed_ids():
    """ID выполненных привычек из session."""
    return session.get("completed", [])


def save_completed_ids(ids):
    """Сохранить ID выполненных привычек в session."""
    session["completed"] = ids
    session.modified = True


def get_custom_habits():
    """Пользовательские привычки из session."""
    return session.get("custom_habits", [])


def save_custom_habits(habits):
    """Сохранить пользовательские привычки в session."""
    session["custom_habits"] = habits
    session.modified = True


def get_all_habits():
    """Базовые + пользовательские привычки."""
    return HABITS + get_custom_habits()


def find_habit(habit_id):
    """Найти привычку по id среди всех."""
    for h in get_all_habits():
        if h["id"] == habit_id:
            return h
    return None


def next_custom_id():
    """Следующий свободный ID для пользовательской привычки.
    Начинаем с 1000, чтобы не пересекаться с базовыми."""
    custom = get_custom_habits()
    if not custom:
        return 1000
    return max(h["id"] for h in custom) + 1


# ---------- Маршруты ----------
@app.route("/")
def index():
    """Главная страница."""
    return render_template(
        "index.html",
        app_name=APP_NAME,
        description=APP_DESCRIPTION,
        total=len(get_all_habits()),
        completed_count=len(get_completed_ids()),
    )


@app.route("/app", methods=["GET", "POST"])
def app_page():
    """Основной экран: список привычек + добавление + отметки."""
    completed = get_completed_ids()
    error = None
    success = None

    if request.method == "POST":
        action = request.form.get("action")

        # --- Отметить выполненной ---
        if action == "complete":
            raw_id = request.form.get("habit_id", "").strip()
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

        # --- Сбросить прогресс ---
        elif action == "reset":
            save_completed_ids([])
            completed = []

        # --- Добавить новую привычку ---
        elif action == "add":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()

            # валидация
            if not title:
                error = "Название привычки не может быть пустым."
            elif len(title) < 3:
                error = "Название слишком короткое (минимум 3 символа)."
            elif len(title) > 80:
                error = "Название слишком длинное (максимум 80 символов)."
            elif not description:
                error = "Добавьте короткое описание привычки."
            elif len(description) > 200:
                error = "Описание слишком длинное (максимум 200 символов)."
            elif not category:
                error = "Выберите или введите категорию."
            elif len(category) > 30:
                error = "Название категории слишком длинное (максимум 30 символов)."
            elif any(h["title"].lower() == title.lower() for h in get_all_habits()):
                error = f"Привычка «{title}» уже есть в списке."
            else:
                new_habit = {
                    "id": next_custom_id(),
                    "title": title,
                    "description": description,
                    "category": category,
                    "image": "custom.png",   # картинка-заглушка
                    "custom": True,
                }
                custom = get_custom_habits()
                custom.append(new_habit)
                save_custom_habits(custom)
                success = f"Привычка «{title}» добавлена!"

        # --- Удалить пользовательскую привычку ---
        elif action == "delete":
            raw_id = request.form.get("habit_id", "").strip()
            if raw_id.isdigit():
                habit_id = int(raw_id)
                custom = get_custom_habits()
                new_custom = [h for h in custom if h["id"] != habit_id]
                if len(new_custom) != len(custom):
                    save_custom_habits(new_custom)
                    # если привычка была выполнена — убираем из completed
                    if habit_id in completed:
                        completed.remove(habit_id)
                        save_completed_ids(completed)
                    success = "Привычка удалена."
                else:
                    error = "Можно удалять только свои привычки."

        else:
            error = "Неизвестное действие."

        if error:
            return redirect(url_for("app_page", error=error))
        if success:
            return redirect(url_for("app_page", success=success))

    # GET
    error = request.args.get("error") or error
    success = request.args.get("success") or success

    return render_template(
        "app.html",
        app_name=APP_NAME,
        habits=get_all_habits(),
        completed=completed,
        error=error,
        success=success,
    )


@app.route("/progress")
def progress():
    """Страница прогресса и результатов."""
    all_habits = get_all_habits()
    completed = get_completed_ids()
    total = len(all_habits)
    done = len(completed)
    percent = round((done / total) * 100) if total else 0

    categories = {}
    for h in all_habits:
        cat = h["category"]
        categories.setdefault(cat, {"total": 0, "done": 0})
        categories[cat]["total"] += 1
        if h["id"] in completed:
            categories[cat]["done"] += 1

    completed_habits = [h for h in all_habits if h["id"] in completed]

    if percent == 100 and total > 0:
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
    return render_template("404.html", app_name=APP_NAME), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html", app_name=APP_NAME), 500


if __name__ == "__main__":
    app.run(debug=True)