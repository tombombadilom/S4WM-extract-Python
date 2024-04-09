# S4WM-extract-Python
# Python PDF Questions to JSON Parser

This code snippet is a Python script that extracts questions and answers from a PDF file and processes them into JSON format. 

## Script Workflow

The script performs the following steps:

1. Imports necessary libraries.
2. Defines constants for page ranges and directories.
3. Initializes logging configuration.
4. Defines functions for:
    - Extracting questions to JSON
    - Reading and processing files
    - Cleaning answers file
    - Creating and clearing directories
    - Extracting text from PDF pages
    - Cleaning HTML tags and page numbers
    - Extracting choices from question text
    - Cleaning redundant or less suitable choice texts
    - Separating question and choices
    - Parsing questions with choices
    - Parsing question items
    - Parsing questions and answers
    - Checking if a choice sequence is valid
    - Parsing choices
    - Saving data to JSON
    - The main function
5. Configures logging and creates/clears output directories.
6. Extracts text from relevant pages of the PDF file.
7. Saves extracted text to files.
8. Cleans the answers text file and saves it to a new file.
9. Extracts answers from the cleaned text file and serializes them to JSON.
10. Saves the serialized JSON to a file.
11. Parses questions and prepares the data structure.
12. Saves questions with matched answers to a JSON file.

The main function is called to execute the script.
