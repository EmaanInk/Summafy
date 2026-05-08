# Function to split large text into smaller chunks
def chunk_text(text, chunk_size=1500, overlap=100):
    
    words = text.split()    # Split the text into individual words
    chunks = []      # List to store all chunks
    start = 0       # Starting index for chunking
    while start < len(words):   # Continue until all words are processed
        end = start + chunk_size    # Define ending index of current chunk
        chunk = words[start:end]    # Extract words for current chunk
        chunks.append(" ".join(chunk))      # Convert chunk back into string and store it
        # Move start index forward
        # Overlap keeps some words repeated between chunks
        # to preserve context
        start += chunk_size - overlap

    return chunks   # Return list of text chunks