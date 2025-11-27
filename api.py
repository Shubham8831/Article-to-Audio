from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

# backend functions
from backend import (
    extract_article_content,
    preprocess_with_llm,
    generate_audio_bytes,
    audio_stream_generator,
    SUPPORTED_LANGUAGES
)

app = FastAPI(title="Article to Audio API")


class GenerateRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None
    language: str = "en"
    type: str = "full"  # "full" or "summary"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate_audio(request: GenerateRequest):

    try:
        # Validate input or url
        if not request.url and not request.text:
            raise HTTPException(400, "Provide either 'url' or 'text'")
        
        if request.language not in SUPPORTED_LANGUAGES:
            raise HTTPException(400, f"Language must be one of {list(SUPPORTED_LANGUAGES.keys())}")
        
        if request.type not in ["full", "summary"]:
            raise HTTPException(400, "Type must be 'full' or 'summary'")
        
        # Get content from the url 
        content = extract_article_content(request.url) if request.url else request.text
        
        if len(content) < 300:
            raise HTTPException(422, "Content too short (min 300 characters)") #raise exception for small content less then 300 characters
        
        # llmpre process 
        processed = preprocess_with_llm(content, request.language)
        text_for_audio = processed["summary"] if request.type == "summary" else processed["cleaned_text"] # seperate the summary and complete text and send the one which is req
        
        # Generate audio buffer
        audio_buffer = generate_audio_bytes(text_for_audio, request.language)
        
        # Return streaming response for the buffer audio
        return StreamingResponse(
            audio_stream_generator(audio_buffer),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=article.mp3"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)