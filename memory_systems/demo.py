from __future__ import annotations

import sys

from .pipeline import (
    MemoryGraphSkeleton,
    build_default_stack,
    create_nvidia_client_from_env,
    save_memory_updates,
)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    stack = build_default_stack("data")
    try:
        llm = create_nvidia_client_from_env()
    except Exception as exc:
        llm = None
        print(f"[WARN] NVIDIA NIM is not configured: {exc}")

    graph = MemoryGraphSkeleton(stack, llm=llm)

    stack.semantic.add_documents(
        [
            "Trong Docker Compose, service name được dùng làm hostname nội bộ.",
            "Khi timeout DB, ưu tiên kiểm tra network policy và DNS.",
        ],
        metadata=[{"topic": "docker"}, {"topic": "debug"}],
    )

    save_memory_updates(stack, "Tên tôi là Linh. Tôi sống ở Đà Nẵng.")
    save_memory_updates(stack, "Tôi dị ứng sữa bò.")
    save_memory_updates(stack, "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.")
    save_memory_updates(
        stack,
        "Nhờ tôi checklist lỗi kết nối.",
        "Đã xong: đã xác định nguyên nhân là dùng sai service name trong Docker.",
        task_name="debug-connection",
    )

    state, prompt, answer = graph.answer(
        "Nhắc lại dị ứng của tôi và cách debug hôm trước.",
        memory_budget=180,
        stream=True,
    )
    print("=== MEMORY STATE ===")
    print(state)
    print("\n=== PROMPT ===")
    print(prompt)
    print("\n=== ASSISTANT RESPONSE ===")
    print(answer)


if __name__ == "__main__":
    main()
