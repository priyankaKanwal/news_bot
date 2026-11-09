
from langchain_community.document_loaders import DirectoryLoader, TextLoader


def load_news_documents():
    loader = DirectoryLoader(
        "data/",
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    documents = loader.load()

    return documents


if __name__ == "__main__":
    documents = load_news_documents()

    print(f"Total documents loaded: {len(documents)}")

    for document in documents:
        print("\n------------------------------")
        print("Metadata:", document.metadata)
        print("Content:", document.page_content)
