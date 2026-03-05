# ---------------------------------------------------------------------------
# HTML Templates & Style Constants
# All HTML snippets and inline styles used by html_builder.py live here.
# To change the look of the emails, edit this file only.
# ---------------------------------------------------------------------------

# ── Colours ────────────────────────────────────────────────────────────────
COLOR_PRIMARY       = "#0057b8"
COLOR_ROW_HIGHLIGHT = "#ffeeba"
COLOR_DELAYED       = "#dc3545"
COLOR_ANTICIPATED   = "#218838"
COLOR_ADDED         = "#17a2b8"
COLOR_PENDING       = "#6c757d"
COLOR_WEEK_CHANGE_BORDER = "#28a745"
COLOR_WEEK_CHANGE_BG     = "#f8f9fa"
COLOR_TABLE_BG      = "#f9f9f9"
COLOR_HEADER_BG     = "#eaeaea"
COLOR_EMPTY_TEXT    = "#888"

# ── Styles ──────────────────────────────────────────────────────────────────
STYLE_TABLE         = "width:100%;border-collapse:collapse;background:#f9f9f9;"
STYLE_HEADER_ROW    = f"background:{COLOR_HEADER_BG};"
STYLE_CELL_CENTER   = "text-align:center;"

# ── Email header ────────────────────────────────────────────────────────────
def email_header(subject: str, intro_title: str, intro_body: str) -> str:
    return (
        f"<h1 style='color:{COLOR_PRIMARY};'>{subject}</h1>"
        f"<p><strong>{intro_title}</strong><br><br>{intro_body}</p>"
    )

# ── Email footer ────────────────────────────────────────────────────────────
EMAIL_FEEDBACK  = "<p><em>Feedback welcome.</em></p>"
EMAIL_FOOTER    = "<hr><small>Automated email.</small>"

# ── Section header ──────────────────────────────────────────────────────────
def section_header(title: str) -> str:
    return f"<div><h2 style='color:{COLOR_PRIMARY};'>{title}</h2>"

# ── Table ───────────────────────────────────────────────────────────────────
TABLE_OPEN  = f"<table border='1' cellspacing='0' cellpadding='4' style='{STYLE_TABLE}'>"
TABLE_CLOSE = "</table>"

def table_header_row(columns: list[str]) -> str:
    cells = "".join(f"<th>{col}</th>" for col in columns)
    return f"<tr style='{STYLE_HEADER_ROW}'>{cells}</tr>"

def table_row(cells: list[str], highlight: str = "") -> str:
    return f"<tr{highlight}>{''.join(cells)}</tr>"

# ── Cells ───────────────────────────────────────────────────────────────────
def cell(value: str) -> str:
    return f"<td>{value}</td>"

def cell_center(value: str) -> str:
    return f"<td style='{STYLE_CELL_CENTER}'>{value}</td>"

def cell_empty() -> str:
    return "<td></td>"

def cell_empty_center() -> str:
    return f"<td style='{STYLE_CELL_CENTER}'></td>"

def cell_link(url: str, label: str) -> str:
    return f"<td><a href='{url}' target='_blank'>{label}</a></td>"

def cell_changes(value: str, color: str) -> str:
    style = f"text-align:center;font-weight:bold;color:{color};"
    return f"<td style='{style}'>{value}</td>"

def cell_state_with_change(state: str, change: str) -> str:
    return f"<td><b>{state}</b><br>({change})</td>"

# ── Highlights ───────────────────────────────────────────────────────────────
HIGHLIGHT_SPRINT_CHANGE = f" style='background:{COLOR_ROW_HIGHLIGHT};'"
HIGHLIGHT_WEEK_CHANGE   = f" style='background-color:{COLOR_WEEK_CHANGE_BG}; border-left:4px solid {COLOR_WEEK_CHANGE_BORDER};'"

# ── Empty state ──────────────────────────────────────────────────────────────
def empty_section(message: str) -> str:
    return f"<p style='color:{COLOR_EMPTY_TEXT};'><em>{message}</em></p>"

# ── Release cell ─────────────────────────────────────────────────────────────
def release_link(url: str, name: str, release_id: str) -> str:
    return f"<a href='{url}' target='_blank'>{name} ({release_id})</a>"

# ── Work item URL ─────────────────────────────────────────────────────────────
def work_item_url(azure_org: str, azure_project: str, work_item_id: int | str) -> str:
    return f"https://dev.azure.com/{azure_org}/{azure_project}/_workitems/edit/{work_item_id}"

# ── Comments section ──────────────────────────────────────────────────────────
COMMENTS_NO_RESULTS = "<p><em>No comments in current iteration.</em></p></div>"
COMMENTS_HEADERS    = ["ID", "Comment", "Author", "Date"]

def comment_row(url: str, wid: int | str, text: str, author: str, date: str) -> str:
    return (
        "<tr>"
        f"<td><a href='{url}' target='_blank'>{wid}</a></td>"
        f"<td>{text}</td>"
        f"<td>{author}</td>"
        f"<td>{date}</td>"
        "</tr>"
    )

