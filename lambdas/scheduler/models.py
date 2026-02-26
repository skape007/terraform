from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union


@dataclass
class QueryDef:
    title: str
    id: str
    description: Optional[str] = None
    empty_description: Optional[str] = None
    show_release_column: bool = False
    track_sprint_changes: bool = False
    track_week_changes: bool = False
    columns: Optional[List[str]] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "QueryDef":
        return QueryDef(
            title=d["title"],
            id=d["id"],
            description=d.get("description"),
            empty_description=d.get("empty_description"),
            show_release_column = bool(d.get("show_release_column", False)),
            track_sprint_changes = bool(d.get("track_sprint_changes", False)),
            track_week_changes = bool(d.get("track_week_changes", False)),
            columns=d.get("columns")
        )


@dataclass
class EmailConfig:
    recipient: Union[str, List[str]]
    email_title: str
    intro_title: Optional[str] = None
    intro_body: Optional[str] = None
    comments: bool = False
    feedback: bool = False
    team: Optional[str] = None
    queries: List[QueryDef] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EmailConfig":
        rec = d["recipient"]
        if isinstance(rec, str):
            recipients = [r.strip() for r in rec.split(",") if r.strip()]
        else:
            recipients = rec
        queries = [QueryDef.from_dict(q) for q in d.get("queries", [])]
        return EmailConfig(
            recipient=recipients,
            email_title=d["email_title"],
            intro_title=d.get("intro_title"),
            intro_body=d.get("intro_body"),
            comments=bool(d.get("comments", False)),
            feedback=bool(d.get("feedback", False)),
            team=d.get("team"),
            queries=queries
        )


@dataclass
class ScheduleDef:
    day_of_week: List[str]
    hour: int
    interval_days: int
    anchor_date: Optional[str] = None  # YYYY-MM-DD


@dataclass
class JobFile:
    group_id: str
    description: Optional[str]
    schedule: ScheduleDef
    email_config: EmailConfig
    enabled: bool = True
    version: Optional[int] = None
    demo_on_ingest: bool = False


@dataclass
class JobItem:
    id: str
    group_id: str
    day_of_week: str
    hour: int
    interval_days: int
    anchor_date: Optional[str]
    enabled: bool
    email_config: EmailConfig
    description: Optional[str]
    version: Optional[int]
    time_slot: str
    original_weekdays: List[str]
    last_run: Optional[str] = None
