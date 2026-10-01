import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

mongo_url = os.getenv("MONGODB_URI")

print("MONGODB_URI encontrada:", bool(mongo_url))

if not mongo_url:
    raise RuntimeError("MONGODB_URI não encontrada no .env")

client = MongoClient(
    mongo_url,
    serverSelectionTimeoutMS=10000,
)

try:
    result = client.admin.command("ping")
    print("MongoDB respondeu:")
    print(result)

except Exception as e:
    print("ERRO AO CONECTAR AO MONGODB:")
    print(type(e).__name__)
    print(e)

finally:
    client.close()
