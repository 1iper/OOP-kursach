# bot_handler.py
from telebot import TeleBot, types
from schedule_service import ScheduleService
from typing import Dict

class UserState:
    def __init__(self, step: str = "", action: str = "", week_type: str = "", day: str = ""):
        self.step = step          # awaiting_group, week_type, day_selection
        self.action = action      # near_lesson, tomorrow, day, week
        self.week_type = week_type
        self.day = day

class BotHandler:
    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.service = ScheduleService()
        self.user_states: Dict[int, UserState] = {}

    def register_handlers(self):
        self.bot.message_handler(commands=['start'])(self.handle_start)
        self.bot.message_handler(commands=['near_lesson'])(self.handle_near_lesson_cmd)
        self.bot.message_handler(commands=['tommorow'])(self.handle_tomorrow_cmd)
        self.bot.message_handler(commands=['all'])(self.handle_all_cmd)
        self.bot.message_handler(func=self.is_day_command)(self.handle_day_cmd)
        self.bot.message_handler(func=lambda m: True)(self.handle_text)

    def is_day_command(self, message):
        if not message.text:
            return False
        parts = message.text.split()
        if len(parts) < 3:
            return False
        day = parts[0].lower()
        return day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def handle_start(self, message):
        self.user_states.pop(message.chat.id, None)
        self.send_main_menu(message.chat.id, "👋 Привет! Я бот с расписанием ЛЭТИ.\n📚 Выберите действие:")

    def send_main_menu(self, chat_id, text):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📚 Ближайшая пара", "📅 Завтра")
        markup.row("📖 День", "🗓️ Неделя")
        self.bot.send_message(chat_id, text, reply_markup=markup)

    def send_week_type_menu(self, chat_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row("Чётная неделя", "Нечётная неделя")
        self.bot.send_message(chat_id, "Выберите тип недели:", reply_markup=markup)

    def send_day_menu(self, chat_id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        days = [
            ("Понедельник", "monday"),
            ("Вторник", "tuesday"),
            ("Среда", "wednesday"),
            ("Четверг", "thursday"),
            ("Пятница", "friday"),
            ("Суббота", "saturday")
        ]
        buttons = [types.InlineKeyboardButton(text=name, callback_data=f"day_{eng}") for name, eng in days]
        markup.add(*buttons)
        self.bot.send_message(chat_id, "Выберите день недели:", reply_markup=markup)

    def handle_text(self, message):
        chat_id = message.chat.id
        text = message.text.strip()

        state = self.user_states.get(chat_id)

        if state and state.step == "awaiting_group":
            self.process_group_input(chat_id, text, state)
            return

        if state and state.step == "week_type":
            if "нечётная" in text.lower():
                state.week_type = "odd"
                self.user_states[chat_id] = state
                if state.action == "day":
                    state.step = "day_selection"
                    self.send_day_menu(chat_id)
                elif state.action == "week":
                    state.step = "awaiting_group"
                    self.bot.send_message(chat_id, "Введите номер группы (например: 4353):")
            elif "чётная" in text.lower():
                state.week_type = "even"
                self.user_states[chat_id] = state
                if state.action == "day":
                    state.step = "day_selection"
                    self.send_day_menu(chat_id)
                elif state.action == "week":
                    state.step = "awaiting_group"
                    self.bot.send_message(chat_id, "Введите номер группы (например: 4353):")
            else:
                self.send_week_type_menu(chat_id)
            return

        # обработка кнопок главного меню
        if text == "📚 Ближайшая пара":
            self.user_states[chat_id] = UserState(step="awaiting_group", action="near_lesson")
            self.bot.send_message(chat_id, "Введите номер группы (например: 4353):")
        elif text == "📅 Завтра":
            self.user_states[chat_id] = UserState(step="awaiting_group", action="tomorrow")
            self.bot.send_message(chat_id, "Введите номер группы (например: 4353):")
        elif text == "📖 День":
            self.user_states[chat_id] = UserState(step="week_type", action="day")
            self.send_week_type_menu(chat_id)
        elif text == "🗓️ Неделя":
            self.user_states[chat_id] = UserState(step="week_type", action="week")
            self.send_week_type_menu(chat_id)
        else:
            self.send_main_menu(chat_id, "❌ Неизвестная команда. Выберите действие:")

    def handle_near_lesson_cmd(self, message):
        parts = message.text.split()
        if len(parts) < 2:
            self.bot.reply_to(message, "Использование: /near_lesson <номер_группы>")
            return
        group = parts[1]
        response = self.service.get_near_lesson(group)
        self.bot.send_message(message.chat.id, response)

    def handle_tomorrow_cmd(self, message):
        parts = message.text.split()
        if len(parts) < 2:
            self.bot.reply_to(message, "Использование: /tommorow <номер_группы>")
            return
        group = parts[1]
        response = self.service.get_tomorrow_schedule(group)
        self.bot.send_message(message.chat.id, response)

    def handle_all_cmd(self, message):
        parts = message.text.split()
        if len(parts) < 3:
            self.bot.reply_to(message, "Использование: /all <odd|even> <номер_группы>")
            return
        week_type = parts[1].lower()
        group = parts[2]
        if week_type not in ("odd", "even"):
            self.bot.reply_to(message, "Неделя должна быть 'odd' или 'even'")
            return
        response = self.service.get_week_schedule(group, week_type)
        self.bot.send_message(message.chat.id, response)

    def handle_day_cmd(self, message):
        parts = message.text.split()
        day = parts[0].lower()
        week_type = parts[1].lower()
        group = parts[2]
        if week_type not in ("odd", "even"):
            self.bot.reply_to(message, "Неделя должна быть 'odd' или 'even'")
            return
        response = self.service.get_day_schedule(group, day, week_type)
        self.bot.send_message(message.chat.id, response)

    def process_group_input(self, chat_id, group_number, state):
        try:
            if state.action == "near_lesson":
                resp = self.service.get_near_lesson(group_number)
            elif state.action == "tomorrow":
                resp = self.service.get_tomorrow_schedule(group_number)
            elif state.action == "day":
                resp = self.service.get_day_schedule(group_number, state.day, state.week_type)
            elif state.action == "week":
                resp = self.service.get_week_schedule(group_number, state.week_type)
            else:
                resp = "❌ Неизвестное действие."
        except Exception as e:
            resp = f"⚠️ Ошибка: {e}"
        self.user_states.pop(chat_id, None)
        self.send_main_menu(chat_id, resp)

    def handle_callback(self, call):
        chat_id = call.message.chat.id
        data = call.data
        if data.startswith("day_"):
            day = data[4:]
            state = self.user_states.get(chat_id)
            if state and state.step == "day_selection":
                state.day = day
                state.step = "awaiting_group"
                self.bot.send_message(chat_id, "Введите номер группы (например: 4353):")
        self.bot.answer_callback_query(call.id)