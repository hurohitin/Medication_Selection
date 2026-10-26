# rule_engine.py


from typing import List, Dict, Tuple


# Синонимы аллергенов → что искать в действующем веществе / группе / названии
ALLERGY_SYNONYMS = {
    "аллергия на пенициллин": [
        "пенициллин", "амоксициллин", "ампициллин", "оксациллин",
        "пиперациллин", "бензилпенициллин", "амоксиклав", "аугментин",
        "флемоксин",
    ],
    "аллергия на аспирин": [
        "аспирин", "ацетилсалициловая", "кардиомагнил",
        "аспирин кардио",
    ],
    "аллергия на сульфаниламиды": [
        "сульфаниламид", "сульфаметоксазол", "сульфадиметоксин",
        "сульфален", "бисептол", "ко-тримоксазол", "сульфагуанидин",
        "фталилсульфатиазол",
    ],
    "аллергия на йод": [
        "йод", "повидон", "бетадин", "йодомарин", "калия йодид",
    ],
    "аллергия на новокаин": [
        "новокаин", "прокаин",
    ],
    "аллергия на лидокаин": [
        "лидокаин",
    ],
    "аллергия на анестетики": [
        "новокаин", "прокаин", "лидокаин", "бупивакаин",
    ],
}


class RuleEngine:
    def __init__(self, kb):
        self.kb = kb

    # Правило 1: симптомы → группы (по частоте встречаемости)
    def rule1_groups_by_symptoms(self, symptoms: List[str]) -> List[str]:
        from collections import Counter
        counter = Counter()
        for s in symptoms:
            for d in self.kb.get_drugs_by_symptom(s):
                counter[d.group] += 1
        return [g for g, _ in counter.most_common()]

    # Правило 2: препарат показан при симптомах
    def rule2_is_indicated(self, drug, symptoms: List[str]) -> bool:
        return any(s in drug.indications for s in symptoms)

    # Правило 3: противопоказание исключает препарат
    def rule3_excluded_by_contraindication(self, drug, patient_contra: List[str]) -> bool:
        return any(c in drug.contraindications for c in patient_contra)

    # Правило 4: аллергия (с учётом синонимов)
    def rule4_excluded_by_allergy(self, drug, allergies: List[str]) -> bool:
        if not allergies:
            return False

        active = drug.active_substance.lower()
        group = drug.group.lower()
        name = drug.name.lower()

        for a in allergies:
            a_low = a.lower().strip()

            # 1. Прямое вхождение в действующее вещество / название
            if a_low in active or a_low in name:
                return True

            # 2. Через синонимы
            if a_low in ALLERGY_SYNONYMS:
                for syn in ALLERGY_SYNONYMS[a_low]:
                    if syn in active or syn in name or syn in group:
                        return True

            # 3. Аллергия = группа препарата (например, "пенициллин" и группа "Пенициллин")
            group_key = a_low.replace("аллергия на ", "").strip()
            if group_key and group_key in group:
                return True

            # 4. Общие аллергии — исключаем всё
            if a_low in ("аллергия на компоненты", "индивидуальная непереносимость"):
                return True

        return False

    # Правило 5: взаимодействие с принимаемыми препаратами
    def rule5_interaction(self, drug, current_drugs: List[str]) -> Tuple[bool, str]:
        for cd in current_drugs:
            for a, b, sev, mech in self.kb.get_interactions_for(drug.name):
                if cd.lower() in (a.lower(), b.lower()):
                    return True, f"{sev}: {mech}"
        return False, ""

    # Правило 6: возрастные ограничения
    def rule6_age_restriction(self, drug, age: int) -> bool:
        return age < drug.min_age or age > drug.max_age

    # Правило 7: финальное включение
    def rule7_can_recommend(self, drug, patient: Dict) -> bool:
        if self.rule3_excluded_by_contraindication(drug, patient.get("chronic", [])):
            return False
        if self.rule4_excluded_by_allergy(drug, patient.get("allergies", [])):
            return False
        if self.rule6_age_restriction(drug, patient.get("age", 30)):
            return False
        bad, _ = self.rule5_interaction(drug, patient.get("current_drugs", []))
        return not bad

    # Правило 8: ранжирование
    def rule8_rank(self, drugs: List, patient: Dict) -> List:
        symptoms = patient.get("symptoms", [])

        def score(d):
            s = 0
            for sym in symptoms:
                if sym in d.indications:
                    s += 3 if sym in ("температура", "запор", "диарея", "изжога") else 2
            return s

        return sorted(drugs, key=score, reverse=True)