"""
This script populates column `information` in table `questions`.

In the routine setup, once a question is created, an appropriate entry is published/pushed to the queue.
And a decoupled asynchronous setup, consumes from the queue, and populates the information column.

We will follow the same approach, rather than making OpenAI call from here to generate the information.
"""

from queueing import publish
from database import get_database_connection


def populate():
    # Fetch all the questions
    queue_name = 'question-information'
    questions = []
    connection = get_database_connection()
    cursor = connection.cursor()
    query = "SELECT id, question FROM questions WHERE information is NULL"
    cursor.execute(query)
    questions = cursor.fetchall()
    cursor.close()
    connection.close()
    # Iterate on questions
    for question in questions:
        question_id = question[0]
        question_text = question[1]
        print(f"Publishing to queue {queue_name} for question {question_id}. Question text is: {question_text}")
        # Publish to queue 'question-information'
        publish('question_information', 'question_information', [question_id], queue_name)
        print(f"Published to queue {queue_name} for question {question_id}")
