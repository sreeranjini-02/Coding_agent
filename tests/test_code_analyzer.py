from code_analyzer import check_code_syntax, check_python_syntax

def test_valid_python():
    assert check_python_syntax("def add(a, b):\n return a + b")["valid"] is True

def test_invalid_python():
    result = check_python_syntax("def add(a, b)\n return a + b")
    assert result["valid"] is False and result["line"] is not None

def test_sql_check_does_not_execute_query():
    assert check_code_syntax("SELECT * FROM users;", "SQL")["valid"] is True
    assert check_code_syntax("SELECT (", "SQL")["valid"] is False

