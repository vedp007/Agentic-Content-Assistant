# Agentic AI Assignment - Current Overview

## Project Goal

This project is an agentic content assistant built for the interview assignment. It accepts text and uploaded files, extracts usable content, understands the user's intent, plans the workflow, and returns text-only responses.

The system is designed to handle:

- Text prompts
- PDF uploads
- Image uploads with OCR fallback support
- Audio uploads with Whisper fallback support
- YouTube transcript fallback support
- Follow-up questions using previous extracted file context

## Current Tech Stack

| Area | Technology |
| --- | --- |
| Backend | FastAPI |
| Frontend | React + Vite |
| LLM | Ollama with `llama3.2:3b` |
| PDF parsing | `pypdf` |
| OCR | Optional `pytesseract`, `pillow`, Tesseract OCR |
| Scanned PDF OCR | Optional `pdf2image`, Poppler, Tesseract OCR |
| Audio transcription | Optional `openai-whisper`, `ffmpeg` |
| UI HTTP client | Axios |
| Tests | Python `unittest` |
| Container files | Dockerfiles + `docker-compose.yml` |

## What Has Been Implemented

### 1. FastAPI Backend

The backend is now more than a placeholder API. It includes:

- `/chat` endpoint for text, file uploads, and follow-up questions
- `/upload` endpoint for saving uploaded files
- CORS support for the React frontend
- Modular route structure
- Agent orchestration layer
- File extraction services
- LLM-backed task execution with heuristic fallback

Main files:

- `backend/app/main.py`
- `backend/app/routes/chat.py`
- `backend/app/routes/upload.py`

### 2. Agent Orchestration Layer

The project now has a planner/executor-style architecture.

Flow:

```text
Input -> Input Router -> Extraction Service -> Intent Agent -> Planner -> Executor -> Text Response
```

Implemented agent modules:

- `backend/app/agents/orchestrator.py`
- `backend/app/agents/intent_agent.py`
- `backend/app/agents/planner.py`
- `backend/app/agents/executor.py`

The backend returns:

- Final text response
- Extracted text
- Detected intent
- Execution plan
- Logs
- Metadata

### 3. Local LLM Integration

Ollama has been integrated using the local model:

```text
llama3.2:3b
```

The backend uses Ollama for:

- Summarization
- Sentiment analysis
- Code explanation
- Conversational answering
- Follow-up question wording
- Action item extraction

If Ollama is not running, the system falls back to heuristic tools instead of crashing.

Implemented file:

- `backend/app/services/ollama_service.py`

### 4. PDF Processing

Text-based PDF parsing is implemented with `pypdf`. Scanned PDF OCR fallback is implemented through optional `pdf2image` + Tesseract OCR dependencies.

Behavior:

- Extracts text from all pages
- Adds page markers
- Returns parser confidence
- Detects likely scanned PDFs when no embedded text is found
- Attempts scanned PDF OCR when optional dependencies are installed
- Provides clear fallback warnings when OCR dependencies or system tools are missing

Implemented file:

- `backend/app/services/pdf_service.py`

### 5. Image, Audio, and YouTube Service Adapters

Adapters are implemented for assignment coverage, with real processing when optional dependencies are installed and clear fallback messages when they are not.

Implemented:

- OCR service adapter using `pytesseract`
- Audio transcription adapter using Whisper
- YouTube transcript adapter using `youtube-transcript-api`

Current behavior:

- Image OCR returns cleaned transcript text and confidence when dependencies are available.
- Scanned PDFs use OCR fallback when PDF embedded text is unavailable.
- Audio transcription returns cleaned transcript text and duration metadata when available.
- YouTube URL detection supports `watch`, `youtu.be`, `shorts`, and `embed` links.
- If optional dependencies are missing, the app returns clear fallback messages instead of crashing.

Files:

- `backend/app/services/ocr_service.py`
- `backend/app/services/audio_service.py`
- `backend/app/services/youtube_service.py`

Optional dependencies for full support:

- OCR: `pillow`, `pytesseract`, Tesseract OCR
- Scanned PDF OCR: `pdf2image`, Poppler, Tesseract OCR
- Audio: `openai-whisper`, `ffmpeg`
- YouTube: `youtube-transcript-api`

### 6. Intent Detection

The system can detect these intents:

- Summarization
- Sentiment analysis
- Code explanation
- Action item extraction
- Text extraction
- YouTube transcript handling
- Audio summary
- Conversational answering
- Clarification required

It follows the assignment rule:

> If the user goal is unclear, ask a follow-up question before acting.

### 7. Follow-Up Context for Uploaded Files

This was an important fix.

Earlier, after uploading a PDF, a message like:

```text
give summary of this file
```

was summarized directly because the backend did not know about the previous PDF.

