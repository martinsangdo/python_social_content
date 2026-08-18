import os
import io
from dotenv import load_dotenv
from google import genai
from PIL import Image

# 1. Tải cấu hình từ tệp .env
load_dotenv()

# 2. Khởi tạo Client Gemini thông thường
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Thiếu GEMINI_API_KEY trong tệp .env!")

client = genai.Client(api_key=api_key)

# 3. Câu lệnh mô tả bức ảnh bạn muốn AI vẽ
prompt_text = "A futuristic city in the style of cyberpunk, 4k resolution, highly detailed"

print(f"🎨 Đang yêu cầu AI tạo ảnh với mô tả: '{prompt_text}'...")

try:
    # 4. Sử dụng mô hình gemini-2.5-flash-image với hàm generate_content thông thường
    response = client.models.generate_content(
        model="gemini-2.5-flash-image", # Tên mô hình thay thế cho Imagen cũ
        contents=prompt_text,
    )

    # 5. Duyệt phần nội dung trả về để tìm và lưu ảnh
    image_count = 0
    for part in response.candidates[0].content.parts:
        # Kiểm tra xem dữ liệu trả về có chứa thuộc tính ảnh (inline_data) hay không
        if hasattr(part, 'inline_data') and part.inline_data:
            image_bytes = part.inline_data.data
            image = Image.open(io.BytesIO(image_bytes))
            
            image_count += 1
            file_name = f"gemini_output_{image_count}.png"
            image.save(file_name)
            print(f"✅ Đã tạo và lưu ảnh thành công: {file_name}")
            
    if image_count == 0:
        print("⚠ Không tìm thấy dữ liệu hình ảnh nào được trả về. Vui lòng kiểm tra lại prompt.")

except Exception as e:
    print(f"❌ Đã xảy ra lỗi: {e}")
#429 RESOURCE_EXHAUSTED.