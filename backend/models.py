from typing import List, Optional
from pydantic import BaseModel


class ActionItem(BaseModel):
    owner: str
    task: str
    due_date: str


class MeetingDetail(BaseModel):
    id: int
    filename: str
    status: str
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_decisions: List[str] = []
    action_items: List[ActionItem] = []
    error: Optional[str] = None
    created_at: str
    updated_at: str


class MeetingListItem(BaseModel):
    id: int
    filename: str
    status: str
    created_at: str
    updated_at: str
