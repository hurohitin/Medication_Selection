# explanation.py


from typing import List, Dict, Tuple


class ExplanationBuilder:

    def build(self, patient: Dict, recommended: List, excluded: List[Dict],
              groups_with_prob: List[Tuple[str, float]] = None) -> str:
        lines = []
        lines.append("=== Пояснение ===")

        if patient.get("symptoms"):
            lines.append(f"Симптомы: {', '.join(patient['symptoms'])}")
        if patient.get("age"):
            lines.append(f"Возраст: {patient['age']}")
        if patient.get("chronic"):
            lines.append(f"Хронические: {', '.join(patient['chronic'])}")
        if patient.get("allergies"):
            lines.append(f"Аллергии: {', '.join(patient['allergies'])}")
        if patient.get("current_drugs"):
            lines.append(f"Принимает: {', '.join(patient['current_drugs'])}")

        lines.append("")
        if groups_with_prob:
            groups_str = ", ".join(f"{g} ({p:.2f})" for g, p in groups_with_prob)
            lines.append(f"Группы: {groups_str}")

        if recommended:
            lines.append(f"Рекомендовано: {', '.join(d.name for d in recommended)}")
        else:
            lines.append("Рекомендаций нет.")

        if excluded:
            lines.append(f"Исключено: {len(excluded)} препаратов.")
            by_reason = {}
            for e in excluded:
                by_reason.setdefault(e["reason"], []).append(e["drug"])
            for reason, drugs in by_reason.items():
                lines.append(f"  • {reason}: {len(drugs)}")

        lines.append("")
        lines.append("Результат носит рекомендательный характер и не заменяет врача.")
        return "\n".join(lines)