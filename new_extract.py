#!/home/tom/pdf_miner_venv/bin/python
import os
import logging
import shutil
import re
import string
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

# Specify directories for outputting intermediate and final results
output_directory = './output'
json_directory = './json'

# Path to the PDF file to be processed
pdf_path = 'C_S4EWM_2020 - Extended Warehouse Management with SAP S4HANA.pdf'

# Initialize logging configuration
log_file = 'process.log'  # Log file path

# Function to initialize logging settings
def initialize_logging():
		# Remove existing log file if it exists to start fresh
		if os.path.exists(log_file):
				os.remove(log_file)
		# Configure basic logging parameters such as format and log level
		logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to extract and transform questions into JSON format
def extract_questions_to_json(input_text):
		# Remove spaces from input_text to simplify pattern matching
		input_text = input_text.replace(" ", "")
		result = []
		# Iterate over all questions based on their numbering
		for i in range(1, TOTAL_QUESTIONS + 1):
				# Define a regex pattern to find each question's answer choices using its number
				pattern = r'{}\.([a-e,]*)'.format(i)
				# Add a lookahead for the next question to ensure we only capture the current question's answers
				if i < TOTAL_QUESTIONS:
						pattern += r'(?={}\.)'.format(i + 1)

				# Search for the pattern in the input text
				match = re.search(pattern, input_text)
				if match:
						answers_raw = match.group(1)
						# Extract any uppercase letters representing answer options and store them in a list
						answers = [answer.upper() for answer in answers_raw.split(',') if answer]

						# Construct a dictionary representing a question's metadata including its answers
						question_dict = {
								"numero": i,
								"answers": answers,
								"answer_number": len(answers)
						}
						result.append(question_dict)
				else:
						# In case no matches are found, create an entry with empty answers indicating an absence of choice options
						result.append({
								"numero": i,
								"answers": [],
								"answer_number": 0
						})

		return result

# Function to read a file and process its content to JSON
def read_file_and_process(file_path):
		# Open and read the content of the given file
		with open(file_path, 'r', encoding='utf-8') as file:
				# Join lines stripping leading/trailing whitespaces and then serialize to JSON
				content = ' '.join([line.strip() for line in file])
				json_results = extract_questions_to_json(content)
				
				# Serialize the list of dictionaries (question items) to a JSON formatted string
				return json.dumps(json_results, indent=2)

# Function to clean the answers file of unnecessary content
def clean_answers_file(input_path, output_path):
		try:
				# Read content of the original answers file
				with open(input_path, 'r') as file:
						lines = file.readlines()

				# Compile a regex pattern to identify and remove unwanted page numbers
				page_pattern = re.compile(r"Page \d+ of \d+")

				cleaned_lines = []  # Prepare a container for the processed lines
				for line in lines:
						# Remove specific unwanted strings such as "Answer Key" and page numbers
						cleaned_line = line.replace("Answer Key", "").strip()
						cleaned_line = page_pattern.sub("", cleaned_line).strip()

						# Collect the cleaned version of the line
						cleaned_lines.append(cleaned_line)

				# Write out the cleaned lines to the specified output file
				with open(output_path, 'w') as file:
						for cleaned_line in cleaned_lines:
								file.write(f"{cleaned_line}\n")

		except Exception as e:
				# If an exception occurs, print an error message to standard output
				print(f"An error occurred: {e}")

# Create a directory if it doesn't exist or clear it if it does
def create_and_clear_directory(directory):
		# Remove the existing directory with its contents, if any
		if os.path.exists(directory):
				shutil.rmtree(directory)
		# Create a fresh directory
		os.makedirs(directory)

# Extract text content from all pages of a PDF file
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

# Function to clean HTML tags and page numbers from a given text
def clean_html_and_page_numbers(text):
		# Use regex to strip out possible HTML tags
		text_without_tags = re.sub('<[^<]+?>', '', text)
		# Decode any HTML entities to normal characters
		cleaned_text = unescape(text_without_tags)
		# Compile regex to match and eliminate page numbers from the text
		page_number_pattern = re.compile(r'Page\s+\d+\s+of\s+\d+', re.IGNORECASE)
		# Apply regex to actually remove the identified page number references
		cleaned_text = page_number_pattern.sub('', cleaned_text).strip()
		return cleaned_text

