from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from memory_systems.pipeline import (
    build_default_stack,
    build_prompt,
    count_words,
    create_nvidia_client_from_env,
    memory_router,
    save_memory_updates,
)


@dataclass
class Scenario:
    idx: int
    title: str
    turns: list[tuple[str, str]]
    final_query: str
    semantic_docs: list[str]
    no_memory_reference: str
    expected_keywords: list[str]
    memory_budget: int = 220


def scenarios() -> list[Scenario]:
    return [
        Scenario(
            idx=1,
            title="Profile recall: name after 6 turns",
            turns=[
                ("user", "Chào bạn."),
                ("user", "Tên tôi là Linh."),
                ("assistant", "Chào Linh, mình có thể giúp gì?"),
                ("user", "Cho tôi checklist debug API."),
                ("assistant", "Checklist: kiểm tra log, timeout, retry, dependency."),
                ("user", "Bây giờ nhắc lại tên tôi."),
            ],
            final_query="Bây giờ nhắc lại tên tôi.",
            semantic_docs=[],
            no_memory_reference="Mình chưa biết tên bạn.",
            expected_keywords=["Linh"],
        ),
        Scenario(
            idx=2,
            title="Conflict update: allergy correction",
            turns=[
                ("user", "Tôi dị ứng sữa bò."),
                ("assistant", "Mình đã ghi nhớ."),
                ("user", "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò."),
                ("assistant", "Mình cập nhật lại rồi."),
                ("user", "Tôi dị ứng gì?"),
            ],
            final_query="Tôi dị ứng gì?",
            semantic_docs=[],
            no_memory_reference="Bạn dị ứng sữa bò.",
            expected_keywords=["đậu nành"],
        ),
        Scenario(
            idx=3,
            title="Profile recall: location after topic switch",
            turns=[
                ("user", "Tôi sống ở Đà Nẵng."),
                ("user", "Cho tôi mẹo học system design."),
                ("assistant", "Tập trung trade-off và CAP theorem."),
                ("user", "Gợi ý quán cà phê để làm việc gần tôi."),
            ],
            final_query="Gợi ý quán cà phê để làm việc gần tôi.",
            semantic_docs=[],
            no_memory_reference="Bạn ở đâu vậy?",
            expected_keywords=["Đà Nẵng"],
        ),
        Scenario(
            idx=4,
            title="Episodic recall: previous debug outcome",
            turns=[
                ("user", "Hôm qua chúng ta debug lỗi DB timeout."),
                ("assistant", "Đã xong: root cause là dùng sai Docker service name."),
                ("user", "Nhắc lại bài học debug hôm qua."),
            ],
            final_query="Nhắc lại bài học debug hôm qua.",
            semantic_docs=["Trong Docker Compose, service name được dùng làm hostname nội bộ."],
            no_memory_reference="Không có dữ liệu phiên trước.",
            expected_keywords=["service name", "hostname"],
        ),
        Scenario(
            idx=5,
            title="Episodic recall: done task status",
            turns=[
                ("user", "Nhờ bạn tổng hợp nguyên nhân fail deploy."),
                ("assistant", "Hoàn tất: thiếu biến môi trường REDIS_URL trên staging."),
                ("user", "Task deploy đã xong chưa và kết quả gì?"),
            ],
            final_query="Task deploy đã xong chưa và kết quả gì?",
            semantic_docs=[],
            no_memory_reference="Chưa rõ trạng thái task.",
            expected_keywords=["hoàn tất", "REDIS_URL"],
        ),
        Scenario(
            idx=6,
            title="Semantic retrieval: Docker FAQ chunk",
            turns=[("user", "Trong Docker Compose, app nên gọi DB bằng gì?")],
            final_query="Trong Docker Compose, app nên gọi DB bằng gì?",
            semantic_docs=["Trong Docker Compose, service name được dùng làm hostname nội bộ."],
            no_memory_reference="Dùng localhost.",
            expected_keywords=["service name", "hostname"],
        ),
        Scenario(
            idx=7,
            title="Semantic retrieval: retry policy chunk",
            turns=[("user", "Retry request thế nào để giảm retry storm?")],
            final_query="Retry request thế nào để giảm retry storm?",
            semantic_docs=[
                "Khi gọi API không ổn định, dùng exponential backoff và jitter để giảm đồng bộ retry."
            ],
            no_memory_reference="Retry liên tục mỗi 1 giây.",
            expected_keywords=["exponential backoff", "jitter"],
        ),
        Scenario(
            idx=8,
            title="Mixed recall: profile + semantic together",
            turns=[
                ("user", "Tên tôi là Linh."),
                ("user", "Tôi làm nghề kỹ sư dữ liệu."),
                ("user", "Docker Compose gọi DB bằng gì? Và gọi tôi thế nào cho đúng?"),
            ],
            final_query="Docker Compose gọi DB bằng gì? Và gọi tôi thế nào cho đúng?",
            semantic_docs=["Trong Docker Compose, service name được dùng làm hostname nội bộ."],
            no_memory_reference="Trả lời thiếu tên hoặc thiếu chunk kỹ thuật.",
            expected_keywords=["Linh", "service name"],
        ),
        Scenario(
            idx=9,
            title="Trim/token budget in long chat",
            turns=[
                *[
                    ("user", f"Đây là turn dài số {i}: " + "chi tiết không liên quan " * 12)
                    for i in range(1, 23)
                ],
                ("user", "Tóm tắt lại điều quan trọng nhất và nhắc profile."),
            ],
            final_query="Tóm tắt lại điều quan trọng nhất và nhắc profile.",
            semantic_docs=["Trong Docker Compose, service name được dùng làm hostname nội bộ."],
            no_memory_reference="Prompt quá dài, lẫn nhiều nhiễu.",
            expected_keywords=["tóm tắt", "profile"],
            memory_budget=90,
        ),
        Scenario(
            idx=10,
            title="Multi-fact update: occupation + timezone",
            turns=[
                ("user", "Tôi làm nghề backend engineer."),
                ("user", "Tôi ở UTC+7."),
                ("user", "À cập nhật lại, tôi chuyển sang platform engineer."),
                ("user", "Nhắc lại nghề hiện tại và timezone của tôi."),
            ],
            final_query="Nhắc lại nghề hiện tại và timezone của tôi.",
            semantic_docs=[],
            no_memory_reference="Không nhớ hoặc nghề cũ.",
            expected_keywords=["platform engineer", "UTC+7"],
        ),
    ]


