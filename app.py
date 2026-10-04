import os
import json
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

def analyze_document(text, filename):
    """Classify a document and extract transaction data in ONE OpenAI request."""
    if not client:
        return "Unknown", {}

    if not text or len(text.strip()) < 10:
        return "Unknown", {}

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-6-astra"),
            input=f"""You are a real estate transaction document analyzer.

Analyze this document and return ONLY valid JSON in this exact structure:
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
- Leave a transaction_data field as an empty string when it is not found.
- Return JSON only. No markdown fences. No explanation.

Filename: {filename}

Document text:
{text[:2500]}"""
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
            doc_type, data = analyze_document(text, doc['filename'])

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