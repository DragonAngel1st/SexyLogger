'''      
                              _|_|_     
 _     _     _     _          (o o)       _     _     _     _     _     _     _     _     _     _   
/ \___/ \___/ \___/ \___--ooO--(_)--Ooo--/ \___/ \___/ \___/ \___/ \___/ \___/ \___/ \___/ \___/ \_
#                                                                                                 #
#  ____       _        _      _      __  __ _                                                     #
# |  _ \ __ _| |_ _ __(_) ___| | __ |  \/  (_)_ __ ___  _ __                                      #
# | |_) / _` | __| '__| |/ __| |/ / | |\/| | | '__/ _ \| '_ \                                     #
# |  __/ (_| | |_| |  | | (__|   <  | |  | | | | | (_) | | | |                                    #
# |_|   \__,_|\__|_|  |_|\___|_|\_\ |_|  |_|_|_|  \___/|_| |_|                                    #
#                                                                                                 # 
#  Date Created  : 2024-10-03                                                                     #
#  Last Updated  : 2024-11-04 10:20:AM                                                            #
#                                                                                                 #
#  Project: AsposePDFExtractor                                                                    #
#                                                                                                 #
#  Description:                                                                                   #
#  --------------------------------------------------------------------------------------------   #
#  This file is a POC for Nextria to extract text from a PDF, translate it using translator model #
#  and reasembles the translated text, in a copy of the pdf, using an LLM in the requested        #
#  language. The current models are loaded/used through the castleguard-sdk library.              #
#  Here an LLM is used to reintegrate the translated fragments into a newPDF while maintaining    #
#  the original formatting.                                                                       #
#                                                                                                 # 
#  License:                                                                                       #
#  --------------------------------------------------------------------------------------------   #
#  This work was done for Nextria Inc. All rights reserved.                                       #
#                                                                                                 #
#  References / Links:                                                                            #
#  --------------------------------------------------------------------------------------------   #
#  - Aspose PDF for Python via .NET documentation : https://docs.aspose.com/pdf/python-net/       #
#  - Aspose PDF for.NET documentation : https://docs.aspose.com/pdf/net/                          #
#  - aspose-pdf repo: https://github.com/aspose-pdf                                               #
#  - location of the repo: https://github.com/nextria-ca/AsposePDFExtractor                       #
#  - castleguard-sdk pipy : https://pypi.org/project/castleguard-sdk/                             #
#                                                                                                 #
###################################################################################################
'''

import asyncio
from pathlib import Path
import aspose.pdf as apdf
import config
from SexyLogger import SexyLogger
from typing import List, Dict
import time
import json
import re
from aspose.pdf.text import TextExtractionOptions, TextAbsorber, TextFragmentAbsorber 

def estimate_tokens(text: str) -> int:  
    """
    Estimate the number of tokens in a text string.
    
    :param text: The input text to be tokenized.
    :return: The estimated token count.
    """
    # Split by whitespace, punctuation, and any special characters
    tokens = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    
    return len(tokens)

def decode_unicode_escapes(text: str) -> str:
    """
    Convert Unicode escape sequences in the text (e.g., \\u00e9) to their actual symbols.
    
    :param text: The input text with Unicode escape sequences.
    :return: The decoded text with correct symbols.
    """
    return text.encode('utf-8').decode('unicode_escape')

