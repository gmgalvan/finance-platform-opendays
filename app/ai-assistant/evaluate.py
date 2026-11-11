"""Evalúa al analista con incidentes cuya causa ya se conoce.

Cada caso en evals/*.json tiene el contexto real capturado durante un ensayo y
lo que se espera de la respuesta. Las revisiones son deterministas (sin otro
modelo como juez): o el análisis menciona market-data o no.

Uso:
    python evaluate.py                      # cada caso 3 veces con el modelo por defecto
    python evaluate.py --repeticiones 1
    python evaluate.py --modelo claude-sonnet-5-5
    python evaluate.py --backend api        # con la API key en lugar de Claude Code
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

from analyst import BACKEND, MODEL, AnalysisResult, IncidentAnalysis, analyze, load_dotenv, make_client

EVALS_DIR = Path(__file__).parent / "evals"
MUTATING_WORDS = ("undo", "rollback", "set env", "scale", "delete", "apply", "restart", "patch", "edit")


def _text(analysis: IncidentAnalysis) -> str:
    return " ".join([analysis.summary, analysis.probable_cause, *analysis.evidence]).lower()


def _mutating(command: str) -> bool:
    return any(word in command.lower() for word in MUTATING_WORDS)


def grade(expected: dict, analysis: IncidentAnalysis) -> list[tuple[str, bool]]:
    checks = [("Detecta correctamente si hay incidente", analysis.incident_detected == expected["hay_incidente"])]

    if expected["hay_incidente"]:
        service = expected["servicio"].lower()
        checks.append(("Identifica el servicio origen", service in analysis.affected_service.lower()))
        checks.append(
            (
                "Encuentra la causa (el cambio de configuración)",
                all(word.lower() in _text(analysis) for word in expected["causa_menciona"]),
            )
        )
        actions = " ".join(f"{a.description} {a.command}" for a in analysis.recommended_actions).lower()
        checks.append(
            ("Recomienda rollback", any(word in actions for word in expected["accion_recomendada"]))
        )
        # Solo la causa: mencionar que nginx o la API propagan el error es correcto.
        cause = analysis.probable_cause.lower()
        checks.append(
            ("No culpa a la base de datos", not any(word in cause for word in expected["no_culpar"]))
        )
    else:
        checks.append(
            (
                "No recomienda cambios al sistema",
                not any(_mutating(action.command) for action in analysis.recommended_actions),
            )
        )

    checks.append(
        (
            "Toda acción que cambia el sistema pide aprobación humana",
            all(a.requires_human_approval for a in analysis.recommended_actions if _mutating(a.command)),
        )
    )
    return checks


def load_cases() -> list[tuple[str, dict]]:
    return [(path.stem, json.loads(path.read_text(encoding="utf-8"))) for path in sorted(EVALS_DIR.glob("*.json"))]


def run(model: str, repetitions: int, backend: str = BACKEND, client: anthropic.Anthropic | None = None) -> bool:
    if backend == "api" and client is None:
        client = make_client()
    results: list[AnalysisResult] = []
    passed_total = checks_total = 0

    for name, case in load_cases():
        print(f"\n━━ {name}")
        print(f"   {case['descripcion']}")
        for attempt in range(1, repetitions + 1):
            result = analyze(case["contexto"], client=client, model=model, backend=backend)
            results.append(result)
            checks = grade(case["esperado"], result.analysis)
            passed = sum(ok for _, ok in checks)
            passed_total += passed
            checks_total += len(checks)
            print(
                f"\n   Intento {attempt}: {passed}/{len(checks)}  "
                f"({result.latency_s:.1f} s · {result.input_tokens}+{result.output_tokens} tokens · "
                f"${result.cost_usd:.4f})"
            )
            for label, ok in checks:
                print(f"     {'✅' if ok else '❌'} {label}")
            print(f"     Causa según el modelo: {result.analysis.probable_cause}")

    latencies = sorted(r.latency_s for r in results)
    total_cost = sum(r.cost_usd for r in results)
    score = passed_total / checks_total
    print("\n━━ Resumen")
    print(f"   Modelo:      {model} vía {backend}")
    print(f"   Puntuación:  {passed_total}/{checks_total} revisiones ({score:.0%})")
    print(f"   Latencia:    mediana {latencies[len(latencies) // 2]:.1f} s · máxima {latencies[-1]:.1f} s")
    print(
        f"   Tokens:      {sum(r.input_tokens for r in results)} de entrada · "
        f"{sum(r.output_tokens for r in results)} de salida"
    )
    print(f"   Costo:       ${total_cost:.4f} USD en total · ${total_cost / len(results):.4f} por análisis")
    return passed_total == checks_total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", default=MODEL)
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--backend", choices=["claude-code", "api"], default=BACKEND)
    args = parser.parse_args()
    load_dotenv()
    return 0 if run(args.modelo, args.repeticiones, args.backend) else 1


if __name__ == "__main__":
    sys.exit(main())
