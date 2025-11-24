from io import BytesIO # in-memory binary stream : it sotres the audio in the memory not disk (laptop band, audio delete)
import json
from typing import Optional, AsyncIterator
import requests

# to extract article
from newspaper import Article
import trafilatura
from readability import Document


from langchain_ollama import ChatOllama # llm 
from gtts import gTTS # text to speech model(google)


# lang
SUPPORTED_LANGUAGES = {
    "en": {"code": "en", "name": "English"},
    "hi": {"code": "hi", "name": "Hindi"},
    "fr": {"code": "fr", "name": "French"},
    "es": {"code": "es", "name": "Spanish"}
}


# this fn extrac the content of article from url we try 3 methrod for this 
def extract_article_content(url):
    
    print(f"Extracting content from: {url}")
    
    # first we try with newspaper3k
    try:
        article = Article(url)
        article.download()
        article.parse()
        content = article.text
        
        if content and len(content) >= 300:
            print("extraction successful with np3k")
            return content
    except Exception as e:
        print(f"failed extraction by np3k: {e}")
    
    # if upar wala fails then we tru- trafilatura
    try:
        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded, include_comments=False)
        
        if content and len(content) >= 300:
            print("extracted with trafilatura")
            return content
    except Exception as e:
        print(f"extraction failed via trafilatura: {e}")
    
    # if above again fails the we try the r-lxml
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        doc = Document(response.content)
        content = doc.summary()
        
        # use beautiful soup to remove html tags
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        content = soup.get_text(separator=' ', strip=True)
        
        if content and len(content) >= 300:
            print(" extracted with r-lxml")
            return content
    except Exception as e:
        print(f"r-lxml failed: {e}")
    
    raise Exception(
        "unable to extract article. The article can be too short or the URL is inaccessible"
    )





# we generate summary and clean the article with llm in this fnution
def preprocess_with_llm(text, target_language: str = "en"): # english by default
    
    language_name = SUPPORTED_LANGUAGES[target_language]["name"]
    print(f"llm preprocessing and translating in {language_name}")
    
    try:
        #llm
        llm = ChatOllama(model="gemma3:1b")
        
        # prompt (gpt se generated h)
        prompt = f"""You are a multilingual text processing assistant. Given the following article text, perform these tasks:

1. Clean the text by fixing grammar, improving structure, removing noise (like ads, navigation text), while preserving all facts and original meaning.
2. Create a concise one-paragraph summary (2-3 sentences) of the main points.
3. Translate BOTH the cleaned text and summary to {language_name}.

IMPORTANT: The output must be ENTIRELY in {language_name}. Every word of both the cleaned_text and summary must be translated to {language_name}.

Return your response ONLY as valid JSON with this exact structure:
{{"cleaned_text": "the cleaned and translated full article text in {language_name}", "summary": "the translated summary in {language_name}"}}

Do not include any other text, explanations, or markdown formatting. Just the JSON with content in {language_name}.

Article text:
{text}

JSON Response in {language_name}:"""
        
        response = llm.invoke(prompt) # invoke the llm 
        
        # Parse JSON response
        try:
            # Clean response - remove markdown code blocks if present
            response_text = response.content if hasattr(response, 'content') else str(response) # if llm response has .content use that else use all the response as strung
            response_text = response_text.strip() # remove spacses
            
            if response_text.startswith("```"): # llm response starts with ```
                # Remove code block formatting
                lines = response_text.split('\n') # split into lines
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text # take everything between the first and last line and join it back to string
                response_text = response_text.replace("```json", "").replace("```", "").strip()# remove ```
            
            result = json.loads(response_text) # json to dict
            


        
            if "cleaned_text" not in result or "summary" not in result: # check if json has 2 keys
                raise ValueError("missing key in llm response")
            
            print(f"Done processing and taranslating in {language_name}")
            return result
            
        except json.JSONDecodeError as e: # if no valid json
            print(f"Failed to parse LLM JSON response: {e}")
            print(f"raw response: {response_text[:500]}....")
            
            # Fallback: if llm fails to translate of give summary then try again
            fallback_prompt = f"Translate this text to {language_name}, return only the translation:\n\n{text}"
            fallback_response = llm.invoke(fallback_prompt)
            fallback_text = fallback_response.content if hasattr(fallback_response, 'content') else str(fallback_response)
            
            return {
                "cleaned_text": fallback_text,
                "summary": fallback_text[:500] + "..." if len(fallback_text) > 500 else fallback_text # no summary but only translation ka first 500 charaters
            }
    
    except Exception as e:
        print(f"llm fail while procesing: {e}")
        # Fallback: if llm fails return original text without translation
        return {
            "cleaned_text": text,
            "summary": text[:500] + "..." if len(text) > 500 else text # for summary first 500 charaters of original extraction
        }






# this funtion generates the audio from the text in particular languate and return it bytesio
def generate_audio_bytes(text, language) -> BytesIO:

    print(f"generating audio in : {language}")
    
    try:
        tts = gTTS(text=text, lang=SUPPORTED_LANGUAGES[language]["code"], slow=False)
        
        # saveing to BytesIO
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        print("autio generated : )")
        return audio_buffer
    
    except Exception as e:
        print(f"error generting audio: {e}")
        raise Exception(f"Audio generation failed: {str(e)}")



# takes audio stored in memory and send it out in small pieces (chunks) — instead of sending the whole file at once; listen while it is still loading

async def audio_stream_generator(audio_buffer: BytesIO, chunk_size: int = 8192) -> AsyncIterator[bytes]:
    while True:
        chunk = audio_buffer.read(chunk_size)
        if not chunk:
            break
        yield chunk





if __name__ == "__main__":
    import asyncio

    # Example article URL to test
    test_url = "https://aws.amazon.com/what-is/large-language-model/"  # replace with any article URL
    target_language = "en"  # en, hi, fr, es

    try:
        # Step 1: Extract article
        article_text = extract_article_content(test_url)
        print(f"\nExtracted article (first 100 chars):\n{article_text[:100]}...\n")

        # Step 2: Preprocess with LLM (clean + summary + translate)
        processed = preprocess_with_llm(article_text, target_language=target_language)
        print(f"\nCleaned text (first 100 chars):\n{processed['cleaned_text'][:100]}...\n")
        print(f"Summary:\n{processed['summary']}\n")

        # Step 3: Generate audio
        audio_bytes = generate_audio_bytes(processed['summary'], language=target_language)

        # Step 4: Save audio to file for testing
        with open("test_article.mp3", "wb") as f:
            f.write(audio_bytes.read())
        print("Audio saved as test_article.mp3")

        # Optional: test streaming generator
        async def test_stream():
            print("\nStreaming audio in chunks...")
            async for chunk in audio_stream_generator(BytesIO(audio_bytes.getvalue()), chunk_size=1024):
                print(f"Chunk size: {len(chunk)} bytes")
        
        asyncio.run(test_stream())

    except Exception as e:
        print(f"Error during test: {e}")
