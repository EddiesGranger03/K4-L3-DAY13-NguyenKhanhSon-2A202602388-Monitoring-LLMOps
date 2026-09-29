# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Báo cáo hoàn thiện từ source, validator, log ứng dụng, Langfuse API và ảnh chụp giao diện thực tế (UI) Langfuse cá nhân cùng Dashboard.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Khánh Sơn
- **MSSV:** 2A202602388
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/EddiesGranger03/K4-L3-DAY13-NguyenKhanhSon-2A202602388-Monitoring-LLMOps
- **Commit SHA cuối:** b64b1aadd414c26fa738cd5d40e03c4166da5cb3
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (đối chiếu challenge cục bộ; không đưa file challenge vào Git).
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602388` (xác nhận qua Projects API).

## 2. Evidence index

Evidence text và ảnh chụp thực tế được lưu đầy đủ trong thư mục `submission/evidence/`.

| Evidence | Đường dẫn/trạng thái |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` và `evidence/01-pytest.txt` — 26 passed |
| Log validator | `evidence/02-log-validator.png` và `evidence/02-log-validator.txt` — 61 records, 100/100, không thấy PII leak |
| Dashboard validator | `evidence/03-dashboard-validator.png` và `evidence/03-dashboard-validator.txt` — dashboard contract 6/6 |
| Structured log | `evidence/04-structured-log.png` — structured log `response_sent` có correlation ID, model, token/cost và user ID hash |
| PII redaction | `evidence/05-pii-redaction.png` — input test chứa PII giả và kết quả log đã redact |
| Trace list | `evidence/06-trace-list.png` và `evidence/06-trace-list.txt` — danh sách traces từ project Langfuse cá nhân `day13-k4-l3a-2A202602388` |
| Trace waterfall | `evidence/07-trace-waterfall.png` và `evidence/07-trace-waterfall.txt` — quan hệ cha-con root, retriever và generation |
| Trace metadata | `evidence/08-trace-metadata.png` và `evidence/08-trace-metadata.txt` — model, token, cost, prompt version |
| Prompt versions | `evidence/09-prompt-versions.png` và `evidence/09-prompt-versions.txt` — prompt day13-chat v1 (baseline, production) và v2 (candidate) |
| Prompt rollback | `evidence/10a-prompt-promote.png`, `evidence/10b-prompt-rollback.png` và `evidence/10-prompt-rollback.txt` — ảnh trước/sau khi promote sang v2 và rollback về v1 |
| Dashboard runtime | `evidence/11-dashboard-overview.png` — dashboard runtime 6 panel đọc trực tiếp từ data/logs.jsonl |
| Incident metric | `evidence/12-incident-metric.png` — biểu đồ đối chiếu baseline/challenge P95 và threshold |
| Incident log | `evidence/13-incident-log.png` — bản ghi structured log response_sent của sự cố |
| Incident trace | `evidence/14-incident-trace.png` và `evidence/14-incident-trace.txt` — trace cùng correlation ID chỉ ra span retrieve-context bị chậm |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline đã ghi nhận | Kết quả cuối đã kiểm tra | Nhận xét |
|---|---:|---:|---|
| `validate_logs.py` | 50/100; 20 record thiếu field bắt buộc, 40 thiếu enrichment, 10 correlation IDs, 0 PII leak | 100/100; 61 record, 0 thiếu field, 0 thiếu enrichment, 28 correlation IDs, 0 PII leak | Output cuối nằm ở `evidence/02-log-validator.txt`; log là nguồn local, không đồng nghĩa với trace. |
| `validate_dashboard.py` | Chưa ghi baseline | 6/6 panel hợp lệ | Validator xác nhận contract YAML, không xác nhận dashboard runtime có dữ liệu. |
| `pytest` | Chưa ghi baseline | 26 passed, 0 failed trong lần chạy mới nhất | Có warning Langfuse export bị môi trường này chặn; test pass không chứng minh Cloud đã nhận mọi trace. |
| Số traces hợp lệ | Chưa ghi baseline | Đã gửi workload 10 query; Cloud có ghi nhận 10 root traces của lượt đó | Các trace gốc được kiểm tra khi prompt chưa tồn tại, nên metadata báo `local-fallback`/`local-v1`; không dùng chúng làm bằng chứng prompt-managed. |
| Số PII leak | Chưa ghi baseline | 0 theo log validator | Cần thêm evidence redaction từ log/test. |
| Latency P95 / TTFT P95 | Baseline workload P95 latency 1008 ms | Dashboard 60 phút đến 09:29 UTC: latency P95 8388 ms, TTFT P95 50 ms | Dashboard tính cả một request đơn lẻ chậm trước challenge; khi so sánh hai batch riêng, challenge P95 là 2662 ms. |
| Retrieval success rate | Chưa có số liệu baseline tách biệt | Dashboard 60 phút đến 09:29 UTC: 100% | Tính từ field `tool_success` của log trong cửa sổ chọn. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware gắn correlation ID cho request và trả lại ID trong response header; API gắn context để các log của cùng request dùng chung ID.
- **Metadata trong structured log:** timestamp, level, service, event, correlation ID, environment; enrichment gồm user ID đã hash, session, feature, model và các field vận hành như latency, token, cost, error/retrieval.
- **Cách scrub PII:** `app/pii.py` che email, số điện thoại Việt Nam, CCCD, số thẻ, passport và địa chỉ có nhãn trước khi serialize log/trace; user ID được SHA-256 và rút gọn.
- **Kiểm chứng:** `validate_logs.py` đạt 100/100, không phát hiện leak trong 61 record đã phân tích. Các test PII hiện có trong `tests/test_pii.py` và test redaction lồng nhau trong `tests/test_logging_scrub.py`.

