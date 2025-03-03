import os
from flask import Flask, request, jsonify
import google.generativeai as genai
import pathlib
from dotenv import load_dotenv
load_dotenv()
# Set up API key
genai.configure(api_key=os.environ["API_KEY"])

app = Flask(__name__)

# Function to process the PDF and extract diagram descriptions
def process_pdf(filepath, figure_no=None):
    # Read the PDF file
    if not filepath.exists():
        raise FileNotFoundError(f"The file {filepath} does not exist.")

    # Define the prompt for extracting diagram descriptions
    if figure_no:
        prompt = f"""The provided PDF contains diagrams and text. Your task is to:
1. Identify the diagram(s) corresponding to figure number(s) {figure_no}.
2. For each identified diagram:
   - Extract all labels (e.g., 1, 2, 3, 4) and their descriptions.
   - Provide a detailed description of the entire figure, explaining what it represents.
3. Format the output for each diagram as a separate paragraph, ensuring that all label numbers are explicitly mentioned in brackets and described.

Example Output:
Figure {figure_no}: This diagram depicts a mechanical device. It consists of a gear (10), a shaft (12), and a casing (14). The gear (10) transfers rotational motion, the shaft (12) transmits power, and the casing (14) provides protection and support to the internal mechanisms.

Please ensure that:
- All label numbers are explicitly mentioned in brackets (e.g., (10), (12), (14)).
- Each label is described clearly in the context of the figure.
- The description of the entire figure is clear and concise.
- Each figure's description is presented in a separate paragraph.
"""
    else:
        prompt = """The provided PDF contains diagrams and text. Your task is to:
1. Identify all diagrams in the PDF.
2. For each diagram:
   - Extract all labels (e.g., 1, 2, 3, 4) and their descriptions.
   - Provide a detailed description of the entire figure, explaining what it represents.
3. Format the output for each diagram as a separate paragraph, ensuring that all label numbers are explicitly mentioned in brackets and described.

Example Output:
Figure 1: This diagram depicts a mechanical device. It consists of a gear (10), a shaft (12), and a casing (14). The gear (10) transfers rotational motion, the shaft (12) transmits power, and the casing (14) provides protection and support to the internal mechanisms.

Figure 2: This diagram illustrates a biomedical apparatus. It includes a sensor (20), a monitoring unit (22), and a display screen (24). The sensor (20) detects physiological signals, the monitoring unit (22) processes the data, and the display screen (24) shows the results in real-time.

Please ensure that:
- All label numbers are explicitly mentioned in brackets (e.g., (10), (12), (14)).
- Each label is described clearly in the context of the figure.
- The description of the entire figure is clear and concise.
- Each figure's description is presented in a separate paragraph.
"""

    # Generate content using the Gemini model
    file = genai.upload_file(filepath)
    model=genai.GenerativeModel("gemini-2.0-flash")
            # Generate content using the prompt
    response = model.generate_content([file, prompt])

    return response.text

@app.route('/extract', methods=['POST'])
def extract_diagrams():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    figure_no = request.form.get('figure_no')

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the file temporarily
    filepath = pathlib.Path(file.filename)
    file.save(filepath)

    try:
        # Process the PDF and get the response
        result = process_pdf(filepath, figure_no)
        return jsonify({"result": result})
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the temporary file
        if filepath.exists():
            filepath.unlink()

if __name__ == "__main__":
    app.run(debug=True)