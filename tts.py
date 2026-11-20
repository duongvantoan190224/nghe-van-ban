import asyncio
import os
from pathlib import Path

import edge_tts


OUTPUT_PATH = Path("output/doc-van-ban.mp3")


async def main() -> None:
    text = os.environ.get("INPUT_TEXT", "").strip()
    voice = os.environ.get("INPUT_VOICE", "vi-VN-HoaiMyNeural").strip()
    rate = os.environ.get("INPUT_RATE", "+0%").strip()

    if not text:
        raise ValueError("INPUT_TEXT đang rỗng. Hãy nhập văn bản cần chuyển thành giọng nói.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(OUTPUT_PATH))
    print(f"Đã tạo tệp âm thanh: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
