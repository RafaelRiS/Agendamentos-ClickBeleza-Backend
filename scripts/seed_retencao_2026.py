
import os
import random
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URL = os.getenv("MONGODB_URI")

if not MONGO_URL:
    raise RuntimeError("MONGODB_URI não configurada no .env")

DATABASE_NAME = "click_beleza"
BATCH_ID = "retencao_ficticia_2026_v1"

YEAR_START = date(2026, 1, 1)
YEAR_END = date(2026, 12, 31)

BARBER = "Natasha Sabrine"
N_CLIENTS = 100
FEEDBACK_PROBABILITY = 0.65

random.seed(20261019)

SERVICES = {
    "Volume 8D": 60,
    "Volume Egípcio": 60,
    "Remoção": 30,
    "Efeito molhado marrom": 60,
    "Fox Eyes": 60,
    "Manutenção Volume 8D": 60,
    "Manutenção Volume Egípcio": 60,
}

MAINTENANCE = {
    "Volume 8D": "Manutenção Volume 8D",
    "Volume Egípcio": "Manutenção Volume Egípcio",
}

FIRST_NAMES = [
    "Ana", "Bruna", "Camila", "Daniela", "Eduarda",
    "Fernanda", "Gabriela", "Helena", "Isabela", "Juliana",
    "Larissa", "Mariana", "Natália", "Olivia", "Patrícia",
    "Rafaela", "Sabrina", "Tatiane", "Vanessa", "Vitória",
    "Amanda", "Beatriz", "Carolina", "Débora", "Elisa",
    "Flávia", "Giovana", "Luana", "Manuela", "Renata",
]

LAST_NAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Costa",
    "Lima", "Alves", "Pereira", "Rocha", "Martins",
    "Ferreira", "Gomes", "Ribeiro", "Carvalho", "Nunes",
]

GENERAL_COMMENTS = {
    1: [
        "Minha experiência não foi boa.",
        "Tive dificuldades durante o processo.",
        "A experiência poderia melhorar bastante.",
    ],
    2: [
        "Achei um pouco complicado agendar.",
        "Tive dificuldade para encontrar um horário.",
        "O processo poderia ser mais simples.",
    ],
    3: [
        "A experiência foi razoável.",
        "Consegui agendar, mas há pontos a melhorar.",
        "Foi uma experiência normal.",
    ],
    4: [
        "Gostei da experiência.",
        "Foi fácil encontrar um horário.",
        "O processo foi bom.",
    ],
    5: [
        "Adorei a experiência!",
        "Foi muito fácil fazer meu agendamento.",
        "Processo simples e rápido.",
    ],
}


# ============================================================
# CLIENTES E PERFIS SIMULADOS
# ============================================================

def create_clients():
    profiles = (
        ["recorrente"] * 40
        + ["ocasional"] * 25
        + ["inativo"] * 20
        + ["novo"] * 15
    )
    random.shuffle(profiles)

    clients = []

    for index, profile in enumerate(profiles, start=1):
        clients.append({
            "client_name": (
                f"{random.choice(FIRST_NAMES)} "
                f"{random.choice(LAST_NAMES)} Teste{index:03d}"
            ),
            "client_phone": f"TESTE26{index:06d}",
            "_seed_profile": profile,
        })

    return clients


def months_for_profile(profile):
    if profile == "recorrente":
        first_month = random.randint(1, 4)
        return [
            month for month in range(first_month, 13)
            if month == first_month or random.random() < 0.82
        ]

    if profile == "ocasional":
        return sorted(
            random.sample(range(1, 13), random.randint(2, 4))
        )

    if profile == "inativo":
        return sorted(
            random.sample(range(1, 7), random.randint(1, 3))
        )

    first_month = random.randint(7, 12)
    months = [first_month]

    if first_month < 12 and random.random() < 0.25:
        months.append(first_month + 1)

    return months


# ============================================================
# SERVIÇOS E HORÁRIOS
# ============================================================

def choose_service(previous_application):
    # Uma aplicação inicial pode ser seguida de manutenção.
    if previous_application and random.random() < 0.70:
        return MAINTENANCE[previous_application]

    # Remoção pode ocorrer independentemente do histórico.
    if random.random() < 0.08:
        return "Remoção"

    service = random.choice([
        "Volume 8D",
        "Volume Egípcio",
        "Efeito molhado marrom",
        "Fox Eyes",
    ])

    return service


