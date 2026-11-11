from ingestion.files import load_file

def test_load_source_file(tmp_path):
    path = tmp_path / "Example.java"
    path.write_text("class Example {}", encoding="utf-8")
    doc = load_file(path)
    assert doc and doc.kind == "file" and "class Example" in doc.text

def test_ignore_unknown_binary(tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"data")
    assert load_file(path) is None

