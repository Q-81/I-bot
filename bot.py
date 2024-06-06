import asyncio
from datetime import datetime, timedelta, time

import logging
import requests
import json

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram import F
from aiogram.types import FSInputFile

from config import *

days_of_week = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

bot = Bot(token="2079878449:AAFVO8sV6N2A7EJGIfrGmlijX8AwBEime0A")
dp = Dispatcher()


@dp.message(Command("start"))
@dp.message(F.text == "В главное меню🔙")
async def start(message: types.Message):
    user = message.from_user.__dict__
    keyboard = None
    print(str(user['id']))
    if str(user['id']) in USERS:
        url = f"http://127.0.0.1:5000/api/check_user/{user['id']}"
        response = requests.request("GET", url)
        if not response.json()['user_exists']:
            url = "http://127.0.0.1:5000/api/add_user"
            response = requests.request("POST", url, json=user)
            out = 'Регистрация в системе пройдена успешно!' if response.status_code == 200 else 'Ошибка регистрации.'
        else:
            out = 'Вас приветствует Q, личный ассистент.\n Выберите желаемое действие.'
            buttons = [
                [types.InlineKeyboardButton(text="Статистика рабочего времени", callback_data="stats")],
                [types.InlineKeyboardButton(text="Информация о компаниях", callback_data="info")]
            ]
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    else:
        out = 'Добрый день! Спустя некоторое время Вы сможете узнать больше об организации, которую я представляю.'
    await message.answer(out, reply_markup=keyboard)

    kb = [
        [
            types.KeyboardButton(text="Напомнить📝"),
            types.KeyboardButton(text="Начало работы 🏃")
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Выберите желаемое действие..."
    )
    await message.answer('Начать работу:', reply_markup=keyboard)


@dp.message(F.text == 'Напомнить📝')
async def set_a_reminder(message: types.Message):
    kb = [
        [
            types.KeyboardButton(text="В главное меню🔙")
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Укажите событие..."
    )
    await message.answer("О каком событии хотели бы получить напоминание?",
                         reply_markup=keyboard)


@dp.message(F.text.in_(['Начало работы 🏃', 'Завершение работы 🏁']))
async def track_activity(message: types.Message):
    user = message.from_user.__dict__
    text, keyboard = None, None
    if str(user['id']) in USERS:
        url = "http://127.0.0.1:5000/api/sessions"
        response = requests.request("GET", url, json=user)
        if response.status_code == 200:
            response = requests.request("POST", url, json=user)

            if response.json()['result'] == 'created':
                text = 'Режим включен успешно!'
                kb = [
                    [
                        types.KeyboardButton(text="Напомнить📝"),
                        types.KeyboardButton(text="Завершение работы 🏁")
                    ],
                ]
            else:
                text = 'Режим выключен успешно.'
                kb = [
                    [
                        types.KeyboardButton(text="Напомнить📝"),
                        types.KeyboardButton(text="Начало работы 🏃")
                    ],
                ]
            keyboard = types.ReplyKeyboardMarkup(
                keyboard=kb,
                resize_keyboard=True,
                input_field_placeholder="Выберите желаемое действие..."
            )
        else:
            pass # TODO hold an error

    else:
        # IF NOT ALLOWED
        text = 'Функция недоступна! Обратитесь в службу поддержки...'

    await message.answer(text, reply_markup=keyboard)


@dp.message(F.text.regexp(r'\d{2}\.\d{2} \([а-яА-Я]{2}\)'))
async def catch_date(message: types.Message):
    # --- Extract only day and month --- #
    raw_date = message.text.split(' ')[0]

    # --- Manually add year --- #
    raw_date += f'.{datetime.now().year}'

    # --- Update the latest reminder --- #
    url = "http://127.0.0.1:5000/api/update_reminder"
    payload = {
        'date': raw_date
    }
    response = requests.request("POST", url, json=payload)
    print(response.json(), response.status_code)
    if response.status_code == 200:
        zero_hour = datetime.strptime(str(ONLINE_IN), "%H")  # Start of counting
        hours = [(zero_hour + timedelta(hours=i)).strftime("%H") for i in range(12)]
        builder = ReplyKeyboardBuilder()
        for i in range(12):
            builder.add(types.KeyboardButton(text=f"{hours[i]}:00"))
        builder.adjust(4)

        await message.answer(
            "Уточните, пожалуйста, час:",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    else:
        await message.answer('Функция недоступна! Обратитесь в службу поддержки...')  # TODO wrap in func


@dp.message(F.text.regexp(r'^\d{2}:\d{2}✅?$'))
async def catch_time(message: types.Message):
    # --- Update the latest reminder --- #
    url = "http://127.0.0.1:5000/api/update_reminder"
    payload = {
        'time': message.text.replace("✅", "")
    }

    response = requests.request("POST", url, json=payload)
    if response.status_code == 200:
        # --- Process minute choosing --- #
        if not '✅' in message.text:
            hour = message.text.split(':')[0]
            minutes = [f"{i}0" for i in range(6)]
            builder = ReplyKeyboardBuilder()
            for minute in minutes:
                builder.add(types.KeyboardButton(text=f"{hour}:{minute}✅"))
            builder.adjust(3)

            await message.answer(
                "И минуты:",
                reply_markup=builder.as_markup(resize_keyboard=True)
            )
        else:
            kb = [
                [
                    types.KeyboardButton(text="В главное меню🔙")
                ],
            ]
            keyboard = types.ReplyKeyboardMarkup(
                keyboard=kb,
                resize_keyboard=True
            )
            await message.answer('Напоминание установлено успешно!',
                                 reply_markup=keyboard)

    else:
        await message.answer('Функция недоступна! Обратитесь в службу поддержки...')  # TODO wrap in func


@dp.message(F.text)
async def reminder_handler(message: types.Message):
    # --- Reminder parsing --- #
    url = "http://127.0.0.1:5000/api/parse_reminder"
    payload = {
        'text': message.text  #.encode('utf-8')
    }
    response = requests.request("POST", url, json=payload)
    print(response.json(), response.status_code)
    # --- Adding the reminder, optionally with parsed tags --- #
    user, text = message.from_user.__dict__, message.text
    url = "http://127.0.0.1:5000/api/add_reminder"
    if response.status_code == 302:
        tags = response.json()  # dict
        # --- Send user, which tags were detected --- #
        # text = ''
        # for token in tags.values():
        #     text += f"{token['word']}: {token['ent_type']}\n"
        payload = {
            'user': user,
            'text': text,
            'tags': tags
        }
    else:
        # TODO add logging like "no tags detected!"
        payload = {
            'user': user,
            'text': text
        }
    response = requests.request("POST", url, json=payload)

    if response.status_code == 201:
        # --- Offer date choosing --- #
        current_date = datetime.now()
        dates = [(current_date + timedelta(days=i)).strftime("%d.%m") for i in range(9)]
        print(current_date.weekday(), current_date.weekday() + 9)
        weekdays = (3 * days_of_week)[current_date.weekday():current_date.weekday() + 9]
        builder = ReplyKeyboardBuilder()
        for i in range(9):
            builder.add(types.KeyboardButton(text=f"{dates[i]} ({weekdays[i]})"))
        builder.adjust(3)

        await message.answer(
            "Какого числа желаете получить напоминание?",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
    else:
        await message.answer('Функция недоступна! Обратитесь в службу поддержки...')  # TODO wrap in func


@dp.callback_query(F.data == "stats")
async def compute_and_send_stats(callback: types.CallbackQuery):
    await callback.answer(
        text="Запрос принят, ожидайте.",
        show_alert=True
    )
    user = callback.from_user.__dict__
    url = "http://127.0.0.1:5000/api/compute_stats"
    response = requests.request("POST", url, params={'n': '10', 'user_id': str(user['id'])})
    if response.status_code == 200:
        path = response.json()['path']
        file = FSInputFile(path)
        await callback.message.answer_photo(file)
    else:
        await callback.message.answer('Ошибка! Попробуйте позже.')


@dp.callback_query(F.data == "info")
async def provide_org_info(callback: types.CallbackQuery):
    await callback.answer(
        text="Запрос принят, ожидайте.",
        show_alert=True
    )
    user = callback.from_user.__dict__
    url = "http://127.0.0.1:5000/api/compute_analysis"
    response = requests.request("POST", url, params={'n': '10', 'user_id': str(user['id']), 'type': 'ORG'})
    if response.status_code == 200:
        print('Success!')
        # path = response.json()['path']
        # file = FSInputFile(path)
        # await callback.message.answer_photo(file)
    else:
        await callback.message.answer('Ошибка! Попробуйте позже.')


def check_for_sessions():
    url = "http://127.0.0.1:5000/api/check_for_sessions"
    response = requests.request("GET", url)
    if response.status_code == 201:
        print(f"HTTP_201_CREATED - {response.json()['result']}")
    else:
        print("HTTP_304_NOT_MODIFIED")


async def check_for_reminders():
    url = "http://127.0.0.1:5000/api/check_for_updates"
    response = requests.request("GET", url)

    if response.status_code == 302:
        for idx, reminder in response.json().items():
            await bot.send_message(
                chat_id=reminder['user_id'],
                text='Вы просили напомнить:\n' + reminder['text']
            )
            await asyncio.sleep(0.5)
    else:
        print(f'No reminders processed. {response.status_code} had been returned.')


async def scheduler():
    END_OF_DAY = time(23, 55)
    while True:
        # --- Get busyness status --- #
        pass

        # --- Check work time --- #
        if not ONLINE_IN <= int(datetime.now().strftime('%H')) <= ONLINE_OUT:
            print(f"Reminders checking is not necessary at {datetime.now().strftime('%H:%M')}")
            await asyncio.sleep((ONLINE_OUT - ONLINE_IN - 1) * 60 * 60)
            continue

        # --- Transfer unfinished sessions --- #
        if datetime.now().time() >= END_OF_DAY:
            check_for_sessions()
            await asyncio.sleep(5*60)

        await check_for_reminders()

        # --- Delay time --- #
        await asyncio.sleep(60)


# Запуск бота
async def main():
    # await bot.delete_webhook(drop_pending_updates=True)
    logging.basicConfig(level=logging.INFO)
    await asyncio.gather(
        dp.start_polling(bot),
        scheduler(),
    )

if __name__ == "__main__":
    asyncio.run(main())
