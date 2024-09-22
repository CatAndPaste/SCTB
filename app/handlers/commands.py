# app/handlers/commands.py

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select

from app.models import User, Order, UserParameters
from app.utils.locale import load_locale
from app.utils.db import get_session
from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

class BuyStates(StatesGroup):
    waiting_for_amount = State()

class SellStates(StatesGroup):
    waiting_for_sell_amount = State()
    waiting_for_sell_price = State()

@router.message(Command('buy'))
async def cmd_buy(message: types.Message, state: FSMContext):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        locale = load_locale(user.language)
        # Отображаем инструкцию и текущий баланс
        balance_text = f"Available USDT: 10000\nCurrent Price: 50000 USDT/BTC"  # Используем фиктивные данные
        await message.answer(f"{locale.get('buy_instruction', 'Please enter the amount to buy in USDT.')}\n\n{balance_text}")
        await state.set_state(BuyStates.waiting_for_amount)

@router.message(BuyStates.waiting_for_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.strip()
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
        # Эмулируем покупку
        bought_btc = amount / 50000  # Предполагаемая цена BTC
        async with get_session() as session:
            user = await session.get(User, message.from_user.id)
            # Создаём ордер покупки в базе данных
            new_order = Order(
                user_id=user.id,
                order_type='buy',
                amount=bought_btc,
                price=50000,
                status='Completed',
                date_created=datetime.utcnow()
            )
            session.add(new_order)
            await session.commit()
        text = f"Purchase successful.\nBought: {bought_btc} BTC\nPrice: {amount} USDT\nDate and time: {datetime.utcnow()}"
        await message.answer(text)
        # Предложить создать ордер на продажу
        await message.answer(f"Do you want to create a sell order for {bought_btc} BTC?", reply_markup=create_sell_order_keyboard())
    except ValueError:
        await message.answer("Invalid amount. Please enter a valid number.")
    finally:
        await state.clear()

def create_sell_order_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="Create Sell Order", callback_data="create_sell_order")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data == 'create_sell_order')
async def process_create_sell_order(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Enter the amount to sell (in BTC):")
    await state.set_state(SellStates.waiting_for_sell_amount)
    await callback_query.answer()

@router.message(SellStates.waiting_for_sell_amount)
async def process_sell_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.strip()
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
        await state.update_data(sell_amount=amount)
        await message.answer("Enter the desired sell price per 1 BTC (in USDT):")
        await state.set_state(SellStates.waiting_for_sell_price)
    except ValueError:
        await message.answer("Invalid amount. Please enter a valid number.")

@router.message(SellStates.waiting_for_sell_price)
async def process_sell_price(message: types.Message, state: FSMContext):
    price_text = message.text.strip()
    try:
        price = float(price_text)
        if price <= 0:
            raise ValueError
        data = await state.get_data()
        amount = data.get('sell_amount')
        total = amount * price
        async with get_session() as session:
            user = await session.get(User, message.from_user.id)
            # Создаём ордер продажи в базе данных
            new_order = Order(
                user_id=user.id,
                order_type='sell',
                amount=amount,
                price=price,
                status='Open',
                date_created=datetime.utcnow()
            )
            session.add(new_order)
            await session.commit()
        text = f"Limit sell order successfully placed.\nSell: {amount} BTC\nSell price per 1 BTC: {price} USDT\nTotal: {total} USDT\nDate and time: {datetime.utcnow()}"
        await message.answer(text)
    except ValueError:
        await message.answer("Invalid price. Please enter a valid number.")
    finally:
        await state.clear()

@router.message(Command('orders'))
async def cmd_orders(message: types.Message):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        locale = load_locale(user.language)
        # Получаем список ордеров из базы данных
        orders = await session.execute(
            select(Order).where(Order.user_id == user.id).order_by(Order.date_created.desc())
        )
        orders = orders.scalars().all()
        if not orders:
            await message.answer("You have no active orders.")
            return
        orders_text = "Order status:\n"
        for order in orders:
            order_text = f"Order №{order.id}\nType: {order.order_type}\nStatus: {order.status}\nAmount: {order.amount} BTC\nPrice: {order.price} USDT\nDate: {order.date_created}"
            orders_text += order_text + "\n\n"
        await message.answer(orders_text)
        # Добавим кнопки для удаления ордеров
        await message.answer("Do you want to cancel any order?", reply_markup=cancel_order_keyboard(orders))

def cancel_order_keyboard(orders):
    buttons = []
    for order in orders:
        if order.status == 'Open':
            buttons.append([types.InlineKeyboardButton(text=f"Cancel Order №{order.id}", callback_data=f"cancel_order_{order.id}")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data.startswith('cancel_order_'))
async def process_cancel_order(callback_query: types.CallbackQuery):
    order_id = int(callback_query.data.split('_')[2])
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order and order.status == 'Open':
            order.status = 'Cancelled'
            await session.commit()
            await callback_query.message.answer(f"Order №{order.id} has been cancelled.")
        else:
            await callback_query.message.answer("Order not found or already completed.")
    await callback_query.answer()

# Продолжение app/handlers/commands.py

class ParamsStates(StatesGroup):
    waiting_for_param_choice = State()
    waiting_for_new_value = State()

@router.message(Command('autobuy'))
async def cmd_autobuy(message: types.Message):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        # Получаем параметры автоторговли
        if not user.parameters:
            # Если параметров нет, создаем со значениями по умолчанию
            params = UserParameters(user_id=user.id)
            session.add(params)
            await session.commit()
        else:
            params = user.parameters
        # Эмулируем запуск или остановку автоторговли
        if params.autobuy_on_growth or params.autobuy_on_fall:
            # Останавливаем автоторговлю
            params.autobuy_on_growth = False
            params.autobuy_on_fall = False
            await session.commit()
            await message.answer("Autotrading cycle stopped.")
        else:
            # Запускаем автоторговлю
            params.autobuy_on_growth = True  # Можно уточнить, какие режимы включать
            await session.commit()
            await message.answer("Autotrading cycle started.")

@router.message(Command('params'))
async def cmd_params(message: types.Message, state: FSMContext):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        # Получаем параметры
        if not user.parameters:
            params = UserParameters(user_id=user.id)
            session.add(params)
            await session.commit()
        else:
            params = user.parameters
        # Отображаем текущие параметры
        params_text = f"Parameters:\n1. Purchase amount (USDT): {params.purchase_amount}\n2. Profit percentage: {params.profit_percentage}%\n3. Purchase delay: {params.purchase_delay} seconds\n4. Growth percentage: {params.growth_percentage}%\n5. Fall percentage: {params.fall_percentage}%\n6. Autobuy on growth: {'Enabled' if params.autobuy_on_growth else 'Disabled'}\n7. Autobuy on fall: {'Enabled' if params.autobuy_on_fall else 'Disabled'}\n\nEnter the number of the parameter you want to change, or type 'reset' to reset to default."
        await message.answer(params_text)
        await state.set_state(ParamsStates.waiting_for_param_choice)

@router.message(ParamsStates.waiting_for_param_choice)
async def process_param_choice(message: types.Message, state: FSMContext):
    choice = message.text.strip().lower()
    if choice == 'reset':
        async with get_session() as session:
            user = await session.get(User, message.from_user.id)
            # Сбрасываем параметры
            if user.parameters:
                session.delete(user.parameters)
                await session.commit()
            await message.answer("Parameters have been reset to default.")
        await state.clear()
    elif choice in ['1', '2', '3', '4', '5', '6', '7']:
        await state.update_data(param_choice=int(choice))
        await message.answer("Enter the new value:")
        await state.set_state(ParamsStates.waiting_for_new_value)
    else:
        await message.answer("Invalid choice. Please enter a number from 1 to 7, or 'reset'.")

@router.message(ParamsStates.waiting_for_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    param_choice = data.get('param_choice')
    new_value = message.text.strip()
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        if not user.parameters:
            params = UserParameters(user_id=user.id)
            session.add(params)
        else:
            params = user.parameters
        try:
            if param_choice in [1, 2, 3, 4, 5]:
                value = float(new_value)
                if value <= 0:
                    raise ValueError
            elif param_choice in [6, 7]:
                value = new_value.lower() in ['true', 'yes', '1', 'enable', 'on']
            if param_choice == 1:
                params.purchase_amount = value
            elif param_choice == 2:
                params.profit_percentage = value
            elif param_choice == 3:
                params.purchase_delay = int(value)
            elif param_choice == 4:
                params.growth_percentage = value
            elif param_choice == 5:
                params.fall_percentage = value
            elif param_choice == 6:
                params.autobuy_on_growth = value
            elif param_choice == 7:
                params.autobuy_on_fall = value
            await session.commit()
            await message.answer("Parameter updated successfully.")
        except ValueError:
            await message.answer("Invalid value. Please enter a valid number.")
    await state.clear()