class PDFTranslator:
    def __init__(self, input_pdf: Path, output_pdf: Path, config: object, source_lang: str = "en", target_lang: str = "fr"):
        """
        Initialize the PDFTranslator class with input and output PDF paths.
        :param input_pdf: Path to the input PDF.
        :param output_pdf: Path to save the translated PDF.
        :param config: Configuration settings (containing the CastleGuard client).
        :param source_lang: Source language (default is 'en').
        :param target_lang: Target language (default is 'fr').
        """
        self.config = config
        self.input_pdf = input_pdf
        self.output_pdf = output_pdf
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.document = apdf.Document(str(self.input_pdf))
        self.cg = config.cg
        self.logger = SexyLogger(name="my_sexy_logger", log_dir="debug_logs", file_logging=True, console_logging=True)

    async def get_paragraphs_for_page(self, document: apdf.Document, page_number: int) -> List[str]:
        """
        Asynchronously extracts paragraphs from a specific page in the document using ParagraphAbsorber.
        :param document: The Aspose.PDF Document object.
        :param page_number: The page number (1-based index).
        :return: A list of strings, each representing a paragraph's text.
        """
        def extract_paragraphs():
            # Initialize ParagraphAbsorber
            paragraph_absorber = apdf.text.ParagraphAbsorber()

            # Apply ParagraphAbsorber to the entire document
            paragraph_absorber.visit(document)

            # Initialize list to hold paragraph texts
            paragraph_texts = []

            # Iterate through the PageMarkups
            for page_markup in paragraph_absorber.page_markups:
                if page_markup.number == page_number:  # Check for specific page
                    # Loop through sections in the current page
                    for section in page_markup.sections:
                        # Loop through paragraphs in the current section
                        for paragraph in section.paragraphs:
                            paragraph_text = []
                            # Loop through each line in the paragraph
                            for line in paragraph.lines:
                                # Loop through text fragments in each line
                                for fragment in line:
                                    paragraph_text.append(fragment.text)
                            # Join the text fragments in the paragraph and add to list
                            paragraph_texts.append(" ".join(paragraph_text))

            return paragraph_texts

        # Run the synchronous extraction in a separate thread
        return await asyncio.to_thread(extract_paragraphs)

    def preprocess_text(self, text: str) -> str:
        """
        Remove unwanted characters and preprocess text fragments.
        :param text: The text to preprocess.
        :return: Preprocessed text with specified characters removed.
        """
        # Define unwanted characters and clean the text
        unwanted_characters = "|•"
        
        # Remove unwanted characters
        for char in unwanted_characters:
            text = text.replace(char, "")

        # Reduce all whitespace sequences to a single space and strip leading/trailing spaces
        text = ' '.join(text.split()).strip()

        # Return empty string if the text is empty after preprocessing
        return text if text else ""

    def decode_unicode_escapes(text: str) -> str:
        """
        Convert Unicode escape sequences in the text (e.g., \\u00e9) to their actual symbols.
        
        :param text: The input text with Unicode escape sequences.
        :return: The decoded text with correct symbols.
        """
        return text.encode('utf-8').decode('unicode_escape')

    async def extract_text_from_page(self, page: apdf.Page) -> str:
        """
        Asynchronously extract the full text from an Aspose.PDF page object.
        :param page: The Aspose.PDF page object.
        :return: The full text of the page.
        """
        
        extraction_options = TextExtractionOptions(TextExtractionOptions.TextFormattingMode.PURE)
        # Ensure page is an apdf.Page object
        assert isinstance(page, apdf.Page), f"Expected 'page' to be an 'apdf.Page' object, got {type(page)}"
        text_absorber = TextAbsorber(extraction_options)

        page.accept(text_absorber)

        text_to_return = self.preprocess_text(text_absorber.text)

        self.logger.add_log_message(f"Original text for current page:\n{text_to_return}")
        self.logger.log_group_to_box()
        
        return text_to_return

    async def extract_text_fragments_from_page(self, page: apdf.Page) -> Dict:
        """
        Extracts text fragments from a page and returns a dictionary with the page number and a list of processed text fragments.
        :param page: The Aspose.PDF page object.
        :return: A dictionary with page number and list of preprocessed text fragments.
        """
        extraction_options = TextExtractionOptions(TextExtractionOptions.TextFormattingMode.PURE)
        text_fragment_absorber = TextFragmentAbsorber()
        text_fragment_absorber.extraction_options = extraction_options
        page.accept(text_fragment_absorber)
        
        # Initialize an empty list to hold the processed text fragments
        processed_fragments = []
        
        # Iterate over each fragment and add the preprocessed text to the list
        for fragment in text_fragment_absorber.text_fragments:
            # Ensure the fragment text is not None before processing
            if fragment.text:
                processed_text = self.preprocess_text(fragment.text)
                processed_fragments.append(processed_text)
        
        # Return the dictionary with the page number and the list of processed text fragments
        return {
            "page_number": page.number,
            "text_fragments": processed_fragments
        }

    async def translate_page(self, page_text: str, page_number: int) -> str:
        """
        Asynchronously extract the text of a specific page and send it to the translator.
        :param page: The Aspose.PDF page object.
        :param page_number: The page number (for logging purposes).
        :return: The translated text for the specific page.
        """
        # Log original text
        self.logger.add_log_message(
            f"Original text for page {page_number}: {page_text}"
            if page_text else "No text found",
            box_group_name=f"original_text_page_{page_number}"
        )
        self.logger.log_group_to_box(add_to_group=f"original_text_page_{page_number}")

        translated_page_text = self.config.cg.translate_text(
            page_text, source_lang=self.source_lang, target_lang=self.target_lang
        )

        # Log translated text
        self.logger.add_log_message(
            f"Translated text for page {page_number}: {translated_page_text}" if translated_page_text else f"No translated text found for page {page_number}.",
            box_group_name=f"translated_text_page_{page_number}"
        )
        self.logger.log_group_to_box(add_to_group=f"translated_text_page_{page_number}")
        return translated_page_text

    def position_to_dict(self, obj):
        """
        Convert Position objects to a dictionary for JSON serialization.
        """
        if isinstance(obj, apdf.text.Position):
            return {"x_indent": obj.x_indent, "y_indent": obj.y_indent}
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    async def send_page_to_llm(self, page_data: Dict, page_number: int) -> Dict:
        """
        Asynchronously send a page's text and fragments to the LLM for translation.
        :param page_data: The JSON structure of the page.
        :param page_number: The page number (for logging).
        :return: A JSON structure containing the translated data.
        """
        # Convert page_data to a JSON string using the custom serializer
        page_data_json = json.dumps(page_data, sort_keys=True, ensure_ascii=False, indent=4)
        

        self.save_json_to_file(page_data_json, f"page_data_json_{page_number}_data.json")

        prompt = (
            f"You will receive the text content of page {page_number} in a JSON structure. "
            "Your task is to translate the text fragments and return a new JSON structure. "
            "Please translate each 'original_text_fragment' and fill in the 'translated_text_fragment' field. "
            "Ensure that the JSON structure is complete and correctly formatted. "
            "Before sending your response, double-check and revise it to ensure accuracy and completeness. "
            "Do not attempt to translate the text_fragments yourself, only fill in the translated_text_fragment field. "
            "Here is an example of the JSON structure I want you to return:\n\n"
            "{\n"
            '  "page_number": 1,\n'
            '  "text_fragments": [\n'
            '    {"original_text_fragment": "This is a fragment.", "translated_text_fragment": "Ceci est un fragment."},\n'
            '    {"original_text_fragment": "Another fragment.", "translated_text_fragment": "Un autre fragment."}\n'
            "  ]\n"
            "}\n\n"
            "Here is the JSON you need to create the translated JSON structure:\n\n"
            f"{page_data_json}\n\n"
            "Ensure that all fields are included and correctly formatted as per the example above in a valid JSON format."
        )

        max_retries = 2
        chat_id = ""  # Initialize chat_id to an empty string or a valid initial value
        for attempt in range(max_retries + 1):
            self.logger.add_log_message(f"Prompt token count: {estimate_tokens(prompt)}")
            self.logger.add_log_message(f"Attempt {attempt + 1} for page {page_number}. Prompt:\n{prompt}")
            
            # Ensure chat_id is not None
            if chat_id is None:
                chat_id = ""  # or set to a default value expected by the API

            response, chat_id = self.config.cg.chat(prompt, chat_id=chat_id)
            response = decode_unicode_escapes(response)

            self.logger.add_log_message(f"Response token count: {estimate_tokens(response)}")
            self.logger.add_log_message(f"Response for page {page_number}, attempt {attempt + 1}, chat_id: {chat_id}:\n{response}")

            # Try to parse the response as JSON
            try:
                response_data = json.loads(response)
                self.logger.add_log_message(f"Valid JSON received for page {page_number} on attempt {attempt + 1}.")
                self.logger.log_group_to_box(use_contour=False)

                # Save the valid JSON response to a file
                self.save_json_to_file(response_data, f"translated_page_{page_number}.json")

                return response_data
            
            except json.JSONDecodeError:
                self.logger.add_log_message(
                    f"Invalid JSON response received for page {page_number} on attempt {attempt + 1}. Retrying..." if attempt < max_retries else
                    f"Invalid JSON response received for page {page_number} after {max_retries} attempts. Raising exception."
                )
                self.logger.log_group_to_box()

                # Update the prompt for retries
                prompt = "Please correct your JSON response, the structure is either incomplete or wrong."

            # Raise an exception if max retries are reached
            if attempt == max_retries:
                self.logger.add_log_message(message=f"{response}", box_group_name="Raw Error response from LLM")
                self.logger.log_group_to_box(add_to_group= "Raw Error response from LLM", use_contour=False)
                # raise Exception(f"Failed to get a valid JSON response for page {page_number} after {max_retries + 1} attempts.")

        return response

    def jsonify_page_fragments(self, page_number: int, original_page_context: str, translated_page_text: str, original_text_fragments: List[str]) -> Dict:
        """
        Create a JSON structure for a page's text and fragments.
        :param page_number: The page number.
        :param original_page_context: The original full page text.
        :param translated_page_text: The translated full page text.
        :param original_text_fragments: List of original text fragments as strings.
        :return: JSON structure ready to send to LLM.
        """
        return_json = {
            "page_data": {
                "page_number": page_number,
                "page_context": {
                    "original": original_page_context,
                    "translated": translated_page_text
                },
                "text_fragments": [
                    {
                        "original_text_fragment": fragment,
                        "translated_text_fragment": ""  # Placeholder for LLM to fill
                    }
                    for fragment in original_text_fragments
                ]
            }
        }

        # Log the JSON structure for debugging
        # self.logger.add_log_message(f"Token count: {estimate_tokens(json.dumps(return_json, indent=4))}")
        self.logger.add_log_message(f"JSON structure for page {page_number}:\n{json.dumps(return_json, indent=4)}")
        self.logger.log_group_to_box(use_contour=False)

        return return_json

    
    def save_document(self) -> None:
        """
        Save the modified PDF document to the output path.
        """
        self.logger.add_log_message(f"Attempting to save document to {self.output_pdf}...")
        self.logger.log_group_to_box()
        self.document.save(str(self.output_pdf))

    async def reintegrate_translated_fragments(self, reassembled_pages: Dict) -> None:
        """
        Reintegration of the translated fragments into the original PDF, replacing the original fragments.
        :param reassembled_pages: The reassembled structure of translated pages and their fragments.
        """
        for page_number, page_data in reassembled_pages.items():
            page = self.document.pages[page_number]
            absorber = apdf.text.TextFragmentAbsorber()
            page.accept(absorber)

            fragments = absorber.text_fragments
            for fragment, translated_fragment in zip(fragments, page_data["text_fragments"]):
                if "translated_text_fragment" in translated_fragment:
                    fragment.text = translated_fragment["translated_text_fragment"]
                self.logger.add_log_message(f"Reintegrated fragments for page {page_number}.")
                self.logger.log_group_to_box()

    def parse_llm_response(self, llm_response: str, page_number: int) -> Dict:
        """
        Parse the LLM response from a string containing JSON structure into a Python dictionary.
        :param llm_response: The string response from the LLM containing a JSON structure.
        :param page_number: The page number (used for error reporting).
        :return: A Python dictionary parsed from the LLM response.
        """
        # Log the raw LLM response for debugging
        # self.logger.add_log_message(f"Raw LLM response for page {page_number}: {llm_response}")
        # self.logger.log_group_to_box()

        if not llm_response.strip():
            # self.logger.add_log_message(f"LLM response for page {page_number} is empty or invalid.")
            # self.logger.log_group_to_box()
            raise Exception(f"LLM response for page {page_number} is empty or invalid.")

        try:
            translated_page_data = json.loads(llm_response)
        except json.JSONDecodeError as e:
            # self.logger.add_log_message(f"Failed to decode LLM response for page {page_number}: {e}")
            # self.logger.log_group_to_box()
            raise Exception(f"Failed to decode LLM response for page {page_number}: {e}")
        
        # Ensure the returned structure contains 'text_fragments'
        if "text_fragments" not in translated_page_data:
            # self.logger.add_log_message(f"'text_fragments' key missing in LLM response for page {page_number}")
            # self.logger.log_group_to_box()
            raise KeyError(f"'text_fragments' key missing in LLM response for page {page_number}")
        
        return translated_page_data
    
    async def process_page(self, page: apdf.Page, page_number: int) -> None:
        """
        Process a single page: extract text, translate, reassemble fragments, jsonify, and send to LLM.
        """
        # Ensure page is an apdf.Page object
        assert isinstance(page, apdf.Page), f"Expected 'page' to be an 'apdf.Page' object, got {type(page)}"

        # Step 1: Extract full text and fragments asynchronously
        start_time = time.time()
        page_text = await self.extract_text_from_page(page)
        end_time = time.time()
        self.logger.add_log_message(f"Time to extract text for page {page_number}: {end_time - start_time:.2f} seconds")
        
        # Step 2: Extract text fragments
        start_time = time.time()
        original_text_fragments = await self.extract_text_fragments_from_page(page)
        end_time = time.time()
        self.logger.add_log_message(f"Time to extract text and fragments for page {page_number}: {end_time - start_time:.2f} seconds")

        # Step 2.1: Extract paragraphs
        start_time = time.time()
        original_paragraphs = self.get_paragraphs_for_page(self.document, page_number)
        end_time = time.time()
        self.logger.add_log_message(f"Time to extract paragraphs for page {page_number}: {end_time - start_time:.2f} seconds")

        # Step 3: Translate the extracted text asynchronously
        start_time = time.time()
        translated_page_text = await self.translate_page(page_text, page_number)
        end_time = time.time()
        self.logger.add_log_message(f"Time to translate text for page {page_number}: {end_time - start_time:.2f} seconds")

        # Step 4: Combine translated page text and fragments into JSON
        start_time = time.time()
        page_data = self.jsonify_page_fragments(page_number, page_text, translated_page_text, original_text_fragments["text_fragments"])
        end_time = time.time()
        self.logger.add_log_message(f"Time to combine translated page text and fragments into JSON for page {page_number}: {end_time - start_time:.2f} seconds")
        
        # Step 5: Send the JSON structure to LLM for fragment translation and reassembly
        start_time = time.time()
        translated_page_data_str = await self.send_page_to_llm(page_data, page_number)
        translated_page_data = self.parse_llm_response(translated_page_data_str, page_number)  # Parse the LLM response
        end_time = time.time()
        self.logger.add_log_message(f"Time to page_data to the LLM for reassembly of the translated fragments into the original_text_fragment structure for page {page_number}: {end_time - start_time:.2f} seconds")

        # Step 6: Reintegrate the translated fragments back into the PDF using original_text_fragments
        start_time = time.time()
        for fragment, translated_fragment in zip(original_text_fragments["text_fragments"], translated_page_data["text_fragments"]):
            # Check if both 'translated_text_fragment' and 'original_text_fragment' keys are present
            if "translated_text_fragment" in translated_fragment and "original_text_fragment" in translated_fragment:
                # Check if the current fragment's text matches the 'original_text_fragment'
                if fragment["text_fragment"] != translated_fragment["original_text_fragment"]:
                    raise Exception("Original text does not match in the received translation from LLM.")
                # Set the fragment text to the translated fragment
                fragment["text_fragment"] = translated_fragment["translated_text_fragment"]
        end_time = time.time()
        self.logger.add_log_message(f"Time to reintegrate translated fragments for page {page_number}: {end_time - start_time:.2f} seconds")
        
        self.logger.log_group_to_box()

    async def process_translation(self) -> None:
        """
        Main function that coordinates the asynchronous processing of each page, manages extraction,
        translation, reassembly, reintegration, and saving the final document.
        """
        total_pages = len(self.document.pages)  # Assume `self.document.pages` holds the PDF's pages
        
        # Start timing the entire process
        start_time = time.time()

        # List to hold tasks for each page
        tasks = []
        
        # Iterate through the pages and create tasks
        for page_number in range(1, total_pages + 1):  # Use 1-based indexing
            page = self.document.pages[page_number]  # Access the page by index using the PageCollection
            tasks.append(self.process_page(page, page_number))
        
        # Asynchronously gather the results of processing all pages
        await asyncio.gather(*tasks)

        # Measure the time for all pages to be processed
        end_time = time.time()
        self.logger.add_log_message(f"Total time to process {total_pages} pages: {end_time - start_time:.2f} seconds")
        
        # Save the final translated PDF document
        start_time = time.time()
        self.save_document()
        end_time = time.time()
        self.logger.add_log_message(f"Total time to save the document: {end_time - start_time:.2f} seconds")

        # Log the final message
        self.logger.log_group_to_box()

    def save_json_to_file(self, json_data: str, filename: str) -> None:
        """
        Save the JSON data to a file in the main directory.
        :param json_data: The JSON data to save.
        :param filename: The name of the file to save the JSON data to.
        """
        # Define the path to the main directory
        main_directory = Path(__file__).parent

        # Create the full path for the file
        file_path = main_directory / filename

        # Write the JSON data to the file with pretty-printing
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json_file.write(json_data)

        # Log the action
        self.logger.add_log_message(f"JSON data saved to {file_path}")
        self.logger.log_group_to_box()

async def main() -> None:
    sexyOne = SexyLogger(name="my_logger", log_dir="debug_logs", forced_box_width=120)

    input_pdf = config.ASSETS_DIR / "PacStar411.pdf"
    output_pdf_name = f"translated_{input_pdf.stem}.pdf"
    output_pdf = config.ASSETS_DIR / output_pdf_name
    output_docx = config.ASSETS_DIR / "output.docx"

    save_options = apdf.DocSaveOptions()
    save_options.mode = apdf.DocSaveOptions.RecognitionMode.FLOW
    save_options.recognize_bullets = True
    save_options.format = apdf.DocSaveOptions.DocFormat.DOC_X

    # Load the file to be converted
    pfile = apdf.Document(str(input_pdf))
    # Save in different formats
    pfile.save(output_file_name=str(output_docx), options=save_options)

    pdf_translator = PDFTranslator(input_pdf=input_pdf, output_pdf=output_pdf, config=config, source_lang="en", target_lang="fr")
    await pdf_translator.process_translation()


if __name__ == "__main__":
    asyncio.run(main())