def overlaps(start, end, intervals):
    return any(start < existing_end and end > existing_start
               for existing_start, existing_end in intervals)


def get_existing_intervals(collection):
    intervals = defaultdict(list)

    for appt in collection.find(
        {"barber": BARBER},
        {"date": 1, "time": 1, "duration": 1, "_seed_batch": 1},
    ):
        if appt.get("_seed_batch") == BATCH_ID:
            continue

        try:
            start_time = datetime.strptime(
                appt["time"], "%H:%M"
            ).time()

            start = datetime.combine(
                date.fromisoformat(appt["date"]), start_time
            )
            end = start + timedelta(minutes=int(appt["duration"]))

            intervals[appt["date"]].append((start, end))
        except (KeyError, ValueError, TypeError):
            print(
                "Aviso: agendamento existente ignorado na "
                "verificação de horários:", appt.get("_id")
            )

    return intervals


def allocate_slot(month, duration, intervals):
    last_day = monthrange(2026, month)[1]
    days = list(range(1, last_day + 1))
    random.shuffle(days)

    # Horários entre 09:00 e 17:00, em intervalos de 30 minutos.
    slots = [
        time(hour, minute)
        for hour in range(9, 17)
        for minute in (0, 30)
    ]
    random.shuffle(slots)

    for day in days:
        appointment_date = date(2026, month, day)
        date_key = appointment_date.isoformat()

        for slot in slots:
            start = datetime.combine(appointment_date, slot)
            end = start + timedelta(minutes=duration)

            if end.time() > time(18, 0):
                continue

            if not overlaps(start, end, intervals[date_key]):
                intervals[date_key].append((start, end))
                return appointment_date, slot

    return None


# ============================================================
# FEEDBACKS FICTÍCIOS
# ============================================================

def create_feedback(appointment, appointment_id):
    ease_rating = random.choices(
        [1, 2, 3, 4, 5],
        weights=[5, 10, 20, 35, 30],
        k=1,
    )[0]

    # A avaliação geral tem alguma relação com a facilidade,
    # mas não é determinada exclusivamente por ela.
    rating = max(
        1,
        min(5, round(0.65 * ease_rating + 0.35 * random.randint(1, 5))),
    )

    appointment_date = date.fromisoformat(appointment["date"])
    appointment_time = datetime.strptime(
        appointment["time"], "%H:%M"
    ).time()

    # O feedback é registrado após o horário do agendamento.
    created_at = datetime.combine(
        appointment_date, appointment_time
    ) + timedelta(minutes=appointment["duration"] + 10)

    return {
        "appointment_id": str(appointment_id),
        "rating": rating,
        "ease_rating": ease_rating,
        "comment": random.choice(GENERAL_COMMENTS[rating]),
        "created_at": created_at,
        "_seed_batch": BATCH_ID,
    }


# ============================================================
# LIMPEZA E GERAÇÃO
# ============================================================

