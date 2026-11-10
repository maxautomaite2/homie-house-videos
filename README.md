# homie-house-videos

Automated "Homie Fixes" Reels for @homiethehouseguy (Homie House / HomeownerPedia).

- `PLAYBOOK.md`: the full recipe (IDs, look, format, concepts, daily production, QC, publishing)
- `engine/render.py`: renders an episode folder into a 1080x1920 mp4 (stills + code animation + Revid voice/music)
- `brand/`: Homie reference sheets and avatar
- `episodes/NNN-slug/`: `episode.json`, `stills/`, `audio.m4a` (the rendered mp4 goes to `out/`, not committed)
- `queue.json`: concepts and their status (proposed, approved, scheduled, posted)
- `log.csv`: one row per published episode

Render an episode: `python3 engine/render.py episodes/001-the-drip` (needs Python 3 with Pillow and ffmpeg).
