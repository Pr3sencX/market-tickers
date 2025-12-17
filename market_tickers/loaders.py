# market_tickers/loaders.py

import csv
import os

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")


def _load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_india_stocks():
    return _load_csv("india_stocks.csv")


def load_usa_stocks():
    return _load_csv("usa_stocks.csv")


def load_indices():
    indices = []
    for file in ["indices_india.csv", "indices_usa.csv", "indices_global.csv"]:
        indices.extend(_load_csv(file))
    return indices
