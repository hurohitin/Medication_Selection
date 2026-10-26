# tests_runner.py

from typing import List, Dict
from inference_bridge import InferenceBridge
from database import HistoryStorage


TEST_CASES: List[Dict] = [
    {
        "id": "ТС-01", "desc": "Позитивный: 2 известных симптома",
        "input": {"symptoms": ["головная боль", "температура"], "age": 30, "sex": "М",
                  "weight": 70, "chronic": [], "allergies": [], "current_drugs": []},
        "expected": "Есть рекомендованные препараты",
        "check": lambda r: len(r.recommended) > 0,
    },
    {
        "id": "ТС-02", "desc": "Негативный: пустой ввод",
        "input": {"symptoms": [], "age": 30, "sex": "М", "weight": 70,
                  "chronic": [], "allergies": [], "current_drugs": []},
        "expected": "Нет рекомендаций",
        "check": lambda r: len(r.recommended) == 0,
    },
    {
        "id": "ТС-03", "desc": "Противопоказание: язва желудка",
        "input": {"symptoms": ["головная боль"], "age": 40, "sex": "М", "weight": 80,
                  "chronic": ["язва желудка"], "allergies": [], "current_drugs": []},
        "expected": "Есть исключённые по противопоказанию",
        "check": lambda r: any("противопоказание" in e["reason"] for e in r.excluded),
    },
    {
        "id": "ТС-04", "desc": "Аллергия на пенициллин",
        "input": {"symptoms": ["боль в горле"], "age": 25, "sex": "Ж", "weight": 60,
                  "chronic": [], "allergies": ["пенициллин"], "current_drugs": []},
        "expected": "Есть исключённые по аллергии",
        "check": lambda r: any("аллергия" in e["reason"].lower() for e in r.excluded),
    },
    {
        "id": "ТС-05", "desc": "Возрастное ограничение (5 лет)",
        "input": {"symptoms": ["температура"], "age": 5, "sex": "М", "weight": 20,
                  "chronic": [], "allergies": [], "current_drugs": []},
        "expected": "Есть исключённые по возрасту",
        "check": lambda r: any("возраст" in e["reason"] for e in r.excluded),
    },
    {
        "id": "ТС-06", "desc": "Взаимодействие с варфарином",
        "input": {"symptoms": ["головная боль"], "age": 60, "sex": "М", "weight": 75,
                  "chronic": [], "allergies": [], "current_drugs": ["варфарин"]},
        "expected": "Есть исключённые по взаимодействию",
        "check": lambda r: any("взаимодействие" in e["reason"] for e in r.excluded),
    },
    {
        "id": "ТС-07", "desc": "Пояснение не пустое",
        "input": {"symptoms": ["насморк"], "age": 30, "sex": "Ж", "weight": 55,
                  "chronic": [], "allergies": [], "current_drugs": []},
        "expected": "Explanation содержит текст",
        "check": lambda r: len(r.explanation) > 20,
    },
    {
        "id": "ТС-08", "desc": "Время отклика < 5 сек",
        "input": {"symptoms": ["кашель", "насморк"], "age": 30, "sex": "М", "weight": 70,
                  "chronic": [], "allergies": [], "current_drugs": []},
        "expected": "elapsed < 5",
        "check": lambda r: r.elapsed < 5.0,
    },
    {
        "id": "ТС-09", "desc": "Граничный: неизвестный симптом",
        "input": {"symptoms": ["абракадабра"], "age": 30, "sex": "М", "weight": 70,
                  "chronic": [], "allergies": [], "current_drugs": []},
        "expected": "Нет рекомендаций, без падения",
        "check": lambda r: len(r.recommended) == 0,
    },
    {
        "id": "ТС-10", "desc": "Комбинация: симптомы + аллергия + возраст",
        "input": {"symptoms": ["температура", "кашель"], "age": 15, "sex": "М", "weight": 50,
                  "chronic": [], "allergies": ["пенициллин"], "current_drugs": []},
        "expected": "Есть исключённые по аллергии",
        "check": lambda r: any("аллергия" in e["reason"].lower() for e in r.excluded),
    },
]


