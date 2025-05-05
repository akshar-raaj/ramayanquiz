# Pydantic models

from enum import Enum
from pydantic import BaseModel


class StatusResponse(BaseModel):
    status: str


class DataStore(Enum):
    POSTGRES = "postgres"
    MONGO = "mongo"


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class Kanda(Enum):
    BALA_KANDA = "Bala Kanda"
    AYODHYA_KANDA = "Ayodhya Kanda"
    ARANYA_KANDA = "Aranya Kanda"
    KISHKINDA_KANDA = "Kishkinda Kanda"
    SUNDARA_KANDA = "Sundara Kanda"
    LANKA_KANDA = "Lanka Kanda"
    UTTARA_KANDA = "Uttara Kanda"


class Answer(BaseModel):
    """
    Represents a single answer in the API request.
    Used im POST /questions to represent one answer for a question
    """
    answer: str
    is_correct: bool | None = False


class AnswerResponse(Answer):
    """
    Represents a single answer in the API response.
    Used in GET /questions endpoint to represent one answer for a question
    """
    id: int
    # It's possible that the RabbitMQ task for translation hasn't executed yet, thus keep these
    # inferred fields like answer_hindi, answer_telugu as optional
    answer_hindi: str | None = None
    answer_telugu: str | None = None


class Question(BaseModel):
    question: str
    kanda: Kanda | None = None
    difficulty: Difficulty | None = None
    tags: list[str] | None = list()
    answers: list[Answer]


class QuestionResponse(Question):
    id: int
    # It's possible that the RabbitMQ task for translation hasn't executed yet, thus keep these
    # inferred fields like question_hindi, question_telugu as optional
    question_hindi: str | None = None
    question_telugu: str | None = None
    information: str | None = None
    answers: list[AnswerResponse]
