
from datetime import date, datetime
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException

from database import appointments_collection, feedback_collection

router = APIRouter(prefix="/analytics", tags=["Analytics - Retenção"])

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = ROOT_DIR / "models" / "modelo_retencao.joblib"

if not MODEL_FILE.exists():
    raise RuntimeError(f"Modelo não encontrado: {MODEL_FILE}")

artifact = joblib.load(MODEL_FILE)
model = artifact["model"]
FEATURES = artifact["features"]


def get_client_analysis(phone: str, today: date):
    appointments = list(
        appointments_collection.find({
            "client_phone": phone,
            "date": {"$lt": today.isoformat()},
        }).sort([("date", 1), ("time", 1)])
    )

    if not appointments:
        return None

    last_appointment = appointments[-1]
    last_date = date.fromisoformat(last_appointment["date"])

    appointment_ids = [str(a["_id"]) for a in appointments]

    feedbacks = list(
        feedback_collection.find({
            "appointment_id": {"$in": appointment_ids},
            "created_at": {
                "$lt": datetime.combine(
                    today, datetime.min.time()
                )
            },
        })
    )

    ease_values = [
        f["ease_rating"]
        for f in feedbacks
        if isinstance(f.get("ease_rating"), (int, float))
    ]
    rating_values = [
        f["rating"]
        for f in feedbacks
        if isinstance(f.get("rating"), (int, float))
    ]

    features = {
        "previous_appointments": len(appointments),
        "days_since_previous": (today - last_date).days,
        "previous_service": last_appointment.get("service", "nenhum"),
        "ease_rating_mean": (
            sum(ease_values) / len(ease_values)
            if ease_values else None
        ),
        "rating_mean": (
            sum(rating_values) / len(rating_values)
            if rating_values else None
        ),
    }

    X = pd.DataFrame([features], columns=FEATURES)
    probabilities = model.predict_proba(X)[0]
    classes = list(model.classes_)
    risk = float(probabilities[classes.index(1)])

    return {
        "client_phone": phone,
        "analysis_date": today.isoformat(),
        "horizon_days": 60,
        "risk_probability": round(risk, 4),
        "risk_percentage": round(risk * 100, 2),
        "classification": (
            "risco de não retorno"
            if risk >= 0.5
            else "retorno mais provável"
        ),
        "previous_appointments": len(appointments),
        "days_since_last_appointment": (today - last_date).days,
        "last_service": last_appointment.get("service"),
        "feedback_count": len(feedbacks),
        "rating_mean": (
            round(sum(rating_values) / len(rating_values), 2)
            if rating_values else None
        ),
        "ease_rating_mean": (
            round(sum(ease_values) / len(ease_values), 2)
            if ease_values else None
        ),
        "model_status": "experimental - treinado com dados fictícios",
    }


@router.get("/retention/summary")
def retention_summary():
    today = date.today()
    phones = appointments_collection.distinct(
        "client_phone",
        {"date": {"$lt": today.isoformat()}}
    )

    clients = [
        result
        for phone in phones
        if phone
        if (result := get_client_analysis(phone, today)) is not None
    ]

    ratings = [
        c["rating_mean"] for c in clients
        if c["rating_mean"] is not None
    ]
    ease_ratings = [
        c["ease_rating_mean"] for c in clients
        if c["ease_rating_mean"] is not None
    ]

    high_risk = sum(c["risk_probability"] >= 0.5 for c in clients)

    return {
        "total_clients": len(clients),
        "high_risk_clients": high_risk,
        "lower_risk_clients": len(clients) - high_risk,
        "average_rating": (
            round(sum(ratings) / len(ratings), 2)
            if ratings else None
        ),
        "average_ease_rating": (
            round(sum(ease_ratings) / len(ease_ratings), 2)
            if ease_ratings else None
        ),
        "model_status": "experimental - treinado com dados fictícios",
    }


@router.get("/retention/clients")
def retention_clients():
    today = date.today()
    phones = appointments_collection.distinct(
        "client_phone",
        {"date": {"$lt": today.isoformat()}}
    )

    clients = [
        result
        for phone in phones
        if phone
        if (result := get_client_analysis(phone, today)) is not None
    ]

    return sorted(
        clients,
        key=lambda client: client["risk_probability"],
        reverse=True,
    )


@router.get("/retention/{phone}")
def analyze_retention(phone: str):
    result = get_client_analysis(phone, date.today())

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Nenhum agendamento passado encontrado para este cliente.",
        )

    return result
