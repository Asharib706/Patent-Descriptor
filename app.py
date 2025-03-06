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
1. First, identify the diagram(s) corresponding to figure number(s) {figure_no} and provide a brief description of each diagram to confirm identification.
2. For each identified diagram:
   - Extract all labels (e.g., 1, 2, 3, 4) and their descriptions.
   - Provide a detailed description of the entire figure, explaining what it represents in a paragraph form. Ensure that all label numbers are explicitly mentioned in brackets (e.g., (10), (12), (14)) and describe how the labeled components are connected to each other.
3. Format the output as a JSON object with the following structure:
   {{
     "brief_description": "Figure {figure_no}: Brief description of the figure/n...(More figure breif description according to the figure numbers)",
     "detailed_description": "Figure {figure_no}: Detailed description of the figure with labels and their connections./n...(More figure breif description according to the figure numbers)"
   }}

Example Output:
{{
  "brief_description": "Figure {figure_no}: This diagram depicts a mechanical device./n...(More figure breif description according to the figure numbers)",
  "detailed_description": "Figure {figure_no}: The diagram shows a mechanical device consisting of a gear (10), a shaft (12), and a casing (14). The gear (10) transfers rotational motion to the shaft (12), which transmits power. The casing (14) provides protection and support to the internal mechanisms, ensuring smooth operation./n...(More figure breif description according to the figure numbers)"
}}
"""
    else:
        prompt = """The provided PDF contains diagrams and text. Your task is to:
1. First, identify all diagrams in the PDF and provide a brief description of each diagram to confirm identification.
2. For each diagram:
   - Extract all labels (e.g., 1, 2, 3, 4) and their descriptions.
   - Provide a detailed description of the entire figure, explaining what it represents in a paragraph form. Ensure that all label numbers are explicitly mentioned in brackets (e.g., (10), (12), (14)) and describe how the labeled components are connected to each other.
3. Format the output as a JSON object with the following structure:
   {{
     "brief_description": "Figure 1: Brief description of the figure\\nFigure 2: Brief description of the figure\\n...",
     "detailed_description": "Figure 1: Detailed description of the figure with labels and their connections.\\nFigure 2: Detailed description of the figure with labels and their connections.\\n..."
   }}

Example Output:
{{
  "brief_description": "Figure 1: This diagram depicts a mechanical device.\\nFigure 2: This diagram illustrates a biomedical apparatus.",
  "detailed_description": "Figure 1: The diagram shows a mechanical device consisting of a gear (10), a shaft (12), and a casing (14). The gear (10) transfers rotational motion to the shaft (12), which transmits power. The casing (14) provides protection and support to the internal mechanisms, ensuring smooth operation.\\nFigure 2: The diagram illustrates a biomedical apparatus with a sensor (20) that detects physiological signals, a monitoring unit (22) that processes the data, and a display screen (24) that shows the results in real-time. The sensor (20) sends data to the monitoring unit (22), which analyzes and displays the results on the screen (24)."
}}
"""

    # Generate content using the Gemini model
    file = genai.upload_file(filepath)
    model = genai.GenerativeModel("gemini-2.0-flash")
    # Generate content using the prompt
    response = model.generate_content([file, prompt])

    # Parse the response text as JSON
    try:
        import json
        result = response.text
        start_index = result.find('{')
        end_index = result.rfind('}') + 1
        cleaned_result = result[start_index:end_index]

        response_json = json.loads(cleaned_result)

        # Check if the response is already in the desired format
        if isinstance(response_json, dict) and all(
            key in response_json for key in ["brief_description", "detailed_description"]
        ):
            # If the response is already in the desired format, return it as is
            return response_json
        else:
            # If not, transform the response into the desired format
            brief_descriptions = []
            detailed_descriptions = []

            if isinstance(response_json, dict):
                for key, value in response_json.items():
                    if isinstance(value, dict):
                        brief_descriptions.append(value.get("brief_description", ""))
                        detailed_descriptions.append(value.get("detailed_description", ""))

            # Combine descriptions into single strings separated by newlines
            final_output = {
                "brief_description": "\n".join(brief_descriptions),
                "detailed_description": "\n".join(detailed_descriptions)
            }
            return final_output
    except json.JSONDecodeError:
        raise ValueError("The model's response could not be parsed as JSON.")

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
        return jsonify(result)  # Return the JSON directly
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up the temporary file
        if filepath.exists():
            filepath.unlink()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