# Function to extract choices from question text
def extract_choices(text):
		# Define regex to separate question text from choices labeled by letters A-E
		choice_pattern = re.compile(r'\b([A-E])\.\s*(.*?)\s*(?=\b[A-E]\b|$)', re.DOTALL)
		# Apply regex to map choice labels to their respective texts in a dictionary
		choices = {match.group(1): match.group(2).strip() for match in choice_pattern.finditer(text)}
		return choices

# Function to clean redundant or less suitable choice texts for questions
def clean_choices(choices):
		cleaned = {}  # Dictionary to store cleaned versions of choices
		for choice in choices:
				letter = choice['letter']
				text = choice['text']

				# Check if the current choice is unique or preferable compared to what's already been captured
				if letter not in cleaned or (len(text) > len(cleaned[letter]['text']) or
																		 (len(text) == len(cleaned[letter]['text']) and text[0].isupper())):
						cleaned[letter] = choice

		# Convert the cleaned choices back into a list format from a dictionary
		return list(cleaned.values())

def separate_question_and_choices(question_item):
		# Define regex pattern to detect where choices start (assuming they start with an 'A.')
		choice_start_pattern = re.compile(r'(?=A[A-Z\s]+\.)')

		# Obtain the question number and its full text
		number = question_item['number']
		full_text = question_item['text']

		# Find where choices begin within the text using the regex pattern
		split_match = choice_start_pattern.search(full_text)
		
		if split_match:
				# Separate the question text from the choices based on the located starting point
				split_index = split_match.start()
				question_text = full_text[:split_index].strip()
				choices_text = full_text[split_index:]

				# Use regex to extract and structure each choice from 'A' to 'E'
				choices_pattern = re.compile(r'([A-E])\s(.*?)\s(?=[A-E]\s|$)', re.DOTALL)
				choices_matches = choices_pattern.findall(choices_text)
				choices = [{'name': m[0], 'label': m[1].strip()} for m in choices_matches]
		else:
				# If no distinct choices are found, assume the entire full_text as the question text
				question_text = full_text
				choices = []

		# Populate the question item with the separate question text and extracted choices
		question_item['text'] = question_text
		question_item['choices'] = choices

		return question_item

# Function to parse questions which include sequential identifiers and corresponding choices
def parse_question_with_choices(question_data):
		# Regex pattern to identify choices denoted by letters A to E followed by a period and space
		choice_pattern = r'([A-E])\.\s*(.+?)(?=(?:\s[A-E]\.)|$)'

		# Grab specific details of the question number and its associated text
		number = question_data.get("number")
		text_with_choices = question_data.get("text")

		# Search and collect all appearances of question choices
		found_choices = re.findall(choice_pattern, text_with_choices)

		# Construct the choices in a structured format for further processing
		choices = [{'letter': match[0], 'text': match[1].strip()} for match in found_choices]

		# If choices aren't identified, return the data without modification
		if not choices:
				return question_data

		# Clean up the choices by removing duplicates and selecting the most appropriate version
		cleaned_choices = clean_choices(choices)

		# Identify where the last choice is within the text so it can be separated from the question stem
		last_choice_index = max(text_with_choices.rfind(f"{choice['letter']}.") for choice in choices)
		text_without_choices = text_with_choices[:last_choice_index].rstrip()

		# Update the original data with now separated question text and the refined choices
		question_data["text"] = text_without_choices
		question_data["choices"] = cleaned_choices

		return question_data

# Parse an individual question item including the cleaning process and extracting choices
def parse_question_item(item):
		# Clean HTML tags and page numbers from the question's text
		cleaned_text = clean_html_and_page_numbers(item['text'])
		
		# Locate the part of the text where choices start, which typically follow the format 'A.', 'B.', etc
		start_of_choices = re.search(r'\b[A-E]\.', cleaned_text)
		if start_of_choices:
				# Separate the text into question content and choices based on the starting point of choices
				choices_text = cleaned_text[start_of_choices.start():]
				question_text = cleaned_text[:start_of_choices.start()].strip()
				# Extract and structure choices from the choices text
				choices = extract_choices(choices_text)
				# Convert and attach the extracted choices to the item dict
				item['choices'] = [{'name': k, 'label': v} for k, v in choices.items()]
		else:
				# If there are no explicit choices, use only the cleaned question text
				question_text = cleaned_text
				item['choices'] = []
		
		# Patterns to identify instructional phrases related to answer selection within the text
		instruction_patterns = ['Choose the correct answer\(s\)\.', 'There are \d+ correct answers to this question\.']
		for pattern in instruction_patterns:
				# Remove such patterns to omit instructions from the final question text
				question_text = re.sub(pattern, '', question_text).strip()
		# Update the item with the finalized question text after cleaning
		item['text'] = question_text
		
		return item


