import os
import base64
import fitz
import json
import re
import tempfile
import zipfile
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import PyPDF2
from datetime import datetime

app = Flask(__name__, static_folder='templates', static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Load API key from environment
DEFAULT_API_KEY = os.getenv('OPENAI_API_KEY')

client = None

# Document type order preference
DOCUMENT_ORDER = [
    "pre approval",
    "proof of funds",
    "agency disclosure",
    "team disclosure",
    "purchase agreement",
    "addendum",
    "property disclosure",
    "lead paint",
    "lead-based paint",
    "affiliated business",
    "aba disclosure"
]

def initialize_client(api_key_input):
    """Initialize OpenAI client with API key."""
    global client
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key_input)
        return client
    except Exception:
        raise ValueError("API initialization error: Check your OpenAI API key is valid")

def split_pdf(pdf_path):
    """Split PDF into individual pages/documents"""
    documents = []
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            for i in range(num_pages):
                pdf_writer = PyPDF2.PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[i])
                
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'page_{i+1:03d}.pdf')
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                documents.append({
                    'path': output_path,
                    'page_num': i + 1,
                    'filename': f'page_{i+1:03d}.pdf'
                })
    except Exception as e:
        raise Exception(f"PDF splitting failed: {str(e)}")
    
    return documents

def extract_text_from_pdf(pdf_path):
    """Extract text from a single PDF page"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    except:
        return ""

def render_pdf_pages(pdf_path):
    """Render each PDF page to a PNG image for visual document analysis."""
    page_images = []

    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf):
            pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                f"pdf_page_{os.getpid()}_{page_number}.png"
            )
            pix.save(image_path)
            page_images.append(image_path)

    return page_images


def analyze_document(text, filename, image_path=None):
    """Classify a document and extract transaction data in ONE OpenAI request."""
    if not client:
        return "Unknown", {}

    if not text or len(text.strip()) < 10:
        return "Unknown", {}

    try:
        prompt_text = f"""You are a real estate transaction document analyzer.

Analyze this document using BOTH the extracted text and the page image when provided. The page image is authoritative for handwritten information, checkboxes, printed form fields, and values that may have been corrupted during text extraction.

Return ONLY valid JSON in this exact structure:
{{
  "document_type": "one allowed document type",
  "transaction_data": {{
    "closing_date": "",
    "earnest_money_amount": "",
    "purchase_price": "",
    "financing_type": "",
    "buyer_names": "",
    "seller_names": "",
    "property_address": ""
  }}
}}

Allowed document_type values:
- Pre-Approval Letter
- Proof of Funds
- Agency Disclosure
- Team Disclosure
- Purchase Agreement
- Addendum
- Property Disclosure
- Lead Paint Disclosure
- Affiliated Business Arrangement
- Other

Rules:
- Use only information actually present in the document.
- Never guess or invent information.
- Use the entire extracted text provided.
- Also inspect the page image carefully when one is provided.
- For handwritten or visually marked fields, use what is visibly written or selected on the page.
- Purchase price may appear as Purchase Price, Sales Price, Contract Price, or Total Purchase Price.
- Earnest money may appear as Earnest Money, Earnest Money Deposit, Deposit, or EMD.
- Closing date may appear as Closing Date, Date of Closing, or Closing.
- Financing type may appear as Financing, Method of Financing, Loan, Mortgage, Cash, Conventional, FHA, VA, USDA, or similar.
- Buyer names may appear as Buyer, Purchaser, or Purchasers.
- Seller names may appear as Seller, Owner, or Sellers.
- Property address may appear as Property Address, Premises, Property, or the address associated with the transaction.
- If a field is clearly present anywhere in the document or visible in the image, extract it.
- If multiple values appear, choose the value that applies to the transaction represented by this document.
- Leave a transaction_data field as an empty string only when the information cannot be found.
- Return JSON only. No markdown fences. No explanation.

Filename: {filename}

