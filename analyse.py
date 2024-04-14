#!/home/tom/pdf_miner_venv/bin/python
# >>> à l'aide de python , analyse les fichiers output/pages/* , deduis la structure des datas, en array d'objets json  et propose moi une methode d'extraction 
import os
import logging
import shutil
import re
import string
import requests
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
TITLE_PATTERN = "C_S4EWM_2020 - Extended Warehouse Management with SAP S4HANA"

# Directories
output_directory = './output'
pages_dir = os.path.join(output_directory, 'pages')
json_dir = './json'
log_directory = './log'
json_filename='questionnaire.json'

# Log file path
log_file_path = os.path.join(log_directory, 'process.log')

# 3. Initializes logging configuration.
logging.basicConfig(filename=log_file_path, filemode='w', level=logging.INFO, format='%(levelname)s:%(message)s')

def open_file(path):
	with open(path, 'r', encoding='utf-8') as file:
		return file.read()

def find_questions(page_text):
	logging.debug("Searching for questions in the text")
	try:
		question_regex = re.compile(r'(?<!\d)(\d{1,3})\.\s*(.*?)(?=(?<!\d)\d{1,3}\.\s*|\Z)', re.DOTALL)
		found_questions = question_regex.findall(page_text)
		if not found_questions:
			logging.debug("No questions detected using regex.")
		return found_questions
	except Exception as error:
		logging.error(f"Error during question search: {error}")
		return []

def analyze_text_page(page_path):
	logging.info(f"Analyzing text page: {page_path}")
	try:
		content = open_file(page_path)
		if not content.strip():
			logging.warning(f"Page {page_path} is empty.")
			return []
		
		found_questions = find_questions(content)
		if not found_questions:
			logging.warning(f"No questions on page {page_path}.")
			return []

		question_infos = [create_question_info(number, text) for number, text in found_questions]
		return question_infos
	except Exception as error:
		logging.error(f"Error during page analysis: {error}")

def stepwise_cut_string(incoming_string, start_char, end_char):
		# Initialize the current character as start_char
		current_char = start_char

		# Initialize an empty list to hold the resulting parts
		parts = []
		
		# Start from the first character after the initial one.
		next_char_code = ord(start_char) + 1

		# Loop until there is no string left or until we reach the end character.
		while next_char_code <= ord(end_char):
				# Identify the next character in sequence
				current_char = chr(next_char_code)
				
				# Search for the next occurrence of the current character in the string
				index_of_current_char = incoming_string.find(current_char)
				
				while index_of_current_char != -1:
						prospective_part = incoming_string[:index_of_current_char].strip()
						
						# Check if the part is not empty and does not start with a lowercase letter
						if prospective_part and not prospective_part[0].islower():
								parts.append(prospective_part)
								break
						
						# Skip to the next occurrence of the current character
						incoming_string = incoming_string[index_of_current_char + 1:]
						index_of_current_char = incoming_string.find(current_char)
				
				# If the end character isn't found within the while condition, exit the loop
				if index_of_current_char == -1:
						parts.append(incoming_string)
						break
				
				# Prepare for the next iteration to look for the subsequent character
				incoming_string = incoming_string[index_of_current_char + 1:]
				next_char_code += 1
		
		# Filter out any empty strings in the parts list just to be extra cautious
		parts = [part for part in parts if part]

		return parts


def extract_choices(choices_text):
	logging.info(f"Analyzing choices: {choices_text}")
	
	# Première étape de découpage du texte
	answers = stepwise_cut_string(choices_text, "A", "G")
	
	# Filtrer les éléments vides si nécessaire
	answers = [item for item in answers if item]
	
	# Prépare un tableau pour accueillir les choix
	choices = []
	
	logging.info(f"Analyzing choices after stepwize cut: {answers}")  # Devrait être answers et non choices
	
	names = ["A", "B", "C", "D", "E", "F", "G"]
	
	if len(answers) > 0 :
		for index, answer in enumerate(answers):  # Ajoute 'enumerate' pour obtenir l'index
			choice = {
				"id": index + 1,  
				"name": names[index],
				"label": answer.strip()  # Utilisation de .strip() pour éliminer les espaces superflus
			}
			# Ajoute le dictionnaire au tableau choices
			choices.append(choice)
	else:
		return []
	
	# Retourne le tableau de choix rempli
	return choices