def parse_questions_and_answers(questions, answers_json):
		# Define the pattern to extract questions
		question_pattern = re.compile(r'(\d+)\.(.+?)(?=\d+\.|$)', re.DOTALL)

		# Extract questions using the defined pattern
		questions_matches = question_pattern.findall(questions)
		
		# Prepare a dictionary of answers with question numbers as keys for easier lookup
		answers_dict = {str(item['numero']): item['answers'] for item in answers_json}
		
		# Prepare final list of questions with correct answers
		# Define the parsed questions list
		parsed_questions = []
		
		# Loop through matches to process each one
		for match in questions_matches:
			number, text = match[0], match[1].strip()
				
			# Ensure text is clean before processing
			text = clean_html_and_page_numbers(text)  # Assuming this function exists and is correctly implemented
				
			# Processing items 
			item = separate_question_and_choices({
				"number": number,
				"text": text,
				"choices": []
			})
			# Parse the question item and extract choices
			item = parse_question_with_choices(item)  # This function should extract choices and remove them from 'text'
				
			# The following steps assume that parse_question_item returns an item with 'choices' extracted
			# and 'text' modified to only include the question label
		
			# Check if the current question's number is in the answers_dict
			correct_answers = answers_dict.get(number, [])  # Assuming answers_dict is defined and accessible here
				
			# After extracting the choices, update `valid_answer_count` if needed
			valid_answer_count = len(correct_answers) if correct_answers else 1  # Updated to be more concise
		
			# Create a dictionary for question data
			question_data = {
				"number": number,
				"text": item["text"],  # This should now be just the question label
				"choices": item["choices"],  # Parsed choices are added here
				"correct_answers": correct_answers,
				"valid_answer_count": valid_answer_count
			}
			# Apply cleaning of choices on the data
			question_data['choices'] = clean_choices(question_data['choices'])
			# Append the processed question data to the list
			parsed_questions.append(question_data)
		
		# Return the list of parsed questions
		return parsed_questions

def parse_questions(text):
    """Parses questions from the given text, extracting question labels, answer choices, and page numbers.

    Args:
        text (str): The text to parse.

    Returns:
        list: A list of dictionaries, each representing a parsed question with the following keys:
            - number (str): The question number.
            - text (str): The question label (without answer choices).
            - num_possible_answers (int): The number of correct answers.
            - choices (list): A list of dictionaries, each representing an answer choice with 'name' and 'label' keys.
            - correct_answers (list): A list of correct answer names (e.g., ['A', 'C']).
            - valid (bool): Whether the choice sequence is valid (A, B, C, ...).
            - page (int): The page number where the question is found.
    """

    questions = []
    question_pattern = re.compile(r'(\d+)\.(.+?)(?=^\d+\.|$)', re.DOTALL | re.MULTILINE)
    matches = question_pattern.findall(text)

    for match in matches:
        number, content = match
        num_correct_answers_match = re.search(r'There are (\d+) correct answers to this question', content, re.IGNORECASE)
        num_correct_answers = int(num_correct_answers_match.group(1)) if num_correct_answers_match else 1

        # Remove HTML tags from the question text
        content = re.sub('<br\s*/?>', '', content)

        # Extract page number
        page_number_match = re.search(r'Page (\d+) of', content)
        page_number = int(page_number_match.group(1)) if page_number_match else None

        # Separate question text and choices
        question_choices_split = re.split(r'(A\s.+)$', content, 1, re.DOTALL)
        question_text, choices_text = question_choices_split[0].strip(), question_choices_split[1]

        # Parse choices
        choices = parse_choices(choices_text)

        # Check choice sequence validity
        choice_letters = list(choices.keys())
        valid_sequence = is_valid_choice_sequence(choice_letters)

        questions.append({
            "number": number,
            "text": question_text,
            "num_possible_answers": num_correct_answers,
            "choices": [{"name": k, "label": v} for k, v in choices.items()],
            "correct_answers": [],  # Placeholders for correct answers
            "valid": valid_sequence,
            "page": page_number
        })

    return questions

