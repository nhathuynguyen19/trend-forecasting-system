import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Đang khởi động Playwright...")

    # Sử dụng async with để tự động quản lý vòng đời (không cần gọi p.stop() thủ công)
    async with async_playwright() as p:
        # Khởi chạy Chromium
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",             # Bắt buộc khi chạy trong Docker/Linux root
                "--disable-dev-shm-usage"   # Tránh lỗi sập trang do thiếu bộ nhớ dùng chung (SHM) trong Docker
            ]
        )
        print("Chromium đã khởi chạy thành công!")

        # Đóng trình duyệt ngay lập tức theo đúng yêu cầu
        await browser.close()
        print("Đã đóng trình duyệt.")

if __name__ == "__main__":
    asyncio.run(main())