Now the frontend stores the latest extracted text and sends it as `context` with follow-up messages. The backend summarizes the PDF content instead of summarizing the instruction.

Updated files:

- `frontend/src/App.jsx`
- `backend/app/routes/chat.py`
- `backend/app/agents/orchestrator.py`

Latest behavior:

- A file and prompt can be sent together in the same chat turn.
- Multipart uploads are detected reliably by filename instead of relying on a strict upload class check.
- The UI shows the attached filename in the user message.
- Follow-up questions continue to use the latest extracted text as context.

### 8. React Frontend

The Vite starter page has been replaced with a usable chat interface.

Implemented UI features:

- Text input
- File upload
- Microphone dictation for browser speech-to-text input
- Send button
- Chat-style responses
- Extracted text panel
- Execution plan panel
- Logs panel
- Cost estimate panel
- Follow-up context support

Microphone dictation behavior:

- The frontend uses `MediaRecorder` to capture short microphone chunks.
- Chunks are sent to the backend `/dictate` endpoint.
- The backend uses Whisper + ffmpeg to transcribe each chunk.
- Returned words are appended directly into the input text box.
- No audio recording is attached when using the microphone dictation button.
- The normal Send button submits the dictated text through the existing chat flow.

Main files:

- `frontend/src/App.jsx`
- `frontend/src/App.css`

### 9. Task Tools

The backend includes tools for:

- Structured summaries
- Sentiment analysis
- Code explanation
- Action item extraction
- Basic Q&A fallback
- Adaptive summary formatting
- Approximate cost estimation

Implemented file:

- `backend/app/services/text_tools.py`
- `backend/app/services/cost_service.py`

Summary behavior:

- Summary requests return the assignment-required structure every time.
- The output includes a 1-line summary, 3 bullets, and a 5-sentence summary.
- Audio and YouTube summaries use the same required summary structure.

Cost estimator behavior:

- Estimates input, output, and total token counts for each plan.
- Reports local Ollama API cost as `$0.00`.
- Returns estimate data in response metadata under `cost_estimate`.
- Adds an `estimate_cost` step to the execution plan.

### 10. Tests

Backend tests are implemented for:

- Summarization format
- Ambiguous input follow-up
- Sentiment analysis
- Code explanation
- Action item extraction
- Empty action item handling
- Follow-up summary using previous context

Test file:

- `backend/app/tests/test_orchestrator.py`

Current status:

```text
23 tests passing
```

### 11. Documentation and Docker Files

Added:

- `README.md`
- `docs/architecture.md`
- `docs/current-overview.md`
- `.gitignore`
- `backend/optional-requirements.txt`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

## Current Working Demo Flow

### Text Summary

User:

```text
summarize this Build an agentic application...
```

System:

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

### PDF Follow-Up Summary

1. User uploads a PDF.
2. System extracts text.
3. User asks:

```text
give summary of this file
```

4. System summarizes the extracted PDF text.

### Action Items

User:

```text
What are the action items? Ravi will finish the API by Friday. Maya should test uploads. The demo must be ready tomorrow.
```

System:

```text
Action items:
- Ravi: Finish the API by Friday
- Maya: Test uploads
- Team: Demo is ready tomorrow
```

## How to Run

Start Ollama:

```powershell
& "C:\Users\Ved Patil\AppData\Local\Programs\Ollama\ollama.exe" serve
```

Start backend:

```powershell
cd E:\projects\agentic-assignment\backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

Start frontend:

```powershell
cd E:\projects\agentic-assignment\frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Verification Completed

The following checks have passed:

- Backend unit tests
- Frontend build
- Ollama model availability
- Direct backend summary with context
- Action item extraction
- Chat API response with LLM path
- Multipart file + prompt route handling
- Assignment-required 1-line, 3-bullet, and 5-sentence summaries
- Audio summary with duration metadata
- Image code screenshot explanation path
- PDF action-item extraction path
- YouTube URL parsing variants
- Cost estimator metadata and plan step

## Remaining Improvements

The project is now functional, but these improvements would make it stronger:

- Install optional OCR system dependencies on the demo machine if image/scanned PDF live demos are required
- Install Whisper and ffmpeg on the demo machine if audio live demos are required
- Add persistent chat sessions instead of only frontend-held context
- Add more PDF sample tests
- Improve README with screenshots
- Record a short demo video
- Remove `venv`, `node_modules`, `dist`, and `__pycache__` before submission
- Optionally add screenshots to README

## Current Status

The project is now a working agentic AI assignment demo with:

- Modular FastAPI backend
- React chat UI
- File upload support
- PDF extraction
- Local LLM reasoning through Ollama
- Intent detection
- Planner/executor flow
- Follow-up handling
- Context-aware file questions
- Tests and documentation
