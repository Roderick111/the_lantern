from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_get_briefing_structure():
    """Test that briefing returns new Dossier and TeachingQuestions structure."""
    case_id = "case_001"
    response = client.get(f"/api/briefing/{case_id}")
    assert response.status_code == 200

    data = response.json()

    # Check Dossier
    assert "dossier" in data
    dossier = data["dossier"]
    assert "title" in dossier
    assert "victim" in dossier
    assert dossier["victim"] == "Professor Aldric Vane (Alchemy Master)"

    # Check Teaching Questions
    assert "teaching_questions" in data
    assert isinstance(data["teaching_questions"], list)
    assert len(data["teaching_questions"]) > 0

    question = data["teaching_questions"][0]
    assert "prompt" in question
    assert "choices" in question
    assert len(question["choices"]) >= 2
