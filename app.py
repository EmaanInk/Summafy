import streamlit as st
from file_reader import read_files
from chunker import chunk_text
from groq import Groq
from dotenv import load_dotenv
import os
import tempfile

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

if "mode" not in st.session_state:
    st.session_state.mode = None
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None

st.set_page_config(page_title="Summafy", page_icon="📄", layout="centered")
st.title("Summafy")
st.caption("From messy files to meaningful knowledge — effortlessly.")

uploaded_file = st.file_uploader("Upload your file", type=["pdf", "txt", "docx", "pptx"])

if uploaded_file:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        st.session_state.extracted_text = read_files(tmp_path)
        os.unlink(tmp_path)
    except Exception as e:
        st.error(f"Could not read file: {str(e)}")
        st.stop()

    st.success("File uploaded successfully!")
    with st.expander("See extracted text"):
        st.text_area("Extracted Text", value=st.session_state.extracted_text, height=300)
    st.divider()
    st.subheader("What do you want to do next?")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📝 Summarize"):
            st.session_state.mode = "summarize"
    with col2:
        if st.button("🧠 Take a Quiz"):
            st.session_state.mode = "quiz"
    with col3:
        if st.button("❓ Ask a Question"):
            st.session_state.mode = "ask"
    with col4:
        if st.button("🔍 More Details"):
            st.session_state.mode = "detail"

    # ── Summarize ──
    if st.session_state.mode == "summarize":
        chunks = chunk_text(st.session_state.extracted_text, chunk_size=1500, overlap=100)
        chunks = chunks[:3]
        progress = st.progress(0)
        try:
            for i, chunk in enumerate(chunks):
                progress.progress((i + 1) / len(chunks))
                st.markdown(f"### Section {i+1}")
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are an expert document summarizer. Create structured summaries with clear headings, bullet points, and highlighted key concepts. Make complex information easy to understand."},
                        {"role": "user", "content": f"Summarize this section thoroughly with headings and bullets. Do not skip any important concept:\n\n{chunk}"}
                    ],
                    stream=True
                )
                st.write_stream(
                    chunk.choices[0].delta.content or ""
                    for chunk in response
                )
            progress.empty()
            st.success("✅ Done! Scroll up to read your results.")
        except Exception as e:
            st.error(f"Could not generate summary. {str(e)}")

    # ── Quiz ──
    elif st.session_state.mode == "quiz":
        num_questions = st.number_input("How many questions?", min_value=5, max_value=30, value=10)
        if st.button("Generate Quiz"):
            try:
                chunks = chunk_text(st.session_state.extracted_text, chunk_size=1500, overlap=100)
                first_chunk = chunks[0] if chunks else st.session_state.extracted_text
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are an expert quiz maker. Generate MCQ questions with 4 options each (A, B, C, D). Mark the correct answer clearly. Go from easy to hard. Format each question clearly numbered."},
                        {"role": "user", "content": f"Generate {num_questions} MCQ questions from easy to hard based on this text:\n\n{first_chunk}"}
                    ],
                    stream=True
                )
                st.write_stream(
                    chunk.choices[0].delta.content or ""
                    for chunk in response
                )
                st.success("✅ Done!")
            except Exception as e:
                st.error(f"Could not generate quiz. {str(e)}")

    # ── Ask a Question ──
    elif st.session_state.mode == "ask":
        question = st.text_input("What do you want to know?")
        if st.button("Get Answer"):
            if not question:
                st.warning("Please type a question first!")
            else:
                try:
                    chunks = chunk_text(st.session_state.extracted_text, chunk_size=1500, overlap=100)
                    first_chunk = chunks[0] if chunks else st.session_state.extracted_text
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": "You are a helpful document assistant. Answer questions based ONLY on the provided text. If the answer isn't in the text, say so honestly. Be specific and cite relevant parts."},
                            {"role": "user", "content": f"Answer this question: {question}\n\nBased on this text:\n\n{first_chunk}"}
                        ],
                        stream=True
                    )
                    st.write_stream(
                        chunk.choices[0].delta.content or ""
                        for chunk in response
                    )
                    st.success("✅ Done!")
                except Exception as e:
                    st.error(f"Could not get answer. {str(e)}")

    # ── More Details ──
    elif st.session_state.mode == "detail":
        chunks = chunk_text(st.session_state.extracted_text, chunk_size=1500, overlap=100)
        chunks = chunks[:3]
        progress = st.progress(0)
        try:
            for i, chunk in enumerate(chunks):
                progress.progress((i + 1) / len(chunks))
                st.markdown(f"### Section {i+1}")
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are an expert educator. Expand on the given text with additional context, real world examples, analogies, and deeper explanations. Use headings and bullets. Be thorough and detailed."},
                        {"role": "user", "content": f"Take this text and expand it massively. For every concept mentioned:\n- Give a detailed explanation\n- Give a real world example\n- Give an analogy that makes it easy to understand\n- Add any related information a student would need to know\n- Explain WHY it matters\n\nBe thorough and detailed. Do not be brief.\n\nText:\n{chunk}"}
                    ],
                    stream=True
                )
                st.write_stream(
                    chunk.choices[0].delta.content or ""
                    for chunk in response
                )
            progress.empty()
            st.success("✅ Done! Scroll up to read your results.")
        except Exception as e:
            st.error(f"Could not generate details. {str(e)}")