def create_question_info(question_num, question_text):
		logging.info(f"Creating question info for question number {question_num}")
		# Define regex patterns with and without the period at the end
		answer_count_patterns = [
				r'(?:There\s*(?:are|is)\s*)(\d+)(?:\s*correct\s*answers(?:\s*to\s*this\s*question)?\.)',
				r'(?:There\s*(?:are|is)\s*)(\d+)(?:\s*correct\s*answers(?:\s*to\s*this\s*question)?)'
		]

		question_info = {
				"number": int(question_num),
				"text": question_text,
				"label": "",
				"choices": [],
				"answer_number": None,
				"type": "radio",  # default type
				"valid": False
		}

		# Try patterns with the period first and then without it
		for pattern in answer_count_patterns:
				answer_count_regex = re.compile(pattern, re.IGNORECASE)
				match_count = answer_count_regex.search(question_text)
				if match_count:
						correct_answers_count = int(match_count.group(1))
						question_info["answer_number"] = correct_answers_count
						question_info["type"] = "checkbox" if correct_answers_count > 1 else "radio"

						separator_position = match_count.end()
						question_label = question_text[:separator_position].rstrip('. ')
						question_choices = question_text[separator_position:].strip()

						question_info["label"] = question_label
						question_info["choices"].extend(extract_choices(question_choices))
						question_info["valid"] = True
						break

		# If no match was found with counting pattern, try with alternate patterns
		if not question_info["valid"]:
				alternate_pattern = re.compile(r'Please\s*choose\s*the\s*correct\s*answer\.?', re.IGNORECASE)
				third_pattern = re.compile(r'Choose\s*the\s*correct\s*answer\(s\)[:.]?', re.IGNORECASE)
				match_alternate = alternate_pattern.search(question_text)
				match_third = third_pattern.search(question_text)

				if match_alternate:
						logging.info(f"Using alternate pattern for question #{question_num}")
						separator_position = match_alternate.end()
						question_label = question_text[:separator_position].rstrip('. ')
						question_choices = question_text[separator_position:].strip()

						question_info["label"] = question_label
						question_info["choices"].extend(extract_choices(question_choices))
						question_info["answer_number"] = 1
						question_info["type"] = "radio"
						question_info["valid"] = True
				elif match_third:
						logging.info(f"Using third pattern for question #{question_num}")
						separator_position = match_third.end()
						question_label = question_text[:separator_position].rstrip('. ')
						question_choices = question_text[separator_position:].strip()

						question_info["label"] = question_label
						question_info["choices"].extend(extract_choices(question_choices))
						question_info["answer_number"] = 99  # Assuming single answer unless specified otherwise
						question_info["type"] = "checkbox"
						question_info["valid"] = True
				else:
						logging.warning(f"No correct answer or alternate pattern for question #{question_num}")

		return question_info


   
def process_text_files(directory, last_question_page):
	questions_data = []
	for page_number in range(1, last_question_page + 1):  # +1 to include the last page
		filename = f"page-{page_number}.txt"  # Assuming the file naming convention is page_X.txt
		full_path = os.path.join(directory, filename)
		
		if os.path.exists(full_path):
			logging.info(f"Processing file {filename}")
			page_questions = analyze_text_page(full_path)

			if page_questions:
				questions_data.extend(page_questions)
			else:
				logging.warning(f"No question data in file {filename}")
		else:
			logging.warning(f"pAGE {filename} does not exist.")
	
	if not questions_data:
		logging.error("No question data extracted from any files.")

	return questions_data


def main():
	logging.info("Starting processing of text pages to generate JSON")
	try:
		if not os.path.exists(json_dir):
			os.makedirs(json_dir)

		questionnaire_data = process_text_files(pages_dir, LAST_QUESTION_PAGE)  # Pass the last question page here
		json_output_path = os.path.join(json_dir, json_filename)

		with open(json_output_path, 'w', encoding='utf-8') as json_file:
			json.dump(questionnaire_data, json_file, ensure_ascii=False, indent=4)
			
		logging.info("JSON data successfully written to file")

	except Exception as error:
		logging.error(f"An error occurred while generating JSON: {error}")

if __name__ == '__main__':
	main()

