from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "results" / "summary.csv"
REPORT_PATH = ROOT / "results" / "edge_cache_fallback_report.xlsx"


def main() -> None:
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError("Run scripts/run_experiment.py before building the report.")

    data = pd.read_csv(SUMMARY_PATH)
    workbook = Workbook()
    overview = workbook.active
    overview.title = "Overview"
    parameters = workbook.create_sheet("Parameters")
    summary = workbook.create_sheet("Summary")
    charts = workbook.create_sheet("Charts")

    _build_overview(overview, data)
    _build_parameters(parameters, data)
    _build_summary(summary, data)
    _build_charts(charts, data)

    for sheet in workbook.worksheets:
        sheet.sheet_view.showGridLines = False
        _size_columns(sheet)

    REPORT_PATH.parent.mkdir(exist_ok=True)
    workbook.save(REPORT_PATH)
    print(f"Wrote {REPORT_PATH}")


def _build_overview(sheet, data: pd.DataFrame) -> None:
    best_mean = data.loc[data["mean_response_time"].idxmin()]
    best_p95 = data.loc[data["p95_response_time"].idxmin()]

    rows = [
        ["Edge Cache Fallback Report", ""],
        ["Scenario", str(data["scenario"].iloc[0])],
        ["Policies", ", ".join(data["policy"].tolist())],
        ["Best mean response time", f"{best_mean['policy']} ({best_mean['mean_response_time']:.3f})"],
        ["Best p95 response time", f"{best_p95['policy']} ({best_p95['p95_response_time']:.3f})"],
        ["Main use", "Readable first-stage report; CSV remains the reproducible data source."],
    ]
    for row in rows:
        sheet.append(row)

    sheet.merge_cells("A1:B1")
    sheet["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="1F4E79")
    for cell in sheet["A"]:
        cell.font = Font(bold=True)
    sheet["A6"].alignment = Alignment(wrap_text=True)
    sheet["B6"].alignment = Alignment(wrap_text=True)


def _build_parameters(sheet, data: pd.DataFrame) -> None:
    parameter_cols = [
        "zipf_alpha",
        "es_availability",
        "origin_delay",
        "local_es_count",
        "neighbor_group_size",
        "k",
    ]
    sheet.append(["Parameter", "Value"])
    first_row = data.iloc[0]
    for name in parameter_cols:
        sheet.append([name, first_row[name]])
    _style_header(sheet, "A1:B1")
    _add_table(sheet, "A1:B7", "ParametersTable")


def _build_summary(sheet, data: pd.DataFrame) -> None:
    display_cols = [
        "policy",
        "mean_response_time",
        "p95_response_time",
        "origin_free_rate",
        "neighbor_failure_rate",
    ]
    sheet.append(display_cols)
    for row in data[display_cols].itertuples(index=False):
        sheet.append(list(row))

    _style_header(sheet, "A1:E1")
    _add_table(sheet, f"A1:E{len(data) + 1}", "SummaryTable")

    for col in ("B", "C"):
        for cell in sheet[col][1:]:
            cell.number_format = "0.000"
    for col in ("D", "E"):
        for cell in sheet[col][1:]:
            cell.number_format = "0.00%"


def _build_charts(sheet, data: pd.DataFrame) -> None:
    chart_data = data[
        [
            "policy",
            "mean_response_time",
            "p95_response_time",
            "origin_free_rate",
            "neighbor_failure_rate",
        ]
    ]
    for row in chart_data.itertuples(index=False):
        if sheet.max_row == 1 and sheet.max_column == 1 and sheet["A1"].value is None:
            sheet.append(chart_data.columns.tolist())
        sheet.append(list(row))

    _style_header(sheet, "A1:E1")

    _add_chart(sheet, "Mean Response Time", 2, "G2")
    _add_chart(sheet, "P95 Response Time", 3, "G18")
    _add_chart(sheet, "Origin-Free Rate", 4, "A18")
    _add_chart(sheet, "Neighbor Failure Rate", 5, "A34")


def _add_chart(sheet, title: str, value_col: int, anchor: str) -> None:
    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = title
    chart.y_axis.title = title
    chart.x_axis.title = "Policy"
    chart.height = 7
    chart.width = 12

    values = Reference(sheet, min_col=value_col, min_row=1, max_row=4)
    categories = Reference(sheet, min_col=1, min_row=2, max_row=4)
    chart.add_data(values, titles_from_data=True)
    chart.set_categories(categories)
    chart.legend = None
    sheet.add_chart(chart, anchor)


def _style_header(sheet, range_name: str) -> None:
    for row in sheet[range_name]:
        for cell in row:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E79")
            cell.alignment = Alignment(horizontal="center")


def _add_table(sheet, ref: str, name: str) -> None:
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    sheet.add_table(table)


def _size_columns(sheet) -> None:
    for column_cells in sheet.columns:
        max_length = 0
        column_letter = get_column_letter(column_cells[0].column)
        for cell in column_cells:
            max_length = max(max_length, len(str(cell.value or "")))
        sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 34)


if __name__ == "__main__":
    main()
