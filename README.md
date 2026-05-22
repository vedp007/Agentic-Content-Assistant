# Agentic Content Assistant

An agentic multimodal assistant built with **FastAPI** and **React**. The application accepts text, images, PDFs, audio files, and YouTube URLs, extracts usable content, detects the user's intent, plans the workflow, and returns a text-only answer with extracted text, execution plan, logs, and cost metadata.

This project was built for the DSAI agentic AI assignment.

## Key Features

- Text chat interface with file upload support.
- PDF parsing with `pypdf`.
- Scanned PDF OCR fallback using `pdf2image` + `pytesseract` when optional dependencies are installed.
- Image OCR using `pytesseract`.
- Audio transcription using Whisper + `ffmpeg`.
- YouTube transcript fetching using `youtube-transcript-api`.
- Intent detection for:
  - summarization
  - sentiment analysis
  - code explanation
  - action-item extraction
  - text extraction
  - YouTube transcript handling
  - conversational answering
- Mandatory follow-up question when the user goal is unclear.
- Planner/executor orchestration with readable plan steps.
- Logs and fallback messages for each run.
- Assignment-compliant summaries:

```text
1-line summary:
...

3 bullets:
- ...
- ...
- ...

5-sentence summary:
...
```

- Optional local LLM support through Ollama.
- Heuristic fallback tools when Ollama or optional processing tools are unavailable.
- React chat UI showing final output, extracted text, plan, logs, and cost estimate.
- Code preview iframe for generated HTML/CSS/JS snippets.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, Pydantic |
| Frontend | React, Vite, Axios |
| PDF parsing | pypdf |
| Image OCR | pytesseract, Pillow, Tesseract OCR |
| Scanned PDF OCR | pdf2image, Poppler, pytesseract |
| Audio transcription | openai-whisper, ffmpeg |
| YouTube transcripts | youtube-transcript-api |
| Local LLM | Ollama with `llama3.2:3b` |
| Tests | Python unittest, ESLint, Vite build |

## Architecture

```text
React Chat UI
    |
FastAPI /chat
    |
Input Router
    |
Extraction Services
    |-- Text
    |-- PDF parser / OCR fallback
    |-- Image OCR
    |-- Audio transcription
    |-- YouTube transcript
    |
Intent Agent
    |
Planner Agent
    |
Tool Executor
    |
Text Response + Extracted Text + Plan + Logs + Metadata
```

Detailed diagram: [docs/architecture.md](docs/architecture.md)

## Project Structure

```text
backend/
  app/
    agents/          # orchestrator, intent agent, planner, executor
    routes/          # FastAPI routes
    services/        # PDF, OCR, audio, YouTube, LLM, cost, text tools
    models/          # Pydantic schemas
    tests/           # backend unit tests
frontend/
  src/
    App.jsx          # main chat UI
    App.css          # UI styling
docs/
  architecture.md
  current-overview.md
```

## Setup

### 1. Clone the repository

```bash
git clone <your-github-repo-url>
cd agentic-assignment
```

### 2. Backend setup

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

For full image, scanned PDF, audio, and YouTube support:

```powershell
pip install -r optional-requirements.txt
```

System tools needed for full support:

- **Tesseract OCR** for image OCR.
- **Poppler** for scanned PDF OCR.
- **ffmpeg** for audio transcription.

### 3. Optional Ollama setup

The app works without Ollama by using heuristic fallbacks. For better natural-language responses, install Ollama and run:

```powershell
ollama pull llama3.2:3b
ollama run llama3.2:3b
```

Optional environment variables:

```powershell
set OLLAMA_MODEL=llama3.2:3b
set OLLAMA_URL=http://127.0.0.1:11434
```

### 4. Frontend setup

```powershell
cd frontend
npm install
```

## Running the Project

Start the backend:

```powershell
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## API Usage

### `POST /chat`

JSON request:

```json
{
  "message": "Summarize this: The backend supports PDF upload and OCR fallback."
}
```

Multipart request:

```text
message: summarize this file
file: <PDF/image/audio file>
context: optional previous extracted text
```

Response includes:

- `response`: final text-only answer
- `extracted_text`: extracted/transcribed content
- `intent`: detected task and confidence
- `plan`: workflow steps
- `logs`: execution notes and fallback messages
- `metadata`: cost estimate, extraction confidence, duration, page count, and other source metadata

## Demo Test Cases

### 1. Audio lecture

Upload a `.wav`, `.mp3`, or `.m4a` file and enter:

```text
summarize this audio
```

Expected output:

- transcript shown under extracted text
- 1-line summary
- 3 bullet points
- 5-sentence summary
- duration metadata when available

### 2. PDF meeting notes

Create/upload a PDF containing:

```text
Meeting Notes

Action Items:
Owner: Ravi will finish the API error handling by Friday.
Owner: Maya should test PDF and image uploads by Monday.
Owner: Ved needs to update the README with demo steps.
Next step: Prepare the final demo walkthrough.
```

Prompt:

```text
What are the action items?
```

Expected output:

```text
Action items:
- Owner: Ravi will finish the API error handling by Friday.
- Owner: Maya should test PDF and image uploads by Monday.
- Owner: Ved needs to update the README with demo steps.
- Next step: Prepare the final demo walkthrough.
```

### 3. Image screenshot containing code

Upload a screenshot of:

```python
def divide_numbers(a, b):
    result = a / b
    return result

print(divide_numbers(10, 0))
```

Prompt:

```text
Explain
```

Expected output:

- detected language
- explanation of what the code does
- division-by-zero warning
- time complexity
- OCR confidence

### 4. Mandatory clarification

Upload a PDF or image without a prompt.

Expected output:

```text
What do you want me to do with this extracted text?
```

## Testing

Backend tests:

```powershell
cd backend
venv\Scripts\python.exe -m unittest discover app/tests
```

Current backend coverage includes the assignment sample cases:

- audio summary with duration
- 3-page PDF action-item extraction
- image OCR code explanation
- follow-up clarification
- sentiment analysis
- YouTube URL parsing
- missing dependency fallbacks

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

Latest verified status:

```text
Backend tests: 23 passing
Frontend lint: passing
Frontend build: passing
```

## Assignment Coverage

| Requirement | Status |
| --- | --- |
| Text input | Implemented |
| Image OCR | Implemented with optional OCR dependencies |
| PDF parsing | Implemented |
| Scanned PDF OCR fallback | Implemented with optional dependencies |
| Audio transcription | Implemented with optional Whisper + ffmpeg |
| YouTube transcript fetching | Implemented |
| Intent detection | Implemented |
| Mandatory follow-up question | Implemented |
| Summarization format | Implemented |
| Sentiment analysis | Implemented |
| Code explanation | Implemented |
| Action-item extraction | Implemented |
| FastAPI backend | Implemented |
| Simple UI | Implemented |
| Architecture diagram | Implemented |
| Tests | Implemented |
| README | Implemented |
| Bonus cost estimator | Implemented |
| Bonus planner/executor orchestration | Implemented |

## Notes for Reviewers

- The app is designed to continue working even when Ollama is not running. In that case, deterministic local fallback functions are used.
- Image OCR, scanned PDF OCR, audio transcription, and YouTube transcripts require optional dependencies and system tools listed above.
- Runtime uploads are stored locally during development and should not be committed.
- Generated folders such as `backend/venv`, `frontend/node_modules`, `frontend/dist`, `backend/uploads`, and `__pycache__` are excluded through `.gitignore`.

## License

This repository is submitted by Ved N. Patil.
