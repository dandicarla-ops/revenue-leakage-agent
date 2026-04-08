"""
Extract text from PDF contracts using pdfplumber + OCR fallback.
Handles both native PDFs and scanned image-based PDFs.
Usage: from src.tools.contract_extractor import extract_text_from_pdf
"""

import pdfplumber
import json
import os

# Optional: OCR imports (only loaded if pdfplumber fails)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️  OCR not installed. Install with: pip install pytesseract pillow pdf2image")
    print("    You'll also need Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")

def extract_text_from_pdf_pdfplumber(pdf_path):
    """
    Try to extract text using pdfplumber (fast, for native PDFs).
    Returns text if substantial content found, None otherwise.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            # Only return if we extracted meaningful content (>200 chars)
            if text and len(text.strip()) > 200:
                return text
            
            return None
    except Exception as e:
        print(f"  ⚠️  pdfplumber error: {e}")
        return None

def extract_text_from_pdf_ocr(pdf_path):
    """
    Extract text using OCR (Tesseract) for scanned/image-based PDFs.
    Slower but works on any PDF format.
    """
    if not OCR_AVAILABLE:
        print(f"  ❌ OCR not available. Install pytesseract and Tesseract.")
        return None
    
    try:
        from pdf2image import convert_from_path
        import pytesseract
        
        # Convert PDF to images (300 DPI for better accuracy)
        images = convert_from_path(pdf_path, dpi=300)
        text = ""
        
        for page_num, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            if page_text:
                text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
        
        return text if len(text.strip()) > 200 else None
    except Exception as e:
        print(f"  ❌ OCR error: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """
    Hybrid extraction: Try pdfplumber first (fast), fall back to OCR if needed.
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        str: Full text content of the PDF, or None if extraction failed
    """
    
    # Step 1: Try pdfplumber (fast for native PDFs)
    text = extract_text_from_pdf_pdfplumber(pdf_path)
    if text:
        return text
    
    # Step 2: Fall back to OCR (slower but works on scanned PDFs)
    print(f"  → pdfplumber found minimal text, trying OCR...")
    text = extract_text_from_pdf_ocr(pdf_path)
    if text:
        return text
    
    # Step 3: Both methods failed
    return None

def extract_all_contracts(contracts_folder):
    """
    Extract text from all PDF files in a folder using hybrid method.
    
    Args:
        contracts_folder (str): Path to folder containing PDF contracts
    
    Returns:
        dict: Dictionary with filename as key and extracted text as value
    """
    extracted_data = {}
    
    if not os.path.exists(contracts_folder):
        print(f"❌ Folder not found: {contracts_folder}")
        return extracted_data
    
    pdf_files = [f for f in os.listdir(contracts_folder) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ No PDF files found in {contracts_folder}")
        return extracted_data
    
    print(f"Found {len(pdf_files)} PDF files. Extracting text...\n")
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(contracts_folder, pdf_file)
        print(f"Extracting: {pdf_file}...")
        
        text = extract_text_from_pdf(pdf_path)
        
        if text:
            extracted_data[pdf_file] = text
            char_count = len(text)
            print(f"  ✅ Success ({char_count} characters)\n")
        else:
            print(f"  ❌ Failed - no text extracted\n")
    
    return extracted_data

def save_extracted_text(extracted_data, output_folder="output"):
    """
    Save extracted text to JSON file.
    
    Args:
        extracted_data (dict): Dictionary of extracted text
        output_folder (str): Folder to save output
    """
    os.makedirs(output_folder, exist_ok=True)
    
    output_file = os.path.join(output_folder, "extracted_contracts.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved extracted text to: {output_file}")

if __name__ == "__main__":
    # Test the extraction
    contracts_folder = "data/sample_contracts"
    
    print("=" * 60)
    print("PDF CONTRACT TEXT EXTRACTION (Hybrid: pdfplumber + OCR)")
    print("=" * 60 + "\n")
    
    extracted = extract_all_contracts(contracts_folder)
    
    if extracted:
        save_extracted_text(extracted)
        print(f"\n✅ Extraction complete! {len(extracted)} contracts processed.")
    else:
        print("\n❌ No contracts were extracted.")