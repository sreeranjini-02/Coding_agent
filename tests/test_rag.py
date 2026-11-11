import chromadb


def test_document_indexing():
    client = chromadb.EphemeralClient()
    collection = client.create_collection(name="test_indexing")

    collection.add(
        ids=["doc1", "doc2"],
        documents=[
            "Python is used for AI and machine learning.",
            "SQL is used for database queries.",
        ],
    )

    results = collection.get()

    assert len(results["ids"]) == 2
    assert "doc1" in results["ids"]
    assert "doc2" in results["ids"]


def test_document_search():
    client = chromadb.EphemeralClient()
    collection = client.create_collection(name="test_search")

    collection.add(
        ids=["python_doc", "sql_doc"],
        documents=[
            "Python programming and machine learning.",
            "SQL databases and database queries.",
        ],
    )

    results = collection.get(ids=["python_doc"])

    assert len(results["ids"]) == 1
    assert results["ids"][0] == "python_doc"
    assert "Python" in results["documents"][0]


def test_document_metadata():
    client = chromadb.EphemeralClient()
    collection = client.create_collection(name="test_metadata")

    collection.add(
        ids=["doc1"],
        documents=["Python engineering guidelines."],
        metadatas=[
            {"source": "python_advanced.md", "category": "python"}
        ],
    )

    results = collection.get(
        ids=["doc1"],
        include=["documents", "metadatas"],
    )

    assert results["documents"][0] == "Python engineering guidelines."
    assert results["metadatas"][0]["source"] == "python_advanced.md"
    assert results["metadatas"][0]["category"] == "python"