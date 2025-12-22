# schedule_service.py
import requests
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List

class ScheduleService:
    API_URL = "https://digital.etu.ru/api/mobile/schedule"

    def __init__(self):
        self._cache: Dict[str, Dict] = {}

    def _fetch_schedule(self, group_number: str) -> Optional[Dict[str, Any]]:
        if group_number in self._cache:
            return self._cache[group_number]

        try:
            response = requests.get(f"{self.API_URL}?groupNumber={group_number}", timeout=10)
            response.raise_for_status()
            data = response.json()
            if group_number not in data:
                return None
            schedule = data[group_number]
            self._cache[group_number] = schedule
            return schedule
        except Exception as e:
            print(f"Ошибка при получении расписания: {e}")
            return None

    @staticmethod
    def _get_week_number(target_date: date) -> int:
        """Возвращает 1 для нечётной, 2 для чётной недели."""
        if target_date.month >= 9:
            start_year = target_date.year
        else:
            start_year = target_date.year - 1
        start_academic = date(start_year, 9, 1)
        days = (target_date - start_academic).days
        weeks = days // 7
        return 1 if weeks % 2 == 0 else 2

    @staticmethod
    def _day_to_index(day: str) -> int:
        days = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }
        return days.get(day.lower(), -1)

    @staticmethod
    def _format_lesson(lesson: Dict[str, Any], index: int = 0) -> str:
        def ru_type(t: str) -> str:
            return {"Лек": "Лекция", "Пр": "Практика", "Лаб": "Лабораторная"}.get(t, t)

        def ru_form(f: str) -> str:
            return {"standard": "Очно", "online": "Онлайн", "distant": "Дистанционно"}.get(f, f)

        lines = []
        if index > 0:
            lines.append(f"{index}.")
        lines.append(f"🕐 {lesson.get('start_time', '')} - {lesson.get('end_time', '')}")
        name = lesson.get("name", "")
        subj_type = lesson.get("subjectType")
        if subj_type:
            name += f" ({ru_type(subj_type)})"
        lines.append(f"📖 {name}")
        teachers = [t for t in [lesson.get("teacher"), lesson.get("second_teacher")] if t]
        if teachers:
            lines.append(f"👨‍🏫 {', '.join(teachers)}")
        room = lesson.get("room")
        form = lesson.get("form")
        loc = ""
        if room:
            loc = f"📍 Ауд. {room}"
            if form:
                loc += f" ({ru_form(form)})"
        elif form:
            loc = f"📍 {ru_form(form)}"
        if loc:
            lines.append(loc)
        url = lesson.get("url")
        if url:
            lines.append(f"🔗 {url}")
        return "\n".join(lines)

    def get_near_lesson(self, group_number: str) -> str:
        schedule = self._fetch_schedule(group_number)
        if not schedule:
            return f"❌ Группа {group_number} не найдена."

        now = datetime.now()
        today = now.date()
        current_time = now.time()
        today_index = today.weekday()
        week_num = self._get_week_number(today)

        day_data = schedule["days"].get(str(today_index))
        if day_data and day_data.get("lessons"):
            today_lessons = [l for l in day_data["lessons"] if l.get("week") == str(week_num)]
            for lesson in today_lessons:
                start = datetime.strptime(lesson["start_time"], "%H:%M").time()
                end = datetime.strptime(lesson["end_time"], "%H:%M").time()
                if start <= current_time <= end:
                    return "Сейчас идёт:\n" + self._format_lesson(lesson)
            for lesson in today_lessons:
                start = datetime.strptime(lesson["start_time"], "%H:%M").time()
                if start > current_time:
                    return "Ближайшая пара сегодня:\n" + self._format_lesson(lesson)

        for i in range(1, 8):
            future_date = today + timedelta(days=i)
            if future_date.weekday() == 6:
                continue
            w_num = self._get_week_number(future_date)
            idx = future_date.weekday()
            day_schedule = schedule["days"].get(str(idx))
            if not day_schedule or not day_schedule.get("lessons"):
                continue
            for lesson in day_schedule["lessons"]:
                if lesson.get("week") == str(w_num):
                    day_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]
                    prefix = "завтра" if i == 1 else day_names[idx]
                    return f"📅 Ближайшая пара будет {prefix} ({'нечётная' if w_num == 1 else 'чётная'} неделя):\n" + self._format_lesson(lesson)

        return "📭 Ближайших пар не найдено."

    def get_day_schedule(self, group_number: str, day: str, week_type: str) -> str:
        schedule = self._fetch_schedule(group_number)
        if not schedule:
            return f"❌ Группа {group_number} не найдена."

        day_idx = self._day_to_index(day)
        if day_idx == -1:
            return "❌ Неверный день недели."

        target_week = "1" if week_type == "odd" else "2"
        day_data = schedule["days"].get(str(day_idx))
        if not day_data or not day_data.get("lessons"):
            return f"📭 В этот день пар нет для группы {group_number}."

        lessons = [l for l in day_data["lessons"] if l.get("week") == target_week]
        if not lessons:
            return f"📭 На {'нечётную' if target_week == '1' else 'чётную'} неделю в этот день пар нет."

        day_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        result = f"📅 Расписание на {day_names[day_idx]} ({'нечётная' if target_week == '1' else 'чётная'} неделя) для группы {group_number}:\n\n"
        for i, lesson in enumerate(lessons, 1):
            result += self._format_lesson(lesson, i) + "\n\n"
        return result.strip()

    def get_tomorrow_schedule(self, group_number: str) -> str:
        tomorrow = datetime.now().date() + timedelta(days=1)
        if tomorrow.weekday() == 6:
            tomorrow += timedelta(days=1)
        w_num = self._get_week_number(tomorrow)
        day_idx = tomorrow.weekday()
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        return self.get_day_schedule(group_number, day_names[day_idx], "odd" if w_num == 1 else "even")

    def get_week_schedule(self, group_number: str, week_type: str) -> str:
        schedule = self._fetch_schedule(group_number)
        if not schedule:
            return f"❌ Группа {group_number} не найдена."

        target_week = "1" if week_type == "odd" else "2"
        day_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]
        result = f"📅 Расписание на {'нечётную' if target_week == '1' else 'чётную'} неделю для группы {group_number}:\n\n"
        has_any = False

        for i in range(6):
            day_data = schedule["days"].get(str(i))
            if not day_data or not day_data.get("lessons"):
                continue
            lessons = [l for l in day_data["lessons"] if l.get("week") == target_week]
            if not lessons:
                continue
            has_any = True
            result += f"--- {day_names[i].capitalize()} ---\n"
            for j, lesson in enumerate(lessons, 1):
                result += self._format_lesson(lesson, j) + "\n\n"

        if not has_any:
            return f"📭 На {'нечётной' if target_week == '1' else 'чётной'} неделе пар нет для группы {group_number}."
        return result.strip()