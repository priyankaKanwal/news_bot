from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag.document_loader import load_news_documents


def split_news_documents():

    # Step 1: Load original news documents
    documents = load_news_documents()

    print("Original documents:", len(documents))

    # Step 2: Create text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        add_start_index=True
    )

    # Step 3: Split documents into chunks
    chunks = text_splitter.split_documents(documents)

    return chunks


if __name__ == "__main__":

    chunks = split_news_documents()

    print("\nTotal chunks created:", len(chunks))

    for index, chunk in enumerate(chunks):

        print("\n------------------------------")
        print("Chunk number:", index + 1)
        print("Source:", chunk.metadata.get("source"))
        print("Start index:", chunk.metadata.get("start_index"))
        print("Content:", chunk.page_content)