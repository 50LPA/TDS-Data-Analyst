from openai import OpenAI
from fastapi import FastAPI, File, UploadFile
import os
import uuid
import subprocess
import json
from fastapi.middleware.cors import CORSMiddleware
import shutil
from typing import List
app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],       # Or specify ["https://example.com"]
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],)

client = OpenAI(
api_key=os.getenv("PERP_API_KEY"),
base_url="https://api.perplexity.ai"
)

'''client = genai.Client(
    api_key=os.getenv("GENAI_API_KEY")
)'''
with open("prompt3.txt", "r") as f:
    prompts = f.read()

with open("prompt4.txt", "r") as f:
    prompta = f.read()

def extract_json(file):
    lines = file.splitlines()
    json_str = "\n".join(lines[1:-1])

    # Parse JSON
    data = json.loads(json_str)
    return data

def code_exec(code, requirements):

    script_name = f"{uuid.uuid4().hex}.py"  # Random unique name
    with open(f"uploads/{script_name}", "w", encoding="utf-8") as f:
        f.write(code)

    req_file = None
    if requirements:
        req_file = "temp_requirements.txt"
        with open(f"uploads/{req_file}", "w", encoding="utf-8") as f:
            f.write(requirements)
    try:
        exec("pip install -r uploads/temp_requirements.txt")
    except:
        pass
    result = subprocess.run(f"python uploads/{script_name}", shell=True, capture_output=True, text=True)

    return {"stdout": result.stdout, "stderr": result.stderr}
@app.post("/answer")
async def answer_chat(files: List[UploadFile] = File(...)):
    folder = "uploads"
    direct=subprocess.run("mkdir -p uploads", shell=True, capture_output=True, text=True)
    results = []
    for file in files:
        contents = await file.read()
        # You can save the file or process it
        with open(f"uploads/{file.filename}", "wb") as f:
            f.write(contents)
        results.append(file.filename)
    with open(f"{folder}/question.txt", "r") as f:
        question_text=f.read()
    response = client.chat.completions.create(model= "sonar-pro",
                                        messages=[{"role": "system", "content" : prompts},
                                                    {"role": "user", "content": f"""question: {question_text},
                                                     "uploaded_files": {",".join(results)},
                                                    Generate Python code that collects the data needed for the question, saves it to {folder}/data.csv, and generates {folder}/metadata.txt with the required metadata. Do not answer the question — only collect the data and metadata. """
                                                    }])

    '''response = client.models.generate_content(
  model='gemini-2.5-flash',
  contents=f"""System_prompt: {prompts},
  User Question: {question_text},
  Uploaded Files: {','.join(results)},
  Generate Python code that collects the data needed for the question, saves it to {folder}/data.csv, and generates {folder}/metadata.txt with the required metadata. Do not answer the question — only collect the data and metadata. """
)'''
    result=json.loads(response.choices[0].message.content)
    #result=extract_json(response.text)
    code = result["code"]
    print(code)
    requirements = ",".join(result["libraries"])
    questions = "\n".join(result["questions"])
    exec_result = code_exec(code, requirements)
    response2 = client.chat.completions.create(model= "sonar-pro",
                                    messages=[{"role": "system", "content" : prompta},
                                                {"role": "user", "content": f"""raw_question: {question_text},
                                                interpreted question: {questions}
                                                """
                                                }])
    
    '''response2 = client.models.generate_content(
  model='gemini-2.5-flash',
  contents=f"""System_prompt: {prompts},
  raw_question: {question_text},
  interpreted question: {questions}"""
)'''
    result2=json.loads(response2.choices[0].message.content)
    #result2 = extract_json(response2.text)
    code2 = result2["code"]
    print(code2)
    requirements2 = ",".join(result2["libraries"])
    exec_result2 = code_exec(code2, requirements2)

    # Path to your JSON file
    file_path = os.path.join(".", "uploads", "result.json")


    # Open and load the JSON file
    with open(file_path, "r", encoding="utf-8") as f:
        answers = json.load(f)  # This converts JSON → Python dict/list
    shutil.rmtree(folder, ignore_errors=True)  # Clean up the uploads folder
    return answers
