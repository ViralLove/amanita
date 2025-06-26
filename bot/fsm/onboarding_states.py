# fsm/onboarding_states.py
from aiogram.fsm.state import StatesGroup, State

class OnboardingStates(StatesGroup):
    LanguageSelection = State()
    OnboardingPathChoice = State()
    InviteInput = State()
    WebAppConnecting = State()
    RestoreAccess = State()
    Completed = State()
