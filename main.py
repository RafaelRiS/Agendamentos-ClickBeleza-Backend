from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import appointments, users

app = FastAPI()

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://agendamentos-click-beleza-frontend-5ofhcy4xc-rafaelris-projects.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(appointments.router)
app.include_router(users.router)
