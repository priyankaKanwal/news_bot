from pathlib import Path

from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader
)


DOCUMENT_TYPES = {
    "leave_policy.txt": "policy",
    "employee_directory.txt": "employee_directory",
    "expense_policy.txt": "policy",
    "project_allocation.txt": "project",
    "leave_balance.txt": "employee_data",
    "company_profile.txt": "company"
}


def load_news_documents():

    loader = DirectoryLoader(
        "data/",
        glob="*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )

    documents = loader.load()

    # Add custom metadata to every document
    for document in documents:

        filename = Path(document.metadata["source"]).name

        document.metadata["document_type"] = DOCUMENT_TYPES.get(
            filename,
            "general"
        )

    return documents


if __name__ == "__main__":

    documents = load_news_documents()

    print("Total documents:", len(documents))

    for document in documents:

        print("\nSource:", document.metadata.get("source"))
        print("Document type:", document.metadata.get("document_type"))