## 5. Tracing và prompt versioning

- **Nguồn traces:** Đã gửi 10 query từ `data/sample_queries.jsonl`; CLI Langfuse ghi nhận 10 root observation ở lượt đó. Không ghi API key/secret vào report.
- **Cấu trúc observations:** Root agent `lab-agent-run`, child retriever `retrieve-context`, child generation `generate-response`; generation có model, usage và cost theo implementation.
- **PII và liên kết log-trace:** Input/output được scrub; correlation ID được gắn metadata để đối chiếu structured log với trace.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** v1, labels `baseline` và `production` sau rollback.
- **Version/label candidate:** v2, label `candidate`; có thêm instruction ràng buộc trả lời ngắn và bám tài liệu.
- **Trace ID của mỗi version:** Production v1 `2056887082a12df0a5d1ea8d93976738` (generation `day13-chat` v1); candidate v2 `1c435e565b3bef4f95e0745e31dccf7d` (generation `day13-chat` v2). Trace v2 là một query mẫu đã được chấp thuận trước, gửi lại lúc 10:55 UTC; correlation ID `req-8aa0af7b`.
- **Promote/rollback:** Đã tạo prompt v1/v2 trên Langfuse, promote production sang v2 rồi đưa production trở lại v1; API hiện xác nhận production v1 active, candidate v2 inactive. Đã có đầy đủ ảnh trước/sau thao tác promote/rollback (`evidence/10a-prompt-promote.png`, `evidence/10b-prompt-rollback.png`) kèm trace xác thực của hai phiên bản. 10 trace workload ban đầu là local fallback.

## 6. Dashboard, SLO và alerts

- **Dashboard contract:** Sáu panel trong `config/dashboard.yaml`: latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality proxy.
- **SLO:** `fast_successful_requests`, cửa sổ 28 ngày, target 99.5% cho response thành công trong ≤3000 ms.
- **Error budget:** 0.5% (= 100% - 99.5%), tương đương tối đa 1 request lỗi/chậm trên 200 request.
- **Alerts/runbooks:** Ba symptom alerts về error rate, latency và retrieval; đều có thời lượng, severity, owner, Slack channel và liên kết tới `docs/alerts.md`.
- **Runtime evidence:** `evidence/11-dashboard-overview.png` chụp dashboard chạy cục bộ từ `data/logs.jsonl`, có sáu panel, dữ liệu, time range và threshold. `validate_dashboard.py` chỉ xác nhận contract YAML, nên đây là kiểm tra bổ sung.

## 7. Điều tra challenge

Metric, log và trace sau đây cùng thuộc challenge cục bộ; không đưa nội dung file challenge vào repository.

