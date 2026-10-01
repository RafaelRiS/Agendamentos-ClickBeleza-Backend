from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from database import analytics_collection

router = APIRouter()


class AnalyticsEvent(BaseModel):
    type: str
    page: str
    screen: Optional[str] = None

    x: Optional[float] = None
    y: Optional[float] = None

    viewportWidth: Optional[int] = None
    viewportHeight: Optional[int] = None


class AnalyticsBatch(BaseModel):
    events: List[AnalyticsEvent]


@router.post("/analytics/events")
def create_analytics_events(data: AnalyticsBatch):

    documents = []

    for event in data.events:

        documents.append({
            "type": event.type,
            "page": event.page,
            "screen": event.screen,
            "x": event.x,
            "y": event.y,
            "viewportWidth": event.viewportWidth,
            "viewportHeight": event.viewportHeight,
            "created_at": datetime.now(timezone.utc)
        })

    if documents:
        analytics_collection.insert_many(documents)

    return {
        "success": True,
        "count": len(documents)
    }

@router.get("/analytics/events")
def get_analytics_events(
    page: Optional[str] = None,
    screen: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 5000
):

    query = {}

    if page:
        query["page"] = page

    if screen:
        query["screen"] = screen

    if event_type:
        query["type"] = event_type

    events = analytics_collection.find(
        query,
        {
            "_id": 0,
            "type": 1,
            "page": 1,
            "screen": 1,
            "x": 1,
            "y": 1,
            "viewportWidth": 1,
            "viewportHeight": 1,
            "created_at": 1
        }
    ).sort(
        "created_at",
        -1
    ).limit(limit)

    return list(events)

@router.get("/heatmap")
def get_heatmap(
    page: str = "/",
    event_type: str = "mousemove"
):
    pipeline = [
        {
            "$match": {
                "page": page,
                "type": event_type,
                "x": {
                    "$ne": None
                },
                "y": {
                    "$ne": None
                },
                "viewportWidth": {
                    "$gt": 0
                },
                "viewportHeight": {
                    "$gt": 0
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "xNormalized": {
                    "$divide": [
                        "$x",
                        "$viewportWidth"
                    ]
                },
                "yNormalized": {
                    "$divide": [
                        "$y",
                        "$viewportHeight"
                    ]
                }
            }
        },
        {
            "$project": {
                "x": {
                    "$round": [
                        "$xNormalized",
                        2
                    ]
                },
                "y": {
                    "$round": [
                        "$yNormalized",
                        2
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "x": "$x",
                    "y": "$y"
                },
                "value": {
                    "$sum": 1
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "x": "$_id.x",
                "y": "$_id.y",
                "value": 1
            }
        },
        {
            "$sort": {
                "value": -1
            }
        }
    ]

    return list(
        analytics_collection.aggregate(pipeline)
    )


