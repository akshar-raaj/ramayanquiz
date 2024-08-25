# Pydantic models

from pydantic import BaseModel


class Answer(BaseModel):
    answer: str
    is_correct: bool | None = False


class Question(BaseModel):
    question: str
    kanda: str | None = None
    tags: list[str] | None = list()
    difficulty: str | None = None
    answers: list[Answer] = list()
