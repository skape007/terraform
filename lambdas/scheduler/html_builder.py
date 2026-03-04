from typing import List, Dict, Any
from functions.azure_client import run_query, get_recent_comments, filter_work_item_types, fetch_work_item_revisions, get_previous_iteration_dates, parse_azure_date, run_wiql, parse_azure_date_end_of_day
from models import JobItem, EmailConfig, QueryDef
from config import config
from datetime import datetime
from wiql_builder import build_sprint_wiql
from functions.logger import appLogger

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


def _normalize_query_columns(columns: List[str]) -> List[str]:
    return [c.strip().upper() for c in columns if c.strip()]


def build_sprint_changes_table(sprint_path, sprint_start, sprint_end, work_items):
    sprint_start = parse_azure_date(sprint_start)
    sprint_end = parse_azure_date(sprint_end)
    rows = []
    
    for wi in work_items:
        wid = wi['id']
        title = wi['fields'].get('System.Title', '')
        revs = fetch_work_item_revisions(wid)
        filtered = filter_revs_in_sprint(revs, sprint_path, sprint_start, sprint_end)

        if filtered:
            initial_effort = filtered[0]['fields'].get('Microsoft.VSTS.Scheduling.Effort')
            final_rev = revs[-1]
            final_effort = final_rev['fields'].get('Microsoft.VSTS.Scheduling.Effort')
            moved = final_rev['fields'].get('System.IterationPath') != sprint_path
            initial_sprint = filtered[0]['fields'].get('System.IterationPath')
            final_sprint = final_rev['fields'].get('System.IterationPath')
            if initial_sprint == sprint_path or final_sprint == sprint_path:
                rows.append((wid, title, initial_effort, final_effort, "Yes" if moved else "No", initial_sprint, final_sprint))

    h = "<div><h2 style='color:#0057b8;'>Sprint Change Tracker</h2>"
    h += ("<table border='1' cellspacing='0' cellpadding='4' style='width:100%;border-collapse:collapse;background:#f9f9f9;'>"
          "<tr style='background:#eaeaea;'>"
          "<th>ID</th><th>Title</th><th>Estimation Effort</th><th>Final Effort</th><th>Moved?</th><th>Initial Sprint</th><th>Final Sprint</th></tr>")
    for r in rows:
        url = f"https://dev.azure.com/{config.azure_org}/{config.azure_project}/_workitems/edit/{r[0]}"
        highlight = ""
        if r[2] != r[3] or r[5] != r[6]:
            highlight = " style='background:#ffeeba;'"  # amarelo claro
        h += ("<tr" + highlight + ">"
            f"<td><a href='{url}' target='_blank'>{r[0]}</a></td>"
            f"<td>{r[1]}</td>"
            f"<td>{r[2]}</td>"
            f"<td>{r[3]}</td>"
            f"<td>{r[4]}</td>"
            f"<td>{r[5]}</td>"
            f"<td>{r[6]}</td>"
            "</tr>")
    h += "</table></div>"
    return h


def build_email_html(item: JobItem, mode_prefix: str | None = None) -> str:
    if isinstance(item.email_config, dict):
        item.email_config = EmailConfig.from_dict(item.email_config)  # type: ignore

    ec = item.email_config
    subject = ec.email_title
    intro_title = ec.intro_title or "Hello Team"
    intro_body = ec.intro_body or "Details below."
    subj_display = f"{mode_prefix} {subject}".strip() if mode_prefix else subject
    html = f"<h1 style='color:#0057b8;'>{subj_display}</h1><p><strong>{intro_title}</strong><br><br>{intro_body}</p>"

    all_ids = []

    for q in ec.queries:
        opt_cols = []
        if hasattr(q, "columns") and getattr(q, "columns", None):
            opt_cols = _normalize_query_columns(getattr(q, "columns", []))
        opt_cols_valid = [c for c in opt_cols if c in OPTIONAL_FIELD_MAP]
        show_release = "RELEASE" in opt_cols or getattr(q, "show_release_column", False)

        witems = run_query(q.id)

        # Add state change information if track_week_changes is enabled
        if getattr(q, "track_week_changes", False):
            appLogger.info(f"[WEEK_CHANGES] Adding state change information for query '{q.title}'")
            from azure_client import get_state_changes_info
            witems = get_state_changes_info(witems)

        sprint_changes_rows = None
        if show_release:
            sprint_start, sprint_end, sprint_path = get_previous_iteration_dates(ec.team or "Dev Team")
            last_sprint_wiql = build_sprint_wiql(sprint_start, sprint_end)
            last_sprint_witems = run_wiql(last_sprint_wiql)
            sprint_changes_rows = get_sprint_changes_rows(sprint_path, sprint_start, sprint_end, last_sprint_witems)

        html += _render_items_table(
            witems=witems,
            title=q.title,
            desc=q.description or "Items",
            empty_desc=q.empty_description or "No items.",
            optional_cols=opt_cols_valid,
            show_release_column=show_release,
            sprint_changes_rows=sprint_changes_rows
        )
        all_ids.extend([w["id"] for w in witems])

        #Create table only with the updates 
        #html = create_sprint_review_table(ec, html, q)

    if ec.comments:
        html += _render_comments_section(all_ids, ec.team or "Dev Team")
    if ec.feedback:
        html += "<p><em>Feedback welcome.</em></p>"
    html += "<hr><small>Automated email.</small>"
    return html


