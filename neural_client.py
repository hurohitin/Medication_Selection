# neural_client.py


import os
from typing import List, Tuple, Optional

try:
    import requests
except ImportError:  # если requests не установлен — API просто отключён
    requests = None


class NeuralAPIClient:
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None,
                 timeout: float = 3.0):
        self.url = url or os.getenv("NEURO_API_URL", "")
        self.token = token or os.getenv("NEURO_API_TOKEN", "")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.url) and requests is not None

    def predict_groups(self, symptoms: List[str], chronic: List[str],
                       allergies: List[str], age: int,
                       current_drugs: List[str]) -> Optional[List[Tuple[str, float]]]:
        """
        Возвращает [(group, prob), ...] либо None, если API недоступен.
        """
        if not self.enabled:
            return None
        payload = {
            "symptoms": symptoms,
            "chronic": chronic,
            "allergies": allergies,
            "age": age,
            "current_drugs": current_drugs,
        }
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            r = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            preds = data.get("predictions", [])
            return [(p["group"], float(p["prob"])) for p in preds]
        except Exception as e:
            print(f"[NeuralAPIClient] API недоступен, fallback на локальную модель: {e}")
            return None