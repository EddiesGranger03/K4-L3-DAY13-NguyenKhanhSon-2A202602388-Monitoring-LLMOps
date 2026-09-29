# Alerts và Runbook

Các điều kiện bên dưới là contract để cấu hình trong công cụ alerting. Dùng cửa sổ trượt và chỉ kích hoạt sau khi điều kiện duy trì đủ thời lượng. Alert dựa trên trải nghiệm người dùng/SLO; Slack là kênh thông báo.

## Alert 1

- Tên: Elevated user-facing error rate
- Severity: page
- Duration: 5 phút liên tục
- Kênh thông báo: Slack
- SLI/SLO liên quan: error rate tối đa 2%; SLO `fast_successful_requests`
- Điều kiện: `request_failed / request_received > 2%` trong cửa sổ trượt 5 phút. Bỏ qua cửa sổ có dưới 20 request để tránh nhiễu.
- Ảnh hưởng tới người dùng: nhiều lượt chat trả HTTP 500 hoặc không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận tỷ lệ lỗi và thời điểm bắt đầu trên metrics/dashboard.
  2. Tìm `request_failed` trong `data/logs.jsonl`, nhóm theo `error_type` và lấy `correlation_id`.
  3. Mở trace Langfuse cùng `correlation_id`, kiểm tra observation lỗi đầu tiên và thời lượng từng bước.
- Mitigation tạm thời: nếu lỗi retrieval phụ thuộc nguồn dữ liệu, khôi phục nguồn gần nhất hoạt động; nếu bắt đầu sau một lần phát hành, rollback bản phát hành. Ghi lại thời điểm và correlation ID trước khi thay đổi.
- Owner: LLMOps on-call

## Alert 2

- Tên: Slow chat responses
- Severity: page
- Duration: 5 phút liên tục
- Kênh thông báo: Slack
- SLI/SLO liên quan: 99.5% request hoàn tất trong 3 giây.
- Điều kiện: P95 `response_sent.latency_ms > 3000` trong cửa sổ trượt 5 phút; chỉ đánh giá khi có ít nhất 20 response.
- Ảnh hưởng tới người dùng: chat phản hồi chậm hoặc hết thời gian chờ.
- Ba bước kiểm tra đầu tiên:
  1. So sánh P50/P95/P99 và TTFT P95 để biết chậm ở toàn request hay ở bước sinh câu trả lời.
  2. Tìm các `response_sent` chậm nhất, ghi lại `correlation_id`.
  3. So sánh thời lượng `retrieve-context` và `generate-response` trong trace tương ứng.
- Mitigation tạm thời: tắt incident/practice đang bật; nếu không phải practice, rollback thay đổi gần nhất hoặc giảm tải theo runbook vận hành.
- Owner: LLMOps on-call

## Alert 3

- Tên: Retrieval unavailable to users
- Severity: ticket
- Duration: 10 phút liên tục
- Kênh thông báo: Slack
- SLI/SLO liên quan: retrieval success rate tối thiểu 90%.
- Điều kiện: tỷ lệ `tool_success == true` trên các request có `tool_success` dưới 90% trong cửa sổ trượt 10 phút; chỉ đánh giá khi có ít nhất 20 lần retrieval.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu ngữ cảnh nội bộ hoặc request thất bại.
- Ba bước kiểm tra đầu tiên:
  1. Đối chiếu `tool_success` trong log để xác nhận lỗi có tập trung trong một khoảng thời gian không.
  2. Nhóm log theo `error_type`, `correlation_id` và thời gian để xác định phạm vi ảnh hưởng.
  3. Mở các trace lỗi, kiểm tra input đã scrub PII và lỗi/thời lượng của `retrieve-context`.
- Mitigation tạm thời: khôi phục vector store/mock corpus đang được cấu hình; nếu lỗi bắt đầu sau thay đổi cấu hình, rollback cấu hình đó. Theo dõi retrieval success rate trước khi đóng alert.
- Owner: AI application team
