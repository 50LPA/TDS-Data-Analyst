import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from openai import OpenAI
import os
import re
import logging
import subprocess
import json
import tempfile
import uuid
import docker
from docker.errors import DockerException
from groq import Groq
from bs4 import BeautifulSoup

app = FastAPI()

'''client = Groq(
    api_key="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"
)'''

client = OpenAI(
    api_key="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",
    base_url="https://api.perplexity.ai"
)

with open("prompt3.txt", "r") as f:
    prompt=f.read()
with open("prompt4.txt", "r") as f:
    prompt_check=f.read()

async def run_python_in_docker(script: str):
    """
    Executes a Python script inside a secure, pre-built Docker container.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        script_name = f"{uuid.uuid4().hex}.py"  # Random unique name
        script_path = os.path.join(temp_dir, script_name)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)
        # 2️⃣ Run it inside Docker
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{temp_dir}:/app:ro",  # mount as read-only
                "code-runner",
                "python3", f"/app/{script_name}"
            ],
            capture_output=True,
            text=True,
            timeout=10  # prevent hanging
        )

        return {"stdout": result.stdout, "stderr": result.stderr}
    
def extract_code(raw: str) -> str:
    lines = raw.strip().splitlines()
    if lines[0].startswith("```python") or lines[0].startswith("```"):
        lines = lines[1:]  # Remove first line (```python)
    if lines[-1] == "```":
        lines = lines[:-1]  # Remove last line (```)
    return "\n".join(lines)

@app.post("/chat")
async def answer_chat(file: UploadFile=File(...)):
    question_bytes= await file.read()
    question_text=question_bytes.decode("utf-8")
    response = client.chat.completions.create(model= "sonar-pro",
                                            messages=[
                                                {"role": "system", "content" : prompt},
                                                {"role": "user", "content" : f"""User Question:{question_text},
                                                Please generate the complete Python script now."""}
                                            ])
    raw=response.choices[0].message.content
    code=extract_code(raw)
    print(code)
    docker_result=await run_python_in_docker(code)
    max_call=2
    i=1
    while i<=max_call:
        if docker_result["stderr"]=="":
            break
        corrected_response = client.chat.completions.create(model= "sonar-pro",
                                                        messages=[{"role":"system", "content":prompt_check},
                                                                {"role":"user","content": f""" Question : {question_text},
                                                                python script: {code},
                                                                Error: {docker_result['stderr']},
                                                                Please return the corrected python script."""}])
        raw_c=corrected_response.choices[0].message.content
        code_c=extract_code(raw_c)
        docker_result=await run_python_in_docker(code_c)
        i+=1
    final_json_output = json.dumps(docker_result["stdout"])
    print(docker_result)
    return final_json_output