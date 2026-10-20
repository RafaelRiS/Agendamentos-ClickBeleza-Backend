
"""
seed_historico_agendamentos.py

Gera histórico SINTÉTICO de agendamentos para testar a retenção.
Não representa atendimentos reais de clientes.

Execução:
    python seed_historico_agendamentos.py
    python seed_historico_agendamentos.py --apply
"""

import argparse
import os
import random
from datetime import date, datetime, timedelta

from pymongo import MongoClient
from pymongo.errors import PyMongoError


# --------------------------------------------------
# CONFIGURAÇÕES
# --------------------------------------------------

DATA_INICIAL = date(2025, 1, 1)
DATA_FINAL = min(date.today() - timedelta(days=1), date(2026, 10, 19))

QUANTIDADE_CLIENTES = 100
SEED = 20261020

SERVICOS = [
    ("Volume 8D", 60),
    ("Volume Egípcio", 60),
    ("Remoção", 30),
    ("Efeito molhado marrom", 60),
    ("Fox Eyes", 60),
    ("Manutenção Volume 8D", 60),
    ("Manutenção Volume Egípcio", 60),
]

PROFISSIONAIS = [
    "Natasha Sabrine",
    "Camila Oliveira",
    "Juliana Santos",
]

NOMES = [
    "Ana Clara", "Mariana", "Juliana", "Beatriz",
    "Larissa", "Camila", "Gabriela", "Fernanda",
    "Amanda", "Isabela", "Letícia", "Carolina",
    "Vitória", "Bruna", "Rafaela", "Júlia",
    "Luana", "Manuela", "Eduarda", "Nicole",
    "Jéssica", "Patrícia", "Vanessa", "Priscila",
    "Aline", "Débora", "Renata", "Bianca",
    "Natália", "Thaís", "Sabrina", "Michele",
]

SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza",
    "Costa", "Pereira", "Rodrigues", "Almeida",
    "Nascimento", "Lima", "Araújo", "Barros",
    "Martins", "Ribeiro", "Carvalho", "Gomes",
    "Ferreira", "Gonçalves", "Mendes", "Cardoso",
    "Teixeira", "Moreira", "Correia", "Monteiro",
]

# DDDs brasileiros válidos
DDDS = [
    11
]

# --------------------------------------------------
# GERAÇÃO DE NÚMEROS TELEFÔNICOS
# --------------------------------------------------

def gerar_telefone():
    ddd = random.choice(DDDS)

    # Celular brasileiro: 9 + oito dígitos.
    numero = f"9{random.randint(0, 99999999):08d}"

    # Sem +, conforme solicitado.
    return f"{ddd}{numero}"

# --------------------------------------------------
# GERAÇÃO DOS CLIENTES
# --------------------------------------------------

def gerar_clientes(quantidade):
    if quantidade > len(NOMES) * len(SOBRENOMES):
        raise ValueError("Quantidade maior que as combinações de nomes disponíveis.")
    clientes = []
    telefones_utilizados = set()
    nomes_utilizados = set()

    while len(clientes) < quantidade:
        nome = (
            f"{random.choice(NOMES)} "
            f"{random.choice(SOBRENOMES)}"
        )

        # Evita repetir nomes na massa gerada.
        if nome in nomes_utilizados:
            continue

        telefone = gerar_telefone()

        # Evita telefones duplicados.
        if telefone in telefones_utilizados:
            continue

        nomes_utilizados.add(nome)
        telefones_utilizados.add(telefone)

        clientes.append({
            "client_name": nome,
            "client_phone": telefone,
        })

    return clientes


# --------------------------------------------------
# GERAÇÃO DE DATAS E HORÁRIOS
# --------------------------------------------------

def gerar_data():
    dias = (DATA_FINAL - DATA_INICIAL).days

    if dias < 0:
        raise ValueError("O intervalo de datas é inválido.")

    return DATA_INICIAL + timedelta(
        days=random.randint(0, dias)
    )


def gerar_horario():
    # Horários entre 09:00 e 17:00, em intervalos de 30 min.
    minutos = random.randrange(9 * 60, 17 * 60 + 1, 30)

    return (
        f"{minutos // 60:02d}:"
        f"{minutos % 60:02d}"
    )


