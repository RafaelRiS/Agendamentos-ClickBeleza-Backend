from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import appointments, users, analytics, feedback

app = FastAPI()

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://agendamentos-click-beleza-frontend-5ofhcy4xc-rafaelris-projects.vercel.app",
    "https://agendamentos-click-beleza-frontend.vercel.app",
    "https://agendamentos-click-beleza-frontend-kv84bi6gn-rafaelris-projects.vercel.app",
    "https://agendamentos-click-beleza-frontend-git-main-rafaelris-projects.vercel.app",
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
app.include_router(analytics.router)
app.include_router(feedback.router)
