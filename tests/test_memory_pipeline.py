from __future__ import annotations

from memory_systems.pipeline import (
    MemoryGraphSkeleton,
    build_default_stack,
    build_prompt,
    count_words,
    memory_router,
    save_memory_updates,
)


def test_profile_conflict_update_allergy(tmp_path):
    stack = build_default_stack(tmp_path)
    save_memory_updates(stack, "Tôi dị ứng sữa bò.")
    save_memory_updates(stack, "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.")

    profile = stack.profile.load_profile()
    assert profile["allergy"] == "đậu nành"


def test_update_at_least_two_profile_facts(tmp_path):
    stack = build_default_stack(tmp_path)
    save_memory_updates(stack, "Tên tôi là Linh. Tôi sống ở Đà Nẵng.")

    profile = stack.profile.load_profile()
    assert profile["name"] == "Linh"
    assert profile["location"] == "Đà Nẵng"


def test_episodic_saved_when_outcome_is_clear(tmp_path):
    stack = build_default_stack(tmp_path)
    save_memory_updates(
        stack,
        "Nhờ tóm tắt nguyên nhân lỗi deploy.",
        "Hoàn tất: lỗi do thiếu biến môi trường.",
        task_name="deploy-debug",
    )
    episodes = stack.episodic.load_episodes()
    assert len(episodes) == 1
    assert episodes[0]["task"] == "deploy-debug"
    assert "thiếu biến môi trường" in episodes[0]["outcome"]


def test_router_and_prompt_injection_have_all_sections(tmp_path):
    stack = build_default_stack(tmp_path)
    stack.semantic.add_documents(
        ["Docker Compose dùng service name làm hostname nội bộ."],
        metadata=[{"topic": "docker"}],
    )
    save_memory_updates(stack, "Tên tôi là Linh.")
    save_memory_updates(
        stack,
        "Chúng ta đang debug lỗi kết nối DB.",
        "Đã xong: dùng sai service name trong docker compose.",
        task_name="debug-db",
    )
    stack.short_term.add_message("assistant", "Bạn có thể gửi log.")
    stack.short_term.add_message("user", "Nhắc lại profile và bài học debug.")

    state = {
        "messages": [],
        "user_profile": {},
        "episodes": [],
        "semantic_hits": [],
        "memory_budget": 180,
    }
    state = memory_router(state, stack)
    prompt = build_prompt(state, "Nhắc lại profile và bài học debug.")

    assert "[USER PROFILE]" in prompt
    assert "[EPISODIC MEMORY]" in prompt
    assert "[SEMANTIC MEMORY HITS]" in prompt
    assert "[RECENT CONVERSATION]" in prompt
    assert "Linh" in prompt
    assert "service name" in prompt


def test_trim_budget_is_applied(tmp_path):
    stack = build_default_stack(tmp_path)
    for index in range(25):
        stack.short_term.add_message("user", f"Message number {index} " + ("x " * 20))
    save_memory_updates(stack, "Tên tôi là Linh. Tôi sống ở Đà Nẵng. Tôi làm nghề kỹ sư dữ liệu.")

    graph = MemoryGraphSkeleton(stack)
    state, prompt = graph.invoke("Hãy tóm tắt nhanh cho tôi.", memory_budget=70)

    assert state["memory_budget"] == 70
    assert count_words(prompt) < 190