def create_sprint_review_table(ec: EmailConfig, html: str | Any, q: QueryDef) -> str | Any:
    if getattr(q, "track_sprint_changes", False):
        # Set sprint_path from query or job config, fallback to iteration of first item
        sprint_start, sprint_end, sprint_path = get_previous_iteration_dates(ec.team or "Dev Team")
        appLogger.info(f"Fetching sprint changes for {sprint_path} from {sprint_start} to {sprint_end}")
        last_sprint_wiql = build_sprint_wiql(sprint_start, sprint_end)
        last_sprint_witems = run_wiql(last_sprint_wiql)
        html += build_sprint_changes_table(sprint_path, sprint_start, sprint_end, last_sprint_witems)
    return html


def filter_revs_in_sprint(revs, sprint_path, sprint_start, sprint_end):
    filtered = []
    for rev in revs:
        changed = rev['fields'].get('System.ChangedDate')
        if changed:
            changed_dt = parse_azure_date(changed)
            if sprint_start <= changed_dt <= sprint_end:
                filtered.append(rev)
    return filtered


def merge_items_with_sprint_changes(witems, sprint_changes_rows):
    # Mapeia work items por ID
    witem_map = {str(it["id"]): it for it in witems}
    sprint_map = {str(r[0]): r for r in sprint_changes_rows}
    all_ids = set(witem_map.keys()) | set(sprint_map.keys())
    merged = []
    for wid in all_ids:
        it = witem_map.get(wid)
        sprint_data = sprint_map.get(wid)
        merged.append((it, sprint_data))
    return merged


def get_sprint_changes_rows(sprint_path, sprint_start, sprint_end, work_items):
    sprint_start = parse_azure_date(sprint_start)
    sprint_end = parse_azure_date_end_of_day(sprint_end)
    rows = []
    for wi in work_items:
        wid = wi['id']
        title = wi['fields'].get('System.Title', '')
        revs = fetch_work_item_revisions(wid)
        filtered = filter_revs_in_sprint(revs, sprint_path, sprint_start, sprint_end)
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


