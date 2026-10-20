
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "retencao_treinamento.csv"
MODEL_DIR = ROOT_DIR / "models"
MODEL_FILE = MODEL_DIR / "modelo_retencao.joblib"

TARGET = "did_not_return_within_60_days"

FEATURES = [
    "previous_appointments",
    "days_since_previous",
    "previous_service",
    "ease_rating_mean",
    "rating_mean",
]


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset não encontrado: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = FEATURES + [TARGET]
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Colunas ausentes no dataset: {missing_columns}. "
            "Execute preparar_dados_retencao.py novamente."
        )

    if df.empty:
        raise ValueError("O dataset está vazio.")

    if df[TARGET].nunique() < 2:
        raise ValueError(
            "O dataset precisa conter exemplos das duas classes."
        )

    # Ordena cronologicamente para que o teste utilize
    # datas posteriores às do treinamento.
    df["snapshot_date"] = pd.to_datetime(
        df["snapshot_date"], errors="raise"
    )
    df = df.sort_values("snapshot_date").reset_index(drop=True)

    X = df[FEATURES].copy()
    y = df[TARGET].astype(int)

    # Divide cronologicamente: 80% iniciais para treino,
    # 20% finais para teste.
    split_index = int(len(df) * 0.80)

    if split_index == 0 or split_index == len(df):
        raise ValueError("Não há amostras suficientes para a divisão.")

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]
    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    if y_train.nunique() < 2:
        raise ValueError(
            "O período de treino contém apenas uma classe. "
            "Será necessário rever a divisão temporal."
        )

    numeric_features = [
        "previous_appointments",
        "days_since_previous",
        "ease_rating_mean",
        "rating_mean",
    ]

    categorical_features = ["previous_service"]

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])

    categorical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="constant", fill_value="nenhum"),
        ),
        (
            "onehot",
            OneHotEncoder(handle_unknown="ignore"),
        ),
    ])

    preprocessing = ColumnTransformer([
        ("numeric", numeric_pipeline, numeric_features),
        ("categorical", categorical_pipeline, categorical_features),
    ])

    model = Pipeline([
        ("preprocessing", preprocessing),
        (
            "classifier",
            RandomForestClassifier(
                n_estimators=300,
                max_depth=6,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    print("\n========== AVALIAÇÃO DO MODELO ==========")
    print(f"Amostras totais: {len(df)}")
    print(f"Amostras de treino: {len(X_train)}")
    print(f"Amostras de teste: {len(X_test)}")
    print(f"Período de treino: até {df.iloc[split_index - 1]['snapshot_date'].date()}")
    print(f"Período de teste: de {df.iloc[split_index]['snapshot_date'].date()} até {df.iloc[-1]['snapshot_date'].date()}")

    print(f"\nAcurácia: {accuracy_score(y_test, predictions):.3f}")

    if y_test.nunique() == 2:
        print(f"ROC-AUC: {roc_auc_score(y_test, probabilities):.3f}")
    else:
        print("ROC-AUC indisponível: o teste contém apenas uma classe.")

    print("\nRelatório de classificação:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=[0, 1],
            target_names=[
                "Retornou em até 60 dias",
                "Não retornou em até 60 dias",
            ],
            zero_division=0,
        )
    )

    print("Matriz de confusão:")
    print(confusion_matrix(y_test, predictions, labels=[0, 1]))

    # Salva o pipeline completo, incluindo pré-processamento.
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump({
        "model": model,
        "features": FEATURES,
        "target": TARGET,
        "horizon_days": 60,
    }, MODEL_FILE)

    print(f"\nModelo salvo em: {MODEL_FILE}")


if __name__ == "__main__":
    main()
