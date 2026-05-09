# ── Imports ──
# streamlit is the framework that turns this python script into a web app
import streamlit as st

# our own file we wrote — contains read_pdf, read_txt, read_docx, read_pptx, read_file
from file_reader import read_files

# our own file we wrote — contains chunk_text that splits large text into smaller pieces
from chunker import chunk_text

# groq is the library that connects us to the LLaMA AI model
from groq import Groq

# load_dotenv reads our .env file and makes GROQ_API_KEY available to the program
from dotenv import load_dotenv

# os lets us interact with the operating system — we use it to delete temp files
import os

# tempfile lets us create temporary files on disk — needed because streamlit
# gives us file objects in memory but our readers need actual file paths
import tempfile

# ── Setup ──
# actually runs load_dotenv — without this line our API key won't be found
load_dotenv()

# creates one connection to groq API that the whole app uses
# api_key reads GROQ_API_KEY from our .env file via os.getenv
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Session State ──
# streamlit reruns the entire script on every user interaction
# session state is a special dictionary that survives those reruns
# the if check means "only create this the first time, not on every rerun"

# mode tracks which button the user clicked — summarize, quiz, ask, or detail
if "mode" not in st.session_state:
    st.session_state.mode = None

# extracted_text stores the text from the uploaded file
# stored in session state so we don't re-read the file on every button click
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None

# chat_history stores the conversation in the chat sidebar
# list of dictionaries like {"role": "user", "content": "hello"}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Page Config ──
# must be the first streamlit command — sets browser tab title, icon, and layout
# layout="wide" gives us full screen width — needed for two column layout
st.set_page_config(page_title="Summafy", page_icon="📄", layout="wide")

# ── Header ──
# displays the main title on the page
st.title("Summafy")

# displays a small subtitle below the title
st.caption("From messy files to meaningful knowledge — effortlessly.")

# ── File Upload ──
# creates a file upload widget that accepts only these four file types
# returns None if no file uploaded, returns a file object if uploaded
uploaded_file = st.file_uploader("Upload your file", type=["pdf", "txt", "docx", "pptx"])

