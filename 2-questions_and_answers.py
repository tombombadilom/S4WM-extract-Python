#!/home/tom/pdf_miner_venv/bin/python
# Import necessary libraries
import os
import logging
import shutil
import re
import string
# tqdm library import is unused in the provided code snippet
# from tqdm import tqdm 
from html import unescape
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from io import StringIO
import json

"""
This code snippet is a Python script that extracts questions and answers from a PDF file and processes them into JSON format. 
The pdf has been peviously cut and text extracted page by page 
as a result we have now one text file by page in teh output/pages directory 
output/pages/
  page-10.txt  page-19.txt  page-27.txt  page-35.txt  page-43.txt  page-51.txt  page-5.txt   page-68.txt  page-76.txt
  page-11.txt  page-1.txt   page-28.txt  page-36.txt  page-44.txt  page-52.txt  page-60.txt  page-69.txt  page-77.txt
  page-12.txt  page-20.txt  page-29.txt  page-37.txt  page-45.txt  page-53.txt  page-61.txt  page-6.txt   page-78.txt
  page-13.txt  page-21.txt  page-2.txt   page-38.txt  page-46.txt  page-54.txt  page-62.txt  page-70.txt  page-79.txt
  page-14.txt  page-22.txt  page-30.txt  page-39.txt  page-47.txt  page-55.txt  page-63.txt  page-71.txt  page-7.txt
  page-15.txt  page-23.txt  page-31.txt  page-3.txt   page-48.txt  page-56.txt  page-64.txt  page-72.txt  page-8.txt
  page-16.txt  page-24.txt  page-32.txt  page-40.txt  page-49.txt  page-57.txt  page-65.txt  page-73.txt  page-9.txt
  page-17.txt  page-25.txt  page-33.txt  page-41.txt  page-4.txt   page-58.txt  page-66.txt  page-74.txt
  page-18.txt  page-26.txt  page-34.txt  page-42.txt  page-50.txt  page-59.txt  page-67.txt  page-75.txt

The script performs the following steps:
1. Imports necessary libraries.
2. Defines constants for page ranges and directories.
3. Initializes logging configuration.
4. load all the text pages one by one, parse them and analyse them
5. identify patterns and define and array of objects as a result
6. write one json by page named page-1.json

The main function is called to execute the script.

"""

# Define constants to specify the range of pages for questions and answers
LAST_QUESTION_PAGE = 79
FIRST_ANSWER_PAGE = 80
LAST_ANSWER_PAGE = 83
TOTAL_QUESTIONS = 422

# Directories
output_directory = './output'
pages_directory = os.path.join(output_directory, 'pages')
json_directory = './json'
log_directory = './log'

# Log file path
log_file_path = os.path.join(log_directory, 'process.log')

# 3. Initializes logging configuration.
logging.basicConfig(filename=log_file_path, filemode='w', level=logging.INFO, format='%(levelname)s:%(message)s')

# The provided text appears to be a series of exam or quiz questions related to SAP S/4HANA Extended Warehouse Management (EWM). The structure of the data across the three pages is consistent, with each question formatted in a similar way:

# Question Number and Text: Each item starts with a number followed by the question text. The questions are related to specific functionalities or configurations within SAP EWM.
# Response Options: Following the question text, several response options are listed, labeled with letters (A, B, C, etc.). These options represent possible answers to the question.
# Instruction for the Number of Correct Answers: Many questions include a note indicating how many answers are correct, guiding the respondent on how many options to select.
# The content covers various topics within SAP EWM, such as handling units, storage bin assignments, network definitions, and physical inventory procedures. Each page seems to continue the sequence of questions without any thematic break, suggesting a comprehensive examination or study guide format rather than distinct topics per page.

# Overall, the data is structured to facilitate a multiple-choice or multi-select testing format, focusing on the detailed aspects of warehouse management systems in an SAP environment.
# Based on the content and structure of the provided text, a suitable JSON structure to represent the data from these pages could be as follows:


