import streamlit as st
import re
from lanchain_helper import get_similar_answer_from_documents
import pyttsx3  # Text-to-speech
import speech_recognition as sr  # Speech recognition
import threading  # Non-blocking TTS

# 🎨 Streamlit Chatbot UI
col1, col2 = st.columns([0.1, 1])

with col1:
    st.image("kenai.png", width=50)

with col2:
    st.markdown("<h1 style='display: flex; align-items: center;'>Oracle Convopilot</h1>", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# ✅ Initialize TTS Engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1)

# ✅ Function to Convert Text to Speech in a Separate Thread
def speak_text(text):
    def run_speech():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=run_speech, daemon=True).start()

# ✅ Function to Capture Voice Input
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            query = recognizer.recognize_google(audio)
            return query
        except sr.WaitTimeoutError:
            return "You didn't say anything. Please try again."
        except sr.UnknownValueError:
            return "Sorry, I didn't catch that. Please try again."
        except sr.RequestError:
            return "Could not request results. Check your internet connection."
    return None

# ✅ Display chat history ABOVE input section
chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# ✅ Fixed input and mic button at the bottom
input_container = st.container()
with input_container:
    input_col, mic_col = st.columns([0.9, 0.1])
    with input_col:
        question = st.chat_input("Ask me anything...")
    with mic_col:
        if st.button("🎤", help="Click to speak", type="primary"):
            voice_input = get_voice_input()
            if voice_input:
                question = voice_input

# ✅ Process the question and generate a response
if question:
    if not re.match(r'^[a-zA-Z0-9\s?.,!@#$%^&*()_+=-]*$', question) or len(question.strip()) < 3:
        response = "I couldn't understand that. Please ask a clear question."
        full_doc = None
    else:
        with st.spinner("🔍 Fetching from SharePoint..."):
            response, full_doc = get_similar_answer_from_documents(question)
    
    # ✅ Add messages to history
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # ✅ Update chat display
    with chat_container:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            st.markdown(response)
    
    # ✅ Show full document content
    if full_doc:
        with st.expander("📄 View Full Document"):
            st.text_area("Document Content", full_doc, height=400)
    
    # ✅ Read out the answer
    speak_text(response)
