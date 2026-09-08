import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URL = os.getenv("MONGODB_URI")

client = MongoClient(MONGO_URL)

db = client["click_beleza"]

appointments_collection = db["agendamentos"]
users_collection = db["users"]
