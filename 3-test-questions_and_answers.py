import unittest
from 2-questions_and_answers import identify_patterns  # Ensure to replace 'your_module' with the actual name of your Python file containing the 'identify_patterns' function.

class TestIdentifyPatterns(unittest.TestCase):
    def test_identify_patterns(self):
        # Example input text
        input_text = """
        1. What is the capital of France?<br />A Paris<br />B London<br />C Berlin<br />There are 1 correct answers<br />
        2. Which planet is known as the Red Planet?<br />A Earth<br />B Mars<br />C Jupiter<br />There are 1 correct answers<br />
        """
        
        # Expected output
        expected_output = [
            {
                "number": 1,
                "text": "What is the capital of France?",
                "options": [
                    {"label": "A", "text": "Paris"},
                    {"label": "B", "text": "London"},
                    {"label": "C", "text": "Berlin"}
                ],
                "correct_answers_count": "1"
            },
            {
                "number": 2,
                "text": "Which planet is known as the Red Planet?",
                "options": [
                    {"label": "A", "text": "Earth"},
                    {"label": "B", "text": "Mars"},
                    {"label": "C", "text": "Jupiter"}
                ],
                "correct_answers_count": "1"
            }
        ]
        
        # Running the function with the input
        result = identify_patterns(input_text)
        
        # Asserting that the output from the function is as expected
        self.assertEqual(result, expected_output)

if __name__ == '__main__':
    unittest.main()