#!/home/tom/pdf_miner_venv/bin/python
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
json_full_name='questionnaire-full.json'
##
## Duplicate file $jsondiir/$json_filename as $json_full_name
## index = load file $json_dir/index.json 
## answers = load file $json_dir/answers.json
## Foreach question aka item , add field answers and page 
## save to json_full_name
def answer_dictionary(json_data):
    answers_dict = {}

    for item in json_data:
        question_number = item.get("numero")
        
        # Initialize an empty list to store answers if they don't exist
        answers_list = item.get("answers", [])
        number_of_answers = item.get("answer_number", 0)

        answers_dict[question_number] = {
            "answers": answers_list,
            "answer_number": number_of_answers
        }

    return answers_dict

def make_index_dictionary(data):
    index_dict = {}
    
    for entry in data:
        question_id = entry["question"]
        page_number = entry["page"]
        
        # Assign the page number to the question ID in the dictionary
        index_dict[question_id] = page_number
        
    return index_dict


# Load the original questionnaire data and parse it into a Python dictionary
with open(os.path.join(json_dir, json_filename), 'r') as original_file:
    data = json.load(original_file)

# Duplicate the file by saving the data you just loaded into json_full_name
with open(os.path.join(json_dir, json_full_name), 'w') as new_file:
    json.dump(data, new_file, indent=4)

# Load the index file and parse it
with open(os.path.join(json_dir, 'index.json'), 'r') as index_file:
    index = json.load(index_file)
index_dictionary = make_index_dictionary(index)

# Load the answers file and parse it
with open(os.path.join(json_dir, 'answers.json'), 'r') as answers_file:
    answers = json.load(answers_file)
answers_dict = answer_dictionary(answers)

# Now update the `data` which contains your questions with additional information
# Now update the `data` which contains your questions with additional information
for item in data:
    question_number = item.get("number")
    if question_number is None:
        continue  # Skip this iteration if 'numero' is missing
    # Assuming that answers_dict provides the correct answers for each question ID
    # Here we add an empty 'answers' list if the question ID does not have associated answers
    item['answers'] = answers_dict[question_number]["answers"]
    item['answer_number'] = answers_dict.get(str(question_number), {}).get("answer_number", 0)
    
    # Add page number from index_dictionary if available
    if question_number in index_dictionary:  # <-- This line was corrected
        item['page'] = index_dictionary[question_number]

with open(os.path.join(json_dir, json_full_name), 'w') as file:
    json.dump(data, file, indent=2)

print(f'File saved as {os.path.join(json_dir, json_full_name)}')