def is_valid_choice_sequence(choice_keys):
    """Checks if the given choice keys form a valid sequence (A, B, C, ...)."""

    choice_keys = sorted(choice_keys)
    if not choice_keys or any(choice_key not in string.ascii_uppercase for choice_key in choice_keys):
        return False
    first_letter = 'A'
    try:
        last_letter = choice_keys[-1]
        end_index = string.ascii_uppercase.index(last_letter) + 1
        expected_sequence = string.ascii_uppercase[:end_index]
    except ValueError:
        return False
    return choice_keys == list(expected_sequence)

def parse_choices(choices_text):
    """Parses answer choices from the given text."""

    choice_pattern = re.compile(r'([A-E])\s(.+?)(?= [A-F]\s|$)', re.DOTALL)
    choices = {}
    for match in choice_pattern.findall(choices_text):
        letter, text = match
        choices[letter] = text.strip()
    return choices

def parse_choices(choices_text):
    """Parses answer choices from the given text."""

    choice_pattern = re.compile(r'([A-E])\s(.+?)(?= [A-F]\s|$)', re.DOTALL)
    choices = {}
    for match in choice_pattern.findall(choices_text):
        letter, text = match
        choices[letter] = text.strip()
    return choices

def parse_choices(choices_text):
    """Parses answer choices from the given text."""

    choice_pattern = re.compile(r'([A-E])\s(.+?)(?= [A-F]\s|$)', re.DOTALL)
    choices = {}
    for match in choice_pattern.findall(choices_text):
        letter, text = match
        choices[letter] = text.strip()
    return choices

def save_to_json(data, json_file_path):
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    	# Configure logging once at the entry point of the script
		initialize_logging()  # Use the initialize_logging function to configure logging
		
		create_and_clear_directory(output_directory)
		create_and_clear_directory(json_directory)

		try:
				logging.info("Starting extraction…")
				pages = extract_pages(pdf_path)
				# Extract relevant pages for questions and answers (adjusted indexing)
				questions_text = ''.join(pages[:LAST_QUESTION_PAGE])
				answers_text = ''.join(pages[FIRST_ANSWER_PAGE - 1:LAST_ANSWER_PAGE])
				# Save extracted text to files
				questions_file_path = os.path.join(output_directory, "questions.txt")
				answers_file_path = os.path.join(output_directory, "answers.txt")

				with open(questions_file_path, 'w', encoding='utf-8') as f_q:
						f_q.write(questions_text)
				logging.info(f"Questions text saved to {questions_file_path}")

				with open(answers_file_path, 'w', encoding='utf-8') as f_a:
						f_a.write(answers_text)
				logging.info(f"Answers text saved to {answers_file_path}")
	 
				# Clean the answers text file and save to a new file
				cleaned_answers_file_path = os.path.join(output_directory, "answers_cleaned.txt")
				clean_answers_file(answers_file_path, cleaned_answers_file_path)

				# Extract answers from the cleaned text file and serialize to JSON
				json_output = read_file_and_process(cleaned_answers_file_path)
				data = json.loads(json_output)

				# Save the serialized JSON to file
				json_file_path = os.path.join(json_directory, "answers.json")
				with open(json_file_path, 'w', encoding='utf-8') as f_a:
						json.dump(data, f_a, ensure_ascii=False, indent=2)
				logging.info(f"Answers JSON saved to {json_file_path}")
				
				# Parse questions and prepare data structure
				#questions = parse_questions(questions_text)
				#questions_with_answers = parse_questions_and_answers(questions, data)
				questions_with_answers = parse_questions(questions_text)
				# Split questions into batches of 10 and save to separate JSON files
				for i in range(0, len(questions_with_answers), 10):
						batch = questions_with_answers[i:i+10]
						batch_file_path = os.path.join(json_directory, f"questions_{i+1}_{i+10}.json")
						save_to_json(batch, batch_file_path)
						logging.info(f"Questions batch {i+1}-{i+10} saved to {batch_file_path}")
						
		except Exception as e:
				logging.error(f"An error occurred: {e}", exc_info=True)
				raise

if __name__ == "__main__":
		main()