# Benchmark: Multi-Memory Agent
## Summary

- Tổng số scenario: `10`
- With-memory pass (theo `with_memory_contains_expected`): `9/10`
- No-memory pass (theo `no_memory_contains_expected`): `3/10`

## Result Table

| # | Scenario | Router memory types used | No-memory result | With-memory result | No-memory pass? | With-memory pass? |
|---|---|---|---|---|---|---|
| 1 | Profile recall: name after 6 turns | `short_term, profile, episodic` | Không nhớ tên | Nhớ đúng `Linh` | Fail | Pass |
| 2 | Conflict update: allergy correction | `short_term, profile` | Không xác định được dị ứng | Nhớ đúng `đậu nành` | Fail | Pass |
| 3 | Profile recall: location after topic switch | `short_term` | Trả lời chung chung | Nhớ đúng `Đà Nẵng` | Fail | Pass |
| 4 | Episodic recall: previous debug outcome | `short_term, episodic, semantic` | Không có dữ liệu phiên trước | Nhớ đúng bài học + `service name` + `hostname` | Fail | Pass |
| 5 | Episodic recall: done task status | `short_term, episodic` | Không có thông tin task | Nhớ đúng `hoàn tất` + `REDIS_URL` | Fail | Pass |
| 6 | Semantic retrieval: Docker FAQ chunk | `short_term, semantic` | Tự trả lời đúng `service name/hostname` dù không memory | Trả lời đúng với semantic chunk | Pass | Pass |
| 7 | Semantic retrieval: retry policy chunk | `short_term, semantic` | Tự trả lời đúng `exponential backoff/jitter` | Trả lời đúng với semantic chunk | Pass | Pass |
| 8 | Mixed recall: profile + semantic together | `short_term, profile, semantic` | Không đạt expected keywords | Có nhớ Linh nhưng thiếu cụm keyword theo rule chấm | Fail | **Fail** |
| 9 | Trim/token budget in long chat | `short_term, profile` | Có chứa `tóm tắt/profile` theo keyword | Có chứa `tóm tắt/profile` theo keyword | Pass | Pass |
| 10 | Multi-fact update: occupation + timezone | `short_term, profile, episodic` | Không biết nghề/timezone | Nhớ đúng `Platform Engineer` + `UTC+7` | Fail | Pass |

## Detailed Scenarios (From JSON Outputs)

### 1) Profile recall: name after 6 turns
- Turns: 6
- No-memory output: `Tôi không thể nhắc lại tên của bạn vì bạn chưa cung cấp thông tin đó.`
- With-memory output: `Tên của bạn là Linh.`
- Prompt words: no-memory `29`, with-memory `63`

### 2) Conflict update: allergy correction
- Turns: 5
- No-memory output: không xác định được dị ứng (trả lời an toàn y tế)
- With-memory output: `Bạn dị ứng đậu nành.`
- Prompt words: no-memory `27`, with-memory `57`

### 3) Profile recall: location after topic switch
- Turns: 4
- No-memory output: gợi ý chung chung, không dùng location đã nêu trước đó
- With-memory output: nhớ đúng user ở `Đà Nẵng` và gợi ý theo ngữ cảnh
- Prompt words: no-memory `33`, with-memory `55`

### 4) Episodic recall: previous debug outcome
- Turns: 3
- No-memory output: không nhớ bài học trước đó
- With-memory output: nhắc đúng bài học debug DB timeout + `Docker service name` + `hostname nội bộ`
- Prompt words: no-memory `30`, with-memory `80`

### 5) Episodic recall: done task status
- Turns: 3
- No-memory output: yêu cầu thêm thông tin vì không có ngữ cảnh
- With-memory output: `Task deploy đã hoàn tất... thiếu REDIS_URL trên staging`
- Prompt words: no-memory `32`, with-memory `67`

### 6) Semantic retrieval: Docker FAQ chunk
- Turns: 1
- No-memory output: vẫn trả lời đúng khái niệm `service name`
- With-memory output: trả lời đúng và bám semantic hit
- Prompt words: no-memory `32`, with-memory `47`

### 7) Semantic retrieval: retry policy chunk
- Turns: 1
- No-memory output: vẫn chứa `exponential backoff` + `jitter`
- With-memory output: đúng với semantic chunk
- Prompt words: no-memory `31`, with-memory `50`

### 8) Mixed recall: profile + semantic together
- Turns: 3
- No-memory output: không đạt keyword expected
- With-memory output: có nhớ `Linh` và nêu hostname nội bộ, nhưng không match đủ keyword rule hiện tại (`service name`) nên fail theo evaluator
- Prompt words: no-memory `36`, with-memory `77`

### 9) Trim/token budget in long chat
- Turns: 23+
- No-memory output: có cụm `tóm tắt` và `profile` nên pass theo keyword
- With-memory output: có cụm `tóm tắt` và `profile` nên pass theo keyword
- Prompt words: no-memory `33`, with-memory `27`

### 10) Multi-fact update: occupation + timezone
- Turns: 4
- No-memory output: không có thông tin nghề/timezone
- With-memory output: `Nghề hiện tại ... Platform Engineer` + `UTC+7`
- Prompt words: no-memory `32`, with-memory `64`

## Coverage Checklist

- Profile recall: #1, #3, #8, #10
- Conflict update: #2, #10
- Episodic recall: #4, #5
- Semantic retrieval: #6, #7, #8
- Trim/token budget: #9
