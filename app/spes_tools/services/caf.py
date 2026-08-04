from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Calculation:
    category: str
    direction: str
    input_amount: float
    gross: float
    net: float
    previdential: float = 0.0
    other_contrib: float = 0.0
    taxes: float = 0.0
    note: str = ""


def money(value: float) -> str:
    s = f"{value:,.2f}"
    return "€ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def parse_amount(value: object) -> float:
    text = str(value).strip().replace("€", "").replace(" ", "")
    if not text:
        raise ValueError("Importo mancante")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    number = float(text)
    if number < 0:
        raise ValueError("L'importo non può essere negativo")
    return number


class Engines:
    SPORT_PREV_RATE = 1 / 24
    SPORT_OTHER_RATE = 0.0203 / 3
    SPORT_THRESHOLD = 5000.0

    @staticmethod
    def worker_rate(total_rate_pct: float, taxable_base_pct: float) -> float:
        return (total_rate_pct / 100.0) * (taxable_base_pct / 100.0) / 3.0

    @classmethod
    def employee_pensioner_from_gross(cls, category: str, gross: float, total_rate_pct: float = 24.0, taxable_base_pct: float = 50.0) -> Calculation:
        rate = cls.worker_rate(total_rate_pct, taxable_base_pct)
        previdential = round(gross * rate, 2)
        net = round(gross - previdential, 2)
        return Calculation(
            category=category,
            direction="Lordo → Netto",
            input_amount=gross,
            gross=round(gross, 2),
            net=net,
            previdential=previdential,
            note=(
                f"Calcolo basato sul prospetto TeamSystem fornito: aliquota complessiva {total_rate_pct:.2f}%, "
                f"base imponibile {taxable_base_pct:.2f}%, quota percettore 1/3. "
                "IRPEF e addizionali non applicate nel caso campione."
            ),
        )

    @classmethod
    def employee_pensioner(cls, category: str, direction: str, amount: float, total_rate_pct: float = 24.0, taxable_base_pct: float = 50.0) -> Calculation:
        if direction == "Lordo → Netto":
            return cls.employee_pensioner_from_gross(category, amount, total_rate_pct, taxable_base_pct)
        target_net = round(amount, 2)
        rate = cls.worker_rate(total_rate_pct, taxable_base_pct)
        if rate >= 1:
            raise ValueError("Le percentuali inserite producono una trattenuta non valida.")
        gross = round(target_net / (1 - rate), 2)
        result = cls.employee_pensioner_from_gross(category, gross, total_rate_pct, taxable_base_pct)
        for cents in range(-5, 6):
            candidate = cls.employee_pensioner_from_gross(category, round(gross + cents / 100, 2), total_rate_pct, taxable_base_pct)
            if candidate.net == target_net:
                result = candidate
                break
        result.direction = direction
        result.input_amount = target_net
        return result

    @classmethod
    def sport_from_gross(cls, gross: float, already_received: float = 0.0, sport_type: str = "Lavoratore sportivo") -> Calculation:
        before_excess = max(0.0, already_received - cls.SPORT_THRESHOLD)
        after_excess = max(0.0, already_received + gross - cls.SPORT_THRESHOLD)
        contributory_part = max(0.0, min(gross, after_excess - before_excess))
        previdential = round(contributory_part * cls.SPORT_PREV_RATE, 2)
        other = round(contributory_part * cls.SPORT_OTHER_RATE, 2) if sport_type == "Lavoratore sportivo" else 0.0
        net = round(gross - previdential - other, 2)
        return Calculation(
            category=sport_type,
            direction="Lordo → Netto",
            input_amount=gross,
            gross=round(gross, 2),
            net=net,
            previdential=previdential,
            other_contrib=other,
            note=(
                "Calcolo sportivo calibrato sui prospetti TeamSystem forniti: soglia annua €5.000, "
                "quota previdenziale percettore 4,1667%; quota aggiuntiva 0,6767% solo per Lavoratore sportivo."
            ),
        )

    @classmethod
    def sport(cls, direction: str, amount: float, already_received: float = 0.0, sport_type: str = "Lavoratore sportivo") -> Calculation:
        if direction == "Lordo → Netto":
            return cls.sport_from_gross(amount, already_received, sport_type)
        target_net = round(amount, 2)
        low, high = target_net, max(target_net + 1000.0, target_net * 1.2)
        while cls.sport_from_gross(high, already_received, sport_type).net < target_net:
            high *= 2
        for _ in range(80):
            mid = (low + high) / 2
            if cls.sport_from_gross(mid, already_received, sport_type).net < target_net:
                low = mid
            else:
                high = mid
        gross = round(high, 2)
        result = cls.sport_from_gross(gross, already_received, sport_type)
        for cents in range(-10, 11):
            candidate_gross = round(gross + cents / 100, 2)
            if candidate_gross < 0:
                continue
            candidate = cls.sport_from_gross(candidate_gross, already_received, sport_type)
            if candidate.net == target_net:
                result = candidate
                break
        result.direction = direction
        result.input_amount = target_net
        return result


def result_lines(r: Calculation) -> list[str]:
    return [
        f"Categoria: {r.category}",
        f"Direzione: {r.direction}",
        "",
        f"Lordo: {money(r.gross)}",
        f"Contributo previdenziale: {money(r.previdential)}",
        f"Altri contributi: {money(r.other_contrib)}",
        f"IRPEF/addizionali: {money(r.taxes)}",
        "-----------------------------------------------",
        f"Netto: {money(r.net)}",
        "",
        f"Nota: {r.note}",
    ]


def pdf_bytes(r: Calculation) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _, height = A4
    y = height - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(55, y, "SPES - CAF Tools - Calcolo Lordo/Netto")
    y -= 35
    c.setFont("Helvetica", 11)
    for line in result_lines(r):
        c.drawString(55, y, line.replace("€", "EUR"))
        y -= 18
        if y < 60:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)
    c.save()
    return buf.getvalue()


def history_path() -> Path:
    return Path.home() / "SPES_CAF_Tools_storico.csv"


def append_caf_history(r: Calculation) -> Path:
    path = history_path()
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        if new_file:
            writer.writerow(["Data", "Categoria", "Direzione", "Input", "Lordo", "Previdenziale", "Altri contributi", "IRPEF/addizionali", "Netto"])
        writer.writerow([
            datetime.now().strftime("%d/%m/%Y %H:%M"), r.category, r.direction,
            f"{r.input_amount:.2f}", f"{r.gross:.2f}", f"{r.previdential:.2f}",
            f"{r.other_contrib:.2f}", f"{r.taxes:.2f}", f"{r.net:.2f}",
        ])
    return path
