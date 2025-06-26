import os
from pathlib import Path

def rename_images(directory_path: str):
    """
    Переименовывает все изображения в указанной папке:
    photo_2025-05-28 09.34.41.jpeg -> Amanita-Product-Img-001.jpeg
    """
    directory = Path(directory_path)
    if not directory.exists():
        print(f"❌ Папка не найдена: {directory_path}")
        return

    images = sorted([f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png"]])
    for idx, file in enumerate(images, start=1):
        new_name = f"Amanita-Product-Img-{idx:03d}{file.suffix.lower()}"
        new_path = file.with_name(new_name)
        file.rename(new_path)
        print(f"✅ {file.name} -> {new_name}")

    print("🎉 Все файлы успешно переименованы!")

if __name__ == "__main__":
    # Укажи абсолютный путь к папке с изображениями
    rename_images("/Users/eslinko/Downloads/Amanita Catalog")
