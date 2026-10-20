
import os
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URL = os.getenv("MONGODB_URI")
DATABASE_NAME = "click_beleza"
BATCH_ID = "retencao_ficticia_2026_v1"

HORIZON_DAYS = 60

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "retencao_treinamento.csv"


def main():
    if not MONGO_URL:
        raise RuntimeError("MONGODB_URI não configurada no .env")

    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=10000)

    try:
        client.admin.command("ping")
        db = client[DATABASE_NAME]

        appointments_collection = db["agendamentos"]
        feedback_collection = db["feedback"]

        appointments = list(
            appointments_collection.find({
                "_seed_batch": BATCH_ID
            })
        )

        if not appointments:
            raise RuntimeError(
                "Nenhum agendamento encontrado para o lote fictício."
            )

        feedbacks = list(
            feedback_collection.find({
                "_seed_batch": BATCH_ID
            })
        )

        # Mapeia feedbacks para o ID do agendamento.
        feedback_by_appointment = {}

        for feedback in feedbacks:
            feedback_by_appointment.setdefault(
                feedback["appointment_id"], []
            ).append(feedback)

        # Normaliza datas e organiza os históricos.
        for appointment in appointments:
            appointment["parsed_date"] = date.fromisoformat(
                appointment["date"]
            )

        appointments.sort(
            key=lambda item: (
                item["client_phone"],
                item["parsed_date"],
                item["time"],
            )
        )

        appointments_by_client = {}

        for appointment in appointments:
            appointments_by_client.setdefault(
                appointment["client_phone"], []
            ).append(appointment)

        rows = []

        # Cada data de análise é um ponto histórico do cliente.
        # Só geramos rótulos quando os 60 dias seguintes estão
        # integralmente dentro do período de dados disponível.
        data_cutoff = date(2026, 12, 31)

        for phone, history in appointments_by_client.items():
            for index, current in enumerate(history):
                snapshot_date = current["parsed_date"]
                horizon_end = snapshot_date + timedelta(
                    days=HORIZON_DAYS
                )

                # Não há observação completa dos 60 dias seguintes.
                if horizon_end > data_cutoff:
                    continue

                previous_appointments = [
                    item for item in history[:index]
                    if item["parsed_date"] <= snapshot_date
                ]

                # Um agendamento na mesma data não conta como
                # um retorno posterior.
                future_return = any(
                    snapshot_date < item["parsed_date"] <= horizon_end
                    for item in history[index + 1:]
                )

                days_since_previous = None

                if previous_appointments:
                    days_since_previous = (
                        snapshot_date
                        - previous_appointments[-1]["parsed_date"]
                    ).days

                prior_feedbacks = []

                for previous in previous_appointments:
                    appointment_id = str(previous["_id"])

                    for feedback in feedback_by_appointment.get(
                        appointment_id, []
                    ):
                        created_at = feedback.get("created_at")

                        if isinstance(created_at, datetime):
                            if created_at.date() <= snapshot_date:
                                prior_feedbacks.append(feedback)

                ease_values = [
                    item["ease_rating"]
                    for item in prior_feedbacks
                    if isinstance(item.get("ease_rating"), (int, float))
                ]

                rating_values = [
                    item["rating"]
                    for item in prior_feedbacks
                    if isinstance(item.get("rating"), (int, float))
                ]

                # Não utilizamos o serviço atual como atributo
                # principal, pois ele pode não representar o
                # histórico de preferência do cliente.
                rows.append({
                    "client_phone": phone,
                    "snapshot_date": snapshot_date.isoformat(),
                    "previous_appointments": len(previous_appointments),
                    "days_since_previous": days_since_previous,
                    "previous_service": (
                        previous_appointments[-1]["service"]
                        if previous_appointments else "nenhum"
                    ),
                    "ease_rating_mean": (
                        sum(ease_values) / len(ease_values)
                        if ease_values else None
                    ),
                    "rating_mean": (
                        sum(rating_values) / len(rating_values)
                        if rating_values else None
                    ),
                    "did_not_return_within_60_days": int(not future_return),
                })

        if not rows:
            raise RuntimeError(
                "Nenhuma amostra elegível. Verifique as datas "
                "e a disponibilidade dos 60 dias de acompanhamento."
            )

        df = pd.DataFrame(rows)

        # Remove identificadores diretos do arquivo de treinamento.
        # O telefone não é uma variável preditiva.
        df = df.drop(columns=["client_phone"])

        df.to_csv(OUTPUT_FILE, index=False)

        print("Dataset de retenção criado!")
        print(f"Arquivo: {OUTPUT_FILE}")
        print(f"Total de amostras: {len(df)}")
        print(
            "Não retornaram em até 60 dias:",
            int(df["did_not_return_within_60_days"].sum())
        )

        print(
            "Retornaram em até 60 dias:",
            int((df["did_not_return_within_60_days"] == 0).sum())
        )
        print("\nDistribuição do rótulo:")
        print(df["did_not_return_within_60_days"].value_counts())

        print("\nPercentual de risco na base:")
        print(
            f"{df['did_not_return_within_60_days'].mean() * 100:.1f}%"
        )

    finally:
        client.close()


if __name__ == "__main__":
    main()
