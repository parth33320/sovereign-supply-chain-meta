import os
import io
import pytest
from unittest.mock import MagicMock, patch
from voice_handler import process_voice_input, transcribe_audio, extract_logistics_intent


def test_process_voice_input_success():
    """
    Test end-to-end voice processing happy path:
    Mock audio transcription returning transcribed text,
    and mock intent extraction returning logistics intent.
    """
    sample_audio = b"RIFF....WAVEfmt...."
    mock_transcript = "Reroute 500 widgets to warehouse B"
    mock_intent = '{"action": "reroute", "item": "widgets", "quantity": 500, "destination": "warehouse B"}'

    with patch("voice_handler.transcribe_audio", return_value=mock_transcript) as mock_transcribe, \
         patch("voice_handler.extract_logistics_intent", return_value=mock_intent) as mock_extract:
        result = process_voice_input(sample_audio)

        mock_transcribe.assert_called_once_with(sample_audio)
        mock_extract.assert_called_once_with(mock_transcript)

        assert result == {
            "transcription": mock_transcript,
            "intent": mock_intent,
            "status": "ok"
        }


def test_process_voice_input_empty_bytes():
    """Test process_voice_input with empty audio bytes returns status error."""
    result = process_voice_input(b"")
    assert result["status"] == "error"
    assert result["transcription"] == ""
    assert "empty" in result["intent"].lower() or "error" in result["intent"].lower()


def test_process_voice_input_invalid_input():
    """Test process_voice_input with None or invalid type returns status error."""
    result = process_voice_input(None)  # type: ignore
    assert result["status"] == "error"
    assert result["transcription"] == ""
    assert "error" in result["intent"].lower() or "invalid" in result["intent"].lower()


def test_process_voice_input_transcription_failure():
    """Test handling when transcribe_audio raises an exception."""
    sample_audio = b"some_audio_bytes"
    with patch("voice_handler.transcribe_audio", side_effect=RuntimeError("Audio transcription service unavailable")):
        result = process_voice_input(sample_audio)
        assert result["status"] == "error"
        assert result["transcription"] == ""
        assert "Audio transcription service unavailable" in result["intent"]


def test_process_voice_input_intent_extraction_failure():
    """Test handling when transcribe_audio succeeds but intent extraction fails."""
    sample_audio = b"some_audio_bytes"
    mock_transcript = "Reroute inventory"
    with patch("voice_handler.transcribe_audio", return_value=mock_transcript), \
         patch("voice_handler.extract_logistics_intent", side_effect=ValueError("LLM extraction failed")):
        result = process_voice_input(sample_audio)
        assert result["status"] == "error"
        assert result["transcription"] == mock_transcript
        assert "LLM extraction failed" in result["intent"]


def test_transcribe_audio_unit():
    """Test transcribe_audio using mock OpenAI client."""
    sample_audio = b"fake_audio_payload"
    mock_response = MagicMock()
    mock_response.text = "Show inventory levels"

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = mock_response

        text = transcribe_audio(sample_audio)
        assert text == "Show inventory levels"
        mock_client.audio.transcriptions.create.assert_called_once()
        call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
        assert call_kwargs["model"] == "muse-voice-transcribe-1.0"


def test_extract_logistics_intent_unit():
    """Test extract_logistics_intent unit test with mocked ChatOpenAI."""
    mock_llm_response = MagicMock()
    mock_llm_response.content = '{"action": "query_inventory", "item": "all"}'

    with patch("voice_handler.ChatOpenAI") as mock_chat_cls:
        mock_chat = MagicMock()
        mock_chat_cls.return_value = mock_chat
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_llm_response

        with patch("voice_handler.ChatPromptTemplate") as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt_cls.from_template.return_value = mock_prompt
            # mock pipe chain
            mock_prompt.__or__.return_value = mock_chain

            intent = extract_logistics_intent("Show me all inventory")
            assert intent == '{"action": "query_inventory", "item": "all"}'


def test_extract_logistics_intent_live_smoke():
    """Live smoke test that executes against Meta LLM if META_API_KEY is present."""
    api_key = os.environ.get("META_API_KEY")
    if not api_key:
        pytest.skip("META_API_KEY is not set, skipping live smoke test")

    transcript = "Reroute 100 units of item SKU-99 from Warehouse A to Warehouse B immediately"
    intent = extract_logistics_intent(transcript)
    assert intent is not None
    assert isinstance(intent, str)
    assert len(intent.strip()) > 0
    assert "reroute" in intent.lower() or "sku-99" in intent.lower() or "warehouse" in intent.lower()
