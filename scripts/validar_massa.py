
from pathlib import Path
from collections import Counter

from dotenv import load_dotenv
from pymongo import MongoClient
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

uri = os.getenv("MONGODB_URI")
if not uri:
    raise RuntimeError("MONGODB_URI não configurada")

client = MongoClient(uri)

try:
    db = client["click_beleza"]
    collection = db["agendamentos"]

    lote = "retencao_ficticia_2026_v1"
    registros = list(collection.find({"_seed_batch": lote}))

    if not registros:
        print("Nenhum registro encontrado para esse lote.")
        raise SystemExit(0)

    por_cliente = Counter(
        (r["client_phone"], r["client_name"])
        for r in registros
    )

    servicos = Counter(r["service"] for r in registros)
    profissionais = Counter(r["barber"] for r in registros)
    meses = Counter(r["date"][:7] for r in registros)

    print(f"Total de agendamentos: {len(registros)}")
    print(f"Clientes distintos: {len(por_cliente)}")
    print(f"Clientes com 1 agendamento: "
          f"{sum(n == 1 for n in por_cliente.values())}")
    print(f"Clientes com vários agendamentos: "
          f"{sum(n > 1 for n in por_cliente.values())}")

    print("\nAgendamentos por serviço:")
    for nome, total in servicos.most_common():
        print(f"  {nome}: {total}")

    print("\nProfissionais encontrados:")
    for nome, total in profissionais.items():
        print(f"  {nome}: {total}")

    print("\nAgendamentos por mês:")
    for mes in sorted(meses):
        print(f"  {mes}: {meses[mes]}")

    conflitos = Counter(
        (r["date"], r["time"], r["barber"])
        for r in registros
    )
    print("\nHorários exatamente duplicados:",
          sum(n - 1 for n in conflitos.values() if n > 1))

finally:
    client.close()
