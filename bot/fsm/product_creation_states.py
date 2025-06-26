from aiogram.fsm.state import State, StatesGroup

class ProductCreationStates(StatesGroup):
    """
    Состояния FSM для пошагового создания продукта.
    """

    TitleInput = State()  # Ввод названия продукта
    DescriptionInput = State()  # Ввод описания продукта
    PriceInput = State()  # Ввод цены (число, без валюты)
    CoverImageInput = State()  # Загрузка обложки продукта (cover_image)
    GalleryInput = State()  # Загрузка галереи изображений (gallery)
    VideoInput = State()  # Загрузка видео (video)
    CategoriesInput = State()  # Ввод списка категорий (categories)
    AttributesInput = State()  # Ввод дополнительных атрибутов (attributes)
    Confirmation = State()  # Финальное подтверждение (просмотр и запуск создания)