# --------------------------------------------------
# GERAÇÃO DOS AGENDAMENTOS
# --------------------------------------------------

def gerar_agendamentos(clientes):
    documentos = []

    # Evita sobreposição de horários para a mesma profissional.
    horarios_ocupados = {}

    for cliente in clientes:
        # Cada cliente terá entre 2 e 8 atendimentos.
        quantidade = random.randint(2, 8)

        datas_cliente = set()
        tentativas = 0

        while len(datas_cliente) < quantidade and tentativas < 500:
            tentativas += 1

            data_atendimento = gerar_data()

            # Evita dois atendimentos do mesmo cliente no mesmo dia.
            if data_atendimento in datas_cliente:
                continue

            servico, duracao = random.choice(SERVICOS)
            profissional = random.choice(PROFISSIONAIS)
            horario = gerar_horario()

            inicio = datetime.combine(
                data_atendimento,
                datetime.strptime(horario, "%H:%M").time()
            )
            fim = inicio + timedelta(minutes=duracao)

            # Não ultrapassar o horário de funcionamento.
            if fim.time() > datetime.strptime(
                "18:00", "%H:%M"
            ).time():
                continue

            chave = (profissional, data_atendimento.isoformat())

            if chave not in horarios_ocupados:
                horarios_ocupados[chave] = []

            conflito = any(
                inicio < fim_existente
                and fim > inicio_existente
                for inicio_existente, fim_existente
                in horarios_ocupados[chave]
            )

            if conflito:
                continue

            horarios_ocupados[chave].append((inicio, fim))
            datas_cliente.add(data_atendimento)

            documentos.append({
                "client_name": cliente["client_name"],
                "client_phone": cliente["client_phone"],
                "service": servico,
                "barber": profissional,
                "date": data_atendimento.isoformat(),
                "time": horario,
                "duration": duracao,
            })

    # Mantém a saída ordenada cronologicamente.
    documentos.sort(
        key=lambda item: (item["date"], item["time"])
    )

    return documentos


# --------------------------------------------------
# INSERÇÃO NO MONGODB
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Confirma a inserção no banco de dados."
    )
    args = parser.parse_args()

    if not args.apply:
        print("Modo de simulação: nada será inserido.")
        print("Execute com --apply para confirmar a gravação.")

    uri = os.getenv("MONGODB_URI")

    if not uri:
        raise RuntimeError(
            "Configure MONGODB_URI nas variáveis de ambiente."
        )

    random.seed(SEED)

    if DATA_FINAL < DATA_INICIAL:
        raise RuntimeError("Não há datas no intervalo configurado.")

    clientes = gerar_clientes(QUANTIDADE_CLIENTES)
    documentos = gerar_agendamentos(clientes)

    print(f"Período: {DATA_INICIAL} até {DATA_FINAL}")
    print(f"Clientes sintéticos: {len(clientes)}")
    print(f"Agendamentos gerados: {len(documentos)}")
    print("\nExemplo de documento:")
    print(documentos[0] if documentos else "Nenhum documento gerado.")

    if not args.apply:
        return

    # Use a mesma base e coleção da aplicação.
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)

    try:
        client.admin.command("ping")

        db = client["click_beleza"]
        collection = db["agendamentos"]

        # Evita duplicar o lote caso o script seja executado novamente.
        telefones = [
            cliente["client_phone"] for cliente in clientes
        ]

        existentes = collection.count_documents({
            "client_phone": {"$in": telefones}
        })

        if existentes:
            raise RuntimeError(
                f"Foram encontrados {existentes} registros "
                "com telefones deste lote. Inserção cancelada "
                "para evitar duplicações."
            )

        resultado = collection.insert_many(documentos)

        print(
            f"\nSucesso: {len(resultado.inserted_ids)} "
            "agendamentos inseridos."
        )

    except PyMongoError as erro:
        print(f"Erro ao acessar o MongoDB: {erro}")
        raise

    finally:
        client.close()


if __name__ == "__main__":
    main()
