import requests
from bs4 import BeautifulSoup

from time import perf_counter
import re

import config
import logging
import input_handler
import datetime
from aiogram import Bot, Dispatcher, executor, types

start = perf_counter()
print("Starting bot...")
logging.basicConfig(level=logging.ERROR)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot)
print("Connected to Telegram API")

news = []
events = []
event_types = {"🎉 Вечеринка": "party", "🎁 День рождения": "birthday", "👬 Прогулка": "walk", "💀 Другие": "other"}
themes = {"📚 Образование": "education", "💻 Гаджеты и технологии": "tech", "🏢 Город": "city", "🎮 Игры": "games"}
associations = {"education": "📚 Образование", "scitech": "💻 Гаджеты и технологии", "city": "🏢 Город",
                "gadgets": "💻 Гаджеты и технологии", "games": "🎮 Игры"}

event_add_cache = {}


def inline(text, data):
	return types.InlineKeyboardButton(text=text, callback_data=data)


def save():
	eventss = []
	for i in events:
		text = {'theme': i.theme, 'name': i.name, 'description': i.description,
		        'phone_number': i.phone_number, 'date': i.date}
		eventss.append(text)
	with open("events.txt", "w", encoding="utf-8") as f:
		f.write(str(eventss))


def load():
	with open("events.txt", "r", encoding="utf-8") as f:
		data = f.read()
	eventss = eval(data)
	for i in eventss:
		events.append(Event(i['theme'], i['name'], i['description'], i['phone_number'], i['date']))


CANCEL_BUTTON = types.InlineKeyboardMarkup(row_width=2)
CANCEL_BUTTON.add(inline("❌ Отменить", "cancel"))


class News:
	def __init__(self, theme, name, link, description):
		self.theme = theme
		self.name = name
		self.link = link
		self.description = description


class Event:
	def __init__(self, theme, name, description, phone_number, date):
		self.theme = theme
		self.name = name
		self.description = description
		self.phone_number = phone_number
		self.date = date


def parse_news():
	titles = []
	soup = BeautifulSoup(requests.get("https://news.rambler.ru/Innopolis/").text, 'html.parser')
	for i in soup.find_all("a"):
		try:
			if 'top-card' in i['class']:
				x = i.find_next('img')
				description = BeautifulSoup(requests.get('https://news.rambler.ru' + i['href']).text,
				                            'html.parser')
				for e in description.find("div", attrs={"id": "bigColumn"}).find_all():
					text = e.find_next("p").text
					if text != " ":
						description = text
						break
				add = True
				for o in titles:
					if o.name == x['alt']:
						add = False
				if add:
					titles.append(News(themes[associations[str(i['href']).split('/')[1]]], x['alt'],
					                   'https://news.rambler.ru' + i['href'], description))
		except Exception as e:
			continue
	return titles


async def send_events(call, page):
	total = 0
	filtered_list = []
	for i in events:
		if i.theme == call.data.split("_")[0]:
			filtered_list.append(i)
			total += 1
	if total == 0:
		category_temp = call.data.split("_")[0]
		await call.message.answer(f"❌ Мероприятий в категории {list(event_types.keys())[list(event_types.values()).index(category_temp)]} пока нет.")
		return
	if page > (total + 2) // 3:
		page = (total + 2) // 3
	if page == 0:
		page = 1
	category_temp = call.data.split("_")[0]
	message = f"Мероприятия в категории {list(event_types.keys())[list(event_types.values()).index(category_temp)]} (страница {page}/{(total + 2) // 3}):\n"
	for i in filtered_list[(page - 1) * 3:min(page * 3, total)]:
		if i.theme == call.data.split("_")[0]:
			message += f"\n*{i.name}*\n{i.description}\nВремя: {datetime.datetime.fromtimestamp(i.date).strftime('%d.%m.%Y %H:%M')}\nСвязаться: {i.phone_number}\n"
	PAGES = types.InlineKeyboardMarkup(row_width=2)
	PAGES.add(inline("◀️", call.data.split("_")[0] + f"_{page}_previous"), inline("▶️", call.data.split("_")[0] + f"_{page}_next"))
	if 'в категории' in call.message.text:
		try:
			await call.message.edit_text(message, reply_markup=PAGES, parse_mode="markdown", disable_web_page_preview=True)
		except Exception as e:
			pass
	else:
		await call.message.answer(message, parse_mode="markdown", reply_markup=PAGES, disable_web_page_preview=True)


