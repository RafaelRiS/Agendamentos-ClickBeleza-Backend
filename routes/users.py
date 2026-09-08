from fastapi import APIRouter, HTTPException
from database import users_collection
from models.user import UserCreate
from datetime import datetime


router = APIRouter()


@router.post("/users")
def create_user(data: UserCreate):

    # Verifica se o email já existe
    existing_user = users_collection.find_one({
        "email": data.email
    })

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado"
        )

    # Cria o usuário
    user = {
        "name": data.name,
        "email": data.email,
        "password": data.password,
        "role": data.role,
        "created_at": datetime.utcnow()
    }

    # Salva no MongoDB
    result = users_collection.insert_one(user)

    return {
        "id": str(result.inserted_id),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"]
    }


@router.get("/users")
def get_users():

    users = users_collection.find()

    return [
        {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "client"),
            "created_at": user.get("created_at")
        }
        for user in users
    ]