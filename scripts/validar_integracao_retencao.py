
import os
from pathlib import Path
from datetime import date, datetime

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.getenv("MONGODB_URI")
PHONE = "TESTE26000001"
API_URL = f"http://127.0.0.1:8000/analytics/retention/{PHONE}"


def main():
    if not MONGO_URL:
        raise RuntimeError("MONGODB_URI não configurada.")

    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=10000)

    try:
        db = client["click_beleza"]
        appointments_collection = db["agendamentos"]
        feedback_collection = db["feedback"]

        today = date.today()

        # 1. Consulta direta ao banco.
        appointments = list(
            appointments_collection.find({
                "client_phone": PHONE,
                "date": {"$lt": today.isoformat()},
            }).sort([
                ("date", 1),
                ("time", 1),
            ])
        )

        print("\n=== CONSULTA AO MONGODB ===")
        print(f"Cliente: {PHONE}")
        print(f"Agendamentos passados: {len(appointments)}")

        if not appointments:
            print("Nenhum agendamento passado encontrado.")
            return

        last = appointments[-1]
        last_date = date.fromisoformat(last["date"])
        days_since = (today - last_date).days

        appointment_ids = [str(a["_id"]) for a in appointments]

        feedback_count = feedback_collection.count_documents({
            "appointment_id": {"$in": appointment_ids},
            "created_at": {
                "$lt": datetime.combine(
                    today, datetime.min.time()
                )
            },
        })

        print(f"Último serviço: {last.get('service')}")
        print(f"Última data: {last_date}")
        print(f"Dias desde a última data: {days_since}")
        print(f"Feedbacks encontrados: {feedback_count}")

        # 2. Consulta à API.
        print("\n=== RESPOSTA DA API ===")

        response = requests.get(API_URL, timeout=15)
        print(f"HTTP: {response.status_code}")

        if response.status_code != 200:
            print(response.text)
            raise RuntimeError("A API não retornou HTTP 200.")

        result = response.json()
        print(result)

        # 3. Verificações automáticas.
        assert result["previous_appointments"] == len(appointments), (
            "Quantidade de agendamentos diferente do MongoDB."
        )
        assert result["days_since_last_appointment"] == days_since, (
            "Dias desde a última visita não correspondem ao banco."
        )
        assert result["last_service"] == last.get("service"), (
            "Último serviço diferente do banco."
        )
        assert result["feedback_count"] == feedback_count, (
            "Quantidade de feedbacks diferente do banco."
        )

        probability = result["risk_probability"]
        assert 0 <= probability <= 1, (
            "Probabilidade fora do intervalo de 0 a 1."
        )
        assert abs(
            result["risk_percentage"] - probability * 100
        ) < 0.02, "Percentual incompatível com a probabilidade."

        print("\nPASSOU: consultas e valores conferidos.")
        print("PASSOU: probabilidade dentro do intervalo válido.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
