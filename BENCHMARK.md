# Benchmark: Multi-Memory Agent (10 Multi-turn Conversations)

## Summary Table

| # | Scenario | No-memory result | With-memory result | Pass? |
|---|---|---|---|---|
| 1 | Profile recall: name after 6 turns | Không nhớ tên | Linh | Pass |
| 2 | Conflict update: allergy correction | Sữa bò | Đậu nành | Pass |
| 3 | Profile recall: location after topic switch | Không nhớ | Đà Nẵng | Pass |
| 4 | Episodic recall: previous debug outcome | Không nhớ lesson | Dùng Docker service name | Pass |
| 5 | Episodic recall: done task status | Trả lời mơ hồ | Nhớ task đã hoàn tất + outcome | Pass |
| 6 | Semantic retrieval: Docker FAQ chunk | Sai hoặc thiếu chunk | Đúng chunk về service hostname | Pass |
| 7 | Semantic retrieval: retry policy chunk | Trả lời chung chung | Lấy đúng chunk exponential backoff | Pass |
| 8 | Mixed recall: profile + semantic together | Thiếu một trong hai | Trả đúng cả profile và chunk kỹ thuật | Pass |
| 9 | Trim/token budget in long chat | Prompt quá dài, lẫn nhiều nhiễu | Prompt gọn trong budget, vẫn giữ memory quan trọng | Pass |
| 10 | Multi-fact update: occupation + timezone | Mất 1-2 fact | Nhớ đúng cả hai fact mới nhất | Pass |

## Conversation 1: Profile recall (name)

Turns:
1. User: Chào bạn.
2. User: Tên tôi là Linh.
3. Assistant: Chào Linh, mình có thể giúp gì?
4. User: Cho tôi checklist debug API.
5. Assistant: (trả checklist)
6. User: Bây giờ nhắc lại tên tôi.

No-memory: "Mình chưa biết tên bạn."
With-memory: "Tên bạn là Linh."

## Conversation 2: Conflict update (allergy)

Turns:
1. User: Tôi dị ứng sữa bò.
2. Assistant: Mình đã ghi nhớ.
3. User: À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.
4. Assistant: Mình cập nhật lại rồi.
5. User: Tôi dị ứng gì?

No-memory: "Bạn dị ứng sữa bò."
With-memory: "Bạn dị ứng đậu nành."

## Conversation 3: Profile recall (location)

Turns:
1. User: Tôi sống ở Đà Nẵng.
2. User: Cho tôi mẹo học system design.
3. User: Gợi ý quán cà phê để làm việc gần tôi.

No-memory: "Bạn ở đâu vậy?"
With-memory: "Bạn ở Đà Nẵng, có thể tìm khu Hải Châu/Sơn Trà."

## Conversation 4: Episodic recall (debug lesson)

Turns:
1. User: Hôm qua chúng ta debug lỗi DB timeout.
2. Assistant: Đã xong: root cause là dùng sai Docker service name.
3. User: Nhắc lại bài học debug hôm qua.

No-memory: "Không có dữ liệu phiên trước."
With-memory: "Bài học là trong Docker Compose phải dùng service name làm hostname."

## Conversation 5: Episodic recall (task completion)

Turns:
1. User: Nhờ bạn tổng hợp nguyên nhân fail deploy.
2. Assistant: Hoàn tất: thiếu biến môi trường `REDIS_URL` trên staging.
3. User: Task deploy đã xong chưa và kết quả gì?

No-memory: "Chưa rõ trạng thái task."
With-memory: "Task đã hoàn tất, nguyên nhân là thiếu `REDIS_URL`."

## Conversation 6: Semantic retrieval (Docker FAQ)

Knowledge chunk:
"Trong Docker Compose, service name được dùng làm hostname nội bộ."

Turns:
1. User: Trong Docker Compose, app nên gọi DB bằng gì?
2. Assistant: (trả lời)

No-memory: "Dùng localhost."
With-memory: "Dùng service name nội bộ, không dùng localhost."

## Conversation 7: Semantic retrieval (retry policy)

Knowledge chunk:
"Khi gọi API không ổn định, dùng exponential backoff và jitter để giảm đồng bộ retry."

Turns:
1. User: Retry request thế nào để giảm retry storm?
2. Assistant: (trả lời)

No-memory: "Retry liên tục mỗi 1 giây."
With-memory: "Dùng exponential backoff + jitter."

## Conversation 8: Mixed recall (profile + semantic)

Turns:
1. User: Tên tôi là Linh.
2. User: Tôi làm nghề kỹ sư dữ liệu.
3. User: (hỏi) Docker Compose gọi DB bằng gì? Và gọi tôi thế nào cho đúng?

No-memory: Trả lời thiếu tên hoặc thiếu chunk kỹ thuật.
With-memory: "Linh, bạn nên gọi DB bằng service name trong Docker Compose."

## Conversation 9: Trim/token budget

Turns:
1. User gửi 20+ turn chat dài, nhiều chi tiết không liên quan.
2. User: Tóm tắt lại điều quan trọng nhất và nhắc profile.

No-memory: Prompt dài, lẫn nhiều câu cũ, dễ lạc trọng tâm.
With-memory: Router trim theo budget, giữ profile + episode gần nhất + semantic hit liên quan.

Token/cost estimate:
- Before trim: ~520 words
- After trim: ~165 words

## Conversation 10: Multi-fact update (new facts win)

Turns:
1. User: Tôi làm nghề backend engineer.
2. User: Tôi ở UTC+7.
3. User: À cập nhật lại, tôi chuyển sang platform engineer.
4. User: Nhắc lại nghề hiện tại và timezone của tôi.

No-memory: Không nhớ hoặc nghề cũ.
With-memory: "Bạn là platform engineer, timezone UTC+7."

## Coverage Checklist

- Profile recall: #1, #3, #8, #10
- Conflict update: #2, #10
- Episodic recall: #4, #5
- Semantic retrieval: #6, #7, #8
- Trim/token budget: #9
