"""Unit tests for execution classes."""

from dinbutler.execution import Execution, ExecutionError, Result


class TestResult:
    """Tests for the Result class."""

    def test_empty_result(self) -> None:
        """Test that an empty result is detected."""
        result = Result()
        assert result.is_empty

    def test_result_with_text(self) -> None:
        """Test result with text content."""
        result = Result(text="Hello, World!")
        assert not result.is_empty
        assert result.text == "Hello, World!"

    def test_result_with_html(self) -> None:
        """Test result with HTML content."""
        result = Result(html="<p>Hello</p>")
        assert not result.is_empty
        assert result.html == "<p>Hello</p>"


class TestExecutionError:
    """Tests for the ExecutionError class."""

    def test_error_string(self) -> None:
        """Test error string representation."""
        error = ExecutionError(
            name="ValueError",
            value="invalid input",
            traceback="Traceback...",
        )
        assert "ValueError" in str(error)
        assert "invalid input" in str(error)


class TestExecution:
    """Tests for the Execution class."""

    def test_successful_execution(self) -> None:
        """Test a successful execution."""
        execution = Execution(
            results=[Result(text="output")],
            exit_code=0,
        )
        assert execution
        assert execution.text == "output"
        assert execution.error is None

    def test_failed_execution(self) -> None:
        """Test a failed execution."""
        execution = Execution(
            results=[],
            error=ExecutionError(
                name="Error",
                value="failed",
                traceback="",
            ),
            exit_code=1,
        )
        assert not execution
        assert execution.error is not None

    def test_multiple_results(self) -> None:
        """Test execution with multiple results."""
        execution = Execution(
            results=[
                Result(text="line1"),
                Result(text="line2"),
            ],
        )
        assert execution.text == "line1\nline2"

    def test_html_result(self) -> None:
        """Test execution with HTML result."""
        execution = Execution(
            results=[
                Result(text="text"),
                Result(html="<p>html</p>"),
            ],
        )
        assert execution.html == "<p>html</p>"

    def test_no_html_result(self) -> None:
        """Test execution without HTML result."""
        execution = Execution(results=[Result(text="text")])
        assert execution.html is None