def _state_template(memory_budget: int) -> dict[str, Any]:
    return {
        "messages": [],
        "user_profile": {},
        "episodes": [],
        "semantic_hits": [],
        "memory_budget": memory_budget,
    }


def _invoke_llm(llm: Any, prompt: str) -> str:
    try:
        completion = llm.invoke([{"role": "user", "content": prompt}])
        content = str(getattr(completion, "content", "")).strip()
        if content:
            return content
        return "[LLM ERROR] Empty response."
    except Exception as exc:
        return f"[LLM ERROR] {exc}"


def _build_no_memory_prompt(scenario: Scenario) -> str:
    return "\n".join(
        [
            "You are a helpful assistant.",
            "Answer concisely based only on the current user message.",
            "Do not assume any stored memory.",
            "",
            "[CURRENT USER MESSAGE]",
            scenario.final_query,
        ]
    )


def _prepare_stack_for_with_memory(scenario: Scenario, scenario_dir: Path) -> tuple[Any, dict[str, Any], str]:
    if scenario_dir.exists():
        shutil.rmtree(scenario_dir)
    scenario_dir.mkdir(parents=True, exist_ok=True)

    stack = build_default_stack(scenario_dir)
    if scenario.semantic_docs:
        stack.semantic.add_documents(
            scenario.semantic_docs,
            metadata=[{"scenario": scenario.idx} for _ in scenario.semantic_docs],
        )

    last_user = ""
    for role, content in scenario.turns:
        if role == "user":
            stack.short_term.add_message("user", content)
            save_memory_updates(stack, user_text=content)
            last_user = content
        else:
            stack.short_term.add_message("assistant", content)
            if last_user:
                save_memory_updates(
                    stack,
                    user_text=last_user,
                    assistant_text=content,
                    task_name=f"scenario-{scenario.idx}",
                )

    state = _state_template(memory_budget=scenario.memory_budget)
    state = memory_router(state, stack)
    prompt = build_prompt(state, scenario.final_query)
    return stack, state, prompt


