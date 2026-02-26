import json, base64, urllib.request, urllib.parse, urllib.error
from typing import List, Dict, Any
from config import config
from datetime import datetime, timedelta
from functions.logger import appLogger
import re


def get_auth_headers(content_type="application/json"):
    auth_string = base64.b64encode(f":{config.azure_pat}".encode()).decode()
    return {
        "Content-Type": content_type,
        "Authorization": f"Basic {auth_string}"
    }


def http_request(url, method, headers, payload=None):
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"HTTPError {e.code}: {error_body}")


def parse_azure_date(date_str: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")


def parse_azure_date_end_of_day(date_str: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt + timedelta(days=1)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")


def get_query_wiql(query_id: str) -> str:
    url = config.get_base_url(config.azure_project) + f"_apis/wit/queries/{query_id}?$expand=wiql&api-version=7.0"
    headers = get_auth_headers()
    try:
        response = http_request(url, "POST", headers)
        if "wiql" not in response:
            raise RuntimeError(f"WIQL not found for {query_id}")
        return response["wiql"]
    except urllib.error.HTTPError as e:
        appLogger.error(f"HTTPError creating PBI: {str(e)}")
        raise



def run_query(query_id: str) -> List[Dict[str, Any]]:
    wiql = get_query_wiql(query_id)
    url = config.get_base_url(config.azure_project) + f"_apis/wit/wiql?api-version=7.0"
    headers = get_auth_headers()
    payload_data = {"query": wiql}
    payload = json.dumps(payload_data).encode("utf-8")
    response = http_request(url, "POST", headers, payload)
    ids = [i["id"] for i in response.get("workItems", [])]

    appLogger.info(ids)

    if not ids:
        return []
    details_url = config.get_base_url(config.azure_project) + f"_apis/wit/workitems?ids={','.join(map(str, ids))}&api-version=7.0"
    details_response = http_request(details_url, "POST", headers)
    return details_response["value"]

# TODO review maybe delete
def run_wiql(wiql_str: str) -> list[dict]:
    url = config.get_base_url(config.azure_project) + f"_apis/wit/wiql?api-version=7.0"
    headers = get_auth_headers()
    payload_data = {"query": wiql_str}
    payload = json.dumps(payload_data).encode("utf-8")

    response = http_request(url, "POST", headers, payload)
    ids = [i["id"] for i in response.get("workItems", [])]

    appLogger.info(ids)
    if not ids:
        return []
    details = config.get_base_url(config.azure_project) + f"_apis/wit/workitems?ids={','.join(map(str, ids))}&api-version=7.0"
    req2 = urllib.request.Request(details, headers=get_auth_headers())

    with urllib.request.urlopen(req2) as r2:
        items = json.loads(r2.read().decode("utf-8"))
    return items["value"]


def get_current_iteration_dates(team: str):
    team_enc = urllib.parse.quote(team)
    url = config.get_base_url(config.azure_project) + f"{team_enc}/_apis/work/teamsettings/iterations?$timeframe=current&api-version=7.0"

    headers = get_auth_headers()
    response = http_request(url, "POST", headers)

    vals = response.get("value", [])
    if not vals:
        return None, None
    attrs = vals[0]["attributes"]

    start = datetime.strptime(attrs["startDate"], "%Y-%m-%dT%H:%M:%SZ")
    end = datetime.strptime(attrs["finishDate"], "%Y-%m-%dT%H:%M:%SZ")
    return start, end


def get_all_iteration_dates(team: str):
    team_enc = urllib.parse.quote(team)
    url = config.get_base_url(config.azure_project) + f"{team_enc}/_apis/work/teamsettings/iterations?&api-version=7.0"

    headers = get_auth_headers()
    response = http_request(url, "POST", headers)

    if not response:
        return None
    return response


def get_previous_sprint(sprints):
    sprints_ordenadas = sorted(
        sprints,
        key=lambda s: datetime.fromisoformat(s['attributes']['startDate'].replace('Z', '+00:00'))
    )
    idx_current = next(
        (i for i, s in enumerate(sprints_ordenadas) if s['attributes']['timeFrame'] == 'current'),
        None
    )
    if idx_current is not None and idx_current > 0:
        return sprints_ordenadas[idx_current - 1]
    return None


def get_previous_iteration_dates(team: str):
    team_sprints = get_all_iteration_dates(team)
    if not team_sprints:
        return None, None, None
    previous_sprint = get_previous_sprint(team_sprints.get("value", []))
    if not previous_sprint:
        return None, None, None
    start = previous_sprint['attributes']['startDate']
    end = previous_sprint['attributes']['finishDate']
    path = previous_sprint['path']
    appLogger.info(f"Fetching {path} from {start} to {end}")
    return start, end, path


def get_recent_comments(work_item_ids, team):
    start, end = get_current_iteration_dates(team)
    if not (start and end):
        return []
    collected = []
    headers = get_auth_headers()
    for wid in work_item_ids:
        url = config.get_base_url(config.azure_project) + f"_apis/wit/workItems/{wid}/comments?api-version=7.1-preview.3"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 400:
                continue
            raise
        for c in data.get("comments", []):
            try:
                cdt = parse_azure_date(c['createdDate'])
            except ValueError:
                continue
            if start <= cdt <= end:
                collected.append({
                    "wid": wid,
                    "text": c.get("text", ""),
                    "author": c["createdBy"]["displayName"],
                    "created": c['createdDate']
                })
    collected.sort(key=lambda x: x["created"], reverse=True)
    return collected


def filter_work_item_types(work_item_id, target_relations_types: List[str]) -> dict | None:
    relations = get_work_item_relations(work_item_id)
    for rel in relations:
        if rel["type"] in target_relations_types:
            return {"id": rel["id"], "name": rel["type"], "url": rel["url"], "title": rel["title"]}
    return None


def get_work_item_relations(work_item_id):
    url = config.get_base_url(config.azure_project) + f"_apis/wit/workItems/{work_item_id}/?api-version=7.0&$expand=relations"
    headers = get_auth_headers()
    response = http_request(url, "POST", headers)
    relations_list = []

    for rel in response.get("relations", []):
        match = re.search(r'/workItems/(\d+)', rel["url"])
        if match:
            rel_id = match.group(1)
            rel_url_api = config.get_base_url(config.azure_project) + f"_apis/wit/workitems/{rel_id}?api-version=7.0"
            rel_req = urllib.request.Request(rel_url_api, headers=headers)
            try:
                with urllib.request.urlopen(rel_req) as r2:
                    rel_raw = r2.read()
                    if not rel_raw or rel_raw.strip() in (b"", b"null"):
                        continue
                    rel_data = json.loads(rel_raw.decode("utf-8"))
                    rel_type = rel_data.get("fields", {}).get("System.WorkItemType")
                    rel_url = config.get_base_url(config.azure_project) + f"_workitems/edit/{rel_id}"
                    relations_list.append({"id": rel_id, "type": rel_type, "url": rel_url, "title": rel_data.get("fields", {}).get("System.Title", "")})
            except Exception as e:
                continue
    return relations_list


def fetch_work_item_revisions(work_item_id: int) -> List[Dict[str, Any]]:
    """
    Fetches all revisions for a given work item from Azure DevOps.
    Returns a list of revision objects with field snapshots.
    """
    url = config.get_base_url(config.azure_project) + f"_apis/wit/workItems/{work_item_id}/revisions?api-version=7.0"
    headers = get_auth_headers()

    response = http_request(url, "POST", headers)
    return response.get("value", [])


def has_state_changes_last_week(work_item_id: int) -> bool:
    """Check if a work item had System.State changes in the last 7 days"""

    try:
        revisions = fetch_work_item_revisions(work_item_id)
        if not revisions or len(revisions) < 2:
            return False

        # Get date 7 days ago
        seven_days_ago = datetime.now() - timedelta(days=7)

        # Check if any revision in the last 7 days has a state change
        for i in range(1, len(revisions)):
            current_rev = revisions[i]
            previous_rev = revisions[i-1]

            # Parse revision date
            changed_date_str = current_rev.get('fields', {}).get('System.ChangedDate')
            if not changed_date_str:
                continue

            try:
                changed_date = parse_azure_date(changed_date_str)
            except:
                continue

            # Check if change was in the last 7 days
            if changed_date >= seven_days_ago:
                current_state = current_rev.get('fields', {}).get('System.State', '')
                previous_state = previous_rev.get('fields', {}).get('System.State', '')

                # If state changed, return True
                if current_state != previous_state:
                    appLogger.info(f"[WEEK_CHANGE] Work item {work_item_id}: State changed from '{previous_state}' to '{current_state}' on {changed_date_str}")
                    return True

        return False

    except Exception as e:
        appLogger.error(f"[WEEK_CHANGE] Error checking state changes for work item {work_item_id}: {str(e)}")
        return False


def get_state_change_info(work_item_id: int) -> dict:
    """Get state change information for a work item in the last 7 days"""

    try:
        revisions = fetch_work_item_revisions(str(work_item_id))
        if not revisions or len(revisions) < 2:
            return {"has_changes": False, "state_change": None}

        # Get date 7 days ago
        seven_days_ago = datetime.now() - timedelta(days=7)

        # Check if any revision in the last 7 days has a state change
        for i in range(1, len(revisions)):
            current_rev = revisions[i]
            previous_rev = revisions[i-1]

            # Parse revision date
            changed_date_str = current_rev.get('fields', {}).get('System.ChangedDate')
            if not changed_date_str:
                continue

            try:
                changed_date = parse_azure_date(changed_date_str)
            except:
                continue

            # Check if change was in the last 7 days
            if changed_date >= seven_days_ago:
                current_state = current_rev.get('fields', {}).get('System.State', '')
                previous_state = previous_rev.get('fields', {}).get('System.State', '')

                # If state changed, return the change info
                if current_state != previous_state:
                    appLogger.info(f"[WEEK_CHANGE] Work item {work_item_id}: State changed from '{previous_state}' to '{current_state}' on {changed_date_str}")
                    return {
                        "has_changes": True,
                        "state_change": f"{previous_state} → {current_state}",
                        "change_date": changed_date_str,
                        "previous_state": previous_state,
                        "current_state": current_state
                    }

        return {"has_changes": False, "state_change": None}

    except Exception as e:
        appLogger.error(f"[WEEK_CHANGE] Error checking state changes for work item {work_item_id}: {str(e)}")
        return {"has_changes": False, "state_change": None}


def get_state_changes_info(work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add state change information to all work items"""
    appLogger.info(f"[WEEK_CHANGE] Adding state change info to {len(work_items)} work items")

    for wi in work_items:
        work_item_id = wi.get('id')
        if work_item_id:
            state_info = get_state_change_info(work_item_id)
            wi['week_state_change'] = state_info

    appLogger.info(f"[WEEK_CHANGE] Completed adding state change information")
    return work_items


#### SYNC FUNCTIONS


"""
Add external update comment to work item
"""
def add_external_update_comment(work_item_id, external_update_content, target_project):

    # Azure DevOps API endpoint for adding comments
    url = config.get_base_url(target_project) + f"wit/workitems/{work_item_id}/comments?api-version=7.1-preview.3"

    # Create HTML formatted comment
    comment_text = f'''<p><strong>External update</strong></p><hr><p>{external_update_content}</p>'''

    payload_data = {"text": comment_text}
    payload = json.dumps(payload_data).encode("utf-8")
    headers = get_auth_headers()

    try:
        response = http_request(url, "POST", headers, payload)
        appLogger.info(f"Comment added to work item {work_item_id} in project {target_project}")
        return response
    except RuntimeError as e:
        appLogger.error(f"HTTPError adding comment: {str(e)}")
        raise


"""
Clear the {field} value
"""
def clear_external_update_field(work_item_id, project, field):

    url = config.get_base_url(project) + f"wit/workitems/{work_item_id}?api-version=7.0"
    fields = f"/fields/{field}"
    payload_data = [
        {"op": "remove", "path": fields}
    ]

    payload = json.dumps(payload_data).encode("utf-8")
    headers = get_auth_headers(content_type="application/json-patch+json")

    try:
        response = http_request(url, "PATCH", headers, payload)
        appLogger.info(f"Field {field} clean for work item {work_item_id}")
        return response
    except RuntimeError as e:
        appLogger.error(f"HTTPError when clearing the field: {str(e)}")
        raise


"""
Search for work item by exact title match
"""
def search_work_item_by_title(title, project):

    # Use WIQL to search for work item by title
    wiql_query = {
        "query": f"SELECT [System.Id] FROM WorkItems WHERE [System.Title] = '{title}'"
    }

    url = config.get_base_url(project) + f"_apis/wit/wiql?api-version=7.0"
    payload = json.dumps(wiql_query).encode("utf-8")
    headers = get_auth_headers()

    try:
        response = http_request(url, "POST", headers, payload)
        work_items = response.get("workItems", [])
        if work_items:
            return work_items[0]["id"]
        return None
    except urllib.error.HTTPError as e:
        print(f"HTTPError searching work item: {str(e)}")
        return None


"""
Get and print work item details for debugging
"""
def get_work_item_details(work_item_id, project):

    url = config.get_base_url(project) + f"_apis/wit/workitems/{work_item_id}?api-version=7.0"
    headers = get_auth_headers()

    try:
        response = http_request(url, "GET", headers)

        appLogger.debug("Target work item details:")
        appLogger.debug(f"  ID: {response.get('id')}")
        appLogger.debug(f"  Title: {response.get('fields', {}).get('System.Title')}")
        appLogger.debug(f"  Type: {response.get('fields', {}).get('System.WorkItemType')}")
        appLogger.debug(f"  State: {response.get('fields', {}).get('System.State')}")

    except RuntimeError as e:
        appLogger.error(f"HTTPError getting work item details: {str(e)}")
        raise


"""
Update {field} in target work item
"""
def update_work_item(project, work_item_id, status, field):

    url = config.get_base_url(project) + f"_apis/wit/workitems/{work_item_id}?api-version=7.0"
    fields = f"/fields/{field}"
    payload_data = [
        {"op": "add", "path": fields, "value": status}
    ]

    payload = json.dumps(payload_data).encode("utf-8")
    headers = get_auth_headers(content_type="application/json-patch+json")

    try:
        result = http_request(url, "PATCH", headers, payload)
        appLogger.info(f"Work item updated: {work_item_id}")
        appLogger.debug(result)
        return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"HTTPError updating target date: {e.code}, {error_body}")
        raise


"""
Create a Product Backlog Item in Azure DevOps
"""
def create_pbi_in_azure(title, description=""):

    # Azure DevOps API endpoint for creating a PBI
    url = config.get_base_url() + f"_apis/wit/workitems/$Product%20Backlog%20Item?api-version=7.0"

    payload_data = [
        {"op": "add", "path": "/fields/System.Title", "value": title}
    ]

    if description:
        payload_data.append({
            "op": "add",
            "path": "/fields/System.Description",
            "value": description
        })

    payload = json.dumps(payload_data).encode("utf-8")
    headers = get_auth_headers(content_type="application/json-patch+json")

    try:
        result = http_request(url, "POST", headers, payload)
        appLogger.info(result)
        return result
    except urllib.error.HTTPError as e:
        appLogger.error(f"HTTPError creating PBI: {str(e)}")
        raise