def main():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=10000)

    try:
        client.admin.command("ping")

        db = client[DATABASE_NAME]
        appointments = db["agendamentos"]
        feedbacks = db["feedback"]

        # Identifica somente os agendamentos pertencentes ao lote.
        old_appointments = list(
            appointments.find(
                {"_seed_batch": BATCH_ID},
                {"_id": 1},
            )
        )

        old_ids = [item["_id"] for item in old_appointments]
        old_id_strings = [str(item_id) for item_id in old_ids]

        # Remove feedbacks vinculados aos agendamentos antigos.
        # Também remove feedbacks marcados diretamente com o lote.
        feedback_filter = {"_seed_batch": BATCH_ID}

        if old_id_strings:
            feedback_filter = {
                "$or": [
                    {"_seed_batch": BATCH_ID},
                    {"appointment_id": {"$in": old_id_strings}},
                ]
            }

        deleted_feedbacks = feedbacks.delete_many(feedback_filter)
        deleted_appointments = appointments.delete_many(
            {"_seed_batch": BATCH_ID}
        )

        print("Limpeza do lote anterior:")
        print(f"  Agendamentos removidos: {deleted_appointments.deleted_count}")
        print(f"  Feedbacks removidos: {deleted_feedbacks.deleted_count}")

        # Prepara os intervalos ocupados por agendamentos não fictícios.
        intervals = get_existing_intervals(appointments)

        clients = create_clients()
        appointment_documents = []
        profiles_by_phone = {}

        for person in clients:
            profile = person["_seed_profile"]
            profiles_by_phone[person["client_phone"]] = profile

            months = months_for_profile(profile)
            previous_application = None

            for month in months:
                service = choose_service(previous_application)
                duration = SERVICES[service]

                allocated = allocate_slot(month, duration, intervals)

                if allocated is None:
                    print(
                        f"Aviso: sem horário livre em {month:02d}/2026 "
                        f"para {person['client_phone']}"
                    )
                    continue

                appointment_date, appointment_time = allocated

                document = {
                    "client_name": person["client_name"],
                    "client_phone": person["client_phone"],
                    "service": service,
                    "barber": BARBER,
                    "date": appointment_date.isoformat(),
                    "time": appointment_time.strftime("%H:%M"),
                    "duration": duration,
                    "_seed_batch": BATCH_ID,
                    "_seed_profile": profile,
                }

                appointment_documents.append(document)

                if service in MAINTENANCE.values():
                    previous_application = next(
                        (
                            application
                            for application, maintenance in MAINTENANCE.items()
                            if maintenance == service
                        ),
                        None,
                    )

                elif service in MAINTENANCE:
                    previous_application = service

                elif service in ("Fox Eyes", "Efeito molhado marrom", "Remoção"):
                    previous_application = None

        if not appointment_documents:
            print("Nenhum agendamento foi gerado.")
            return

        # Insere agendamentos primeiro para obter os ObjectIds reais.
        result = appointments.insert_many(appointment_documents)

        feedback_documents = []
        today = date.today()

        for appointment, appointment_id in zip(
            appointment_documents, result.inserted_ids
        ):
            appointment_date = date.fromisoformat(appointment["date"])

            # Nunca cria feedback para agendamentos futuros.
            if appointment_date >= today:
                continue

            if random.random() > FEEDBACK_PROBABILITY:
                continue

            feedback_documents.append(
                create_feedback(appointment, appointment_id)
            )

        if feedback_documents:
            feedbacks.insert_many(feedback_documents)

        # ====================================================
        # VALIDAÇÃO
        # ====================================================

        batch_appointments = list(
            appointments.find({"_seed_batch": BATCH_ID})
        )
        batch_feedbacks = list(
            feedbacks.find({"_seed_batch": BATCH_ID})
        )

        clients_count = len({
            item["client_phone"] for item in batch_appointments
        })

        appointment_ids = {
            str(item["_id"]) for item in batch_appointments
        }

        valid_feedback_links = sum(
            item.get("appointment_id") in appointment_ids
            for item in batch_feedbacks
        )

        service_counts = Counter(
            item["service"] for item in batch_appointments
        )
        profile_counts = Counter(
            item["_seed_profile"] for item in batch_appointments
        )

        print("\nMassa de retenção criada!")
        print(f"Clientes planejados: {N_CLIENTS}")
        print(f"Clientes com agendamentos: {clients_count}")
        print(f"Agendamentos: {len(batch_appointments)}")
        print(f"Feedbacks: {len(batch_feedbacks)}")
        print(f"Feedbacks vinculados corretamente: {valid_feedback_links}")
        print(f"Profissionais: {set(a['barber'] for a in batch_appointments)}")

        print("\nAgendamentos por serviço:")
        for service, total in service_counts.most_common():
            print(f"  {service}: {total}")

        print("\nAgendamentos por perfil simulado:")
        for profile, total in profile_counts.items():
            print(f"  {profile}: {total}")

        # Verifica sobreposição entre os registros gerados.
        by_date = defaultdict(list)

        for item in batch_appointments:
            start = datetime.combine(
                date.fromisoformat(item["date"]),
                datetime.strptime(item["time"], "%H:%M").time(),
            )
            end = start + timedelta(minutes=item["duration"])
            by_date[item["date"]].append((start, end))

        conflicts = 0
        for day_intervals in by_date.values():
            day_intervals.sort()
            for previous, current in zip(
                day_intervals, day_intervals[1:]
            ):
                if current[0] < previous[1]:
                    conflicts += 1

        print(f"\nConflitos entre agendamentos do lote: {conflicts}")

        if valid_feedback_links != len(batch_feedbacks):
            print("ATENÇÃO: existem feedbacks com vínculos inválidos.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
