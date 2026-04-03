from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from models.appointment import Appointment
from fastapi import Query
from typing import List
from fastapi import Header, HTTPException
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

class AppointmentResponse(BaseModel):
    id: int
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

ADMIN_PASSWORD = "123456"

def verify_admin(password: str = Header(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Não autorizado")

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
        client_name=data.client_name,
        client_phone=data.client_phone,
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

@router.get("/appointments", response_model=List[AppointmentResponse])
def list_appointments(

    phone: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)

    if phone:
        query = query.filter(Appointment.client_phone == phone)

    return query.all()

@router.delete("/appointments/{id}")
def delete_appointment(id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == id).first()

    if not appointment:
        return {"error": "Agendamento não encontrado"}

    db.delete(appointment)
    db.commit()

    return {"message": "Agendamento deletado"}

@router.put("/appointments/{id}")
def update_appointment(id: int, data: dict, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == id).first()

    if not appointment:
        return {"error": "Agendamento não encontrado"}

    appointment.service = data.get("service", appointment.service)

    db.commit()
    db.refresh(appointment)

    return appointment