# {
#   "exam": {
#     "title": "SAP S/4HANA Extended Warehouse Management (EWM)",
#     "questions": [
#       {
#         "number": 5,
#         "text": "EWM can be used with the following releases:",
#         "options": [
#           {"label": "A", "text": "From SAP R/3 4.6C forward with Service Pack 06."},
#           {"label": "B", "text": "Only SAP ECC 6.0 and beyond."},
#           {"label": "C", "text": "Only SAP ECC 5.0 and beyond."},
#           {"label": "D", "text": "From SAP R/3 3.0F forward with Service Pack 06."}
#         ],
#         "correct_answers": ["A", "B", "D"]
#       },
#       {
#         "number": 6,
#         "text": "What transactions in the ERP system can generate EWM-relevant posting changes?",
#         "options": [
#           {"label": "A", "text": "VLMOVE"},
#           {"label": "B", "text": "VA01"},
#           {"label": "C", "text": "MIGO"},
#           {"label": "D", "text": "ME21N"}
#         ],
#         "correct_answers": ["A", "C"]
#       },
#       {
#         "number": 7,
#         "text": "In Labor Management, what document contains all of the relevant data that can be used to compare the planned and actual times?",
#         "options": [
#           {"label": "A", "text": "Planned workload"},
#           {"label": "B", "text": "Tailored measurement services"},
#           {"label": "C", "text": "Performance document"},
#           {"label": "D", "text": "Executed workload"},
#           {"label": "E", "text": "Inbound delivery"}
#         ],
#         "correct_answer": "C"
#       },
#       // Additional questions would follow the same structure
#     ]
#   }
# }

# 5. identify patterns and define an array of objects as a result
# Function to identify patterns and define an array of objects as a result
# Function to identify patterns and define an array of objects as a result
def identify_patterns(text):
    question_pattern = re.compile(r'\d+\.(.*?)<br />')
    option_pattern = re.compile(r'([A-Z])\s*(.*?)<br />')
    correct_answers_pattern = re.compile(r'There are (\d+) correct answers')
    
    question_chunks = question_pattern.split(text)
    identified_data = []
    
    for i in range(1, len(question_chunks), 3):
        try:
            question_number = int(question_chunks[i].strip())
            question_text = question_chunks[i + 1].strip()
            options = [{'label': m.group(1), 'text': m.group(2).strip()} for m in option_pattern.finditer(question_text)]
            correct_answers_match = correct_answers_pattern.search(question_text)
            correct_answers_count = correct_answers_match.group(1) if correct_answers_match else "unknown"
            
            question_data = {
                "number": question_number,
                "text": question_text.split('<br />')[0],
                "options": options,
                "correct_answers_count": correct_answers_count
            }
            identified_data.append(question_data)
            
            # Logging successful parsing
            logging.info(f"Successfully parsed question number: {question_number}")
        except ValueError as e:
            logging.error(f"ValueError encountered: {e} - Data: {question_chunks[i]}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error: {e} - Data: {question_chunks[i]}")
            continue
    
    return identified_data

def process_pages():
    for page_number in range(1, LAST_QUESTION_PAGE + 1):
        txt_path = os.path.join(pages_directory, f'page-{page_number}.txt')
        
        # Check if text file exists
        if not os.path.exists(txt_path):
            logging.warning(f"Text file does not exist: {txt_path}")
            continue
        
        with open(txt_path, 'r') as file:
            text_content = file.read()
        
        # Check if text content is empty
        if text_content.strip() == '':
            logging.warning(f"Text file is empty: {txt_path}")
            continue
        
        data = identify_patterns(text_content)
        if not data:
            logging.warning(f"No data identified in file: {txt_path}")
            continue
        
        json_filename = f'page-{page_number}.json'
        
        # Reset JSON file if it already exists
        json_path = os.path.join(json_directory, json_filename)
        with open(json_path, 'w+') as json_file:
            json.dump(data, json_file, indent=4)
        
        # Logging processed files
        logging.info(f'Processed {txt_path} into {json_filename}')

if __name__ == "__main__":
    process_pages()