# Release checklist — run on EVERY feature addition (customer requirement, 2026-11-03)

1. Help content: add/update the module in `backend/pmc_lib/help_content_data.py` (or `help_content_extra.py`
   for newer admin sections). Every admin-bar section must have a module.
2. Help videos: regenerate only what changed (hash cache skips unchanged):
   `PMC_BASE=<preview url> PMC_ADMIN_EMAIL=... PMC_ADMIN_PW=... PMC_VENDOR_EMAIL=... PMC_VENDOR_PW=... \
    setsid nohup python3 scripts/help_videos/make_videos.py [slug ...] > /tmp/vids.log 2>&1 &`
   Output: frontend/public/help-videos/<slug>.mp4 + manifest.json (shown on /help/<slug> and in the admin Help panel).
   Needs ffmpeg + python playwright chromium (`python3 -m playwright install chromium`). Voice: OpenAI tts-1-hd "nova" via EMERGENT_LLM_KEY.
3. Master training manual: rebuild with the manual builder (tools/manual/build.py) so the PDF in
   frontend/public/downloads/manual/ includes the new module.
4. Build bundle (scripts/build_v59*.sh) → secret scan must pass.