def _render_items_table(
    witems: List[Dict[str, Any]],
    title: str,
    desc: str,
    empty_desc: str,
    optional_cols: List[str],
    show_release_column: bool = False,
    sprint_changes_rows: List[Any] = None,
    current_sprint: str = None
) -> str:
    h = f"<div><h2 style='color:#0057b8;'>{title}</h2>"
    base_headers = ["ID", "Title", "State"]
    opt_headers = [OPTIONAL_FIELD_MAP[c][0] for c in optional_cols]
    if show_release_column:
        base_headers += ["Iteration", "Release", "Estimation Effort", "Final Effort", "Changes", "Initial Sprint", "Final Sprint"]
    h += f"<p>{desc}</p>"

    # Status legend block (always in English)
    merged_items = None
    if show_release_column and sprint_changes_rows:
        witem_map = {str(it["id"]): it for it in witems}
        sprint_map = {str(r[0]): r for r in sprint_changes_rows}
        all_ids = sorted(set(witem_map.keys()) | set(sprint_map.keys()), key=int)
        merged_items = []
        for wid in all_ids:
            it = witem_map.get(wid)
            sprint_data = sprint_map.get(wid)
            merged_items.append((it, sprint_data))
    else:
        merged_items = [(it, None) for it in sorted(witems, key=lambda x: int(x["id"]))]

    if merged_items and len(merged_items) > 0:
        h += "<table border='1' cellspacing='0' cellpadding='4' style='width:100%;border-collapse:collapse;background:#f9f9f9;'>"
        h += "<tr style='background:#eaeaea;'>" + "".join(f"<th>{col}</th>" for col in base_headers + opt_headers) + "</tr>"
        for it, sprint_data in merged_items:
            row_cells = []
            highlight = ""
            iteration = ""
            initial_sprint = ""
            final_sprint = ""
            changes = "-"  # Initialize changes variable

            # Check if this work item has state changes in the last 7 days for highlighting
            has_week_changes = False
            if it and 'week_state_change' in it:
                has_week_changes = it['week_state_change'].get('has_changes', False)

            if it:
                f = it["fields"]
                url = f"https://dev.azure.com/{config.azure_org}/{config.azure_project}/_workitems/edit/{it['id']}"
                row_cells.append(f"<td><a href='{url}' target='_blank'>{it['id']}</a></td>")
                row_cells.append(f"<td>{f.get('System.Title','')}</td>")

                # Handle State column - show state changes if available
                current_state = f.get('System.State','')
                state_cell_content = current_state
                if 'week_state_change' in it and it['week_state_change'].get('has_changes', False):
                    state_change = it['week_state_change'].get('state_change', '')
                    if state_change:
                        state_cell_content = f"<b>{current_state}</b><br>({state_change})"

                row_cells.append(f"<td>{state_cell_content}</td>")
                iteration = f.get('System.IterationPath','')
                if show_release_column:
                    row_cells.append(f"<td>{iteration}</td>")
                    release_cell = _build_release_cell(it['id'])
                    row_cells.append(f"<td>{release_cell}</td>")
            elif sprint_data:
                url = f"https://dev.azure.com/{config.azure_org}/{config.azure_project}/_workitems/edit/{sprint_data[0]}"
                row_cells.append(f"<td><a href='{url}' target='_blank'>{sprint_data[0]}</a></td>")
                row_cells.append(f"<td>{sprint_data[1]}</td>")
                row_cells.append(f"<td></td>")  # Empty state cell
                if show_release_column:
                    row_cells += ["<td></td>"] * 2  # Iteration, Release empty

            if show_release_column:
                if sprint_data:
                    initial_effort = sprint_data[2]
                    final_effort = sprint_data[3]
                    initial_sprint = sprint_data[5]
                    final_sprint = sprint_data[6]
                    changes = _get_changes_value(iteration, initial_sprint, final_sprint, current_sprint)
                elif it and show_release_column and sprint_changes_rows:
                    # Item not in sprint_changes_rows: show effort from the item itself
                    initial_effort = it["fields"].get("Microsoft.VSTS.Scheduling.Effort", "")
                    final_effort = ""
                    initial_sprint = it["fields"].get("System.IterationPath", "")
                    final_sprint = it["fields"].get("System.IterationPath", "")
                    changes = "Pending"
                else:
                    initial_effort = ""
                    final_effort = ""
                    initial_sprint = ""
                    final_sprint = ""
                    changes = "-"
                color = ""
                if changes == "Delayed":
                    color = "color:#dc3545;"
                elif changes == "Anticipated":
                    color = "color:#218838;"
                elif changes == "Added":
                    color = "color:#17a2b8;"
                elif changes == "Pending":
                    color = "color:#6c757d;"
                style = f"style='text-align:center;font-weight:bold;{color}'"
                row_cells += [
                    f"<td>{initial_effort}</td>",
                    f"<td>{final_effort}</td>",
                    f"<td {style}>{changes}</td>",
                    f"<td>{initial_sprint}</td>",
                    f"<td>{final_sprint}</td>"
                ]
                if changes != "-":
                    highlight = " style='background:#ffeeba;'"
            if it:
                for oc in optional_cols:
                    _, field_key = OPTIONAL_FIELD_MAP[oc]
                    field_value = f.get(field_key,'')

                    # Check if this is a custom field that might need special handling
                    if field_key.startswith('Custom.'):
                        custom_key = field_key.replace('Custom.', '')
                        if 'custom' in it and custom_key in it['custom']:
                            field_value = it['custom'][custom_key]

                    # Special handling for PI field - remove project prefix
                    if oc == "PI" and isinstance(field_value, str) and "\\" in field_value:
                        field_value = field_value.split("\\")[-1]

                    # Format date fields if they match ISO date pattern
                    if isinstance(field_value, str) and field_value:
                        # Check if it's an ISO date string (e.g., 2025-08-04T00:00:00Z)
                        import re
                        date_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$'
                        if re.match(date_pattern, field_value):
                            try:
                                # Extract just the date part (YYYY-MM-DD)
                                field_value = field_value.split('T')[0]
                            except:
                                pass  # Keep original value if parsing fails

                    # Convert URLs starting with https:// to clickable links
                    if isinstance(field_value, str) and field_value.startswith('https://'):
                        field_value = f"<a href='{field_value}' target='_blank'>{field_value}</a>"

                    row_cells.append(f"<td style='text-align:center;'>{field_value}</td>")
            else:
                row_cells += [f"<td style='text-align:center;'></td>"] * len(optional_cols)

            # Add highlighting for rows with state changes
            if has_week_changes:
                highlight = " style='background-color:#f8f9fa; border-left:4px solid #28a745;'"

            h += f"<tr{highlight}>" + "".join(row_cells) + "</tr>"
            pass
        h += "</table>"
    else:
        h += f"<p style='color:#888;'><em>{empty_desc}</em></p>"
    return h + "</div>"


