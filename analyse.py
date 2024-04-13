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
pages_directory = os.path.join(output_directory, 'pages')
json_directory = './json'
log_directory = './log'
JSON_FILE='questionnaire.json'

# Log file path
log_file_path = os.path.join(log_directory, 'process.log')

# 3. Initializes logging configuration.
logging.basicConfig(filename=log_file_path, filemode='w', level=logging.INFO, format='%(levelname)s:%(message)s')

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to extract questions from text using a regex pattern
def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to extract questions from text using a regex pattern
def extract_questions(text):
    # Modify the pattern to match question numbers followed by text without using look-behind
    question_pattern = re.compile(r'(\d{1,3})\.\s*([^\d]+?)(?=(?:\s*\d{1,3}\.|$))', re.DOTALL)
    questions = question_pattern.findall(text)
    return questions

# Function to analyze each page
def analyze_page(file_path):
    # Extract questions from the provided text content
    questions = extract_questions(read_file(file_path))
    # Process each extracted question to build question data
    question_data_list = [extract_question_data(question[0], question[1].strip()) for question in questions]
    return question_data_list

def extract_question_data(number,text):
    # Define the dictionary structure as required
    question_data = {
        "number": None,
        "text": "",
        "label": "",
        "choices": [],
        "answers": [],  
        "valid": True, 
        "answer_number": None,
        "type": "radio"  # Default type
    }

    # Regular expression pattern to capture variations of "There are X correct answers"
    correct_answers_pattern = re.compile(r'There\s*are\s*(\d+)\s*correct\s*answers?', re.IGNORECASE)
    
    # Attempt to find the pattern in the provided text
    match = correct_answers_pattern.search(text)
    if not match:
        question_data["valid"] = False
        return question_data
    
    answer_number = int(match.group(1))
    question_data["answer_number"] = answer_number
    question_data["type"] = "checkbox" if answer_number > 1 else "radio"

    # Extract the label and choices from the text
    # Assuming that the number of the question and the actual text of the question are also present before the pattern
    start_of_choices = match.end()
    question_parts = text[:start_of_choices].strip().split('.', 1) # Split only on the first dot
    if len(question_parts) == 2:
        question_data["number"] = int(question_parts[0])
        question_data["text"] = question_parts[1].strip()
        question_data["label"] = question_data["text"]

    # Getting the choices list after the correct answers pattern
    choices_text = text[start_of_choices:].strip()
    choice_pattern = re.compile(r'\(([A-D])\)\s*([^,)]+)')
    raw_choices = choice_pattern.findall(choices_text)
    
    # Populate choices and corresponding answers
    for choice in raw_choices:
        question_data["choices"].append({
            "label": choice[0],
            "text": choice[1].strip()
        })
        question_data["answers"].append(choice[0])

    return question_data

# Function to parse all .txt page files corresponding to the question numbers
# Function to parse all .txt page files corresponding to the question numbers
def parse_pages(directory):
    json_objects = []
    for question_num in range(1, LAST_QUESTION_PAGE + 1):
        filename = f"page-{question_num}.txt"
        file_path = os.path.join(directory, filename)

        if os.path.isfile(file_path):
            page_question_data = analyze_page(file_path)  # This function will return a list of questions
            
            if page_question_data:
                json_objects.extend(page_question_data)
        else:
            logging.warning(f"Page {filename} does not exist")

    return json_objects

def main():
    logging.info("Parsing .txt pages and generating JSON")
    try:
        # Ensure json directory exists
        if not os.path.exists(json_directory):
            os.makedirs(json_directory)

        # Parse all .txt pages and generate JSON array of objects
        json_data = parse_pages(pages_directory)

        # Save the resulting JSON data into a file
        with open(os.path.join(json_directory, JSON_FILE), 'w', encoding='utf-8') as outfile:
            json.dump(json_data, outfile, ensure_ascii=False, indent=4)
            logging.info("Successfully saved JSON data to file")

    except Exception as e:
        logging.error(f"An error occurred during parsing: {e}")

if __name__ == '__main__':
    main()