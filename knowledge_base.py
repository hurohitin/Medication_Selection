# knowledge_base.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import os
import sqlite3

OWL_AVAILABLE = False
try:
    from owlready2 import get_ontology
    OWL_AVAILABLE = True
except ImportError:
    OWL_AVAILABLE = False


@dataclass
class Drug:
    name: str
    active_substance: str
    group: str
    atx_code: str = ""
    indications: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    interactions: List[str] = field(default_factory=list)
    min_age: int = 0
    max_age: int = 120


@dataclass
class Symptom:
    name: str
    location: str = ""


@dataclass
class Contraindication:
    name: str
    type: str = "относительное"
    risk: str = "средняя"


class KnowledgeBase:
    """
    База знаний. Загружает данные из SQLite (drugs.db).
    OWL-файл (knowledgebase.owl) загружается и используется для SPARQL-отбора
    кандидатов (ЛР3, ЛР6).
    """

    def __init__(self, db_path: str = "drugs.db", owl_path: str = "knowledgebase.owl"):
        self.db_path = db_path
        self.owl_path = owl_path
        self.onto = None
        self.use_owl = False

        self.symptoms: Dict[str, Symptom] = {}
        self.drugs: Dict[str, Drug] = {}
        self.groups: Dict[str, str] = {}
        self.contraindications: Dict[str, Contraindication] = {}
        self.interactions: List[tuple] = []

        self._try_load_owl()
        self._load_from_db()

    # ---------- OWL (ЛР3, ЛР6) ----------
    def _try_load_owl(self):
        if not OWL_AVAILABLE:
            print("[KnowledgeBase] owlready2 не установлен — OWL пропущен.")
            return
        if not os.path.exists(self.owl_path):
            print(f"[KnowledgeBase] OWL-файл '{self.owl_path}' не найден — пропущен.")
            return
        try:
            self.onto = get_ontology(self.owl_path).load()
            self.use_owl = True
            print(f"[KnowledgeBase] OWL-онтология загружена: {self.owl_path}")
        except Exception as e:
            print(f"[KnowledgeBase] Ошибка загрузки OWL: {e}")

    # ---------- SQLite (ЛР6) ----------
    def _load_from_db(self):
        if not os.path.exists(self.db_path):
            print(f"[KnowledgeBase] БД '{self.db_path}' не найдена. Запусти seed_data.py")
            return

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Группы
        cur.execute("SELECT id, name, atx_code FROM groups")
        group_id_to_name = {}
        for gid, gname, atx in cur.fetchall():
            self.groups[gname] = atx
            group_id_to_name[gid] = gname

        # Симптомы
        cur.execute("SELECT name, location FROM symptoms")
        for name, loc in cur.fetchall():
            self.symptoms[name] = Symptom(name=name, location=loc or "")

        # Противопоказания
        cur.execute("SELECT name, type, risk FROM contraindications")
        for name, ctype, risk in cur.fetchall():
            self.contraindications[name] = Contraindication(name=name, type=ctype, risk=risk)

        # Препараты
        cur.execute("""SELECT id, name, active_substance, group_id, min_age, max_age
                       FROM drugs""")
        drug_id_to_obj = {}
        for did, dname, active, gid, min_age, max_age in cur.fetchall():
            gname = group_id_to_name.get(gid, "Прочее")
            drug = Drug(
                name=dname,
                active_substance=active,
                group=gname,
                atx_code=self.groups.get(gname, ""),
                min_age=min_age or 0,
                max_age=max_age or 120,
            )
            self.drugs[dname] = drug
            drug_id_to_obj[did] = drug

        # Показания
        cur.execute("""SELECT ds.drug_id, s.name
                       FROM drug_symptoms ds JOIN symptoms s ON s.id = ds.symptom_id""")
        for did, sname in cur.fetchall():
            if did in drug_id_to_obj:
                drug_id_to_obj[did].indications.append(sname)

        # Противопоказания
        cur.execute("""SELECT dc.drug_id, c.name
                       FROM drug_contra dc JOIN contraindications c ON c.id = dc.contra_id""")
        for did, cname in cur.fetchall():
            if did in drug_id_to_obj:
                drug_id_to_obj[did].contraindications.append(cname)

        # Побочные реакции
        cur.execute("""SELECT ds.drug_id, se.name
                       FROM drug_side ds JOIN side_effects se ON se.id = ds.side_id""")
        for did, sename in cur.fetchall():
            if did in drug_id_to_obj:
                drug_id_to_obj[did].side_effects.append(sename)

        # Взаимодействия
        cur.execute("""SELECT da.name, db.name, di.severity, di.mechanism
                       FROM drug_interactions di
                       JOIN drugs da ON da.id = di.drug_a_id
                       JOIN drugs db ON db.id = di.drug_b_id""")
        for a, b, sev, mech in cur.fetchall():
            self.interactions.append((a, b, sev, mech))
            if a in self.drugs:
                self.drugs[a].interactions.append(b)
            if b in self.drugs:
                self.drugs[b].interactions.append(a)

        conn.close()

        print(f"[KnowledgeBase] Загружено: {len(self.drugs)} препаратов, "
              f"{len(self.symptoms)} симптомов, "
              f"{len(self.contraindications)} противопоказаний, "
              f"{len(self.interactions)} взаимодействий.")

    # ---------- API для «моста» ----------
    def get_drugs_by_symptom(self, symptom: str) -> List[Drug]:
        return [d for d in self.drugs.values() if symptom in d.indications]

    def get_drugs_by_group(self, group: str) -> List[Drug]:
        return [d for d in self.drugs.values() if d.group == group]

    def get_contraindication(self, name: str) -> Optional[Contraindication]:
        return self.contraindications.get(name)

    def get_interactions_for(self, drug_name: str) -> List[tuple]:
        result = []
        for a, b, sev, mech in self.interactions:
            if a == drug_name or b == drug_name:
                result.append((a, b, sev, mech))
        return result

    def all_groups(self) -> List[str]:
        return list(self.groups.keys())

    # ---------- OWL / SPARQL (ЛР3, ЛР6) ----------
    def sparql_drugs_by_symptoms(self, symptoms: List[str]) -> List[str]:
        """
        Возвращает имена препаратов, показанных при данных симптомах,
        ЧЕРЕЗ OWL-ОНТОЛОГИЮ (SPARQL). Используется как первичный источник
        кандидатов в «Мосте». Если OWL недоступна — возвращает [].
        """
        if not self.use_owl or self.onto is None or not symptoms:
            return []

        # Сопоставляем русские названия симптомов с локальными именами
        # индивидов онтологии через data property «название_симптома».
        symptom_iris = []
        for s in symptoms:
            try:
                ind = self.onto.search_one(название_симптома=s)
            except Exception:
                ind = None
            if ind is not None:
                symptom_iris.append(ind.name)

        if not symptom_iris:
            return []

        values = ", ".join(f":{iri}" for iri in symptom_iris)
        query = f"""
        PREFIX : <http://www.semanticweb.org/med#>
        SELECT DISTINCT ?prepName WHERE {{
            ?prep a :препарат .
            ?prep :название_препарата ?prepName .
            ?prep :показанПри ?sym .
            VALUES ?sym {{ {values} }}
        }}
        """
        try:
            rows = list(self.onto.world.sparql(query))
            return [str(r[0]) for r in rows if r and r[0]]
        except Exception as e:
            print(f"[KnowledgeBase] SPARQL error: {e}")
            return []