def _build_release_cell(work_item_id: int) -> str:
    release_info = filter_work_item_types(work_item_id, ['Release'])
    if release_info:
        release_link = release_info['url']
        release_name = release_info['title']
        release_id = release_info['id']
        return f"<a href='{release_link}' target='_blank'>{release_name} ({release_id})</a>"
    return ""


def _render_comments_section(work_item_ids: List[int], team: str) -> str:
    comments = get_recent_comments(work_item_ids, team)
    h = "<div><h2 style='color:#0057b8;'>Recent Comments/Updates</h2>"
    if not comments:
        return h + "<p><em>No comments in current iteration.</em></p></div>"
    h += "<table border='1' cellspacing='0' cellpadding='4' style='width:100%;border-collapse:collapse;background:#f9f9f9;'>"
    h += "<tr style='background:#eaeaea;'><th>ID</th><th>Comment</th><th>Author</th><th>Date</th></tr>"
    for c in comments:
        try:
            ds = datetime.strptime(c['created'], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            ds = c['created']
        url = f"https://dev.azure.com/{config.azure_org}/{config.azure_project}/_workitems/edit/{c['wid']}"
        h += ("<tr>"
              f"<td><a href='{url}' target='_blank'>{c['wid']}</a></td>"
              f"<td>{c['text']}</td>"
              f"<td>{c['author']}</td>"
              f"<td>{ds}</td>"
              "</tr>")
    h += "</table></div>"
    return h

def get_parent_id(work_item: Dict[str, Any]) -> str | None:
    # Tries to find parent ID from relations or System.Parent field
    relations = work_item.get("relations", [])
    for rel in relations:
        if rel.get("rel","").lower() == "system.parent":
            # Azure DevOps links use url with last part as id
            url = rel.get("url","")
            if url and url.strip().isdigit():
                return url.strip()
            # Try to extract id from URL
            if "/workItems/" in url:
                return url.split("/workItems/")[-1]
    # Fallback to System.Parent field (if present)
    parent_id = work_item.get("fields", {}).get("System.Parent")
    if parent_id and isinstance(parent_id, int):
        return str(parent_id)
    return None


def _extract_sprint_number(sprint_str):
    import re
    m = re.search(r'\((\d+)\)', sprint_str or "")
    return int(m.group(1)) if m else None


def _get_changes_value(iteration, initial_sprint, final_sprint, current_sprint):
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
    # Regra 1: Iteration vazio e Final Sprint == sprint atual
    if not iteration or iteration.strip() == "":
        if final_sprint == current_sprint:
            return "Added"
    # Regra 2: Final Sprint > Initial Sprint
    ini_num = _extract_sprint_number(initial_sprint)
    appLogger.debug("ini_num:" + str(ini_num))
    fin_num = _extract_sprint_number(final_sprint)
    appLogger.debug("fin_num:" + str(fin_num))
    if ini_num is not None and fin_num is not None:
        if fin_num > ini_num:
            return "Delayed"
        if ini_num > fin_num:
            return "Anticipated"
    # Regra 3: Initial Sprint == "DEP" e Final Sprint preenchido e diferente de "DEP"
    if (initial_sprint or "").strip() == "DEP" and final_sprint and final_sprint.strip() != "DEP":
        return "Added"
    # Caso contrário
    return "-"
