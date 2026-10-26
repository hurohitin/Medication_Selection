# main.py


import tkinter as tk
from tkinter import ttk, messagebox
import math

from knowledge_base import KnowledgeBase
from inference_bridge import InferenceBridge
from database import HistoryStorage


# ---------------------------------------------------------------------
BG_DARK      = "#0f172a"
BG_CARD      = "#1e293b"
BG_INPUT     = "#334155"
ACCENT       = "#38bdf8"
ACCENT_HOVER = "#0ea5e9"
TEXT_MAIN    = "#f1f5f9"
TEXT_MUTED   = "#94a3b8"
SUCCESS      = "#22c55e"
WARNING      = "#f59e0b"
DANGER       = "#ef4444"


class AnimatedBackground(tk.Canvas):
    def __init__(self, master, width=900, height=820, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG_DARK, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.circles = []
        for i in range(6):
            c = self.create_oval(0, 0, 0, 0, fill="", outline=ACCENT, width=1)
            self.circles.append({
                "id": c,
                "x": (i * 150) % width,
                "y": (i * 90) % height,
                "r": 40 + i * 15,
                "dx": 0.3 + i * 0.1,
                "dy": 0.2 + i * 0.05,
                "phase": i * 1.2,
            })
        self._animate()

    def _animate(self):
        for c in self.circles:
            c["x"] += c["dx"]
            c["y"] += c["dy"]
            if c["x"] > self.width + c["r"]:
                c["x"] = -c["r"]
            if c["y"] > self.height + c["r"]:
                c["y"] = -c["r"]
            r = c["r"] + 5 * math.sin(c["phase"])
            self.coords(c["id"],
                        c["x"] - r, c["y"] - r,
                        c["x"] + r, c["y"] + r)
        self.after(50, self._animate)


class DrugESApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Подбор лекарственных препаратов")
        self.root.geometry("900x780")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)

        self.kb = KnowledgeBase("drugs.db", "knowledgebase.owl")
        self.bridge = InferenceBridge(self.kb)
        self.storage = HistoryStorage("history.db")

        self._setup_styles()
        self._build_ui()

    # ------------------------------------------------------------------
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=BG_DARK)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("TLabel", background=BG_DARK, foreground=TEXT_MAIN,
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG_DARK, foreground=TEXT_MAIN,
                        font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background=BG_DARK, foreground=TEXT_MUTED,
                        font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground=BG_INPUT, foreground=TEXT_MAIN,
                        bordercolor=BG_INPUT, insertcolor=TEXT_MAIN)
        style.configure("Accent.TButton", background=ACCENT, foreground=BG_DARK,
                        font=("Segoe UI", 11, "bold"),
                        borderwidth=0, focusthickness=0, padding=10)
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])
        style.configure("Ghost.TButton", background=BG_CARD, foreground=TEXT_MAIN,
                        font=("Segoe UI", 10), borderwidth=0, padding=8)
        style.map("Ghost.TButton", background=[("active", BG_INPUT)])

    # ------------------------------------------------------------------
    def _build_ui(self):
        self.bg_canvas = AnimatedBackground(self.root)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        main = ttk.Frame(self.root)
        main.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(main, text="Подбор лекарственных препаратов",
                  style="Title.TLabel").pack(pady=(0, 4))
        ttk.Label(main, text="Введите симптомы и данные о пациенте",
                  style="Subtitle.TLabel").pack(pady=(0, 20))

        card = ttk.Frame(main, style="Card.TFrame", padding=20)
        card.pack(fill="x", pady=10)

        # Симптомы
        ttk.Label(card, text="Симптомы (через запятую)",
                  background=BG_CARD).pack(anchor="w")
        self.symptoms_entry = tk.Text(card, height=3, width=70,
                                      bg=BG_INPUT, fg=TEXT_MAIN,
                                      insertbackground=TEXT_MAIN,
                                      relief="flat", font=("Segoe UI", 10),
                                      padx=8, pady=6)
        self.symptoms_entry.pack(fill="x", pady=(4, 12))

        hints = ", ".join(list(self.kb.symptoms.keys())[:8])
        ttk.Label(card, text=f"Например: {hints}",
                  background=BG_CARD, foreground=TEXT_MUTED,
                  font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(0, 12))

        # Возраст / Пол
        row1 = ttk.Frame(card, style="Card.TFrame")
        row1.pack(fill="x", pady=4)

        ttk.Label(row1, text="Возраст", background=BG_CARD).pack(side="left")
        self.age_spin = tk.Spinbox(row1, from_=0, to=120, width=6,
                                   bg=BG_INPUT, fg=TEXT_MAIN,
                                   insertbackground=TEXT_MAIN,
                                   relief="flat", font=("Segoe UI", 10),
                                   buttonbackground=BG_INPUT)
        self.age_spin.pack(side="left", padx=(8, 30))

        ttk.Label(row1, text="Пол", background=BG_CARD).pack(side="left")
        self.sex_entry = ttk.Entry(row1, width=6)
        self.sex_entry.insert(0, "М")
        self.sex_entry.pack(side="left", padx=8)

        # Хронические заболевания — обычное поле
        ttk.Label(card, text="Хронические заболевания (через запятую)",
                  background=BG_CARD).pack(anchor="w", pady=(12, 0))
        self.chronic_entry = ttk.Entry(card)
        self.chronic_entry.pack(fill="x", pady=(4, 12))

        # Аллергии — обычное поле
        ttk.Label(card, text="Аллергии (через запятую)",
                  background=BG_CARD).pack(anchor="w")
        self.allergies_entry = ttk.Entry(card)
        self.allergies_entry.pack(fill="x", pady=(4, 12))

        # Принимаемые препараты — обычное поле
        ttk.Label(card, text="Принимаемые препараты (через запятую)",
                  background=BG_CARD).pack(anchor="w")
        self.current_drugs_entry = ttk.Entry(card)
        self.current_drugs_entry.pack(fill="x", pady=(4, 0))

        # Кнопки
        btns = ttk.Frame(main)
        btns.pack(pady=18)

        self.find_btn = ttk.Button(btns, text="Подобрать",
                                   style="Accent.TButton",
                                   command=self.on_diagnose)
        self.find_btn.pack(side="left", padx=6)

        ttk.Button(btns, text="Очистить", style="Ghost.TButton",
                   command=self.on_clear).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    def _parse_list(self, s: str):
        return [x.strip().lower() for x in s.split(",") if x.strip()]

    def on_diagnose(self):
        try:
            age_raw = self.age_spin.get().strip()
            if not age_raw.isdigit():
                raise ValueError("Возраст должен быть целым неотрицательным числом.")
            age = int(age_raw)
            if age < 0 or age > 120:
                raise ValueError("Возраст должен быть в диапазоне 0–120.")

            patient = {
                "symptoms": self._parse_list(self.symptoms_entry.get("1.0", "end")),
                "age": age,
                "sex": self.sex_entry.get().strip() or "М",
                "chronic": self._parse_list(self.chronic_entry.get()),
                "allergies": self._parse_list(self.allergies_entry.get()),
                "current_drugs": self._parse_list(self.current_drugs_entry.get()),
            }

            if not patient["symptoms"]:
                messagebox.showwarning("Внимание", "Введите хотя бы один симптом.")
                return

        except ValueError as e:
            messagebox.showerror("Ошибка ввода", str(e))
            return

        self.find_btn.configure(text="Анализ...", state="disabled")
        self.root.after(300, lambda: self._run_and_show(patient))

    def _run_and_show(self, patient):
        try:
            result = self.bridge.run_diagnosis(patient)
            self.storage.save_history(patient, result)
            self._show_result_window(result, patient)
        except Exception as e:
            messagebox.showerror("Ошибка анализа",
                                 f"Не удалось выполнить анализ:\n{e}")
        finally:
            self.find_btn.configure(text="Подобрать", state="normal")

    # ------------------------------------------------------------------
    def _show_result_window(self, result, patient):
        win = tk.Toplevel(self.root)
        win.title("Результат подбора")
        win.configure(bg=BG_DARK)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        try:
            win.attributes("-alpha", 1.0)
        except Exception:
            pass

        target_w, target_h = 620, 660
        start_w, start_h = 400, 420
        win.geometry(f"{start_w}x{start_h}+"
                     f"{self.root.winfo_x() + 150}+{self.root.winfo_y() + 60}")

        def grow(w, h):
            w = min(w + 40, target_w)
            h = min(h + 40, target_h)
            win.geometry(f"{w}x{h}")
            if w < target_w or h < target_h:
                win.after(12, lambda: grow(w, h))
            else:
                try:
                    win.attributes("-alpha", 1.0)
                except Exception:
                    pass

        win.after(20, lambda: grow(start_w, start_h))

        tk.Label(win, text="Рекомендация",
                 bg=BG_DARK, fg=TEXT_MAIN,
                 font=("Segoe UI", 20, "bold")).pack(pady=(24, 4))
        tk.Label(win, text="На основании введённых данных",
                 bg=BG_DARK, fg=TEXT_MUTED,
                 font=("Segoe UI", 10)).pack(pady=(0, 20))

        card = tk.Frame(win, bg=BG_CARD, padx=20, pady=20)
        card.pack(fill="x", padx=24, pady=8)

        top = result.recommended[:3]

        if not top:
            tk.Label(card,
                     text="К сожалению, подходящих препаратов не найдено.\n"
                          "Попробуйте изменить симптомы или обратитесь к врачу.",
                     bg=BG_CARD, fg=WARNING,
                     font=("Segoe UI", 11), justify="center").pack(pady=20)
        else:
            for i, d in enumerate(top, 1):
                self._drug_row(card, i, d, patient)

        if result.excluded and top:
            tk.Label(win,
                     text=f"С учётом ваших данных не рекомендованы "
                          f"{len(result.excluded)} препаратов.",
                     bg=BG_DARK, fg=TEXT_MUTED,
                     font=("Segoe UI", 9, "italic")).pack(pady=(8, 0))

        disclaimer = tk.Frame(win, bg=BG_CARD, padx=14, pady=14)
        disclaimer.pack(fill="x", padx=24, pady=(16, 8))

        tk.Label(disclaimer, text="⚠  Внимание",
                 bg=BG_CARD, fg=WARNING,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(disclaimer,
                 text="Приложение носит рекомендательный характер\n"
                      "и не заменяет консультацию врача. Перед приёмом\n"
                      "любого препарата обратитесь к специалисту.",
                 bg=BG_CARD, fg=TEXT_MUTED,
                 font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=(4, 0))

        tk.Button(win, text="Закрыть",
                  bg=BG_CARD, fg=TEXT_MAIN,
                  activebackground=BG_INPUT, activeforeground=TEXT_MAIN,
                  font=("Segoe UI", 10), relief="flat",
                  padx=20, pady=8,
                  command=win.destroy).pack(pady=16)

    def _drug_row(self, parent, index, drug, patient):
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", pady=8)

        num = tk.Label(row, text=str(index),
                       bg=ACCENT, fg=BG_DARK,
                       font=("Segoe UI", 11, "bold"),
                       width=2, height=1)
        num.pack(side="left", padx=(0, 12))

        info = tk.Frame(row, bg=BG_CARD)
        info.pack(side="left", fill="x", expand=True)

        tk.Label(info, text=drug.name,
                 bg=BG_CARD, fg=TEXT_MAIN,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")

        matched = [s for s in patient["symptoms"] if s in drug.indications]
        reason = f"Показан при: {', '.join(matched)}" if matched \
            else f"Группа: {drug.group}"

        tk.Label(info, text=reason,
                 bg=BG_CARD, fg=TEXT_MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")

    # ------------------------------------------------------------------
    def on_clear(self):
        self.symptoms_entry.delete("1.0", "end")
        self.chronic_entry.delete(0, "end")
        self.allergies_entry.delete(0, "end")
        self.current_drugs_entry.delete(0, "end")
        self.age_spin.delete(0, "end"); self.age_spin.insert(0, "0")
        self.sex_entry.delete(0, "end"); self.sex_entry.insert(0, "М")


if __name__ == "__main__":
    root = tk.Tk()
    app = DrugESApp(root)
    root.mainloop()