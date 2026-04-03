from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models.appointment import Appointment
from fastapi import Query
from typing import List
from datetime import datetime, timedelta
import os

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AppointmentCreate(BaseModel):
    client_name: str
    client_phone: str
    service: str
    barber: str
    date: str
    time: str
    duration: int

    class Config:
        from_attributes = True

def to_minutes(time_str: str):
    h, m = map(int, time_str.split(":"))
    return h * 60 + m

@router.post("/appointments")
def create_appointment(data: AppointmentCreate, db: Session = Depends(get_db)):
    # 🚫 Verifica se já existe agendamento no mesmo horário
    existing = db.query(Appointment).filter(
        Appointment.date == data.date,
        Appointment.time == data.time,
        Appointment.barber == data.barber
    ).first()

    duration: int = data.duration  # você pode melhorar isso depois

    new_start = to_minutes(data.time)
    new_end = new_start + duration

    appointments = db.query(Appointment).filter(
        Appointment.date == data.date,
        Appointment.barber == data.barber
    ).all()

    for appt in appointments:
        existing_start = to_minutes(appt.time)
        existing_end = existing_start + appt.duration  # ou salvar duration no banco

        # 🔥 REGRA DE CONFLITO
        if new_start < existing_end and new_end > existing_start:
            return {"error": "Horário já ocupado"}

    # ✅ Se não existir, salva
    appointment = Appointment(
        client_name=data.name,
        client_phone=data.phone,
        service=data.service,
        barber=data.barber,
        date=data.date,
        time=data.time,
        duration=data.duration,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return appointment

@router.get("/appointments", response_model=List[AppointmentCreate])
def list_appointments(
    phone: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)

    if phone:
        query = query.filter(Appointment.client_phone == phone)

    return query.all()
