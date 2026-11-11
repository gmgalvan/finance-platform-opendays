"""Pruebas del asistente de IA sin llamar a la API (no gastan dinero)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app" / "ai-assistant"))

import analyst  # noqa: E402
import evaluate  # noqa: E402
from analyst import Action, IncidentAnalysis  # noqa: E402

INCIDENT = evaluate.EVALS_DIR / "market-data-cambio-de-configuracion.json"
HEALTHY = evaluate.EVALS_DIR / "sistema-sano.json"


def make_analysis(**overrides) -> IncidentAnalysis:
    values = {
        "incident_detected": True,
        "summary": "market-data falla la mitad de las solicitudes.",
        "user_impact": "La tabla de cotizaciones muestra datos de ejemplo.",
        "affected_service": "market-data",
        "probable_cause": "Cambio de configuración FAILURE_RATE=0.5 en market-data.",
        "evidence": ["rollout history: Config: FAILURE_RATE=0.5", "503 en /api/market/quotes"],
        "confidence": "alta",
        "recommended_actions": [
            Action(
                description="Revertir market-data",
                command="kubectl -n finance rollout undo deployment/market-data",
                requires_human_approval=True,
            )
        ],
        "open_questions": [],
    }
    values.update(overrides)
    return IncidentAnalysis(**values)


class FakeMessages:
    def __init__(self, parsed, stop_reason="end_turn"):
        self.parsed = parsed
        self.stop_reason = stop_reason
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            parsed_output=self.parsed,
            stop_reason=self.stop_reason,
            stop_details=None,
            usage=SimpleNamespace(input_tokens=5000, output_tokens=1000),
        )


def fake_client(parsed, stop_reason="end_turn"):
    return SimpleNamespace(messages=FakeMessages(parsed, stop_reason))


def expected(path):
    return json.loads(path.read_text(encoding="utf-8"))["esperado"]


def test_eval_cases_are_valid():
    cases = dict(evaluate.load_cases())
    assert set(cases) == {"market-data-cambio-de-configuracion", "sistema-sano"}
    for case in cases.values():
        assert {"descripcion", "esperado", "contexto"} <= set(case)
        assert {"prometheus", "jaeger", "kubernetes"} <= set(case["contexto"])


def test_correct_incident_analysis_passes_every_check():
    checks = evaluate.grade(expected(INCIDENT), make_analysis())

    assert all(ok for _, ok in checks), checks


@pytest.mark.parametrize(
    ("overrides", "failing_check"),
    [
        ({"affected_service": "PostgreSQL"}, "Identifica el servicio origen"),
        ({"probable_cause": "PostgreSQL está saturado; FAILURE_RATE no influye"}, "No culpa a la base de datos"),
        ({"probable_cause": "La base de datos está lenta", "evidence": [], "summary": "Errores"}, "Encuentra la causa (el cambio de configuración)"),
        ({"recommended_actions": []}, "Recomienda rollback"),
        (
            {
                "recommended_actions": [
                    Action(description="Rollback", command="kubectl rollout undo deployment/market-data", requires_human_approval=False)
                ]
            },
            "Toda acción que cambia el sistema pide aprobación humana",
        ),
    ],
)
def test_wrong_incident_analysis_fails_the_right_check(overrides, failing_check):
    checks = dict(evaluate.grade(expected(INCIDENT), make_analysis(**overrides)))

    assert checks[failing_check] is False


def test_inventing_an_incident_on_a_healthy_system_fails():
    checks = dict(evaluate.grade(expected(HEALTHY), make_analysis()))

    assert checks["Detecta correctamente si hay incidente"] is False
    assert checks["No recomienda cambios al sistema"] is False


def test_analyze_sends_context_without_tools_and_computes_cost():
    client = fake_client(make_analysis())
    context = json.loads(INCIDENT.read_text(encoding="utf-8"))["contexto"]

    result = analyst.analyze(context, client=client, model="claude-haiku-5-5")

    call = client.messages.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert "tools" not in call
    assert call["output_format"] is IncidentAnalysis
    assert "FAILURE_RATE" in call["messages"][0]["content"]
    assert result.cost_usd == pytest.approx((5000 * 0.10 + 1000 * 0.50) / 1_000_000)


def test_refusal_is_reported():
    with pytest.raises(analyst.AnalysisRefused):
        analyst.analyze({}, client=fake_client(None, stop_reason="refusal"))


def test_render_marks_actions_that_need_approval():
    result = analyst.AnalysisResult(make_analysis(), "claude-haiku-5-5", 2.0, 5000, 1000)

    text = analyst.render(result)

    assert "requiere aprobación humana" in text
    assert "La IA no ejecutó nada" in text


def test_claude_code_backend_runs_without_tools_or_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-no-debe-usarse")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        output = {
            "is_error": False,
            "structured_output": make_analysis().model_dump(),
            "total_cost_usd": 0.0021,
            "modelUsage": {
                "claude-haiku-5-5": {
                    "inputTokens": 100,
                    "cacheCreationInputTokens": 4000,
                    "cacheReadInputTokens": 0,
                    "outputTokens": 900,
                }
            },
        }
        return SimpleNamespace(stdout=json.dumps(output), stderr="", returncode=0)

    result = analyst.analyze_with_claude_code({"prueba": True}, "claude-haiku-5-5", runner=fake_run)

    command = captured["command"]
    assert command[:2] == ["claude", "-p"]
    assert command[command.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in command
    assert not any(key.startswith("ANTHROPIC_") for key in captured["env"])
    assert result.analysis.affected_service == "market-data"
    assert (result.input_tokens, result.output_tokens) == (4100, 900)
    assert result.cost_usd == 0.0021
    assert result.backend == "claude-code"


def test_claude_code_error_is_reported():
    def fake_run(command, **kwargs):
        return SimpleNamespace(stdout=json.dumps({"is_error": True, "result": "sin sesión"}), stderr="", returncode=1)

    with pytest.raises(RuntimeError, match="sin sesión"):
        analyst.analyze_with_claude_code({}, runner=fake_run)