# everything below only runs if the user has actually uploaded a file
if uploaded_file:

    # ── File Reading ──
    try:
        # tempfile.NamedTemporaryFile creates a temporary file on disk
        # delete=False means don't delete it immediately — we need it to stay
        # suffix gives it the right extension (.pdf, .txt etc) so our reader knows what type it is
        # uploaded_file.name is the original filename like "notes.pdf"
        # .split('.')[-1] splits by dot and takes the last part — the extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
            # reads all bytes from the uploaded file and writes to the temp file
            tmp.write(uploaded_file.read())
            # saves the path of the temp file so we can pass it to read_files()
            tmp_path = tmp.name

        # calls read_files() from file_reader.py with the temp file path
        # read_files() detects the extension and calls the right reader function
        # returns all the text as one big string — stored in session state
        st.session_state.extracted_text = read_files(tmp_path)

        # deletes the temp file now that we have the text — clean up after ourselves
        os.unlink(tmp_path)

    # if anything goes wrong during file reading — wrong format, corrupted file etc
    except Exception as e:
        # shows a red error message to the user with what went wrong
        st.error(f"Could not read file: {str(e)}")
        # stops the entire app from running further — without this it would crash
        # trying to use text that doesn't exist
        st.stop()

    # shows a green success message after file is read successfully
    st.success("File uploaded successfully!")

    # expander is a collapsible section — collapsed by default
    # user can click to see the raw extracted text if they want to verify it
    with st.expander("See extracted text"):
        # displays the extracted text in a scrollable box
        # value= fills it with our extracted text
        # height=300 makes it 300 pixels tall
        st.text_area("Extracted Text", value=st.session_state.extracted_text, height=300)

    # draws a horizontal dividing line
    st.divider()

    st.subheader("What do you want to do next?")

    # ── Two Column Layout ──
    # splits the screen into two columns
    # [1.5, 1] means left column is 1.5x wider than right column
    # left = main content area, right = chat sidebar
    main_col, chat_col = st.columns([1.5, 1])

    # ── Main Column ──
    with main_col:

        # splits main_col into 3 equal columns for the three mode buttons
        col1, col2, col3 = st.columns(3)

        # each button is in its own column so they appear side by side
        # st.button() returns True when clicked — that's why we use if
        # when clicked we store the mode in session state so it survives the rerun
        with col1:
            if st.button("📝 Summarize"):
                st.session_state.mode = "summarize"
        with col2:
            if st.button("🧠 Take a Quiz"):
                st.session_state.mode = "quiz"
        with col3:
            if st.button("🔍 More Details"):
                st.session_state.mode = "detail"

        # ── Summarize Mode ──
        if st.session_state.mode == "summarize":

            # splits text into chunks of 1500 words with 100 word overlap
            # overlap means consecutive chunks share 100 words so context isn't lost
            chunks = chunk_text(st.session_state.extracted_text, chunk_size=1500, overlap=100)

            # only process first 3 chunks to save tokens and time
            chunks = chunks[:3]

            # creates a progress bar starting at 0
            progress = st.progress(0)

            try:
                # loops through each chunk with its index number
                for i, chunk in enumerate(chunks):

                    # updates progress bar — (i+1)/len(chunks) gives a value between 0 and 1
                    # e.g. chunk 1 of 3 = 0.33, chunk 2 of 3 = 0.66, chunk 3 of 3 = 1.0
                    progress.progress((i + 1) / len(chunks))

                    # shows a heading for each section
                    st.markdown(f"### Section {i+1}")

                    # sends this chunk to the AI model
                    response = client.chat.completions.create(
                        # smaller faster model — uses fewer tokens
                        model="llama-3.1-8b-instant",
                        messages=[
                            # system message tells AI what its job is
                            {"role": "system", "content": "You are an expert document summarizer. Create structured summaries with clear headings, bullet points, and highlighted key concepts. Make complex information easy to understand."},
                            # user message contains the actual chunk of text to summarize
                            {"role": "user", "content": f"Summarize this section thoroughly with headings and bullets. Do not skip any important concept:\n\n{chunk}"}
                        ],
                        # stream=True makes text appear word by word instead of all at once
                        stream=True
                    )

                    # st.write_stream reads each chunk from the streaming response
                    # and displays it as it arrives — creates the typing effect
                    # "or ''" handles None chunks that groq sends between text chunks
                    st.write_stream(
                        chunk.choices[0].delta.content or ""
                        for chunk in response
                    )

                # removes the progress bar after all chunks are done
                progress.empty()

                # shows green success message
                st.success("✅ Done! Scroll up to read your results.")

            # catches any error from the API — rate limits, timeouts etc
            except Exception as e:
                st.error(f"Could not generate summary. {str(e)}")

        # ── Quiz Mode ──
        elif st.session_state.mode == "quiz":

            # number input widget — user sets how many questions they want
            # min_value and max_value set the allowed range
            # value=10 is the default
            num_questions = st.number_input("How many questions?", min_value=5, max_value=30, value=10)

            # quiz only generates when user clicks this button
            # prevents auto-generation every time the screen reruns
            if st.button("Generate Quiz"):
                try:
                    chunks = chunk_text(st.session_state.extracted_text, chunk_size=1500, overlap=100)

                    # for quiz we only use the first chunk
                    # if chunks is empty for some reason, fall back to full text
                    first_chunk = chunks[0] if chunks else st.session_state.extracted_text

                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": "You are an expert quiz maker. Generate MCQ questions with 4 options each (A, B, C, D). Mark the correct answer clearly. Go from easy to hard. Format each question clearly numbered."},
                            # f-string injects num_questions and first_chunk into the prompt
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

        # ── More Details Mode ──
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

    # ── Chat Column ──
    with chat_col:
        st.subheader("💬 Ask your document")

        # displays all previous messages in the chat history
        # loops through each message dictionary in the list
        for msg in st.session_state.chat_history:
            # st.chat_message shows user or assistant bubble based on role
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # chat_input is a fixed input box at the bottom of the column
        # returns the typed message when user hits enter, None otherwise
        question = st.chat_input("Ask anything about your document...")

        if question:
            # immediately add user message to history so it shows up
            st.session_state.chat_history.append({"role": "user", "content": question})

            # chunk the text and use first chunk for answering
            chunks = chunk_text(st.session_state.extracted_text, chunk_size=1500, overlap=100)
            first_chunk = chunks[0] if chunks else st.session_state.extracted_text

            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a helpful document assistant. Answer questions based ONLY on the provided document text. Be specific and concise."},
                        # includes both the document text and the user's question
                        {"role": "user", "content": f"Document:\n{first_chunk}\n\nQuestion: {question}"}
                    ]
                    # no stream=True here — we collect full answer then display
                )

                # extracts the text content from the response object
                answer = response.choices[0].message.content

                # adds AI response to chat history
                st.session_state.chat_history.append({"role": "assistant", "content": answer})

                # forces streamlit to rerun the script so the new message appears
                # without this the chat wouldn't update visually
                st.rerun()

            except Exception as e:
                st.error(f"Could not get answer: {str(e)}")

# shown at the bottom regardless of whether a file is uploaded or not
# honest transparency about current limitations
st.info("💡 Note: Summafy reads text content. Images and diagrams inside documents are not processed yet.")