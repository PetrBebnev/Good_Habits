# -*- coding: utf-8 -*-
"""
Полный набор тестов для приложения «Полезные привычки».

Покрытие:
  - Главная страница
  - Список привычек (/app): отметка, снятие, сброс
  - Добавление пользовательских привычек
  - Удаление пользовательских привычек
  - Валидация формы добавления
  - Страница прогресса (/progress)
  - Обработка ошибок (404, пустые данные, дубликаты)
  - Данные из data.py

Запуск:
    python -m pytest -v
    python -m unittest test_app -v
"""

import unittest
from app import app
from data import HABITS


class HabitsTrackerTestCase(unittest.TestCase):
    """Базовый класс: настройка клиента и очистка сессии."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        self.client = app.test_client()

    def tearDown(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    # ---- вспомогательные методы ----
    def add_habit(self, title="Тестовая привычка",
                  description="Описание тестовой привычки",
                  category="Тест"):
        """Отправить форму добавления привычки."""
        return self.client.post(
            "/app",
            data={
                "action": "add",
                "title": title,
                "description": description,
                "category": category,
            },
            follow_redirects=True,
        )

    def complete_habit(self, habit_id):
        """Отметить привычку выполненной."""
        return self.client.post(
            "/app",
            data={"action": "complete", "habit_id": str(habit_id)},
            follow_redirects=True,
        )

    def get_custom_habits(self):
        """Вернуть список пользовательских привычек из session."""
        with self.client.session_transaction() as sess:
            return sess.get("custom_habits", [])

    def get_completed(self):
        """Вернуть список выполненных привычек из session."""
        with self.client.session_transaction() as sess:
            return sess.get("completed", [])


# ============================================================
# 1. Главная страница
# ============================================================
class TestIndexPage(HabitsTrackerTestCase):

    def test_index_loads(self):
        """Главная страница открывается и возвращает 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_index_contains_app_name(self):
        """На главной есть название приложения."""
        response = self.client.get("/")
        self.assertIn("Полезные привычки".encode("utf-8"), response.data)

    def test_index_has_buttons(self):
        """На главной есть кнопки «Начать» и «Посмотреть прогресс»."""
        response = self.client.get("/")
        self.assertIn("Начать".encode("utf-8"), response.data)
        self.assertIn("прогресс".encode("utf-8"), response.data)

    def test_index_shows_total_count(self):
        """На главной указано количество привычек."""
        response = self.client.get("/")
        self.assertIn(str(len(HABITS)).encode("utf-8"), response.data)


# ============================================================
# 2. Основной экран со списком привычек
# ============================================================
class TestAppPage(HabitsTrackerTestCase):

    def test_app_page_loads(self):
        """Страница /app открывается."""
        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)

    def test_all_base_habits_displayed(self):
        """На странице отображаются все базовые привычки."""
        response = self.client.get("/app")
        for habit in HABITS:
            self.assertIn(
                habit["title"].encode("utf-8"),
                response.data,
                msg=f"Привычка '{habit['title']}' не найдена на странице",
            )

    def test_mark_habit_as_completed(self):
        """Отметка привычки сохраняется в session."""
        habit_id = HABITS[0]["id"]
        self.complete_habit(habit_id)
        self.assertIn(habit_id, self.get_completed())

    def test_unmark_habit(self):
        """Снятие отметки удаляет привычку из session."""
        habit_id = HABITS[0]["id"]
        self.complete_habit(habit_id)
        self.client.post(
            "/app",
            data={"action": "uncomplete", "habit_id": str(habit_id)},
            follow_redirects=True,
        )
        self.assertNotIn(habit_id, self.get_completed())

    def test_reset_progress(self):
        """Сброс прогресса очищает completed."""
        for habit in HABITS[:3]:
            self.complete_habit(habit["id"])

        self.client.post(
            "/app",
            data={"action": "reset"},
            follow_redirects=True,
        )
        self.assertEqual(self.get_completed(), [])

    def test_reset_does_not_delete_custom_habits(self):
        """Сброс прогресса не удаляет пользовательские привычки."""
        self.add_habit("Моя привычка")
        self.complete_habit(HABITS[0]["id"])

        self.client.post("/app", data={"action": "reset"},
                         follow_redirects=True)

        self.assertEqual(self.get_completed(), [])
        self.assertEqual(len(self.get_custom_habits()), 1)


