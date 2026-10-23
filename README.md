# Лабораторна робота №7 — Система керування завданнями (Варіант 14)

## Встановлення та запуск

1. Створіть та активуйте віртуальне середовище:
   python -m venv .venv
   .venv\Scripts\activate

2. Встановіть залежності:
   python -m pip install -e ".[test]"

3. Запустіть програму:
   python -m task_manager.main

4. Запустіть інтеграційні тести:
   pytest -v

5. Команди Alembic:
   alembic upgrade head
   alembic current
