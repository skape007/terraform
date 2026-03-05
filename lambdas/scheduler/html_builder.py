import re
from typing import Any
from models import JobItem, EmailConfig, QueryDef
from config import config
from datetime import datetime
from wiql_builder import build_sprint_wiql
from functions.logger import appLogger
from functions.azure_client import run_query, get_recent_comments, \
    filter_work_item_types, fetch_work_item_revisions, get_previous_iteration_dates, \
    parse_azure_date, run_wiql, parse_azure_date_end_of_day, get_state_changes_info
from html_templates import (
    email_header, EMAIL_FEEDBACK, EMAIL_FOOTER,
    section_header, TABLE_OPEN, TABLE_CLOSE,
    table_header_row, table_row,
    cell, cell_center, cell_empty, cell_empty_center, cell_link,
    cell_changes, cell_state_with_change,
    HIGHLIGHT_SPRINT_CHANGE, HIGHLIGHT_WEEK_CHANGE,
    empty_section, release_link, work_item_url,
    COMMENTS_NO_RESULTS, COMMENTS_HEADERS, comment_row,
    COLOR_DELAYED, COLOR_ANTICIPATED, COLOR_ADDED, COLOR_PENDING,
)

OPTIONAL_FIELD_MAP = {
    "TYPE": ("Type", "System.WorkItemType"),
    "AREAPATH": ("Area", "System.AreaPath"),
    "TAGS": ("Tags", "System.Tags"),
    "EFFORT": ("Effort", "Microsoft.VSTS.Scheduling.Effort"),
    "PI": ("PI", "System.IterationPath"),
    "TARGET_SPRINT": ("Target Sprint", "Custom.TargetSprint"),
    "TARGET_DATE": ("Target date", "Microsoft.VSTS.Scheduling.TargetDate"),
    "ITERATION": ("Iteration", "System.IterationPath"),
    "JIRA_ID": ("JIRA ID", "Custom.JIRAID")
}

SPRINT_CHANGE_HEADERS = ["Iteration", "Release", "Estimation Effort", "Final Effort", "Changes", "Initial Sprint", "Final Sprint"]


def __normalize_query_columns(columns: list[str]) -> list[str]:
    return [c.strip().upper() for c in columns if c.strip()]


def build_email_html(item: JobItem,
                     mode_prefix: str | None = None) -> str:
    if isinstance(item.email_config, dict):
        item.email_config = EmailConfig.from_dict(item.email_config)  # type: ignore

    ec = item.email_config
    subject = ec.email_title
    intro_title = ec.intro_title or "Hello Team"
    intro_body = ec.intro_body or "Details below."
    subj_display = f"{mode_prefix} {subject}".strip() if mode_prefix else subject
    html = email_header(subj_display, intro_title, intro_body)

    all_ids = []

    for q in ec.queries:
        opt_cols = []
        if hasattr(q, "columns") and getattr(q, "columns", None):
            opt_cols = __normalize_query_columns(getattr(q, "columns", []))
        opt_cols_valid = [c for c in opt_cols if c in OPTIONAL_FIELD_MAP]
        show_release = "RELEASE" in opt_cols or getattr(q, "show_release_column", False)

        witems = run_query(q.id)

        if getattr(q, "track_week_changes", False):
            appLogger.info(f"[WEEK_CHANGES] Adding state change information for query '{q.title}'")
            witems = get_state_changes_info(witems)

        sprint_changes_rows = None
        if show_release:
            sprint_start, sprint_end, sprint_path = get_previous_iteration_dates(ec.team or "Dev Team")
            last_sprint_wiql = build_sprint_wiql(sprint_start, sprint_end)
            last_sprint_witems = run_wiql(last_sprint_wiql)
            sprint_changes_rows = __get_sprint_changes_rows(sprint_path, sprint_start, sprint_end, last_sprint_witems)

        html += __render_items_table(
            witems=witems,
            title=q.title,
            desc=q.description or "Items",
            empty_desc=q.empty_description or "No items.",
            optional_cols=opt_cols_valid,
            show_release_column=show_release,
            sprint_changes_rows=sprint_changes_rows
        )
        all_ids.extend([w["id"] for w in witems])

    if ec.comments:
        html += __render_comments_section(all_ids, ec.team or "Dev Team")
    if ec.feedback:
        html += EMAIL_FEEDBACK
    html += EMAIL_FOOTER
    return html


