# Pydantic models

from enum import Enum
from pydantic import BaseModel


class DataStore(Enum):
    POSTGRES = "postgres"
    MONGO = "mongo"


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Kanda(Enum):
    BALA_KANDA = "Bala Kanda"
    AYODHYA_KANDA = "Ayodhya Kanda"
    ARANYA_KANDA = "Aranya Kanda"
    KISHKINDA_KANDA = "Kishkinda Kanda"
    SUNDARA_KANDA = "Sundara Kanda"
    LANKA_KANDA = "Lanka Kanda"
    UTTARA_KANDA = "Uttara Kanda"


class Answer(BaseModel):
    answer: str
    is_correct: bool | None = False


class Question(BaseModel):
    question: str
    kanda: Kanda | None = None
    difficulty: Difficulty | None = None
    tags: list[str] | None = list()
    answers: list[Answer] = list()