# ============================================================
# 3. Добавление пользовательских привычек
# ============================================================
class TestAddHabit(HabitsTrackerTestCase):

    def test_add_habit_success(self):
        """Успешное добавление новой привычки."""
        response = self.add_habit("Пить зелёный чай",
                                  "Каждое утро",
                                  "Здоровье")
        self.assertEqual(response.status_code, 200)
        self.assertIn("добавлена".encode("utf-8"), response.data)
        self.assertIn("Пить зелёный чай".encode("utf-8"), response.data)

        customs = self.get_custom_habits()
        self.assertEqual(len(customs), 1)
        self.assertEqual(customs[0]["title"], "Пить зелёный чай")
        self.assertEqual(customs[0]["category"], "Здоровье")
        self.assertTrue(customs[0].get("custom"))

    def test_add_multiple_habits(self):
        """Можно добавить несколько привычек."""
        self.add_habit("Первая привычка")
        self.add_habit("Вторая привычка")
        self.add_habit("Третья привычка")
        self.assertEqual(len(self.get_custom_habits()), 3)

    def test_custom_habit_id_starts_from_1000(self):
        """ID пользовательских привычек начинается с 1000."""
        self.add_habit("Первая")
        customs = self.get_custom_habits()
        self.assertEqual(customs[0]["id"], 1000)

    def test_custom_ids_are_unique(self):
        """ID пользовательских привычек уникальны."""
        self.add_habit("Первая")
        self.add_habit("Вторая")
        self.add_habit("Третья")
        ids = [h["id"] for h in self.get_custom_habits()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_add_empty_title_fails(self):
        """Пустое название → ошибка, ничего не сохраняется."""
        response = self.add_habit(title="")
        self.assertIn("не может быть пустым".encode("utf-8"), response.data)
        self.assertEqual(self.get_custom_habits(), [])

    def test_add_short_title_fails(self):
        """Слишком короткое название → ошибка."""
        response = self.add_habit(title="Аб")
        self.assertIn("слишком короткое".encode("utf-8"), response.data)

    def test_add_long_title_fails(self):
        """Слишком длинное название → ошибка."""
        response = self.add_habit(title="А" * 100)
        self.assertIn("слишком длинное".encode("utf-8"), response.data)

    def test_add_empty_description_fails(self):
        """Пустое описание → ошибка."""
        response = self.add_habit(description="")
        self.assertIn("короткое описание".encode("utf-8"), response.data)

    def test_add_long_description_fails(self):
        """Слишком длинное описание → ошибка."""
        response = self.add_habit(description="А" * 250)
        self.assertIn("слишком длинное".encode("utf-8"), response.data)

    def test_add_empty_category_fails(self):
        """Пустая категория → ошибка."""
        response = self.add_habit(category="")
        self.assertIn("категорию".encode("utf-8"), response.data)

    def test_add_duplicate_title_fails(self):
        """Дубликат названия → ошибка."""
        self.add_habit("Уникальная привычка")
        response = self.add_habit("Уникальная привычка")
        self.assertIn("уже есть".encode("utf-8"), response.data)
        self.assertEqual(len(self.get_custom_habits()), 1)

    def test_add_duplicate_case_insensitive(self):
        """Дубликат в другом регистре тоже отклоняется."""
        self.add_habit("Полезная Привычка")
        response = self.add_habit("полезная привычка")
        self.assertIn("уже есть".encode("utf-8"), response.data)

    def test_add_duplicate_of_base_habit_fails(self):
        """Нельзя дублировать базовую привычку."""
        base_title = HABITS[0]["title"]
        response = self.add_habit(base_title)
        self.assertIn("уже есть".encode("utf-8"), response.data)

    def test_custom_habit_appears_in_list(self):
        """Добавленная привычка появляется на /app."""
        self.add_habit("Моя уникальная привычка")
        response = self.client.get("/app")
        self.assertIn("Моя уникальная привычка".encode("utf-8"),
                      response.data)


# ============================================================
# 4. Удаление пользовательских привычек
# ============================================================
class TestDeleteHabit(HabitsTrackerTestCase):

    def test_delete_custom_habit(self):
        """Пользовательскую привычку можно удалить."""
        self.add_habit("Временная привычка")
        habit_id = self.get_custom_habits()[0]["id"]

        response = self.client.post(
            "/app",
            data={"action": "delete", "habit_id": str(habit_id)},
            follow_redirects=True,
        )
        self.assertIn("удалена".encode("utf-8"), response.data)
        self.assertEqual(self.get_custom_habits(), [])

    def test_delete_removes_from_completed(self):
        """Удаление привычки убирает её из completed."""
        self.add_habit("Временная")
        habit_id = self.get_custom_habits()[0]["id"]
        self.complete_habit(habit_id)
        self.assertIn(habit_id, self.get_completed())

        self.client.post(
            "/app",
            data={"action": "delete", "habit_id": str(habit_id)},
            follow_redirects=True,
        )
        self.assertNotIn(habit_id, self.get_completed())

    def test_cannot_delete_base_habit(self):
        """Базовую привычку удалить нельзя."""
        base_id = HABITS[0]["id"]
        response = self.client.post(
            "/app",
            data={"action": "delete", "habit_id": str(base_id)},
            follow_redirects=True,
        )
        self.assertIn("только свои".encode("utf-8"), response.data)

    def test_delete_nonexistent_habit(self):
        """Удаление несуществующей привычки → ошибка."""
        response = self.client.post(
            "/app",
            data={"action": "delete", "habit_id": "9999"},
            follow_redirects=True,
        )
        self.assertIn("только свои".encode("utf-8"), response.data)


# ============================================================
# 5. Валидация / защита от ошибок
# ============================================================
class TestErrorHandling(HabitsTrackerTestCase):

    def test_empty_habit_id_shows_error(self):
        """Пустой habit_id → ошибка, ничего не сохраняется."""
        response = self.client.post(
            "/app",
            data={"action": "complete", "habit_id": ""},
            follow_redirects=True,
        )
        self.assertIn("Не выбрана привычка".encode("utf-8"), response.data)
        self.assertEqual(self.get_completed(), [])

    def test_non_digit_habit_id_shows_error(self):
        """Нечисловой habit_id → ошибка."""
        response = self.client.post(
            "/app",
            data={"action": "complete", "habit_id": "abc"},
            follow_redirects=True,
        )
        self.assertIn("Не выбрана привычка".encode("utf-8"), response.data)

    def test_nonexistent_habit_id_shows_error(self):
        """Несуществующий id привычки → ошибка."""
        response = self.client.post(
            "/app",
            data={"action": "complete", "habit_id": "9999"},
            follow_redirects=True,
        )
        self.assertIn("не существует".encode("utf-8"), response.data)

    def test_duplicate_completion_shows_warning(self):
        """Повторная отметка → предупреждение."""
        habit_id = HABITS[0]["id"]
        self.complete_habit(habit_id)
        response = self.complete_habit(habit_id)
        self.assertIn("уже отмечена".encode("utf-8"), response.data)

    def test_unknown_action_shows_error(self):
        """Неизвестное действие → ошибка."""
        response = self.client.post(
            "/app",
            data={"action": "hack", "habit_id": "1"},
            follow_redirects=True,
        )
        self.assertIn("Неизвестное действие".encode("utf-8"),
                      response.data)

    def test_404_page(self):
        """Несуществующая страница → 404 с сообщением."""
        response = self.client.get("/no-such-page")
        self.assertEqual(response.status_code, 404)
        self.assertIn("не найдена".encode("utf-8"), response.data)

    def test_404_page_has_link_home(self):
        """На странице 404 есть ссылка на главную."""
        response = self.client.get("/unknown")
        self.assertIn("главную".encode("utf-8"), response.data)


# ============================================================
# 6. Страница прогресса
# ============================================================
class TestProgressPage(HabitsTrackerTestCase):

    def test_progress_loads_empty(self):
        """Прогресс открывается при пустой статистике."""
        response = self.client.get("/progress")
        self.assertEqual(response.status_code, 200)
        self.assertIn("0 /".encode("utf-8"), response.data)

    def test_progress_after_completion(self):
        """После отметки привычка попадает в выполненные."""
        habit_id = HABITS[0]["id"]
        self.complete_habit(habit_id)

        response = self.client.get("/progress")
        self.assertIn(HABITS[0]["title"].encode("utf-8"), response.data)

    def test_progress_percent_100(self):
        """При выполнении всех привычек = 100%."""
        for habit in HABITS:
            self.complete_habit(habit["id"])

        response = self.client.get("/progress")
        self.assertIn("100%".encode("utf-8"), response.data)
        self.assertIn("Потрясающе".encode("utf-8"), response.data)

    def test_progress_empty_message(self):
        """При пустом прогрессе показывается мотивация."""
        response = self.client.get("/progress")
        self.assertIn("Начни отмечать".encode("utf-8"), response.data)

    def test_progress_shows_categories(self):
        """На прогрессе есть категории привычек."""
        response = self.client.get("/progress")
        for habit in HABITS:
            self.assertIn(habit["category"].encode("utf-8"),
                          response.data)

    def test_progress_includes_custom_habit_category(self):
        """Категория пользовательской привычки появляется на /progress."""
        self.add_habit("Моя привычка", "Описание", "Своя категория")
        response = self.client.get("/progress")
        self.assertIn("Своя категория".encode("utf-8"), response.data)

    def test_progress_includes_custom_completed(self):
        """Выполненная пользовательская привычка видна на /progress."""
        self.add_habit("Своя привычка", "Описание", "Своя категория")
        habit_id = self.get_custom_habits()[0]["id"]
        self.complete_habit(habit_id)

        response = self.client.get("/progress")
        self.assertIn("Своя привычка".encode("utf-8"), response.data)


# ============================================================
# 7. Данные из data.py
# ============================================================
class TestData(unittest.TestCase):

    def test_minimum_habits_count(self):
        """В data.py минимум 10 привычек."""
        self.assertGreaterEqual(len(HABITS), 10)

    def test_habit_fields(self):
        """У каждой привычки есть обязательные поля."""
        required = {"id", "title", "description", "category", "image"}
        for habit in HABITS:
            self.assertTrue(
                required.issubset(habit.keys()),
                msg=f"У привычки {habit.get('title')} не хватает полей",
            )

    def test_unique_ids(self):
        """ID базовых привычек уникальны."""
        ids = [h["id"] for h in HABITS]
        self.assertEqual(len(ids), len(set(ids)),
                         "ID привычек должны быть уникальны")

    def test_unique_titles(self):
        """Названия базовых привычек уникальны."""
        titles = [h["title"].lower() for h in HABITS]
        self.assertEqual(len(titles), len(set(titles)),
                         "Названия привычек должны быть уникальны")

    def test_categories_not_empty(self):
        """У каждой привычки есть категория."""
        for habit in HABITS:
            self.assertTrue(habit["category"].strip(),
                            f"У '{habit['title']}' пустая категория")

    def test_titles_not_empty(self):
        """У каждой привычки есть название."""
        for habit in HABITS:
            self.assertTrue(habit["title"].strip(),
                            f"Пустое название у привычки с id={habit['id']}")


# ============================================================
# 8. Интеграционные сценарии
# ============================================================
class TestIntegrationScenarios(HabitsTrackerTestCase):

    def test_full_user_journey(self):
        """Полный путь пользователя: зайти, добавить, отметить, посмотреть."""
        # 1. Открыть главную
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)

        # 2. Открыть /app
        r = self.client.get("/app")
        self.assertEqual(r.status_code, 200)

        # 3. Добавить привычку
        self.add_habit("Моя привычка дня", "Описание", "Моё")

        # 4. Отметить базовую привычку
        self.complete_habit(HABITS[0]["id"])

        # 5. Отметить пользовательскую привычку
        custom_id = self.get_custom_habits()[0]["id"]
        self.complete_habit(custom_id)

        # 6. Проверить прогресс
        r = self.client.get("/progress")
        self.assertIn("Моя привычка дня".encode("utf-8"), r.data)
        self.assertIn(HABITS[0]["title"].encode("utf-8"), r.data)

        # 7. Проверить, что в session оба ID
        completed = self.get_completed()
        self.assertIn(HABITS[0]["id"], completed)
        self.assertIn(custom_id, completed)

    def test_progress_persists_across_requests(self):
        """Прогресс сохраняется между запросами."""
        self.complete_habit(HABITS[0]["id"])
        self.client.get("/progress")
        self.client.get("/app")
        self.assertEqual(self.get_completed(), [HABITS[0]["id"]])

    def test_add_and_delete_then_add_again(self):
        """Можно добавить, удалить и снова добавить привычку."""
        self.add_habit("Привычка X")
        habit_id = self.get_custom_habits()[0]["id"]

        self.client.post("/app",
                         data={"action": "delete",
                               "habit_id": str(habit_id)},
                         follow_redirects=True)
        self.assertEqual(self.get_custom_habits(), [])

        self.add_habit("Привычка X")
        self.assertEqual(len(self.get_custom_habits()), 1)


# ============================================================
# Запуск
# ============================================================
if __name__ == "__main__":
    unittest.main(verbosity=2)