#!/home/tom/pdf_miner_venv/bin/python
import re
import json
import shutil
import os
import logging
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from io import StringIO

# Define paths
output_directory = './output'
json_directory = './json'
pdf_path = 'C_S4EWM_2020 - Extended Warehouse Management with SAP S4HANA.pdf'
log_file = 'process.log'

# Initialize logging
def initialize_logging():
    if os.path.exists(log_file):
        os.remove(log_file)
    logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

def extract_pages(pdf_path):
    text_content = []
    resource_manager = PDFResourceManager()
    with open(pdf_path, 'rb') as f:
        for page in PDFPage.get_pages(f):
            outfp = StringIO()
            device = TextConverter(resource_manager, outfp)
            interpreter = PDFPageInterpreter(resource_manager, device)
            interpreter.process_page(page)
            text_content.append(outfp.getvalue())
            # It's important to close the device after each page to avoid memory issues
            device.close()
    return text_content

def parse_questions_and_answers(text):
    # Patterns to extract questions and answers
    question_pattern = re.compile(r'(\d+)\.\s+(.+?)(?=\d+\.\s|$)', re.DOTALL)
    answer_pattern = re.compile(r'([A-E])\s(.+?)(?= [A-E]\s|$)', re.DOTALL)

    questions = []
    
    matches = question_pattern.findall(text)
    if not matches:
        logging.warning("No questions were found in the text.")
        
    for number, content in matches:
        content = re.sub('<br\s*/?>', '', content).strip()
        num_possible_answers = 1
        num_correct_answers_match = re.search(r'There are (\d+) correct answers to this question', content)
        if num_correct_answers_match:
            num_possible_answers = int(num_correct_answers_match.group(1))

        choices_matches = answer_pattern.findall(content)
        if not choices_matches:
            logging.warning(f"No choices found for question {number}.")
            
        choices = {match[0]: match[1].strip() for match in choices_matches}
        
        valid_sequence = all(ord(choices[i][0]) - ord(choices[i-1][0]) == 1 for i in range(1, len(choices)))

        question_data = {
            "number": number.strip(),
            "text": content.split('A')[0].strip(),
            "num_possible_answers": num_possible_answers,
            "choices": choices,
            "correct_answers": [],
            "valid": valid_sequence
        }
        questions.append(question_data)
    
    return questions

def save_to_json(data, json_file_path):
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    initialize_logging()
    
    # Create or clear the directories
    for directory in [output_directory, json_directory]:
        if os.path.exists(directory):
            logging.info(f"Clearing directory: {directory}")
            shutil.rmtree(directory)
        os.makedirs(directory)

    try:
        logging.info("Starting extraction...")
        extracted_text = ''.join(extract_pages(pdf_path))  # Join all pages into a single string
        
        if not extracted_text.strip():
            logging.error("The extracted text from the PDF is empty.")
            return
        
        parsed_data = parse_questions_and_answers(extracted_text)  # Parse the string to obtain the structured data

        if not parsed_data:
            logging.error("No data was parsed from the text.")
            return

        # Save the structured data to a JSON file
        json_file_path = os.path.join(json_directory, "questions_with_answers.json")
        save_to_json(parsed_data, json_file_path)
        logging.info("Data extraction complete.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
