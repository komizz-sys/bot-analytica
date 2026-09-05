import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

import config
from database import init_db, add_expense, get_expenses_sum, get_recent_expenses, delete_expense
from keyboards import main_menu_kb
from states import ExpenseStates
from services.shop_client import get_revenue, ShopApiError

logging.basicConfig(level=logging.INFO)

# Те же формулировки периодов, что и в stats_api.py магазина — держим
# в одном месте на всякий случай, если понадобится поменять.
PERIOD_SQL = {
    "today": "datetime('now', 'start of day')",
    "week": "datetime('now', '-7 day')",
    "month": "datetime('now', '-30 day')",
    "all": None,
}
PERIOD_TITLES = {
    "today": "📊 Сегодня",
    "week": "📅 За неделю",
    "month": "🗓 За месяц",
    "all": "♾ За всё время",
}


def format_uzs(amount: int) -> str:
    return f"{amount:,.0f}".replace(",", " ") + " сум"


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def build_report(period: str) -> str:
    try:
        revenue = await get_revenue(period)
    except ShopApiError as e:
        return f"⚠️ Не удалось получить данные от магазина:\n{e}"

    since_sql = None
    if PERIOD_SQL[period]:
        # Считаем ту же точку отсчёта, что и в самом запросе (см. services/shop_client)
        import aiosqlite
        async with aiosqlite.connect(config.DB_PATH) as db:
            async with db.execute(f"SELECT {PERIOD_SQL[period]}") as cur:
                since_sql = (await cur.fetchone())[0]

    manual_expenses = await get_expenses_sum(since_sql)

    income_by_cat = revenue["income_by_category"]
    income_total = revenue["income_total"]
    rent_auto_cost = revenue.get("rent_auto_cost_uzs", 0)
    total_cost = rent_auto_cost + manual_expenses
    profit = income_total - total_cost

    cat_names = {
        "stars": "⭐ Звёзды",
        "premium": "💎 Premium",
        "simple_gift": "🎁 Подарки",
        "nft_rent": "🖼 Аренда NFT",
    }
    lines = [f"<b>{PERIOD_TITLES[period]}</b>\n"]
    lines.append(f"Заказов оплачено: <b>{revenue['orders_count']}</b>\n")
    lines.append("<b>Доход по категориям:</b>")
    for cat, name in cat_names.items():
        amount = income_by_cat.get(cat, 0)
        if amount:
            lines.append(f"  {name}: {format_uzs(amount)}")
    lines.append(f"\n💰 <b>Доход всего:</b> {format_uzs(income_total)}")

    lines.append(f"\n<b>Расход:</b>")
    if rent_auto_cost:
        lines.append(f"  🖼 Аренда (авто, MarketApp): {format_uzs(rent_auto_cost)}")
    lines.append(f"  💸 Внесено вручную (звёзды/подарки/etc): {format_uzs(manual_expenses)}")
    lines.append(f"📉 <b>Расход всего:</b> {format_uzs(total_cost)}")

    profit_emoji = "✅" if profit >= 0 else "❌"
    lines.append(f"\n{profit_emoji} <b>Прибыль: {format_uzs(profit)}</b>")

    if rent_auto_cost:
        lines.append(
            "\n<i>Расход по аренде — приблизительный: считается по текущему курсу TON, "
            "не по курсу на момент самой аренды.</i>"
        )

    return "\n".join(lines)


async def main():
    await init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ Этот бот только для админов магазина.")
            return
        await message.answer(
            "👋 Бот-аналитик готов.\n\n"
            "Показывает доход/расход/прибыль основного магазина и ведёт "
            "учёт ручных расходов (закупка звёзд/подарков через Fragment/MarketApp).",
            reply_markup=main_menu_kb(),
        )

    @dp.message(F.text.in_(["📊 Сегодня", "📅 Неделя", "🗓 Месяц", "♾ За всё время"]))
    async def show_report(message: Message):
        if not is_admin(message.from_user.id):
            return
        period_map = {
            "📊 Сегодня": "today",
            "📅 Неделя": "week",
            "🗓 Месяц": "month",
            "♾ За всё время": "all",
        }
        period = period_map[message.text]
        await message.answer("⏳ Считаю...")
        report = await build_report(period)
        await message.answer(report)

    @dp.message(F.text == "💸 Добавить расход")
    async def start_expense(message: Message, state: FSMContext):
        if not is_admin(message.from_user.id):
            return
        await state.set_state(ExpenseStates.entering_amount)
        await message.answer("Сколько сум потратил? (только число, например: 55000)")

    @dp.message(ExpenseStates.entering_amount)
    async def got_amount(message: Message, state: FSMContext):
        text = message.text.strip().replace(" ", "").replace(",", "")
        if not text.isdigit():
            await message.answer("Нужно просто число, например: 55000. Попробуй ещё раз:")
            return
        await state.update_data(amount=int(text))
        await state.set_state(ExpenseStates.entering_description)
        await message.answer("На что потратил? (например: Купил 5000 звёзд на Fragment)")

    @dp.message(ExpenseStates.entering_description)
    async def got_description(message: Message, state: FSMContext):
        data = await state.get_data()
        amount = data["amount"]
        description = message.text.strip()
        await add_expense(amount, description, message.from_user.id)
        await state.clear()
        await message.answer(
            f"✅ Расход добавлен: {format_uzs(amount)} — {description}",
            reply_markup=main_menu_kb(),
        )

    @dp.message(F.text == "📃 История расходов")
    async def list_expenses(message: Message):
        if not is_admin(message.from_user.id):
            return
        rows = await get_recent_expenses(10)
        if not rows:
            await message.answer("Расходов пока не было.")
            return
        lines = ["<b>Последние 10 расходов:</b>\n"]
        for r in rows:
            lines.append(f"#{r['id']} — {format_uzs(r['amount_uzs'])} — {r['description']} ({r['created_at']})")
        lines.append("\nЧтобы удалить расход, напиши: <code>/del ID</code> (например: /del 3)")
        await message.answer("\n".join(lines))

    @dp.message(Command("del"))
    async def cmd_delete_expense(message: Message, command: CommandObject):
        if not is_admin(message.from_user.id):
            return
        args = (command.args or "").strip()
        if not args.isdigit():
            await message.answer("Укажи номер расхода: /del 3")
            return
        expense_id = int(args)
        ok = await delete_expense(expense_id)
        if ok:
            await message.answer(f"🗑 Расход #{expense_id} удалён.")
        else:
            await message.answer(f"Расход #{expense_id} не найден — проверь номер в «История расходов».")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
