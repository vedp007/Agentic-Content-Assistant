# Architecture

```mermaid
flowchart TD
    A[React Chat UI] --> B[FastAPI Gateway]
    B --> C[Input Router]
    C --> D[Text Input]
    C --> E[PDF Service]
    C --> F[OCR Service]
    C --> G[Audio Service]
    C --> H[YouTube Transcript Service]
    D --> I[Intent Agent]
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J[Planner Agent]
    J --> K[Tool Executor]
    K --> L[Response Formatter]
    L --> M[Text-only Response + Plan + Logs]
```

## Runtime Flow

1. The frontend sends text and an optional file to `/chat`.
2. The backend saves the upload, detects the input type, and extracts content.
3. The intent agent classifies the task and asks a follow-up question when the goal is unclear.
4. The planner records the workflow steps.
5. The executor runs the matching tool and returns a text-only result with logs.