def _contains_keywords(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return all(keyword.lower() in lowered for keyword in keywords)


def _render_markdown(results: list[dict[str, Any]], output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Benchmark Run Output (LLM-backed)")
    lines.append("")
    lines.append(f"- Generated at: `{datetime.now().isoformat(timespec='seconds')}`")
    lines.append(f"- Total scenarios: `{len(results)}`")
    lines.append("")
    lines.append(
        "| # | Scenario | No-memory (LLM) | With-memory (LLM) | With-memory contains expected keywords? |"
    )
    lines.append("|---|---|---|---|---|")
    for item in results:
        lines.append(
            f"| {item['idx']} | {item['title']} | {item['no_memory_output']} | {item['with_memory_output']} | {'Pass' if item['with_memory_contains_expected'] else 'Fail'} |"
        )
    lines.append("")

    for item in results:
        lines.append(f"## Scenario {item['idx']}: {item['title']}")
        lines.append("")
        lines.append("Turns:")
        for turn in item["turns"]:
            lines.append(f"- {turn['role']}: {turn['content']}")
        lines.append("")
        lines.append(f"- Reference no-memory (from BENCHMARK.md): `{item['no_memory_reference']}`")
        lines.append(f"- No-memory LLM output: `{item['no_memory_output']}`")
        lines.append(f"- With-memory LLM output: `{item['with_memory_output']}`")
        lines.append(f"- Expected keywords: `{', '.join(item['expected_keywords'])}`")
        lines.append(
            f"- Contains expected keywords: `{'Pass' if item['with_memory_contains_expected'] else 'Fail'}`"
        )
        lines.append(
            f"- Prompt words: no-memory=`{item['no_memory_prompt_words']}`, with-memory=`{item['with_memory_prompt_words']}`"
        )
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    llm = create_nvidia_client_from_env()
    items = scenarios()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    outputs_dir = Path("benchmark_outputs")
    outputs_dir.mkdir(exist_ok=True)
    run_dir = outputs_dir / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for scenario in items:
        no_memory_prompt = _build_no_memory_prompt(scenario)
        no_memory_output = _invoke_llm(llm, no_memory_prompt)

        scenario_dir = run_dir / f"scenario_{scenario.idx:02d}"
        _, state, with_memory_prompt = _prepare_stack_for_with_memory(scenario, scenario_dir=scenario_dir)
        with_memory_output = _invoke_llm(llm, with_memory_prompt)

        with_memory_contains_expected = _contains_keywords(with_memory_output, scenario.expected_keywords)
        no_memory_contains_expected = _contains_keywords(no_memory_output, scenario.expected_keywords)

        results.append(
            {
                "idx": scenario.idx,
                "title": scenario.title,
                "turns": [{"role": role, "content": content} for role, content in scenario.turns],
                "no_memory_reference": scenario.no_memory_reference,
                "expected_keywords": scenario.expected_keywords,
                "no_memory_prompt": no_memory_prompt,
                "with_memory_prompt": with_memory_prompt,
                "no_memory_output": no_memory_output,
                "with_memory_output": with_memory_output,
                "no_memory_prompt_words": count_words(no_memory_prompt),
                "with_memory_prompt_words": count_words(with_memory_prompt),
                "no_memory_contains_expected": no_memory_contains_expected,
                "with_memory_contains_expected": with_memory_contains_expected,
                "memory_state": state,
            }
        )
        print(
            f"[Scenario {scenario.idx}] no-memory keywords={no_memory_contains_expected}, "
            f"with-memory keywords={with_memory_contains_expected}"
        )

    json_path = outputs_dir / f"benchmark_run_{timestamp}.json"
    md_path = outputs_dir / f"benchmark_run_{timestamp}.md"
    latest_json = outputs_dir / "latest.json"
    latest_md = outputs_dir / "latest.md"

    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    _render_markdown(results, md_path)
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    with_memory_pass = sum(1 for row in results if row["with_memory_contains_expected"])
    print(f"Benchmark done with LLM: {with_memory_pass}/{len(results)} with-memory cases contain expected keywords.")
    print(f"Saved markdown: {md_path}")
    print(f"Saved json: {json_path}")
    print(f"Latest markdown: {latest_md}")
    print(f"Latest json: {latest_json}")


if __name__ == "__main__":
    main()
