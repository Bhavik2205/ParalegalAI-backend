# file_handler.py
import os
import fitz  # PyMuPDF
import docx
import pytesseract
from PIL import Image
import pandas as pd

UPLOAD_DIR = "uploads"

def create_session_folder(session_id: str) -> str:
    folder_path = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def save_file(file, session_id: str, filename: str) -> str:
    folder = create_session_folder(session_id)
    file_path = os.path.join(folder, filename)
    file.save(file_path)
    return file_path

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with fitz.open(file_path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

def extract_text_from_image(file_path: str) -> str:
    image = Image.open(file_path)
    return pytesseract.image_to_string(image)

def extract_text_from_excel(file_path: str) -> str:
    df = pd.read_excel(file_path)
    return df.to_string(index=False)

def extract_text_from_csv(file_path: str) -> str:
    df = pd.read_csv(file_path)
    return df.to_string(index=False)

def handle_file_upload(file, session_id: str, filename: str) -> dict:
    file_ext = filename.split(".")[-1].lower()
    file_path = save_file(file, session_id, filename)

    extracted_text = ""
    if file_ext == "pdf":
        extracted_text = extract_text_from_pdf(file_path)
    elif file_ext == "docx":
        extracted_text = extract_text_from_docx(file_path)
    elif file_ext in ["xls", "xlsx"]:
        extracted_text = extract_text_from_excel(file_path)
    elif file_ext == "csv":
        extracted_text = extract_text_from_csv(file_path)
    elif file_ext in ["jpg", "jpeg", "png"]:
        extracted_text = extract_text_from_image(file_path)
    else:
        extracted_text = None

    return {
        "status": "success",
        "file_path": file_path,
        "file_type": file_ext,
        "extracted_text": extracted_text,
        "metadata": {"filename": filename}
    }
