import assemblyai as aai
from config import settings

aai.settings.api_key = settings.assemblyai_api_key


def transcribe(file_path: str) -> list[dict]:
    """
    Transcribe a local video/audio file.
    Returns sentences: [{text, start_ms, end_ms}, ...]
    """
    config = aai.TranscriptionConfig(
        punctuate=True,
        format_text=True,
        language_detection=True,
        speech_models=[aai.SpeechModel.universal],
    )

    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(file_path)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(f"AssemblyAI error: {transcript.error}")

    sentences = transcript.get_sentences()
    return [
        {
            "text": s.text,
            "start_ms": s.start,
            "end_ms": s.end,
        }
        for s in sentences
    ]
