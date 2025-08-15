from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import shutil, os, subprocess, uuid, json

# Initialize FastAPI
app = FastAPI()

# Path for uploads and temporary processing
BASE_FOLDER = "uploads"
os.makedirs(BASE_FOLDER, exist_ok=True)

# Paths for LLM prompts (you can also inline them)
FIRST_PROMPT = """
You are a precise data extraction and analysis assistant.
You must only:
1. Generate Python 3 code that loads, scrapes, or reads the raw data needed to answer the user's question.
2. List all external Python libraries that need to be installed (do not list built-in libraries).
3. Extract the main questions the user is asking (without answering them).
...
Output format:
Respond only in valid JSON with this schema:
{
  "code": "...",
  "libraries": ["..."],
  "questions": ["..."]
}
"""
SECOND_PROMPT = """
You are a precise Python code generation assistant.
You must only:
1. Generate Python 3 code that, based on the provided question and metadata, retrieves or processes the data necessary to answer the question.
2. List all external Python libraries that must be installed (exclude built-in libraries).
3. If any images/visualizations are generated, convert them to base64-encoded PNGs and include them in the output JSON.
...
Output schema:
{
  "code": "...",
  "libraries": ["..."]
}
"""

# Utility function to call LLM (replace with Perplexity Sonet executable command)
def call_llm(prompt: str, question_file_path: str):
    """Returns JSON from LLM for given prompt and question file."""
    # Example: assuming your LLM is called via CLI executable `sonet`
    cmd = [
        "sonet",
        "--prompt", prompt,
        "--input_file", question_file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)

# Execute generated Python code safely
def execute_code(code: str, folder: str):
    code_file = os.path.join(folder, "exec_code.py")
    with open(code_file, "w") as f:
        f.write(code)
    # Run code in subprocess
    subprocess.run(["python", code_file], check=True)

@app.post("/answer")
async def answer_question(file: UploadFile = File(...)):
    # Create unique folder for this request
    folder = os.path.join(BASE_FOLDER, str(uuid.uuid4()))
    os.makedirs(folder, exist_ok=True)

    # Save uploaded file
    file_path = os.path.join(folder, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Step 1: call first prompt LLM
    llm_step1_output = call_llm(FIRST_PROMPT, file_path)
    code_step1 = llm_step1_output["code"]
    libraries_step1 = llm_step1_output["libraries"]
    questions = llm_step1_output["questions"]

    # Execute Step 1 code to generate data.csv & metadata
    execute_code(code_step1, folder)

    # Step 2: call second prompt LLM with question & metadata
    llm_step2_output = call_llm(SECOND_PROMPT, file_path)
    code_step2 = llm_step2_output["code"]
    libraries_step2 = llm_step2_output["libraries"]

    # Execute Step 2 code to generate result.json
    execute_code(code_step2, folder)

    # Load result.json to return
    result_file = os.path.join(folder, "result.json")
    with open(result_file) as f:
        result_data = json.load(f)

    # Return JSON response
    return JSONResponse(content=result_data)