def run_all_tests(bridge: InferenceBridge, storage: HistoryStorage) -> List[Dict]:
    report = []
    for tc in TEST_CASES:
        try:
            result = bridge.run_diagnosis(tc["input"])
            passed = bool(tc["check"](result))
            actual = (
                f"рекомендовано: {len(result.recommended)}, "
                f"исключено: {len(result.excluded)}, "
                f"время: {result.elapsed}с"
            )
        except Exception as e:
            passed = False
            result = None
            actual = f"Исключение: {e}"
            print(f"[tests] Ошибка в {tc['id']}: {e}")

        status = "Pass" if passed else "Fail"
        report.append({
            "id": tc["id"], "desc": tc["desc"],
            "expected": tc["expected"], "actual": actual, "status": status,
        })
        storage.save_test_result(tc["id"], tc["desc"], tc["expected"], actual, status)
    return report


# ---------------------------------------------------------------------
# UI-тесты (ЛР7, ТС-11, ТС-12)
# ---------------------------------------------------------------------
def run_ui_tests() -> List[Dict]:
    """
    Проверяет поведение GUI: кнопку «Очистить» и отсутствие падения
    при некорректном возрасте. Запускается в отдельном Tk-инстансе.
    """
    import tkinter as tk
    from main import DrugESApp  # импорт внутри, чтобы не тянуть Tk при обычных тестах

    results = []

    # ТС-11: кнопка «Очистить»
    try:
        root = tk.Tk()
        root.withdraw()
        app = DrugESApp(root)

        app.symptoms_entry.insert("1.0", "головная боль, температура")
        app.chronic_entry.insert(0, "язва желудка")
        app.allergies_entry.insert(0, "пенициллин")
        app.current_drugs_entry.insert(0, "варфарин")
        app.age_spin.delete(0, "end"); app.age_spin.insert(0, "45")

        app.on_clear()

        cleared = (
            app.symptoms_entry.get("1.0", "end").strip() == ""
            and app.chronic_entry.get().strip() == ""
            and app.allergies_entry.get().strip() == ""
            and app.current_drugs_entry.get().strip() == ""
            and app.age_spin.get().strip() == "0"
        )
        results.append({
            "id": "ТС-11", "desc": "UI: кнопка «Очистить» сбрасывает все поля",
            "expected": "Все поля пусты, возраст = 0",
            "actual": "OK" if cleared else "Поля не очищены",
            "status": "Pass" if cleared else "Fail",
        })
        root.destroy()
    except Exception as e:
        results.append({
            "id": "ТС-11", "desc": "UI: кнопка «Очистить»",
            "expected": "Все поля пусты", "actual": f"Ошибка: {e}", "status": "Fail",
        })

    # ТС-12: конфиденциальность — в history.db нет ФИО/паспорта
    try:
        storage = HistoryStorage("history.db")
        hist = storage.get_history()
        forbidden = ("фио", "паспорт", "снилс", "инн")
        leak = any(
            any(f in str(rec).lower() for f in forbidden)
            for rec in hist
        )
        results.append({
            "id": "ТС-12", "desc": "Конфиденциальность: нет ФИО/паспорта в истории",
            "expected": "Нет запрещённых полей",
            "actual": "OK" if not leak else "Обнаружены запрещённые поля",
            "status": "Pass" if not leak else "Fail",
        })
    except Exception as e:
        results.append({
            "id": "ТС-12", "desc": "Конфиденциальность",
            "expected": "Нет запрещённых полей", "actual": f"Ошибка: {e}", "status": "Fail",
        })

    return results


if __name__ == "__main__":
    from knowledge_base import KnowledgeBase
    from inference_bridge import InferenceBridge
    from database import HistoryStorage

    kb = KnowledgeBase("drugs.db", "knowledgebase.owl")
    bridge = InferenceBridge(kb)
    storage = HistoryStorage("history.db")

    report = run_all_tests(bridge, storage)
    report += run_ui_tests()

    print("\n=== ПРОТОКОЛ ИСПЫТАНИЙ ===")
    passed = 0
    for r in report:
        print(f"{r['id']} [{r['status']}] {r['desc']}")
        print(f"    ожидалось: {r['expected']}")
        print(f"    получено:  {r['actual']}")
        if r["status"] == "Pass":
            passed += 1
    print(f"\nИтого: {passed}/{len(report)} Pass")