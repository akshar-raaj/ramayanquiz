"""
Test Pydantic models.

We need to ensure that no unintended changes are made to the Pydantic models.
Else it has the potential to break the API contract.
"""


from models import Question


class TestQuestion():

    def test_expected_fields(self):
        expected_keys = ["question", "kanda", "difficulty", "tags", "answers"]
        found_keys = Question.schema()['properties'].keys()
        for key in expected_keys:
            assert key in found_keys
