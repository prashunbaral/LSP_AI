# main.py
import os
import csv
import re
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import requests

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini API setup
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": GEMINI_API_KEY
}

# Load essay
with open("essay.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Split into paragraphs
paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

# Prompt Template
PROMPT_TEMPLATE = """
Extract the following details from the paragraph below:
- Company Name
- Founding Date in YYYY-MM-DD format (assume 01-01 if only year is given, and 1st of the month if only month+year is given)
- List of founders in Python list format like ["Founder 1", "Founder 2"]

Return in this exact format:
Company: <Company Name>
Date: <YYYY-MM-DD>
Founders: [<founder1>, <founder2>, ...]

Paragraph:
{paragraph}
"""

# Function to parse LLM output
def parse_output(output: str):
    try:
        name = re.search(r'Company:\s*(.+)', output).group(1).strip()
        date = re.search(r'Date:\s*(.+)', output).group(1).strip()
        founders_raw = re.search(r'Founders:\s*(\[.+\])', output).group(1).strip()
        founders = eval(founders_raw)

        # Normalize incomplete dates
        parts = date.split('-')
        if len(parts) == 1:
            date = f"{parts[0]}-01-01"
        elif len(parts) == 2:
            date = f"{parts[0]}-{parts[1]}-01"

        return {
            "company_name": name,
            "founding_date": date,
            "founders": founders
        }
    except Exception as e:
        print("⚠️ Failed to parse output:\n", output)
        return None

# Process each paragraph
results = []
skipped = 0
company_keywords = ["founded", "established", "launched"]
for para in paragraphs:
    # Only process paragraphs likely to contain company info
    if not any(kw in para.lower() for kw in company_keywords):
        skipped += 1
        continue
    prompt = PROMPT_TEMPLATE.format(paragraph=para)
    response = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]})
    try:
        llm_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("⚠️ Failed to get LLM response for paragraph:", para)
        print("Response:", response.text)
        continue
    parsed = parse_output(llm_text)
    if parsed:
        results.append(parsed)

# Export to CSV
if results:
    df = pd.DataFrame(results)
    df.index += 1
    df.insert(0, "S.N.", df.index)
    df["founders"] = df["founders"].apply(lambda x: str(x))
    df.to_csv("company_info.csv", index=False)
    print(f"✅ Extraction complete. CSV saved as company_info.csv. Skipped {skipped} non-company paragraphs.")
else:
    print("❌ No results to save.")
    print(f"Skipped {skipped} non-company paragraphs.")
