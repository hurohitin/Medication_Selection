# neural_net.py


import numpy as np
import random
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from typing import List, Tuple


class NeuroClassifier:
    def __init__(self,
                 symptoms_vocab: List[str],
                 contra_vocab: List[str],
                 drugs_vocab: List[str],
                 groups: List[str]):
        self.symptoms_vocab = list(symptoms_vocab)
        self.contra_vocab = list(contra_vocab)
        self.drugs_vocab = list(drugs_vocab)
        self.groups = list(groups)

        self.mlb_symptoms = MultiLabelBinarizer(classes=self.symptoms_vocab)
        self.mlb_contra = MultiLabelBinarizer(classes=self.contra_vocab)
        self.mlb_drugs = MultiLabelBinarizer(classes=self.drugs_vocab)

        self.mlp = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation="relu",
            solver="adam",
            max_iter=1500,
            random_state=42,
            early_stopping=True,
            n_iter_no_change=20,
        )
        self.rf = RandomForestClassifier(
            n_estimators=100, random_state=42, n_jobs=-1,
        )
        self._trained = False

    # ------------------------------------------------------------------
    def _build_vector(self, symptoms, chronic, allergies, age, current_drugs):
        s_vec = self.mlb_symptoms.transform([symptoms])[0]
        c_vec = self.mlb_contra.transform([chronic])[0]
        allergies_known = [a for a in allergies if a in self.contra_vocab]
        a_vec = self.mlb_contra.transform([allergies_known])[0]
        d_vec = self.mlb_drugs.transform([current_drugs])[0]
        age_vec = np.array([age / 120.0])
        return np.concatenate([s_vec, c_vec, a_vec, d_vec, age_vec])

    # ------------------------------------------------------------------
    def fit_from_kb(self, kb):
        X_raw, y = [], []
        all_symptoms = list(kb.symptoms.keys())

        for drug in kb.drugs.values():
            if not drug.indications:
                continue

            for _ in range(50):
                n_sym = min(len(drug.indications), random.randint(1, 3))
                symptoms = random.sample(drug.indications, n_sym)

                if random.random() < 0.3:
                    extra = random.choice(all_symptoms)
                    if extra not in symptoms:
                        symptoms.append(extra)

                if len(symptoms) > 1 and random.random() < 0.2:
                    symptoms = symptoms[:-1]

                chronic = []
                if drug.contraindications and random.random() < 0.4:
                    chronic = random.sample(drug.contraindications, 1)

                allergies = []
                if random.random() < 0.15:
                    allergies = [drug.active_substance]

                if random.random() < 0.2:
                    age = random.choice([5, 10, 15, 80, 90])
                else:
                    age = random.randint(drug.min_age, min(drug.max_age, 100))

                current_drugs = []
                if drug.interactions and random.random() < 0.3:
                    current_drugs = [random.choice(drug.interactions)]

                X_raw.append((symptoms, chronic, allergies, age, current_drugs))
                y.append(drug.group)

        if not X_raw:
            print("[NeuroClassifier] Нет данных для обучения.")
            return

        self.mlb_symptoms.fit([s for s, _, _, _, _ in X_raw])
        self.mlb_contra.fit([c for _, c, _, _, _ in X_raw])
        self.mlb_drugs.fit([d for _, _, _, _, d in X_raw])

        X = np.array([
            self._build_vector(s, c, a, age, d)
            for (s, c, a, age, d) in X_raw
        ])

        self.mlp.fit(X, y)
        self.rf.fit(X, y)
        self._trained = True
        print(f"[NeuroClassifier] Обучено на {len(X)} примерах, классов: {len(set(y))}.")

    # ------------------------------------------------------------------
    def predict_groups(self,
                       symptoms: List[str],
                       chronic: List[str] = None,
                       allergies: List[str] = None,
                       age: int = 30,
                       current_drugs: List[str] = None) -> List[Tuple[str, float]]:
        if not self._trained:
            return [(g, 1.0 / len(self.groups)) for g in self.groups]

        chronic = chronic or []
        allergies = allergies or []
        current_drugs = current_drugs or []

        symptoms_known = [s for s in symptoms if s in self.symptoms_vocab]
        chronic_known = [c for c in chronic if c in self.contra_vocab]
        allergies_known = [a for a in allergies if a in self.contra_vocab]
        drugs_known = [d for d in current_drugs if d in self.drugs_vocab]

        if not symptoms_known and not chronic_known and not allergies_known:
            return []

        x = self._build_vector(symptoms_known, chronic_known,
                               allergies_known, age, drugs_known).reshape(1, -1)
        proba = self.mlp.predict_proba(x)[0]
        pairs = list(zip(self.mlp.classes_, proba))
        pairs.sort(key=lambda p: p[1], reverse=True)
        return pairs

    def metrics(self, kb) -> dict:
        if not self._trained:
            return {}
        X_raw, y = [], []
        for drug in kb.drugs.values():
            if drug.indications:
                X_raw.append((drug.indications, [], [], drug.min_age, []))
                y.append(drug.group)
        if not X_raw:
            return {}
        X = np.array([self._build_vector(s, c, a, age, d)
                      for (s, c, a, age, d) in X_raw])
        return {
            "MLP": round(self.mlp.score(X, y), 4),
            "RF": round(self.rf.score(X, y), 4),
        }