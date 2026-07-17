"""Worker CLI test — the loop drains the queue and exits at --max-iterations."""
import pytest

from llm_chat.models import AnalysisArtifact
from llm_chat.services.report_jobs import enqueue

DAY1 = 1780000000.0


@pytest.fixture(autouse=True)
def _fake_llm(monkeypatch):
    monkeypatch.setenv("CLOZE_FAKE_LLM", "1")
    monkeypatch.delenv("REPORTS_WORKER_MODE", raising=False)


def test_worker_cli_drains_queue(app, make_conversation):
    conv_a = make_conversation([("user", "First conversation.", DAY1)])
    conv_b = make_conversation([("user", "Second conversation.", DAY1)])
    enqueue("extract", conversation_id=conv_a.id)
    enqueue("extract", conversation_id=conv_b.id)

    runner = app.test_cli_runner()
    result = runner.invoke(args=["reports-worker", "--tick", "0", "--max-iterations", "3"])

    assert result.exit_code == 0, result.output
    assert "reports-worker stopped" in result.output
    assert result.output.count("-> done") == 2
    assert AnalysisArtifact.query.count() == 2