- **Challenge ID / khoảng thời gian:** `day13-k4-l3a-monitoring-llmops-v1`; năm phản hồi challenge ghi lúc 09:28:35–09:28:46 UTC ngày 29/09/2026.
- **Triệu chứng metric:** P95 của batch baseline 10 phản hồi là 1008 ms; P95 của năm phản hồi challenge là 2662 ms, vượt ngưỡng challenge 2000 ms. Cả năm phản hồi challenge đều trên ngưỡng. Xem `evidence/12-incident-metric.png`.
- **Log line / correlation ID:** `response_sent` lúc `2026-09-29T09:28:46.369059Z`, `correlation_id=req-b25ae916`, `latency_ms=2654`, `ttft_ms=50`, model `claude-sonnet-4-5`; xem `evidence/13-incident-log.png`.
- **Trace ID / span gây ảnh hưởng:** Langfuse trace `2056887082a12df0a5d1ea8d93976738` có cùng correlation ID. Root `lab-agent-run` 2.655 s; child `retrieve-context` 2.501 s; `generate-response` 0.152 s. Xem `evidence/14-incident-trace.png`, `evidence/14-incident-trace.txt` và `evidence/07-trace-waterfall.png`.
- **Root cause:** Retrieval trong mock RAG bị làm chậm; span retriever chiếm khoảng 94% thời gian root. Đây là kết luận từ waterfall và đoạn xử lý `rag_slow` trong `app/mock_rag.py`, không phải lỗi generation hay TTFT.
- **Fix action / preventive measure:** Tắt chế độ chậm sau khi hoàn tất challenge; trong môi trường thật cần đặt timeout/cache cho retrieval và alert khi latency retrieval vượt ngưỡng, giữ correlation ID để truy từ metric sang log và trace. Chưa tuyên bố đã triển khai timeout/cache.

## 8. Giải thích và tự đánh giá

- **Quyết định kỹ thuật:** Scrub PII trước khi ghi log/trace và hash user ID; giữ local prompt fallback để app vẫn chạy khi prompt service không khả dụng.
- **Lỗi/blocker:** Langfuse SDK có các lần export timeout; unit test vẫn pass nhưng cảnh báo export có nghĩa trace ingest cần được kiểm tra riêng.
- **Cách xử lý:** Phân biệt test result với telemetry delivery; kiểm tra validator local và tra Cloud riêng, không xem `tracing_enabled` là bằng chứng Cloud đã nhận trace.
- **Metrics → Logs → Traces:** Metrics xác định triệu chứng và thời gian; correlation ID tìm request trong structured logs; trace waterfall giúp khoanh vùng observation/span gây chậm hoặc lỗi.
- **Prompt/token/cost/SLO/rollback:** Prompt version tạo khả năng so sánh và rollback; token/cost làm rõ tác động vận hành; SLO/error budget định lượng độ tin cậy và mức lỗi chấp nhận được.
- **Điều học được / hạn chế:** Việc so sánh đúng các batch và gắn correlation ID giúp tránh nhầm request chậm đơn lẻ với nguyên nhân challenge. Bản nộp đã có đầy đủ ảnh giao diện Langfuse 06–10/14 và ảnh trước/sau rollback; cần chốt commit SHA cuối trước khi nộp.

## 9. Checklist trước khi nộp

- [x] Test và validators đã chạy; output text có trong evidence.
- [ ] Re-run test/validators sau khi tạo commit cuối và lưu evidence gắn với commit đó.
- [x] Điền Challenge ID, incident timeline, metric, correlation ID, trace ID, root cause và action.
- [x] Thêm structured-log/PII evidence đã scrub.
- [x] Thêm ảnh Langfuse traces, waterfall, metadata, prompt versions và rollback từ project cá nhân.
- [x] Thêm ảnh dashboard runtime, incident metric, incident log và incident trace UI.
- [x] Xác nhận tên project Langfuse cá nhân; học viên nên hoàn thiện tự đánh giá bằng lời của mình.
- [ ] Thu hồi secret Langfuse đã xuất hiện trong chat, thay trong `.env`; không commit `.env`.
- [ ] Commit source/report/evidence sau khi hoàn thiện; cập nhật SHA cuối và nộp URL + SHA trên LMS/Codelabs.