async def send_news(call, page):
	total = 0
	filtered_list = []
	for i in news:
		if i.theme == call.data.split("_")[0]:
			filtered_list.append(i)
			total += 1
	if total == 0:
		category_temp = call.data.split("_")[0]
		await call.message.answer(f"❌ Новостей в категории {list(themes.keys())[list(themes.values()).index(category_temp)]} пока нет.")
		return
	if page > (total + 2) // 3:
		page = (total + 2) // 3
	if page == 0:
		page = 1
	category_temp = call.data.split("_")[0]
	message = f"Новости в категории {list(themes.keys())[list(themes.values()).index(category_temp)]} (страница {page}/{(total + 2) // 3}):\n"
	for i in filtered_list[(page - 1) * 3:min(page * 3, total)]:
		if i.theme == call.data.split("_")[0]:
			message += f"\n[{i.name}]({i.link})\n{i.description[:69]}...\n"
	PAGES = types.InlineKeyboardMarkup(row_width=2)
	PAGES.add(inline("◀️", call.data.split("_")[0] + f"_{page}_previous"), inline("▶️", call.data.split("_")[0] + f"_{page}_next"))
	if 'в категории' in call.message.text:
		try:
			await call.message.edit_text(message, reply_markup=PAGES, parse_mode="markdown", disable_web_page_preview=True)
		except Exception as e:
			pass
	else:
		await call.message.answer(message, parse_mode="markdown", reply_markup=PAGES, disable_web_page_preview=True)


@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
	MENU = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
	MENU.add("📰 Новости Иннополиса", "🎉 Мероприятия", "📃 Добавить мероприятие")
	await message.answer("Добро пожаловать, спасибо, что решили воспользоваться нашим ботом.", reply_markup=MENU)


