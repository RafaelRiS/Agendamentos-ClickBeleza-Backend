from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from database import appointments_collection
from typing import List
from bson import ObjectId

router = APIRouter()


class AppointmentCreate(BaseModel):
    client_name: str
    client_phone: str
    service: str
    barber: str
    date: str
    time: str
    duration: int


class AppointmentResponse(BaseModel):
    id: str
    client_name: str
    client_phone: str
    service: str
    barber: str
    date: str
    time: str
    duration: int


def to_minutes(time_str: str):
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


ADMIN_PASSWORD = "123456"


def verify_admin(password: str = Header(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=403,
            detail="Não autorizado"
        )


def appointment_to_response(appointment):
    return {
        "id": str(appointment["_id"]),
        "client_name": appointment["client_name"],
        "client_phone": appointment["client_phone"],
        "service": appointment["service"],
        "barber": appointment["barber"],
        "date": appointment["date"],
        "time": appointment["time"],
        "duration": appointment["duration"],
    }


@router.post("/appointments")
def create_appointment(data: AppointmentCreate):

    new_start = to_minutes(data.time)
    new_end = new_start + data.duration

    appointments = appointments_collection.find({
        "date": data.date,
        "barber": data.barber
    })

    for appt in appointments:

        existing_start = to_minutes(appt["time"])
        existing_end = existing_start + appt["duration"]

        if new_start < existing_end and new_end > existing_start:
            return {
                "error": "Horário já ocupado"
            }

    appointment = {
        "client_name": data.client_name,
        "client_phone": data.client_phone,
        "service": data.service,
        "barber": data.barber,
        "date": data.date,
        "time": data.time,
        "duration": data.duration,
    }

    result = appointments_collection.insert_one(appointment)

    appointment["_id"] = result.inserted_id

    return appointment_to_response(appointment)


@router.get(
    "/appointments",
    response_model=List[AppointmentResponse]
)
def list_appointments(phone: str = None):

    query = {}

    if phone:
        query["client_phone"] = phone

    appointments = appointments_collection.find(query)

    return [
        appointment_to_response(appt)
        for appt in appointments
    ]


@router.delete("/appointments/{id}")
def delete_appointment(id: str):

    if not ObjectId.is_valid(id):
        return {
            "error": "ID inválido"
        }

    result = appointments_collection.delete_one({
        "_id": ObjectId(id)
    })

    if result.deleted_count == 0:
        return {
            "error": "Agendamento não encontrado"
        }

    return {
        "message": "Agendamento deletado"
    }


@router.put("/appointments/{id}")
def update_appointment(
    id: str,
    data: dict
):

    if not ObjectId.is_valid(id):
        return {
            "error": "ID inválido"
        }

    appointment = appointments_collection.find_one({
        "_id": ObjectId(id)
    })

    if not appointment:
        return {
            "error": "Agendamento não encontrado"
        }

    update_data = {}

    if "service" in data:
        update_data["service"] = data["service"]

    if update_data:
        appointments_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )

    updated = appointments_collection.find_one({
        "_id": ObjectId(id)
    })

    return appointment_to_response(updated)
