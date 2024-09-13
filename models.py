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


class Answer(BaseModel):
    answer: str
    is_correct: bool | None = False


class Question(BaseModel):
    question: str
    kanda: str | None = None
    difficulty: str | None = None
    tags: list[str] | None = list()
    answers: list[Answer] = list()