def __filter_revs_in_sprint(revs: list[dict],
                            sprint_path: str,
                            sprint_start: datetime,
                            sprint_end: datetime) -> list[dict]:
    filtered = []
    for rev in revs:
        changed = rev['fields'].get('System.ChangedDate')
        if changed:
            changed_dt = parse_azure_date(changed)
            if sprint_start <= changed_dt <= sprint_end:
                filtered.append(rev)
    return filtered


def __get_sprint_changes_rows(sprint_path: str,
                              sprint_start: str,
                              sprint_end: str,
                              work_items: list[dict]) -> list[tuple]:
    sprint_start = parse_azure_date(sprint_start)
    sprint_end = parse_azure_date_end_of_day(sprint_end)
    rows = []
    for wi in work_items:
        wid = wi['id']
        title = wi['fields'].get('System.Title', '')
        revs = fetch_work_item_revisions(wid)
        filtered = __filter_revs_in_sprint(revs, sprint_path, sprint_start, sprint_end)
        if filtered:
            initial_effort = filtered[0]['fields'].get('Microsoft.VSTS.Scheduling.Effort')
            final_rev = revs[-1]
            final_effort = final_rev['fields'].get('Microsoft.VSTS.Scheduling.Effort')
            moved = final_rev['fields'].get('System.IterationPath') != sprint_path
            initial_sprint = filtered[0]['fields'].get('System.IterationPath')
            final_sprint = final_rev['fields'].get('System.IterationPath')
            if initial_sprint == sprint_path or final_sprint == sprint_path:
                rows.append((wid, title, initial_effort, final_effort, "Yes" if moved else "No", initial_sprint, final_sprint))
    return rows


def __render_items_table(
    witems: list[dict],
    title: str,
    desc: str,
    empty_desc: str,
    optional_cols: list[str],
    show_release_column: bool = False,
    sprint_changes_rows: list[Any] | None = None,
    current_sprint: str | None = None
) -> str:
    base_headers = ["ID", "Title", "State"]
    opt_headers = [OPTIONAL_FIELD_MAP[c][0] for c in optional_cols]
    if show_release_column:
        base_headers += SPRINT_CHANGE_HEADERS

    h = section_header(title)
    h += f"<p>{desc}</p>"

    if show_release_column and sprint_changes_rows:
        witem_map = {str(it["id"]): it for it in witems}
        sprint_map = {str(r[0]): r for r in sprint_changes_rows}
        all_ids = sorted(set(witem_map.keys()) | set(sprint_map.keys()), key=int)
        merged_items = [(witem_map.get(wid), sprint_map.get(wid)) for wid in all_ids]
    else:
        merged_items = [(it, None) for it in sorted(witems, key=lambda x: int(x["id"]))]

    if merged_items:
        h += TABLE_OPEN
        h += table_header_row(base_headers + opt_headers)
        for it, sprint_data in merged_items:
            row_cells = []
            highlight = ""
            iteration = ""

            has_week_changes = it and it.get('week_state_change', {}).get('has_changes', False)

            if it:
                f = it["fields"]
                url = work_item_url(config.azure_org, config.azure_project, it['id'])
                row_cells.append(cell_link(url, it['id']))
                row_cells.append(cell(f.get('System.Title', '')))

                current_state = f.get('System.State', '')
                if it.get('week_state_change', {}).get('has_changes', False):
                    state_change = it['week_state_change'].get('state_change', '')
                    row_cells.append(cell_state_with_change(current_state, state_change) if state_change else cell(current_state))
                else:
                    row_cells.append(cell(current_state))

                iteration = f.get('System.IterationPath', '')
                if show_release_column:
                    row_cells.append(cell(iteration))
                    row_cells.append(cell(__build_release_cell(it['id'])))

            elif sprint_data:
                url = work_item_url(config.azure_org, config.azure_project, sprint_data[0])
                row_cells.append(cell_link(url, sprint_data[0]))
                row_cells.append(cell(sprint_data[1]))
                row_cells.append(cell_empty())
                if show_release_column:
                    row_cells += [cell_empty(), cell_empty()]

            if show_release_column:
                if sprint_data:
                    initial_effort = sprint_data[2]
                    final_effort   = sprint_data[3]
                    initial_sprint = sprint_data[5]
                    final_sprint   = sprint_data[6]
                    changes = __get_changes_value(iteration, initial_sprint, final_sprint, current_sprint)
                elif it and sprint_changes_rows:
                    initial_effort = it["fields"].get("Microsoft.VSTS.Scheduling.Effort", "")
                    final_effort   = ""
                    initial_sprint = it["fields"].get("System.IterationPath", "")
                    final_sprint   = it["fields"].get("System.IterationPath", "")
                    changes = "Pending"
                else:
                    initial_effort = final_effort = initial_sprint = final_sprint = ""
                    changes = "-"

                color_map = {
                    "Delayed": COLOR_DELAYED,
                    "Anticipated": COLOR_ANTICIPATED,
                    "Added": COLOR_ADDED,
                    "Pending": COLOR_PENDING,
                }
                color = color_map.get(changes, "")
                row_cells += [
                    cell(str(initial_effort)),
                    cell(str(final_effort)),
                    cell_changes(changes, color) if color else cell(changes),
                    cell(str(initial_sprint)),
                    cell(str(final_sprint)),
                ]
                if changes != "-":
                    highlight = HIGHLIGHT_SPRINT_CHANGE

            if it:
                f = it["fields"]
                for oc in optional_cols:
                    _, field_key = OPTIONAL_FIELD_MAP[oc]
                    field_value = f.get(field_key, '')

                    if field_key.startswith('Custom.'):
                        custom_key = field_key.replace('Custom.', '')
                        if 'custom' in it and custom_key in it['custom']:
                            field_value = it['custom'][custom_key]

                    if oc == "PI" and isinstance(field_value, str) and "\\" in field_value:
                        field_value = field_value.split("\\")[-1]

                    if isinstance(field_value, str) and field_value:
                        if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$', field_value):
                            try:
                                field_value = field_value.split('T')[0]
                            except Exception:
                                pass
                        if field_value.startswith('https://'):
                            field_value = f"<a href='{field_value}' target='_blank'>{field_value}</a>"

                    row_cells.append(cell_center(str(field_value)))
            else:
                row_cells += [cell_empty_center()] * len(optional_cols)

            if has_week_changes:
                highlight = HIGHLIGHT_WEEK_CHANGE

            h += table_row(row_cells, highlight)
        h += TABLE_CLOSE
    else:
        h += empty_section(empty_desc)
    return h + "</div>"


