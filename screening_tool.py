import os
import openai
import pdfplumber
import csv
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
openai.api_key = ""

results = []

def chat_gpt(conversation):
    response = openai.ChatCompletion.create(
        model="gpt-4o-2024-08-06",
        messages=conversation
    )
    return response['choices'][0]['message']['content']

def pdf_to_text(file_path):
    text = ''
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None  # Return None if there's an issue with the file
    return text if text.strip() else None  # Return None if the text is empty

def update_csv(results):
    with open('results.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Resume Name", "Comments", "Suitability"])
        csv_writer.writerows(results)

@app.route('/upload', methods=['GET', 'POST'])
def upload_resume():
    global results
    if request.method == 'POST':
        resume_files = request.files.getlist('file[]')
        job_description = request.form['job_description']

        if not resume_files or not job_description:
            return jsonify({"error": "Please provide resume files and a job description."}), 400

        results = []
        for resume_file in resume_files:
            resume_text = pdf_to_text(resume_file)

            # Skip invalid or empty PDFs
            if resume_text is None:
                continue

            conversation = [
                {"role": "system", "content": "You are a highly experienced recruiter and talent evaluation expert. Your role is to assess candidates' resumes based on specific job descriptions."},
                {"role": "user", "content": f"Evaluate the following resume against the provided job description. Focus on qualifications, experience, and skills relevant to the job requirements. Conclude with one of the following classifications based on how well the candidate matches the job: 'Well Suited', 'Moderately Well Suited', or 'Not Well Suited'.\n\nJob Description: {job_description}\n\nResume: {resume_text}\n\nProvide a detailed assessment followed by the classification."}
            ]

            response = chat_gpt(conversation)

            # Replace newline characters with spaces in the response
            response = response.replace('\n', ' ')

            # Determine the suitability category
            response_lower = response.lower()
            if "not well suited" in response_lower:
                suitability = "Not Well Suited"
            elif "moderately well suited" in response_lower:
                suitability = "Moderately Well Suited"
            else:
                suitability = "Well Suited"

            results.append([resume_file.filename, response, suitability])

        return jsonify({"results": results})
    else:  
        return render_template('upload.html')

@app.route('/download_csv', methods=['GET'])
def download_csv():
    global results
    update_csv(results)
    return send_file('results.csv', as_attachment=True)

@app.route('/')
def index():
    return render_template('upload.html')

if __name__ == '__main__':
    app.run()
