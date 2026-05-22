import unittest
from unittest.mock import AsyncMock, patch

from app.routes.chat import chat, dictate
from app.models.schemas import ExtractedContent, IntentResult
from app.agents.executor import execute_intent
from app.agents.orchestrator import run_agent
from app.services.audio_service import transcribe_audio
from app.services.ocr_service import ocr_pil_image
from app.services.youtube_service import extract_video_id


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict("os.environ", {"DISABLE_OLLAMA": "1"})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_summarization_uses_required_assignment_format(self):
        result = run_agent(
            "Summarize this: The team met on Monday. Ravi owns the API. "
            "Maya owns the UI. The demo is due Friday. Risks remain around OCR."
        )

        self.assertEqual(result.intent.intent, "summarization")
        self.assertIn("cost_estimate", result.metadata)
        self.assertTrue(any(step.name == "estimate_cost" for step in result.plan))
        self.assertIn("1-line summary", result.response)
        self.assertIn("3 bullets", result.response)
        self.assertIn("5-sentence summary", result.response)
        self.assertNotIn("Summarize this", result.response)

    def test_summarization_returns_all_formats_when_requested(self):
        result = run_agent(
            "Summarize this in all 3 formats: The team met on Monday. Ravi owns the API. "
            "Maya owns the UI. The demo is due Friday. Risks remain around OCR."
        )

        self.assertEqual(result.intent.intent, "summarization")
        self.assertIn("1-line summary", result.response)
        self.assertIn("3 bullets", result.response)
        self.assertIn("5-sentence summary", result.response)

    def test_summarization_returns_bullets_when_requested(self):
        result = run_agent(
            "Summarize this in 3 bullets: The team met on Monday. Ravi owns the API. "
            "Maya owns the UI. The demo is due Friday. Risks remain around OCR."
        )

        self.assertEqual(result.intent.intent, "summarization")
        self.assertIn("1-line summary", result.response)
        self.assertIn("3 bullets", result.response)
        self.assertIn("5-sentence summary", result.response)

    def test_ambiguous_text_requests_follow_up(self):
        result = run_agent("This document contains quarterly updates and budget notes.")

        self.assertTrue(result.intent.needs_clarification)
        self.assertIn("clarify", result.response.lower())

    def test_sentiment_analysis(self):
        result = run_agent("Analyze sentiment: I love the clear UI but the upload bug is bad.")

        self.assertEqual(result.intent.intent, "sentiment_analysis")
        self.assertIn("Label:", result.response)
        self.assertIn("Confidence:", result.response)

    def test_standalone_sentiment_ignores_previous_file_context(self):
        result = run_agent(
            "Analyze sentiment: I love the clear UI but the upload bug is bad.",
            context="The assignment requires building an agentic application with PDF extraction.",
        )

        self.assertEqual(result.intent.intent, "sentiment_analysis")
        self.assertNotIn("assignment requires", result.extracted_text.lower())
        self.assertNotEqual(result.metadata.get("context_source"), "previous_extraction")
        self.assertIn("Label:", result.response)

    def test_code_explanation(self):
        code = "Explain code:\nfor item in items:\n    print(item)"
        result = run_agent(code)

        self.assertEqual(result.intent.intent, "code_explanation")
        self.assertIn("Time complexity", result.response)

    def test_action_items(self):
        result = run_agent(
            "What are the action items? Owner: Ravi will finish the API by Friday.\n"
            "Next step: Maya should test uploads."
        )

        self.assertEqual(result.intent.intent, "action_items")
        self.assertIn("Action items", result.response)
        self.assertNotIn("- What are the action items?", result.response)

    def test_action_items_without_content(self):
        result = run_agent("What are the action items?")

        self.assertEqual(result.intent.intent, "action_items")
        self.assertIn("No explicit action items", result.response)

    def test_follow_up_action_items_uses_previous_context(self):
        result = run_agent(
            "What are the action items?",
            context="Owner: Ravi will finish the API by Friday. Next step: Maya should test uploads.",
        )

        self.assertEqual(result.intent.intent, "action_items")
        self.assertEqual(result.metadata.get("context_source"), "previous_extraction")
        self.assertIn("Ravi", result.response)

    def test_follow_up_summary_uses_previous_context(self):
        result = run_agent(
            "give summary of this file",
            context="The project accepts PDFs. It extracts text. It asks clarification when goals are unclear.",
        )

        self.assertEqual(result.intent.intent, "summarization")
        self.assertIn("project accepts PDFs", result.extracted_text)
        self.assertIn("1-line summary", result.response)
        self.assertNotIn("give summary of this file", result.response)

    def test_extraction_confidence_is_exposed_in_metadata(self):
        with patch("app.agents.orchestrator.extract_input") as extract_input_mock:
            extract_input_mock.return_value = ExtractedContent(
                source_type="image",
                text="Visible OCR text.",
                confidence=0.73,
            )
            result = run_agent("What do you want me to do with this extracted text?")

        self.assertEqual(result.metadata["extraction_confidence"], 0.73)

    def test_sample_audio_lecture_transcribes_summarizes_and_returns_duration(self):
        with patch("app.agents.orchestrator.extract_input") as extract_input_mock:
            extract_input_mock.return_value = ExtractedContent(
                source_type="audio",
                text=(
                    "The lecture introduced agentic AI systems. It explained input extraction. "
                    "The speaker described planning and tool execution. Robust systems ask clarifying questions. "
                    "The conclusion emphasized logging, fallbacks, and evaluation."
                ),
                confidence=0.8,
                metadata={"filename": "lecture.wav", "duration_seconds": 300.0},
            )

            result = run_agent("summarize this audio", file_path=__import__("pathlib").Path("lecture.wav"))

        self.assertEqual(result.intent.intent, "summarization")
        self.assertIn("1-line summary", result.response)
        self.assertIn("3 bullets", result.response)
        self.assertIn("5-sentence summary", result.response)
        self.assertEqual(result.metadata["duration_seconds"], 300.0)

    def test_sample_pdf_meeting_notes_action_items(self):
        with patch("app.agents.orchestrator.extract_input") as extract_input_mock:
            extract_input_mock.return_value = ExtractedContent(
                source_type="pdf",
                text=(
                    "[Page 1]\nMeeting notes: Product review.\n"
                    "[Page 2]\nOwner: Ravi will finish the API by Friday.\n"
                    "[Page 3]\nNext step: Maya should test uploads by Monday."
                ),
                confidence=0.9,
                metadata={"filename": "meeting-notes.pdf", "pages": 3},
            )

            result = run_agent(
                "What are the action items?",
                file_path=__import__("pathlib").Path("meeting-notes.pdf"),
            )

        self.assertEqual(result.intent.intent, "action_items")
        self.assertIn("Ravi", result.response)
        self.assertIn("Maya", result.response)
        self.assertEqual(result.metadata["pages"], 3)

    def test_sample_image_code_snippet_explain_detects_bug_and_complexity(self):
        with patch("app.agents.orchestrator.extract_input") as extract_input_mock:
            extract_input_mock.return_value = ExtractedContent(
                source_type="image",
                text="def divide(total):\n    return total / 0",
                confidence=0.88,
                metadata={"filename": "code.png", "size": (800, 500)},
            )

            result = run_agent("Explain", file_path=__import__("pathlib").Path("code.png"))

        self.assertEqual(result.intent.intent, "code_explanation")
        self.assertIn("Detected language: python", result.response)
        self.assertIn("division by zero", result.response.lower())
        self.assertIn("Time complexity", result.response)
        self.assertEqual(result.metadata["extraction_confidence"], 0.88)

    def test_pdf_content_words_do_not_imply_summary_without_goal(self):
        extracted = ExtractedContent(
            source_type="pdf",
            text="This document mentions summary, sentiment analysis, and action items as possible features.",
        )

        from app.agents.intent_agent import detect_intent

        intent = detect_intent("", extracted)

        self.assertTrue(intent.needs_clarification)
        self.assertEqual(intent.intent, "clarification_required")

    def test_embedded_task_in_uploaded_content_drives_intent(self):
        extracted = ExtractedContent(
            source_type="pdf",
            text=(
                "Task: What are the action items?\n"
                "Owner: Ravi will finish the API by Friday.\n"
                "Next step: Maya should test uploads."
            ),
        )

        from app.agents.intent_agent import detect_intent

        intent = detect_intent("", extracted)

        self.assertEqual(intent.intent, "action_items")
        self.assertEqual(intent.constraints.get("goal_source"), "embedded_in_input")

    def test_youtube_video_id_parsing(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=abc123&t=20s"),
            "abc123",
        )
        self.assertEqual(extract_video_id("https://youtu.be/abc123"), "abc123")
        self.assertEqual(extract_video_id("https://www.youtube.com/shorts/abc123"), "abc123")

    def test_ocr_missing_tesseract_returns_warning(self):
        class FakeImage:
            size = (100, 50)

        class FakePytesseractModule:
            class pytesseract:
                class TesseractNotFoundError(Exception):
                    pass

            @staticmethod
            def image_to_string(_image):
                raise FakePytesseractModule.pytesseract.TesseractNotFoundError()

        with patch.dict("sys.modules", {"pytesseract": FakePytesseractModule}):
            text, confidence, warnings, metadata = ocr_pil_image(FakeImage(), "sample.png")

        self.assertEqual(text, "")
        self.assertEqual(confidence, 0.0)
        self.assertIn("Tesseract OCR", warnings[0])
        self.assertEqual(metadata["ocr_engine"], "tesseract_missing")

    def test_empty_image_extraction_warning_is_user_visible(self):
        response = execute_intent(
            "explain what is in this image",
            ExtractedContent(
                source_type="image",
                warnings=["Tesseract OCR is not installed or is not available in PATH."],
            ),
            IntentResult(intent="conversational_answering", confidence=0.7),
        )

        self.assertIn("Tesseract OCR", response)

    def test_audio_missing_ffmpeg_returns_warning(self):
        class FakeWhisper:
            @staticmethod
            def load_model(_name):
                class FakeModel:
                    @staticmethod
                    def transcribe(_path):
                        raise FileNotFoundError()

                return FakeModel()

        with patch.dict("sys.modules", {"whisper": FakeWhisper}):
            result = transcribe_audio(__import__("pathlib").Path("sample.wav"))

        self.assertEqual(result.source_type, "audio")
        self.assertIn("ffmpeg", result.warnings[0])

    def test_chat_multipart_accepts_file_and_prompt(self):
        class FakeRequest:
            headers = {"content-type": "multipart/form-data; boundary=test"}

            async def form(self):
                class FakeUpload:
                    filename = "sample.pdf"

                return {
                    "message": "summarize this file",
                    "context": "",
                    "file": FakeUpload(),
                }

        async def run_route():
            with patch("app.routes.chat.save_upload", new_callable=AsyncMock) as save_upload, patch(
                "app.routes.chat.run_agent"
            ) as run_agent_mock:
                save_upload.return_value = "uploads/sample.pdf"
                run_agent_mock.return_value.model_dump.return_value = {
                    "response": "ok",
                    "extracted_text": "Document text",
                    "intent": {"intent": "summarization", "confidence": 0.9},
                    "plan": [],
                    "logs": [],
                    "metadata": {},
                }

                response = await chat(FakeRequest())

                save_upload.assert_called_once()
                run_agent_mock.assert_called_once_with(
                    message="summarize this file",
                    file_path="uploads/sample.pdf",
                    context="",
                )
                return response

        import asyncio

        response = asyncio.run(run_route())

        self.assertEqual(
            response,
            {
                "response": "ok",
                "extracted_text": "Document text",
                "intent": {"intent": "summarization", "confidence": 0.9},
                "plan": [],
                "logs": [],
                "metadata": {},
            },
        )

    def test_dictate_route_returns_transcript(self):
        class FakeRequest:
            async def form(self):
                class FakeUpload:
                    filename = "mic.webm"

                return {"file": FakeUpload()}

        async def run_route():
            with patch("app.routes.chat.save_upload", new_callable=AsyncMock) as save_upload, patch(
                "app.routes.chat.transcribe_audio"
            ) as transcribe_mock:
                save_upload.return_value = "uploads/mic.webm"
                transcribe_mock.return_value = ExtractedContent(
                    source_type="audio",
                    text="hello from microphone",
                    metadata={"duration_seconds": 4.5},
                )

                response = await dictate(FakeRequest())

                save_upload.assert_called_once()
                transcribe_mock.assert_called_once_with("uploads/mic.webm")
                return response

        import asyncio

        response = asyncio.run(run_route())

        self.assertEqual(response["transcript"], "hello from microphone")
        self.assertEqual(response["metadata"]["duration_seconds"], 4.5)


if __name__ == "__main__":
    unittest.main()