def __build_release_cell(work_item_id: int) -> str:
    release_info = filter_work_item_types(work_item_id, ['Release'])
    if release_info:
        return release_link(release_info['url'], release_info['title'], release_info['id'])
    return ""


def __render_comments_section(work_item_ids: list[int],
                              team: str) -> str:
    comments = get_recent_comments(work_item_ids, team)
    h = section_header("Recent Comments/Updates")
    if not comments:
        return h + COMMENTS_NO_RESULTS
    h += TABLE_OPEN
    h += table_header_row(COMMENTS_HEADERS)
    for c in comments:
        try:
            ds = datetime.strptime(c['created'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            ds = c['created']
        url = work_item_url(config.azure_org, config.azure_project, c['wid'])
        h += comment_row(url, c['wid'], c['text'], c['author'], ds)
    h += TABLE_CLOSE + "</div>"
    return h


def __extract_sprint_number(sprint_str: str | None) -> int | None:
    import re
    m = re.search(r'\((\d+)\)', sprint_str or "")
    return int(m.group(1)) if m else None


def __get_changes_value(iteration: str,
                        initial_sprint: str,
                        final_sprint: str,
                        current_sprint: str | None) -> str:
    if not iteration:
        iteration = ""
    appLogger.debug("iteration:" + iteration)
    if not current_sprint:
        current_sprint = ""
    appLogger.debug("current_sprint:" + current_sprint)
    if not initial_sprint:
        initial_sprint = ""
    appLogger.debug("current_sprint:" + initial_sprint)
    if not final_sprint:
        final_sprint = ""
    appLogger.debug("final_sprint:" + final_sprint)

    if not iteration or iteration.strip() == "":
        if final_sprint == current_sprint:
            return "Added"

    ini_num = __extract_sprint_number(initial_sprint)
    appLogger.debug("ini_num:" + str(ini_num))
    fin_num = __extract_sprint_number(final_sprint)
    appLogger.debug("fin_num:" + str(fin_num))
    if ini_num is not None and fin_num is not None:
        if fin_num > ini_num:
            return "Delayed"
        if ini_num > fin_num:
            return "Anticipated"

    if (initial_sprint or "").strip() == "DEP" and final_sprint and final_sprint.strip() != "DEP":
        return "Added"

    return "-"
