# main.py
import telebot
from bot_handler import BotHandler

TOKEN = '8490919762:AAFH6CBEy6xE160WWiQ6UjegB_RZBzxeYXM'  # ← замените на свой

bot = telebot.TeleBot(TOKEN)
handler = BotHandler(bot)
handler.register_handlers()

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    handler.handle_callback(call)

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(non_stop=True, interval=0)