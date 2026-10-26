# Подбор лекарственных препаратов (прототип ЭС)

Лабораторные работы №6–7 по дисциплине «Технологии и инструментальные средства проектирования ИС».

## Запуск
1. Установить зависимости: `pip install -r requirements.txt`
2. Сгенерировать БД: `python seed_data.py`
3. Запустить GUI: `python main.py`
4. Запустить тесты (ЛР7): `python tests_runner.py`

## Структура
- `main.py` — GUI (tkinter)
- `inference_bridge.py` — «Мост» (машина вывода)
- `knowledge_base.py` — загрузка БЗ (OWL + SQLite)
- `rule_engine.py` — правила 1–8
- `neural_net.py` — локальная модель
- `neural_client.py` — клиент внешней нейросети (API)
- `explanation.py` — подсистема объяснения
- `database.py` — история и протоколы тестов
- `seed_data.py` — генератор `drugs.db`
- `tests_runner.py` — ПМИ/Протокол (ЛР7)
- `knowledgebase.owl` — онтология (ЛР3)