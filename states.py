from aiogram.fsm.state import State, StatesGroup


class ExpenseStates(StatesGroup):
    entering_amount = State()
    entering_description = State()
