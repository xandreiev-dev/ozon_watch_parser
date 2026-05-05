from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from ozon_watch_parser.config.brands import BRAND_URLS
from ozon_watch_parser.config.columns import OUTPUT_COLUMNS


def brand_file_name(brand: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", brand.strip().lower())
    return f"ozon_watch_{safe}.xlsx"


def final_output_file_name(run_date: date | None = None) -> str:
    run_date = run_date or date.today()
    return f"Ozon_watch_ru_{run_date.strftime('%Y%m%d')}.xlsx"


class StreamingXlsxWriter:
    def __init__(self, path: str | Path, columns: list[str] | None = None):
        self.path = Path(path)
        self.columns = columns or OUTPUT_COLUMNS
        self.workbook = None
        self.sheet = None
        self._open()

    def _open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.workbook = Workbook()
        self.sheet = self.workbook.active
        self.sheet.title = "Data"
        self.sheet.append(self.columns)
        self._save()

    def _save(self) -> None:
        self.workbook.save(self.path)

    @staticmethod
    def excel_safe(value):
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    def append_many(self, rows: list[dict]) -> None:
        if not rows:
            return
        for row in rows:
            self.sheet.append([self.excel_safe(row.get(column, "")) for column in self.columns])
        self._save()

    def close(self) -> None:
        if self.workbook:
            self._save()


def aggregate_brand_exports(
    export_dir: str | Path,
    run_date: date | None = None,
) -> tuple[Path | None, int]:
    export_path = Path(export_dir)
    expected_names = {brand_file_name(brand) for brand in BRAND_URLS}
    files = sorted(path for path in export_path.iterdir() if path.is_file() and path.name in expected_names)
    frames: list[pd.DataFrame] = []

    for path in files:
        try:
            frame = pd.read_excel(path)
        except Exception:
            continue
        if "Article" in frame.columns:
            frame = frame[frame["Article"].fillna("").astype(str).str.strip() != ""].copy()
        if "model" in frame.columns:
            # Не выкидываем неизвестные модели: для часов это полезный сырой материал.
            frame["model"] = frame["model"].fillna("")
        if not frame.empty:
            frames.append(frame)

    if not frames:
        return None, 0

    combined = pd.concat(frames, ignore_index=True)
    if "Article" in combined.columns:
        combined = combined.drop_duplicates(subset=["Article"], keep="first")

    ordered_columns = [column for column in OUTPUT_COLUMNS if column in combined.columns]
    ordered_columns.extend(column for column in combined.columns if column not in ordered_columns)
    combined = combined[ordered_columns]

    out_path = export_path / final_output_file_name(run_date=run_date)
    combined.to_excel(out_path, index=False, engine="openpyxl")

    for path in files:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    return out_path, len(combined)
