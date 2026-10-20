
import os
import random
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

# Carrega as variáveis do .env na raiz do projeto
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URL = os.getenv("MONGODB_URI")

if not MONGO_URL:
    raise RuntimeError("MONGODB_URI não configurada no .env")

client = MongoClient(MONGO_URL)
db = client["click_beleza"]
appointments = db["agendamentos"]

# Identifica os registros criados por este script
BATCH_ID = "retencao_ficticia_2026_v1"

random.seed(2026)

N_CLIENTS = 100

NAMES = [
    "Ana Silva", "Bruno Santos", "Carla Oliveira",
    "Daniel Souza", "Eduarda Costa", "Felipe Lima",
    "Gabriela Alves", "Henrique Pereira", "Isabela Rocha",
    "João Martins", "Karen Ferreira", "Lucas Ribeiro",
    "Mariana Gomes", "Nicolas Carvalho", "Olivia Almeida",
    "Pedro Barbosa", "Rafaela Nunes", "Samuel Cardoso",
    "Tatiana Moreira", "Vinicius Teixeira",
]

SERVICES = [
    ("Volume 8D", 60),
    ("Volume Egípcio", 60),
    ("Remoção", 30),
    ("Efeito molhado marrom", 60),
    ("Fox Eyes", 60),
    ("Manutenção Volume 8D", 60),
    ("Manutenção Volume Egípcio", 60),
]

# Período completo do ano de 2026
YEAR_START = date(2026, 1, 1)
YEAR_END = date(2026, 12, 31)


def random_phone(index):
    # Prefixo fictício para evitar usar telefones reais.
    # Não são números destinados a contato.
    return f"TESTE26{index:06d}"


def random_datetime(start, end):
    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def generate_client(index):
    first = random.choice(NAMES).split()[0]
    last = random.choice([
        "Silva", "Santos", "Oliveira", "Souza",
        "Costa", "Lima", "Alves", "Pereira",
        "Rocha", "Martins",
    ])

    return {
        "client_name": f"{first} {last} Teste{index:03d}",
        "client_phone": random_phone(index),
    }


def generate_appointments_for_client(client, profile):
    # Cada perfil tem um comportamento de retorno diferente.
    if profile == "recorrente":
        first_month = random.randint(1, 4)
        months = list(range(first_month, 13))
        months = [
            month for month in months
            if random.random() < 0.82
        ]
        if not months:
            months = [first_month]

    elif profile == "ocasional":
        count = random.randint(2, 4)
        months = sorted(random.sample(range(1, 13), count))

    elif profile == "inativo":
        # Último agendamento até junho.
        months = sorted(random.sample(range(1, 7), random.randint(1, 3)))

    else:  # novo
        first_month = random.randint(7, 12)
        months = [first_month]

        # Alguns clientes novos retornam uma vez.
        if first_month < 12 and random.random() < 0.25:
            months.append(first_month + 1)

    generated = []

    for month in months:
        last_day = (
            date(2026, month + 1, 1) - timedelta(days=1)
            if month < 12
            else YEAR_END
        )

        day = random_datetime(
            date(2026, month, 1),
            last_day,
        )

        service, duration = random.choice(SERVICES)
        hour = random.choice(range(9, 18))
        minute = random.choice([0, 30])

        generated.append({
            **client,
            "service": service,
            "barber": "Natasha Sabrine",
            "date": day.isoformat(),
            "time": f"{hour:02d}:{minute:02d}",
            "duration": duration,
            "_seed_batch": BATCH_ID,
            "_seed_profile": profile,
        })

    return generated


def main():
    # Evita duplicar este lote em execuções posteriores.
    existing = appointments.count_documents({
        "_seed_batch": BATCH_ID
    })

    if existing:
        print(
            f"O lote já existe: {existing} agendamentos. "
            "Nenhum registro foi inserido."
        )
        return

    profiles = (
        ["recorrente"] * 40
        + ["ocasional"] * 25
        + ["inativo"] * 20
        + ["novo"] * 15
    )
    random.shuffle(profiles)

    documents = []

    for index, profile in enumerate(profiles, start=1):
        client_data = generate_client(index)
        documents.extend(
            generate_appointments_for_client(
                client_data,
                profile,
            )
        )

    if not documents:
        print("Nenhum agendamento gerado.")
        return

    result = appointments.insert_many(documents)

    print("Massa de dados criada com sucesso!")
    print(f"Clientes fictícios: {N_CLIENTS}")
    print(f"Agendamentos inseridos: {len(result.inserted_ids)}")
    print(f"Lote: {BATCH_ID}")
    print(
        "Período: "
        f"{min(doc['date'] for doc in documents)} até "
        f"{max(doc['date'] for doc in documents)}"
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()
