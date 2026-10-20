
"""
seed_historico_feedbacks.py

Gera feedbacks SINTÉTICOS para os agendamentos históricos
já existentes no MongoDB.

Não cria agendamentos e não altera feedbacks existentes.

Execução:
    python seed_historico_feedbacks.py
    python seed_historico_feedbacks.py --apply
"""

import argparse
import os
import random
from datetime import datetime, time, timedelta, timezone

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError


SEED = 20261021

# Probabilidade de cada agendamento receber feedback.
# Ajuste para 1.0 se quiser avaliar todos os agendamentos.
PROBABILIDADE_FEEDBACK = 0.85

COMENTARIOS = {
    5: [
        "Agendamento rápido e muito fácil de realizar!",
        "O site é intuitivo e consegui agendar sem dificuldades.",
        "Consegui escolher o serviço e o horário facilmente.",
        "Processo de agendamento simples e eficiente.",
        "Gostei muito da facilidade para agendar pelo site.",
        "Todas as informações estavam claras e organizadas.",
        "Consegui concluir meu agendamento em poucos minutos.",
    ],
    4: [
        "O agendamento foi fácil, mas algumas informações poderiam ser mais claras.",
        "Gostei do site, só tive uma pequena dificuldade para encontrar o serviço.",
        "Consegui agendar sem problemas, mas o processo poderia ser mais rápido.",
        "O site é bom e fácil de usar.",
        "Foi tranquilo agendar, mas senti falta de algumas informações.",
        "A experiência foi boa, com pequenos pontos a melhorar.",
    ],
    3: [
        "Consegui realizar o agendamento, mas tive algumas dúvidas durante o processo.",
        "O site funciona, mas algumas etapas poderiam ser mais intuitivas.",
        "O processo de agendamento foi razoável.",
        "Tive um pouco de dificuldade para encontrar um horário disponível.",
        "As informações poderiam estar mais organizadas.",
        "Consegui agendar, mas precisei de um pouco mais de tempo.",
    ],
    2: [
        "Tive dificuldade para encontrar o serviço que queria agendar.",
        "O processo de agendamento não foi muito intuitivo.",
        "Algumas informações do site não estavam claras.",
        "Demorei bastante para conseguir concluir o agendamento.",
        "Tive dificuldades para selecionar um horário disponível.",
        "O site poderia facilitar mais o processo de agendamento.",
    ],
    1: [
        "Tive muita dificuldade para realizar o agendamento pelo site.",
        "Não consegui entender facilmente como concluir o agendamento.",
        "O processo foi confuso e pouco intuitivo.",
        "Tive problemas durante as etapas do agendamento.",
        "Não encontrei as informações necessárias para agendar.",
        "Foi muito difícil concluir o agendamento pelo site.",
    ],
}


def gerar_avaliacao():
    """
    Gera notas correlacionadas, mas não necessariamente iguais.
    """

    rating = random.choices(
        [1, 2, 3, 4, 5],
        weights=[3, 5, 12, 30, 50],
        k=1,
    )[0]

    # A facilidade tende a acompanhar a satisfação,
    # mas pode variar de forma independente.
    ease_rating = random.choices(
        [1, 2, 3, 4, 5],
        weights={
            1: [35, 30, 20, 10, 5],
            2: [15, 30, 30, 20, 5],
            3: [5, 15, 35, 30, 15],
            4: [3, 5, 17, 35, 40],
            5: [2, 3, 10, 25, 60],
        }[rating],
        k=1,
    )[0]

    comment = random.choice(COMENTARIOS[rating])

    return rating, ease_rating, comment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Confirma a gravação dos feedbacks.",
    )
    args = parser.parse_args()

    uri = os.getenv("MONGODB_URI")

    if not uri:
        raise RuntimeError(
            "Configure MONGODB_URI no ambiente ou no arquivo .env."
        )

    random.seed(SEED)

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)

    try:
        client.admin.command("ping")

        db = client["click_beleza"]
        appointments_collection = db["agendamentos"]
        feedback_collection = db["feedback"]

        # Localiza os agendamentos históricos.
        # Este script destina-se à massa sintética criada anteriormente.
        appointments = list(
            appointments_collection.find({
                "client_phone": {
                    "$regex": r"^\d{11}$"
                },
                "date": {
                    "$gte": "2025-01-01",
                    "$lte": "2026-10-19",
                },
            })
        )

        # IDs em string, como espera a rota POST /feedback.
        appointment_ids = [
            str(appointment["_id"])
            for appointment in appointments
        ]

        # Não duplica avaliações já existentes.
        existing_ids = set(
            feedback["appointment_id"]
            for feedback in feedback_collection.find(
                {"appointment_id": {"$in": appointment_ids}},
                {"appointment_id": 1},
            )
        )

        novos_feedbacks = []
        ignorados = 0

        for appointment in appointments:
            appointment_id = str(appointment["_id"])

            if appointment_id in existing_ids:
                ignorados += 1
                continue

            # O histórico deve ser anterior ao dia atual.
            appointment_date = datetime.strptime(
                appointment["date"], "%Y-%m-%d"
            ).date()

            if appointment_date >= datetime.now().date():
                continue

            if random.random() > PROBABILIDADE_FEEDBACK:
                continue

            rating, ease_rating, comment = gerar_avaliacao()

            # Avaliação acontece após o atendimento.
            hora = datetime.strptime(
                appointment.get("time", "12:00"), "%H:%M"
            ).time()

            inicio = datetime.combine(appointment_date, hora)
            fim_atendimento = inicio + timedelta(
                minutes=int(appointment.get("duration", 60))
            )

            atraso = timedelta(
                minutes=random.randint(5, 180),
                seconds=random.randint(0, 59),
            )

            created_at = (
                fim_atendimento + atraso
            ).replace(tzinfo=timezone.utc)

            novos_feedbacks.append({
                "appointment_id": appointment_id,
                "rating": rating,
                "ease_rating": ease_rating,
                "comment": comment,
                "created_at": created_at,
            })

        print(f"Agendamentos históricos encontrados: {len(appointments)}")
        print(f"Feedbacks já existentes: {ignorados}")
        print(f"Novos feedbacks preparados: {len(novos_feedbacks)}")

        if novos_feedbacks:
            print("\nExemplo:")
            print(novos_feedbacks[0])

        if not args.apply:
            print("\nSimulação: nenhum feedback foi inserido.")
            print("Execute com --apply para confirmar.")
            return

        if novos_feedbacks:
            result = feedback_collection.insert_many(novos_feedbacks)
            print("Banco:", db.name)
            print("Coleção:", feedback_collection.name)

            print(
                "Total de feedbacks na coleção:",
                feedback_collection.count_documents({})
            )

            print(
                "Feedbacks deste lote:",
                feedback_collection.count_documents({
                    "appointment_id": {
                        "$in": appointment_ids
                    }
                })
            )
            print(f"\nInseridos {len(result.inserted_ids)} feedbacks.")
        else:
            print("\nNenhum feedback novo para inserir.")

    except PyMongoError as erro:
        print(f"Erro no MongoDB: {erro}")
        raise

    finally:
        client.close()


if __name__ == "__main__":
    main()
