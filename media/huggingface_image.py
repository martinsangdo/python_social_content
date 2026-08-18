import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# 1. Tải cấu hình từ tệp .env
load_dotenv()
hf_token = os.getenv("HF_TOKEN")

if not hf_token:
    raise ValueError("❌ Thiếu HF_TOKEN trong tệp .env!")

# 2. Khởi tạo client (tự động chọn provider đang hỗ trợ model, ví dụ nscale/together/fal-ai...)
client = InferenceClient(api_key=hf_token)

# 3. Nội dung mô tả bức ảnh bạn muốn vẽ
prompt_text = "A futuristic cyberpunk city with neon lights, raining night, 4k resolution, cinematic composition"

print(f"🎨 Đang gửi yêu cầu tới Hugging Face để vẽ: '{prompt_text}'...")

try:
    # 4. Gửi yêu cầu tới model Flux.1-schnell (mô hình vẽ tranh siêu nhanh)
    image = client.text_to_image(
        prompt_text,
        model="black-forest-labs/FLUX.1-schnell",
    )

    # 5. Lưu ảnh trả về (PIL.Image) thành file
    file_name = "flux_output.png"
    image.save(file_name)
    print(f"✅ Đã tạo và lưu ảnh thành công: {file_name}")

except Exception as e:
    print(f"❌ Đã xảy ra lỗi hệ thống: {e}")
