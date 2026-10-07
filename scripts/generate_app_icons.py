"""
PMC Managers — Mobile App Store asset generator.

Generates:
 - 1024x1024 brand icon (forest-green + navy + brass)
 - iOS launch screen (portrait, 2732x2732 safe)
 - Android feature graphic (1024x500)
 - Store-ready "hero" marketing banner

Run:  python3 /app/scripts/generate_app_icons.py
Output: /app/frontend/public/downloads/mobile_assets/
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

OUT = Path("/app/frontend/public/downloads/mobile_assets")
OUT.mkdir(parents=True, exist_ok=True)

PROMPTS = {
    "icon_1024": (
        "Design a flat, modern, premium iOS/Android app icon for a global "
        "procurement SaaS platform called PMC Managers. Centre the mark on a "
        "deep forest-green #0b3d2e background with a subtle navy-to-forest "
        "radial gradient. The mark is a bold, geometric monogram letter 'P' "
        "and 'M' interlocked, rendered in rich brass / champagne gold "
        "#d4af37 with crisp metallic highlights, suggesting a seal of trust "
        "and institutional authority. Add a very thin gold ring around the "
        "monogram. Perfectly square, no text, no watermark, no shadow outside "
        "the icon canvas, 1024x1024 pixel-sharp, flat vector style, clean "
        "rounded-corners App Store aesthetic."
    ),
    "splash_portrait": (
        "Vertical mobile splash screen, 1290x2796 iPhone portrait aspect. "
        "Deep navy #0b1e3f background with a soft forest-green radial glow "
        "centred vertically. Place a large brass / champagne gold #d4af37 "
        "'PM' monogram seal in the exact middle, with crisp metallic edge "
        "highlights. Below the seal, in elegant modern serif, the words "
        "'PMC MANAGERS' in brass gold, letter-spaced, centred. Below that, "
        "in thin uppercase small-caps, 'GLOBAL PROCUREMENT' in soft "
        "warm-white #f6e8c8. Minimalist, premium, cinematic, no shadows "
        "outside the frame, no watermark. iOS launch screen quality."
    ),
    "android_feature_1024x500": (
        "Google Play feature graphic, 1024x500 landscape. Deep navy "
        "#0b1e3f background with a forest-green #0b3d2e gradient wash on "
        "the right third. Left half: large brass / champagne gold #d4af37 "
        "'PMC MANAGERS' wordmark in elegant modern serif, letter-spaced. "
        "Beneath it a thin brass divider line and the tagline 'Procurement "
        "• Tenders • Reverse Auctions • Escrow' in soft warm-white #f6e8c8 "
        "small caps. Right half: a stylised brass seal/monogram 'PM' with "
        "crisp metallic highlights, floating. No bevels, no shadows outside "
        "the canvas, no watermark, flat premium corporate feel."
    ),
}


async def generate_one(session_id: str, prompt: str, out_name: str) -> Path:
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        sys.exit("EMERGENT_LLM_KEY missing in /app/backend/.env")

    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message="You are a top-tier brand designer producing production-ready app store assets.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    msg = UserMessage(text=prompt)
    _, images = await chat.send_message_multimodal_response(msg)
    if not images:
        print(f"[WARN] {out_name}: no image returned")
        return None

    img_bytes = base64.b64decode(images[0]["data"])
    out_path = OUT / f"{out_name}.png"
    out_path.write_bytes(img_bytes)
    print(f"[OK] wrote {out_path}  ({len(img_bytes)/1024:.0f} KB)")
    return out_path


async def main() -> None:
    tasks = [
        generate_one(f"pmc-{name}", prompt, name)
        for name, prompt in PROMPTS.items()
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
