#!/home/tom/pdf_miner_venv/bin/python

import os
import logging
import shutil
import re
from html import unescape
from html import unescape
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from io import StringIO
import json

# Define constants to specify the range of pages for questions and answers
LAST_QUESTION_PAGE = 79
FIRST_ANSWER_PAGE = 80
LAST_ANSWER_PAGE = 83
TOTAL_QUESTIONS = 422

output_directory = './output'
json_directory = './json'
pdf_path = 'C_S4EWM_2020 - Extended Warehouse Management with SAP S4HANA.pdf'
log_file = 'process.log'

def initialize_logging():
		if os.path.exists(log_file):
				os.remove(log_file)
		logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO,
												format='%(asctime)s - %(levelname)s - %(message)s')

def create_and_clear_directory(directory):
		if os.path.exists(directory):
				shutil.rmtree(directory)
		os.makedirs(directory)

def extract_pages(pdf_path):
		# Initialize a resource manager instance
		resource_manager = PDFResourceManager()
		pages_text = []  # List to hold the extracted text from each page
		# Open and read the binary content of the PDF file
		with open(pdf_path, 'rb') as file:
				try:
						# Get an iterator over the pages of the PDF
						for page in PDFPage.get_pages(file):
								# Capture the text of the page within an in-memory string stream
								with StringIO() as output_string:
										with TextConverter(resource_manager, output_string) as device:
												# Initialize a page interpreter object
												interpreter = PDFPageInterpreter(resource_manager, device)
												# Process the current page and record its text
												interpreter.process_page(page)
												text = output_string.getvalue()
												pages_text.append(text)
				except Exception as e:
						# Log any exceptions that occur during processing
						logging.error(f"Error extracting pages: {e}", exc_info=True)
						# Re-raise the exception for visibility and potential handling higher up the call stack
						raise
		return pages_text

def clean_html_and_page_numbers(text):
		text_without_tags = re.sub('<[^<]+?>', '', text)
		cleaned_text = unescape(text_without_tags)
		page_number_pattern = re.compile(r'Page\s+\d+\s+of\s+\d+', re.IGNORECASE)
		cleaned_text = page_number_pattern.sub('', cleaned_text).strip()
		return cleaned_text

def parse_questions(questions_text):
		question_pattern = re.compile(r'(\d+)\.(.+?)(?=\d+\.|$)', re.DOTALL)
		questions = [clean_html_and_page_numbers(match[1].strip()) for match in question_pattern.findall(questions_text)]
		
		return [{'number': i+1, 'text': question} for i, question in enumerate(questions) if question]

def save_to_json(data, json_file_path):
		with open(json_file_path, 'w', encoding='utf-8') as f:
				json.dump(data, f, ensure_ascii=False, indent=2)
def parse_answers(answers_text):
    # Removing page information and "Answer Key" title
    cleaned_text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', answers_text)
    cleaned_text = re.sub(r'Answer Key', '', cleaned_text)
    questions = []

    pattern = re.compile(r'(\d+)\.\s*([a-zA-Z\s,]+)(?=\d+\.|\Z)')
    matches = pattern.findall(cleaned_text)
    
    for match in matches:
        question_num, answers = match
        # Clean up the answers, remove extraneous characters and split by commas or whitespace
        clean_answers = [answer.upper() for answer in re.sub(r'[^\w\s]', '', answers).split()]
        # Create a dictionary for each question, as specified
        question_info = {
            "number": int(question_num),
            "answers": clean_answers,
            "answer_number": len(clean_answers),
						"valid": (len(clean_answers) > 0)
        }
        questions.append(question_info)
    
    return questions
