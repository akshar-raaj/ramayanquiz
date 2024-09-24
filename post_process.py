"""
Performs post-processing on a Question and the associated choices.
"""

from database import fetch_question, update_column_value, fetch_question_answers
from translate import translate


def post_process(question_id: int):
    """
    The function translates the english text for a question and the associated choices to various target languages.

    In addition, it update the question row in the database and sets the translated text. Thus it assumes that proper columns exist.
    """
    print(f"Post processing for {question_id} started.")
    question = fetch_question(question_id)
    if question == {}:
        print("Invalid question id")
        return
    hindi_text = translate(question['question'])
    update_column_value('questions', question_id, 'question_hindi', hindi_text)
    # TODO: Translate all answers for this question
    answers = fetch_question_answers(question_id)
    for answer in answers:
        hindi_text = translate(answer['answer'])
        update_column_value('answers', answer['id'], 'answer_hindi', hindi_text)
    telugu_text = translate(question['question'], translate_to='Telugu')
    update_column_value('questions', question_id, 'question_telugu', telugu_text)
    for answer in answers:
        telugu_text = translate(answer['answer'], translate_to='Telugu')
        update_column_value('answers', answer['id'], 'answer_telugu', telugu_text)
    print(f"Post processing for {question_id} completed.")