from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from models.appointment import Appointment
from routes import appointments, users
from pydantic import BaseModel

from routes.appointments import AppointmentCreate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pode deixar "*" por enquanto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# cria as tabelas no banco
Base.metadata.create_all(bind=engine)

app.include_router(appointments.router)
app.include_router(users.router)