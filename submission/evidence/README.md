# Evidence cá nhân

Ảnh được chụp từ terminal, dashboard local và giao diện Langfuse Cloud của học viên; các file `.txt` là output text bổ sung dùng để đối chiếu API.

- [01-pytest.png](01-pytest.png), [01-pytest.txt](01-pytest.txt): kết quả 26 test pass (kèm test nested PII).
- [02-log-validator.png](02-log-validator.png), [02-log-validator.txt](02-log-validator.txt): kết quả 61 records, 100/100, không thấy PII leak.
- [03-dashboard-validator.png](03-dashboard-validator.png), [03-dashboard-validator.txt](03-dashboard-validator.txt): dashboard contract 6/6.
- [04-structured-log.png](04-structured-log.png): structured `response_sent` log; hiển thị correlation ID, model, token/cost và user ID đã hash.
- [05-pii-redaction.png](05-pii-redaction.png): input PII giả và kết quả đã redacted.
- [06-trace-list.png](06-trace-list.png), [06-trace-list.txt](06-trace-list.txt): danh sách traces của workload chạy thực tế trong project Langfuse cá nhân `day13-k4-l3a-2A202602388`.
- [07-trace-waterfall.png](07-trace-waterfall.png), [07-trace-waterfall.txt](07-trace-waterfall.txt): root (`lab-agent-run`), retriever (`retrieve-context`) và generation (`generate-response`) của trace sự cố, thể hiện đúng quan hệ cha-con và duration.
- [08-trace-metadata.png](08-trace-metadata.png), [08-trace-metadata.txt](08-trace-metadata.txt): correlation ID, managed prompt v1, model, token và cost; chỉ lưu trường an toàn.
- [09-prompt-versions.png](09-prompt-versions.png), [09-prompt-versions.txt](09-prompt-versions.txt): trạng thái prompt v1 (`baseline`, `production`) và v2 (`candidate`) trên Langfuse.
- [10a-prompt-promote.png](10a-prompt-promote.png), [10b-prompt-rollback.png](10b-prompt-rollback.png), [10-prompt-rollback.txt](10-prompt-rollback.txt): trạng thái trước/sau khi promote `production` sang v2 và rollback về v1; kèm trace xác thực của v1/v2.
- [11-dashboard-overview.png](11-dashboard-overview.png): ảnh dashboard runtime sáu panel đọc trực tiếp từ `data/logs.jsonl`.
- [12-incident-metric.png](12-incident-metric.png): ảnh đối chiếu baseline/challenge P95 và threshold.
- [13-incident-log.png](13-incident-log.png): ảnh bản ghi structured log có correlation ID của sự cố (`req-b25ae916`).
- [14-incident-trace.png](14-incident-trace.png), [14-incident-trace.txt](14-incident-trace.txt): trace Langfuse cùng correlation ID, chỉ ra retriever (`retrieve-context`) là span chậm chiếm 94% latency.

Toàn bộ ảnh chụp giao diện Langfuse (06–10/14) được chụp trực tiếp từ project Langfuse cá nhân `day13-k4-l3a-2A202602388`, đảm bảo hiển thị đúng tên project và che giấu toàn bộ API key/secret.

Checklist đầy đủ: [docs/SUBMISSION.md](../../docs/SUBMISSION.md). Không commit `.env`, Langfuse key/secret, `config/challenge.json`, log chứa PII hoặc cache.