Extracted document text:
{text[:12000]}"""

        content = [
            {
                "type": "input_text",
                "text": prompt_text
            }
        ]

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as image_file:
                image_b64 = base64.b64encode(image_file.read()).decode("utf-8")

            content.append({
                "type": "input_image",
                "image_url": f"data:image/png;base64,{image_b64}"
            })

        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-6-astra"),
            input=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )
        raw = response.output_text.strip()

        # Remove accidental markdown JSON fences if a model adds them.
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)

        document_type = str(result.get("document_type", "Other")).strip() or "Other"
        transaction_data = result.get("transaction_data") or {}

        if not isinstance(transaction_data, dict):
            transaction_data = {}

        cleaned_data = {}
        for key, value in transaction_data.items():
            if value is not None and str(value).strip():
                cleaned_data[str(key).strip()] = str(value).strip()

        return document_type, cleaned_data

    except Exception:
        app.logger.exception("OpenAI document analysis failed for %s", filename)
        raise RuntimeError(
            "OpenAI document analysis failed. Check the Render logs for details."
        )


def classify_document(text, filename):
    """Compatibility wrapper."""
    document_type, _ = analyze_document(text, filename)
    return document_type


def extract_transaction_data(pdf_path, doc_type):
    """Compatibility wrapper."""
    text = extract_text_from_pdf(pdf_path)
    _, transaction_data = analyze_document(text, os.path.basename(pdf_path))
    return transaction_data


def sort_documents(documents_with_types):
    """Sort documents according to the preferred transaction document order."""
    priority_map = {doc_type: idx for idx, doc_type in enumerate(DOCUMENT_ORDER)}

    def get_priority(doc):
        doc_type = str(doc.get("type", "Other")).lower()
        for keyword, priority in priority_map.items():
            if keyword in doc_type:
                return priority
        return len(DOCUMENT_ORDER)

    return sorted(documents_with_types, key=get_priority)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_file(os.path.join('templates', filename))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    # Use API key from form, fall back to environment
    api_key_input = DEFAULT_API_KEY
    if not api_key_input:
        return jsonify({'error': 'OpenAI API key is not configured on the server. Add OPENAI_API_KEY in Render.'}), 400
    
    try:
        initialize_client(api_key_input)
    except Exception as e:
        return jsonify({'error': f'OpenAI initialization error: {str(e)}'}), 401
    
    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Save uploaded file
        filename = secure_filename(pdf_file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(upload_path)
        
        # Split PDF
        documents = split_pdf(upload_path)
        
        # Classify and extract data
        transaction_data = {}
        documents_with_types = []
        
        for i, doc in enumerate(documents):
            text = extract_text_from_pdf(doc['path'])
            page_images = render_pdf_pages(doc['path'])
            image_path = page_images[0] if page_images else None
            doc_type, data = analyze_document(text, doc['filename'], image_path)

            doc['type'] = doc_type
            documents_with_types.append(doc)

            if data:
                for key, value in data.items():
                    if value and value != 'null' and key not in transaction_data:
                        transaction_data[key] = value

        # Sort documents
        sorted_docs = sort_documents(documents_with_types)
        
        # Create output zip
        output_zip = os.path.join(app.config['UPLOAD_FOLDER'], f'organized_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
        with zipfile.ZipFile(output_zip, 'w') as zipf:
            for i, doc in enumerate(sorted_docs):
                # Rename files in order
                doc_type_clean = doc['type'].replace(' ', '_').lower()
                new_filename = f'{i+1:02d}_{doc_type_clean}.pdf'
                zipf.write(doc['path'], arcname=new_filename)
        
        return jsonify({
            'success': True,
            'file': output_zip,
            'transaction_data': transaction_data,
            'documents_count': len(sorted_docs)
        }), 200
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500

@app.route('/download/<path:filepath>')
def download(filepath):
    try:
        return send_file(filepath, as_attachment=True, download_name='organized_pdfs.zip')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)