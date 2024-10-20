import re
import fitz
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from PIL import Image
import pytesseract
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
import uvicorn
from fastapi.security.api_key import APIKeyHeader

app = FastAPI()
load_dotenv()

# Setting up Tesseract
# pytesseract.pytesseract.tesseract_cmd = os.getenv('Tesseract')
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

api_keys = os.getenv('API_KEYS') 
# print(api_keys)
api_key_header = APIKeyHeader(name='X_api_key')
if api_keys:
    valid_api_keys = api_keys.split(",")
else:
    valid_api_keys = []

# Function to validate the API key
def get_api_key(api_key: str):
    if api_key not in valid_api_keys:
        print(api_key)
        raise HTTPException(
            status_code=403,
            detail="Could not validate API key",
        )


# Define a function to extract text from a single page of the PDF
def extract_text_from_page(page):
    # Extract text from a specific page
    return page.get_text("text")


# Define a function to extract codes based on the fixed pattern
def extract_codes_from_text(text):
    # Regex pattern for codes like AC1-21-02-15-3, AC1-21-02-15-12, etc.
    pattern = r'[A-Z]{2}\d-\d{2}-\d{2}-\d{1,2}-\d{1,2}'
    # pattern = r'\*\s*\|\|\|\s*([A-Z]{2}\d-\d{2}-\d{2}-\d{1,2}-\d{1,2})\s*\|\|\|\s*\*'
    codes = re.findall(pattern, text)
    return codes


# extracting codes using ocr
def extract_codes_from_image(page):
    pix = page.get_pixmap()  
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(img)  
    return text


# function to check if the pdf has images or text
def check_pdf (doc):
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        if page.get_text("text").strip(): 
            return False
    return True

# API route 
@app.post('/extract')
async def extract(file : UploadFile = File(...), api_key: str=Header(..., alias="X_api_key")):
    get_api_key(api_key)
    temp_pdf = 'temp.pdf'
    with open(temp_pdf, "wb") as f:
        content =  await file.read()
        f.write(content)

    # Open the PDF document
    doc = fitz.open(temp_pdf)


    # Empty list to collect all the codes along with page nos
    codes_with_page_no = []

    contains_image = check_pdf(doc)

    # Loop through each page in the PDF
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)

        if contains_image:
            # print('image')
            text = extract_codes_from_image(page)
            # print(text)
        else:    
        # Extract text from the current page
            # print('text')
            text = extract_text_from_page(page)
        # Extract codes from the current page's text
        codes = extract_codes_from_text(text)
        code = codes[0] if codes else None
        # print (code)
        # Print the result for each page
        if code:
            parts = code.split('-')
            certificate_id = parts[0]  
            document_id = parts[1]        
            sequence = parts[-3] 
            page_number = parts[-1]   
            total_pages = parts[-2]       
            
            codes_with_page_no.append({
                "certificate_id": certificate_id,
                "document_id": document_id,
                "sequence": sequence,
                "total_pages": total_pages,
                "page_number": page_number
                })
        else:
            # Pages with no codes found
            codes_with_page_no.append({
                "certificate_id": None,
                "document_id": None,
                "sequence": None,
                "total_pages": None,
                "page_number": None
            })


    # closing the pdf
    doc.close()

    # Clean up the temporary file
    os.remove(temp_pdf)   

    if codes_with_page_no:
        return JSONResponse(content={"extracted_data": codes_with_page_no})
    else:
        return {'message' : 'NO CODES FOUND'}

if __name__=='__main__' :
    uvicorn.run(app, host = '127.0.0.1', port = 8000)