def parse_choices(question):
	# Extraire tout ce qui se trouve après la letre A majuscule incluse
	# Si il y a plusieurs A majuscule , prendre celui qui est le plus loin dans la chaine
	# conter les lettre majuscules qui se suivent (A, B, C, D, E) mais elles peuvent être en désordre
	# car affcihées en tableau sur deux colonnes
	# ex A label 1 C label 3 B label 2 D label 4 
	# reconstituer un arrau d'objets json avec la structure suivante 
	# [{'id': 1, 'name': 'A', 'label': 'label 1'},{'id': 2, 'name': 'B', 'label': 'label 2'} ... ]
	last_a_index = question.rfind('A')

  # Extract all choices after the last capital 'A' found
	if last_a_index != -1:
		choices_str = question[last_a_index:]

    # Find all matches that fit the pattern after the letter 'A'
    # The pattern looks for a capital letter followed by any mix of letters and spaces, and then stops if another capital letter or end of string is found.
		matches = re.findall(r'([A-E])([a-zA-Z\s]+?)(?=[A-E]|$)', choices_str)

    # Create the list of dictionaries with the extracted data, stripping extraneous whitespace from the labels
		choices_list = [{'id': index + 1, 'name': match[0], 'label': match[1].strip()} for index, match in enumerate(matches)]

		return choices_list
	else:
    # No occurrence of 'A' was found, return an empty array
		return []

def parse_label(question):
		# Trouver la position de la lettre 'A' majuscule
		# Si il y a plusieurs A majuscule , prendre celui qui est le plus loin dans la chaine
		pos = question.rfind('A')
		# Find the position of the capital 'A'
		if pos == -1:
				return question
		# Retourner la sous-chaîne jusqu'à la lettre 'A' majuscule (non comprise)
		return question[:pos]


def match_questions_and_answers(parsed_questions, parsed_answers):
		# Assuming both parsed_questions and parsed_answers are lists and each question has a unique number
		qa_match = []
		for question in parsed_questions:
				question_number = question['number']
				question['label'] = parse_label(question['text'])
				
				corresponding_answer = next((answer for answer in parsed_answers if answer['number'] == question_number), None)
				
				if corresponding_answer:  # Check if corresponding_answer is not None
						question['choices'] = parse_choices(question['text'])
						question['answers'] = corresponding_answer['answers']
						question['valid'] = corresponding_answer['valid']
						question['answer_number'] = corresponding_answer['answer_number']
						question['type'] = 'checkbox' if question['answer_number'] > 1 else 'radio'
				else:
						# Handle the case where there is no corresponding answer
						question['choices'] = parse_choices(question['text'])
						question['answers'] = []  # Set to an empty list or another default value
						question['valid'] = False
						question['answer_number'] = 0
				
				qa_match.append(question)

		return qa_match


def main():
		initialize_logging()
		create_and_clear_directory(output_directory)
		create_and_clear_directory(json_directory)

		try:
				logging.info("Starting extraction…")
				full_text = extract_pages(pdf_path)

				questions_text = '\n'.join(full_text[:LAST_QUESTION_PAGE])
				answers_text = '\n'.join(full_text[FIRST_ANSWER_PAGE - 1:LAST_ANSWER_PAGE])
				print(answers_text)
				questions_file_path = os.path.join(output_directory, "questions.txt")
				answers_file_path = os.path.join(json_directory, "answers.json")

				parsed_questions = parse_questions(questions_text)
				parsed_answers = parse_answers(answers_text)

				save_to_json(parsed_questions, questions_file_path)
				logging.info(f"Questions text saved to {questions_file_path}")

				save_to_json(parsed_answers, answers_file_path)
				logging.info(f"Answers text saved to {answers_file_path}")

				questions_with_answers = match_questions_and_answers(parsed_questions, parsed_answers)

				questions_with_answers_json_path = os.path.join(json_directory, "questions_with_answers.json")
				save_to_json(questions_with_answers, questions_with_answers_json_path)
				logging.info(f"Questions with answers JSON saved to {questions_with_answers_json_path}")

		except Exception as e:
				logging.error(f"An error occurred: {e}", exc_info=True)
				raise

if __name__ == "__main__":
		main()
