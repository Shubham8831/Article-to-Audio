import streamlit as st
import requests
from io import BytesIO
import time



# Configuration
API_URL = "https://article-to-audio.onrender.com/"

# Page configuration
st.set_page_config(
    page_title="Article to Speech Converter Solution",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        padding: 10px;
    }
    .success-box {
        padding: 20px;
        background-color: #d4edda;
        border-radius: 5px;
        margin: 10px 0;
    }
    .translation-info {
        padding: 15px;
        background-color: #e8f4f8;
        border-left: 4px solid #2196F3;
        border-radius: 4px;
        margin: 10px 0;
        color: #000000
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title("Article to Speech Converter Solution")
st.markdown("""
Convert any URL to audio in multiple languages
""")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Language selection with enhanced info
    language = st.selectbox(
        "Output Language",
        options=["en", "hi", "fr", "es"],
        format_func=lambda x: {
            "en": "🇬🇧 English",
            "hi": "🇮🇳 Hindi",
            "fr": "🇫🇷 French",
            "es": "🇪🇸 Spanish"
        }[x],
        help="Article will be translated to this language before audio generation"
    )
    
    # Output type selection
    output_type = st.radio(
        "Output Type",
        options=["full", "summary"],
        format_func=lambda x: "Full Article" if x == "full" else "Summary"
    )
    
    

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 Input")
    
    # Input method tabs
    input_tab = st.radio(
        "Input Method",
        options=["URL", "Text"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if input_tab == "URL":
        url_input = st.text_input(
            "Article URL",
            placeholder="https://example.com/article",
            help="Enter the URL of the article you want to convert (in any language)"
        )
        text_input = None
    else:
        text_input = st.text_area(
            "Article Text",
            placeholder="Paste your article text here (in any language)...",
            height=300,
            help="Paste the full text of the article (in any language)"
        )
        url_input = None
    
    # Generate button
    generate_btn = st.button("🎵 Generate & Play Audio", type="primary")

with col2:
    st.subheader("🎧 Output")
    output_container = st.container()

# Initialize session state
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None
if 'cleaned_text' not in st.session_state:
    st.session_state.cleaned_text = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'target_language' not in st.session_state:
    st.session_state.target_language = None

# Process generation request
if generate_btn:
    # Validation
    if not url_input and not text_input:
        st.error(" Please provide either a URL or article text!")
    elif url_input and not url_input.startswith(('http://', 'https://')):
        st.error(" Please provide a valid URL starting with http:// or https://")
    else:
        with st.spinner(" Processing your request..."):
            try:
                # Prepare request
                payload = {
                    "language": language,
                    "type": output_type
                }
                
                if url_input:
                    payload["url"] = url_input
                else:
                    payload["text"] = text_input
                
                # Show progress
                progress_text = st.empty()
                progress_text.info("📡 Extracting article content...")
                time.sleep(0.5)
                
                progress_text.info("🌍 Translating to selected language...")
                
                # Make API request
                response = requests.post(
                    f"{API_URL}/generate",
                    json=payload,
                    stream=True,
                    timeout=120
                )
                
                if response.status_code == 200:
                    progress_text.info("🎵 Generating audio...")
                    
                    # Read audio data
                    audio_bytes = BytesIO()
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            audio_bytes.write(chunk)
                    
                    audio_bytes.seek(0)
                    st.session_state.audio_data = audio_bytes.read()
                    
                    # Extract and decode metadata from headers
                    import base64
                    
                    if 'X-Cleaned-Text' in response.headers:
                        try:
                            # Decode from base64
                            encoded_text = response.headers['X-Cleaned-Text']
                            decoded_text = base64.b64decode(encoded_text).decode('utf-8')
                            st.session_state.cleaned_text = decoded_text
                        except:
                            st.session_state.cleaned_text = "Preview unavailable"
                    
                    if 'X-Summary' in response.headers:
                        try:
                            # Decode from base64
                            encoded_summary = response.headers['X-Summary']
                            decoded_summary = base64.b64decode(encoded_summary).decode('utf-8')
                            st.session_state.summary = decoded_summary
                        except:
                            st.session_state.summary = "Preview unavailable"
                    
                    if 'X-Target-Language' in response.headers:
                        st.session_state.target_language = response.headers['X-Target-Language']
                    
                    progress_text.success(" Audio generated successfully!")
                    time.sleep(1)
                    progress_text.empty()
                    
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    st.error(f" Error: {error_detail}")
                    
            except requests.exceptions.Timeout:
                st.error(" Request timed out. Please try again with a shorter article.")
            except requests.exceptions.ConnectionError:
                st.error(" Cannot connect to API server. Make sure it's running on port 8000.")
            except Exception as e:
                st.error(f" An error occurred: {str(e)}")

# Display output
with output_container:
    if st.session_state.audio_data:
        st.success(" Audio is ready")
        
        # Show translation info if available
        if st.session_state.target_language:
            st.markdown(f"""
            <div class="translation-info">
                <strong>Translated to:</strong> {st.session_state.target_language}<br>
                <small>The URL/article is automatically translated and converted to audio in your selected language.</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Audio player
        st.audio(st.session_state.audio_data, format="audio/mp3")
        
        # Download button
        st.download_button(
            label="Download Audio",
            data=st.session_state.audio_data,
            file_name=f"article_{language}_{output_type}.mp3",
            mime="audio/mpeg"
        )
        
        
                
    else:
        st.info("Generate & Play Audio")
        st.markdown("""
        **Sollution Working :**
        1. Paste link or text 
        2. Select language you want to here audio in
        3. Choose what you want to here complete url or summary or it
        4. Click generate
        """)


# Health check indicator
with st.sidebar:
    st.divider()
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=2)
        if health_response.status_code == 200:
            st.success(" API Server: Online")
        else:
            st.error(" API Server: Error")
    except:
        st.error("API Server: Offline")