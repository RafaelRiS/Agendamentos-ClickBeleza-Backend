from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import appointments, users

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# cria as tabelas no banco quando em SQLite
# Base.metadata.create_all(bind=engine)

app.include_router(appointments.router)
app.include_router(users.router)