# inference_bridge.py


import os
import time
import joblib
from dataclasses import dataclass, field
from typing import List, Dict

from knowledge_base import KnowledgeBase
from neural_net import NeuroClassifier
from neural_client import NeuralAPIClient
from rule_engine import RuleEngine
from explanation import ExplanationBuilder


MODEL_PATH = "neuro_model.pkl"


@dataclass
class DiagnosticResult:
    recommended: List = field(default_factory=list)
    excluded: List[Dict] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    explanation: str = ""
    elapsed: float = 0.0
    owl_used: bool = False
    neural_source: str = "local"  # "api" | "local"


class InferenceBridge:
    TOP_N = 3
    MIN_GROUP_PROB = 0.25

    W_SYMPTOM_MATCH = 3.0
    W_GROUP_PROB = 4.0
    W_SIDE_EFFECT_PENALTY = 0.3
    W_AGE_PENALTY = 0.5
    W_SUBSTANCE_BONUS = 0.5

    def __init__(self, kb: KnowledgeBase, model_path: str = MODEL_PATH):
        self.kb = kb
        self.api = NeuralAPIClient()

        loaded = False
        if os.path.exists(model_path):
            try:
                self.neuro = joblib.load(model_path)
                if len(self.neuro.groups) == len(kb.all_groups()):
                    print(f"[InferenceBridge] Модель загружена из {model_path}")
                    loaded = True
                else:
                    print("[InferenceBridge] Модель устарела, переобучаю...")
            except Exception as e:
                print(f"[InferenceBridge] Ошибка загрузки модели: {e}")

        if not loaded:
            print("[InferenceBridge] Обучение новой модели...")
            self.neuro = NeuroClassifier(
                symptoms_vocab=list(kb.symptoms.keys()),
                contra_vocab=list(kb.contraindications.keys()),
                drugs_vocab=list(kb.drugs.keys()),
                groups=kb.all_groups(),
            )
            self.neuro.fit_from_kb(kb)
            try:
                joblib.dump(self.neuro, model_path)
                print(f"[InferenceBridge] Модель сохранена в {model_path}")
            except Exception as e:
                print(f"[InferenceBridge] Не удалось сохранить модель: {e}")

        self.rules = RuleEngine(kb)
        self.explainer = ExplanationBuilder()

    # ------------------------------------------------------------------
    def run_diagnosis(self, patient: Dict) -> DiagnosticResult:
        start = time.time()

        symptoms = patient.get("symptoms", [])
        chronic = patient.get("chronic", [])
        allergies = patient.get("allergies", [])
        current_drugs = patient.get("current_drugs", [])
        age = patient.get("age", 30)

        # 1. Нейросеть: сначала внешний API (готовая), иначе локальный суррогат
        predicted = None
        neural_source = "local"
        if self.api.enabled:
            predicted = self.api.predict_groups(
                symptoms=symptoms, chronic=chronic, allergies=allergies,
                age=age, current_drugs=current_drugs,
            )
            if predicted is not None:
                neural_source = "api"

        if predicted is None:
            predicted = self.neuro.predict_groups(
                symptoms=symptoms, chronic=chronic, allergies=allergies,
                age=age, current_drugs=current_drugs,
            )

        groups_with_prob = [(g, p) for g, p in predicted if p >= self.MIN_GROUP_PROB]

        # 2. Фолбэк, если нейросеть не дала ни одной группы
        if not groups_with_prob:
            fallback = self.rules.rule1_groups_by_symptoms(symptoms)
            groups_with_prob = [(g, 0.0) for g in fallback[:5]]

        groups = [g for g, _ in groups_with_prob]

        # 3. Кандидаты: сначала OWL (ЛР3), затем SQLite (fallback/дополнение)
        candidates = []
        seen = set()

        # 3a. OWL/SPARQL — первичный источник (демонстрирует интеграцию БЗ)
        owl_names = self.kb.sparql_drugs_by_symptoms(symptoms)
        for name in owl_names:
            drug = self.kb.drugs.get(name)
            if drug and drug.name not in seen:
                seen.add(drug.name)
                candidates.append(drug)

        # 3b. SQLite по группам — дополняем (гарантирует покрытие)
        for g in groups:
            for d in self.kb.get_drugs_by_group(g):
                if d.name not in seen:
                    seen.add(d.name)
                    candidates.append(d)

        # 4. Правила 3–6 (только если данные введены)
        recommended, excluded = [], []
        for drug in candidates:
            reason = None

            if chronic and self.rules.rule3_excluded_by_contraindication(drug, chronic):
                reason = "противопоказание"
            elif allergies and self.rules.rule4_excluded_by_allergy(drug, allergies):
                reason = "аллергия"
            elif self.rules.rule6_age_restriction(drug, age):
                reason = "возраст"
            elif current_drugs:
                bad, _ = self.rules.rule5_interaction(drug, current_drugs)
                if bad:
                    reason = "взаимодействие"

            if reason:
                excluded.append({"drug": drug.name, "reason": reason})
            else:
                recommended.append(drug)

        # 5. Ранжирование
        prob_map = dict(groups_with_prob)
        scored = [(d, self._score(d, symptoms, prob_map, age)) for d in recommended]
        scored.sort(key=lambda x: x[1], reverse=True)

        # 6. Топ-N с score > 0
        top = [d for d, s in scored if s > 0][:self.TOP_N]

        # 7. Пояснение
        explanation = self.explainer.build(patient, top, excluded, groups_with_prob)

        return DiagnosticResult(
            recommended=top,
            excluded=excluded,
            groups=[f"{g} ({p:.2f})" for g, p in groups_with_prob],
            explanation=explanation,
            elapsed=round(time.time() - start, 3),
            owl_used=bool(owl_names),
            neural_source=neural_source,
        )

    # ------------------------------------------------------------------
    def _score(self, drug, symptoms, prob_map, age) -> float:
        matched = sum(1 for s in symptoms if s in drug.indications)

        # Приоритет «температура», «запор», «диарея», «изжога»
        specific = 0
        for s in symptoms:
            if s in drug.indications:
                specific += 3 if s in ("температура", "запор", "диарея", "изжога") else 2

        group_prob = prob_map.get(drug.group, 0.0)
        side_penalty = len(drug.side_effects) * self.W_SIDE_EFFECT_PENALTY

        age_penalty = 0.0
        if drug.min_age > 0 and age - drug.min_age < 3:
            age_penalty += self.W_AGE_PENALTY
        if drug.max_age < 120 and drug.max_age - age < 5:
            age_penalty += self.W_AGE_PENALTY

        substance_bonus = 0.0
        active_lower = drug.active_substance.lower()
        for s in symptoms:
            if s.lower() in active_lower:
                substance_bonus += self.W_SUBSTANCE_BONUS

        return (
            specific
            + self.W_GROUP_PROB * group_prob
            - side_penalty
            - age_penalty
            + substance_bonus
        )