@dp.message_handler()
async def message_handler(message: types.Message):
	if_waiting = input_handler.run_check(message.from_user.id)
	if if_waiting:
		match if_waiting:
			case "event_name":
				event_add_cache[message.from_user.id]['name'] = message.text
				input_handler.wait_for(message.from_user.id, "event_description")
				await message.answer("Введите описание вашего мероприятия:", reply_markup=CANCEL_BUTTON)
			case "event_description":
				event_add_cache[message.from_user.id]['description'] = message.text
				input_handler.wait_for(message.from_user.id, "event_number")
				await message.answer("Введите ваш номер телефона для связи (формат +7XXXXXXXXXX):",
				                     reply_markup=CANCEL_BUTTON)
			case "event_number":
				if not re.search("\+7[0-9]{10}", message.text):
					input_handler.wait_for(message.from_user.id, "event_number")
					await message.answer(
						"Номер телефона должен быть в формате +7XXXXXXXXXX. Попорбуйте снова:",
						reply_markup=CANCEL_BUTTON)
					return
				event_add_cache[message.from_user.id]['number'] = message.text
				input_handler.wait_for(message.from_user.id, "event_date")
				await message.answer("Введите дату вашего мероприятия (формат DD.MM.YYYY HH:MM):",
				                     reply_markup=CANCEL_BUTTON)
			case "event_date":
				if not re.search("[0-3][0-9].[0-1][0-9].[0-9]{4} [0-2][0-9]:[0-5][0-9]", message.text):
					input_handler.wait_for(message.from_user.id, "event_date")
					await message.answer("Дата должна быть в формате DD.MM.YYYY HH:MM. Попробуйте снова:",
					                     reply_markup=CANCEL_BUTTON)
					return
				cache = event_add_cache[message.from_user.id]
				events.append(Event(cache['type'], cache['name'], cache['description'], cache['number'],
				                    datetime.datetime.strptime(message.text, '%d.%m.%Y %H:%M').timestamp()))

				event_add_cache.pop(message.from_user.id)
				await message.answer("Ваше мероприятие создано!")
			case "query":
				msg = f"Мероприятия по запросу {message.text}:\n"
				counter = 0
				for i in events:
					if message.text.lower() in str(i.name).lower() or message.text.lower() in str(
							i.description).lower():
						if counter == 5:
							break
						msg += f"\n*{i.name}*\n{i.description}\nВремя: {datetime.datetime.fromtimestamp(i.date).strftime('%d.%m.%Y %H:%M')}\nСвязаться: {i.phone_number}\n"
						counter += 1
				await message.answer(msg, parse_mode="markdown", disable_web_page_preview=True)
		return
	match message.text:
		case "🎉 Мероприятия":
			MENU = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
			BUTTONS = []
			for i in event_types:
				BUTTONS.append(inline(i, event_types[i]))
			MENU.add(*BUTTONS)
			MENU.add(inline("🔎 Поиск", "search_event"))
			await message.answer("Выберите категорию:", reply_markup=MENU)
		case "📰 Новости Иннополиса":
			MENU = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
			BUTTONS = []
			for i in themes:
				BUTTONS.append(inline(i, themes[i]))
			MENU.add(*BUTTONS)
			await message.answer("Выберите категорию:", reply_markup=MENU)
		case "📃 Добавить мероприятие":
			MENU = types.InlineKeyboardMarkup(resize_keyboard=True, row_width=2)
			BUTTONS = []
			for i in event_types:
				BUTTONS.append(inline(i, event_types[i] + '_'))
			MENU.add(*BUTTONS)
			await message.answer("Выберите категорию вашего мероприятия:", reply_markup=MENU)
		case _:
			await message.answer("Неизвестная команда!")


@dp.callback_query_handler()
async def callback_listener(call: types.CallbackQuery):
	if call.data in themes.values():
		await send_news(call, 1)
	elif call.data in event_types.values():
		await send_events(call, 1)
	elif call.data[:-1] in event_types.values():
		event_add_cache[call.from_user.id] = {"type": call.data[:-1]}
		await call.message.answer("Введите название мероприятия:", reply_markup=CANCEL_BUTTON)
		input_handler.wait_for(call.from_user.id, "event_name")
	elif call.data.split("_")[0] in event_types.values():
		match call.data.split("_")[2]:
			case "previous":
				await send_events(call, int(call.data.split("_")[1]) - 1)
			case "next":
				await send_events(call, int(call.data.split("_")[1]) + 1)
	elif call.data.split("_")[0] in themes.values():
		match call.data.split("_")[2]:
			case "previous":
				await send_news(call, int(call.data.split("_")[1]) - 1)
			case "next":
				await send_news(call, int(call.data.split("_")[1]) + 1)
	match call.data:
		case "cancel":
			try:
				input_handler.cancel(call.from_user.id)
				event_add_cache.pop(call.from_user.id)
				await call.message.answer("Отменено!")
			except Exception as e:
				pass
		case "search_event":
			input_handler.wait_for(call.from_user.id, "query")
			await call.message.answer("Введите ваш запрос:", reply_markup=CANCEL_BUTTON)
	await call.answer()


async def on_startup(dp: Dispatcher):
	global news
	print("Running startup tasks...")
	print("Parsing news...")
	news = parse_news()
	print("News have been parsed.")
	print("Loading events...")
	load()
	print(f'Done, took {round(perf_counter() - start, 3)}s')
	print("Bot has been started.")


async def on_shutdown(dp: Dispatcher):
	start1 = perf_counter()
	print("Running shutdown tasks...")
	print("Saving events...")
	save()
	print(f'Done, took {round(perf_counter() - start1, 3)}s')
	print("Bot has been stopped.")


executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
