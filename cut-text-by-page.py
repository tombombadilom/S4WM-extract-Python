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

OUTPUT_FILE_NAME = 'index.json'
QUESTIONS_FILE_NAME = 'questions.txt'

# Data containing page numbers and the first question on each page
pages_to_questions = [

]
# Directories
output_directory = './output'
pages_directory = os.path.join(output_directory, 'pages')
json_directory = './json'
log_directory = './log'

# Path to the PDF file to be processed
pdf_path = 'C_S4EWM_2020 - Extended Warehouse Management with SAP S4HANA.pdf'

# Initialize logging configuration
log_file = 'process.log'  # Log file path

## je veux que tu charges le fichiers ./output/questions.txt 
## Ensuite tu dois le decouper en $LAST_ANSWER_PAGE fichiers
## crée un repertoire dans ./output/pages que tu videras d'abord à chaque execution 
## puis decoupe le fichier ./output/questions.txt  , 
# utilise comme repere de découpe la pagination Page 1 of 83 ou 1 est le numero de la page
# fait tourner une boucle de 1 à $LAST_ANSWER_PAGE et colle le texte de chaque page 
# dans un fichier different et dans le repertoire ./output/pages/.
# page-1.txt , page-2.txt .....

# Ensure the directories exist or create them if they don't
os.makedirs(output_directory, exist_ok=True)
shutil.rmtree(pages_directory, ignore_errors=True)
os.makedirs(pages_directory)
os.makedirs(json_directory, exist_ok=True)
os.makedirs(log_directory, exist_ok=True)

# Set up logging configuration
logging.basicConfig(filename=os.path.join(log_directory, log_file),
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')

# Path to the 'questions.txt' file to be read
questions_file_path = os.path.join(output_directory, QUESTIONS_FILE_NAME)
# Updated OUTPUT_FILE_PATH with json_directory
OUTPUT_FILE_PATH = os.path.join(json_directory, OUTPUT_FILE_NAME)
# Read the contents of the questions.txt file
try:
    with open(questions_file_path, 'r', encoding='utf-8') as file:
        questions_content = file.read()
except FileNotFoundError:
    print(f"Error: The file {questions_file_path} does not exist.")
    exit()

# Define regex pattern for finding page breaks
page_delimiter_pattern = re.compile(r'Page (\d+) of \d+')

# Use the regex pattern to split the content into pages
pages = page_delimiter_pattern.split(questions_content)

# Dictionary to store the mapping from page numbers to their text
page_texts = {}

# List to hold the mapping of question numbers to page numbers
question_to_page_index = []

# Current question number initialization
current_question_number = 1

# Loop over the pages and store the text in a dictionary
# j'attend sur 79 pages l'indexage de 422 questions ....
# à titre d'exemple j'ouvre la page 2
# the first thing i can read is 11. a number followed by a . , it means it's a question number
# If i open page 3 : first thing i read is 16. , same thing than previous
# In conclusion i can say that page 1 goes from question 1 to 10 , page 2 from question 11 to 15 , etc ... .
# Define regex pattern for finding page breaks and question numbers
page_delimiter_pattern = re.compile(r'Page (\d+) of \d+')
pattern = re.compile(r'(\d+)\.')

# Use the regex pattern to split the content into pages
pages = page_delimiter_pattern.split(questions_content)
page_texts = {}  # Dictionary to store the mapping from page numbers to their text

for i in range(1, len(pages), 2):
    page_number = int(pages[i])
    page_text = pages[i + 1].strip()  # Get the text for the current page
    page_texts[page_number] = page_text  # Store the page text in the dictionary

    # Processing question numbers
    matches = pattern.findall(page_text)

    # Write each page's content to individual text files
    for page_number, page_text in sorted(page_texts.items()):
        page_filename = f'page-{page_number}.txt'
        page_filepath = os.path.join(pages_directory, page_filename)
    
    try:
        with open(page_filepath, 'w', encoding='utf-8') as page_file:
            page_file.write(page_text)
            logging.info(f'Written page {page_number} to file {page_filename}')
    except Exception as e:
        logging.error(f'Failed to write page {page_number} to file {page_filename}: {e}')

    # Find all occurrences of question numbers in this page_text
    matches = pattern.findall(page_text)
    if matches:
        # Use the last matched question number as the starting number for the next page
        last_question_num_on_page = int(matches[-1])
        pages_to_questions.append({
            "numero": last_question_num_on_page,
            "page": page_number
        })
        # Prepare the current_question_number for the next iteration
        if page_number < LAST_QUESTION_PAGE:
            current_question_number = last_question_num_on_page + 1

# Additional check to make sure we have at least one page-to-question mapping before continuing
if not pages_to_questions:
    logging.error("No questions found in the provided text. Check your input file and regex.")
    exit(1)

# Write each page's content to individual files
for page_number, page_text in page_texts.items():
    page_filename = f'page-{page_number}.txt'
    page_filepath = os.path.join(pages_directory, page_filename)
    with open(page_filepath, 'w', encoding='utf-8') as page_file:
        page_file.write(page_text)


# Function to create a mapping from questions to pages
def map_questions_to_pages(pages_to_questions, total_questions):
    questions_to_page_index = []
    for i in range(len(pages_to_questions) - 1):
        start_question = pages_to_questions[i]['numero']
        end_question = pages_to_questions[i + 1]['numero'] - 1
        page_number = pages_to_questions[i]['page']

        for question_number in range(start_question, end_question + 1):
            questions_to_page_index.append({
                "question": question_number,
                "page": page_number
            })
        
    # Add the last page
    questions_to_page_index.extend([{
        "question": qn,
        "page": pages_to_questions[-1]['page']
    } for qn in range(pages_to_questions[-1]['numero'], total_questions + 1)])

    return questions_to_page_index

# Remove the existing JSON file if it exists
if os.path.exists(OUTPUT_FILE_NAME):
    os.remove(OUTPUT_FILE_NAME)

# Generate the mapping from questions to pages
questions_to_page_mapping = map_questions_to_pages(pages_to_questions, TOTAL_QUESTIONS)


# Remove the existing JSON file if it exists and the output is valid
if questions_to_page_mapping:
    if os.path.exists(OUTPUT_FILE_PATH):
        os.remove(OUTPUT_FILE_PATH)

    try:
        with open(OUTPUT_FILE_PATH, 'w') as outfile:
            json.dump(questions_to_page_mapping, outfile, indent=2)
            logging.info(f'Successfully wrote the JSON file: {OUTPUT_FILE_PATH}')
    except Exception as e:
        logging.error(f'Failed to write JSON file: {e}')
else:
    logging.error("The questions to page mapping is empty. JSON file will not be created.")




print("Processing complete.")


