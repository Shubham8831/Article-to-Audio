from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl, model_validator
from typing import Optional

import asyncio
from concurrent.futures import ThreadPoolExecutor
import base64

# Import backend functions
from backend import (
    extract_article_content,
    preprocess_with_llm,
    generate_audio_bytes,
    audio_stream_generator,
    SUPPORTED_LANGUAGES
)


# Initialize FastAPI
app = FastAPI(title="article to audio sollution")

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)


from pydantic import BaseModel, model_validator
from typing import Optional

class GenerateRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None
    language: str = "en"
    type: str = "full"  # "full" or "summary"

    @model_validator(mode='before')
    @classmethod
    def validate_all(cls, values):
        url = values.get('url')
        text = values.get('text')
        language = values.get('language', 'en')
        type_ = values.get('type', 'full')

        # Check at least url or text is provided
        if not text and not url:
            raise ValueError("Either 'url' or 'text' must be provided")

        # Validate language
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Language must be one of {list(SUPPORTED_LANGUAGES.keys())}")

        # Validate type
        if type_ not in ["full", "summary"]:
            raise ValueError("Type must be 'full' or 'summary'")

        return values 

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "message": "Service is running"
    }



@app.post("/generate")
async def generate_audio(request: GenerateRequest):
    """
    Main endpoint to generate audio from article.
    
    Process:
    1. Extract article content (from URL or use provided text)
    2. Preprocess with LLM (clean + summarize + translate to target language)
    3. Generate audio with gTTS in the target language
    4. Stream audio response
    """
    try:
        # Step 1: Get article content
        if request.url:
            # Extract from URL (blocking operation, run in executor)
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                executor, 
                extract_article_content, 
                request.url
            )
        else:
            content = request.text
        
        # Validate content length
        if len(content) < 300:
            raise HTTPException(
                status_code=422,
                detail="Article content too short (minimum 300 characters required)"
            )
        
        # Step 2: Preprocess with LLM (clean, summarize, and translate)
        loop = asyncio.get_event_loop()
        processed = await loop.run_in_executor(
            executor,
            preprocess_with_llm,
            content,
            request.language  # Pass target language for translation
        )
        
        # Step 3: Select text based on type
        if request.type == "summary":
            text_for_audio = processed["summary"]
        else:
            text_for_audio = processed["cleaned_text"]
        
        # Step 4: Generate audio (blocking operation)
        audio_buffer = await loop.run_in_executor(
            executor,
            generate_audio_bytes,
            text_for_audio,
            request.language
        )
        
        # Step 5: Stream response
        # Encode non-Latin text for headers (base64 to handle all characters)
        cleaned_preview = processed["cleaned_text"][:200] + "..."
        summary_preview = processed["summary"][:200] + "..."
        
        # Encode to base64 to safely pass through HTTP headers
        cleaned_encoded = base64.b64encode(cleaned_preview.encode('utf-8')).decode('ascii')
        summary_encoded = base64.b64encode(summary_preview.encode('utf-8')).decode('ascii')
        
        return StreamingResponse(
            audio_stream_generator(audio_buffer),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=article.mp3",
                "X-Cleaned-Text": cleaned_encoded,
                "X-Summary": summary_encoded,
                "X-Target-Language": SUPPORTED_LANGUAGES[request.language]["name"],
                "X-Encoding": "base64"  # Flag to indicate base64 encoding
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")