from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from database import feedback_collection, appointments_collection
from bson import ObjectId
from datetime import datetime

router = APIRouter()


class FeedbackCreate(BaseModel):
    appointment_id: str
    rating: int = Field(..., ge=1, le=5)
    ease_rating: int = Field(..., ge=1, le=5)
    comment: str = ""


@router.post("/feedback")
def create_feedback(data: FeedbackCreate):

    # Verifica se o ID do agendamento é válido
    if not ObjectId.is_valid(data.appointment_id):
        raise HTTPException(
            status_code=400,
            detail="Agendamento inválido"
        )

    # Procura o agendamento no MongoDB
    appointment = appointments_collection.find_one({
        "_id": ObjectId(data.appointment_id)
    })

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Agendamento não encontrado"
        )

    # Cria a avaliação
    feedback = {
        "appointment_id": data.appointment_id,
        "rating": data.rating,
        "ease_rating": data.ease_rating,
        "comment": data.comment,
        "created_at": datetime.utcnow(),
    }

    # Salva no MongoDB
    result = feedback_collection.insert_one(feedback)

    return {
        "success": True,
        "id": str(result.inserted_id),
        "message": "Avaliação registrada com sucesso",
    }
