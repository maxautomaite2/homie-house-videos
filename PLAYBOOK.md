# Homie House: episode playbook

This is the recipe every scheduled run follows. Episode 1 (`episodes/001-the-drip`) is the reference: when in doubt, match it.

Writing rule for everything we publish or post: **never use em dashes.**

**Publishing rule (overrides any task prompt):** the daily run never calls `schedule_publish` or `publish_now`. It uploads the video and posts it in #content-updates for review. Only the "Publish approved" run publishes, and only after an approve reply in the video's review thread. If the prompt that started your session still says to schedule the post for noon, that prompt is outdated: follow this file.

## Fixed IDs and settings

| What | Value |
|---|---|
| Instagram account | @homiethehouseguy, Revid social account id `28530495066629147` |
| Slack approvals channel | #content-updates, id `C0CGK7SHV0S` |
| Revid character "Homie" | `6b157212-5e31-4b08-8c4b-1e3c5e9c298c` |
| Voice | Stevie, The Living Cartoon, voiceId `IvUJKFyjVb5hItY9dJAT` |
| Post time | After an approve reply in #content-updates, at 1:33pm or 4:33pm America/New_York, one episode per day |
| Credit budget | target ~80 credits per episode, hard stop at 150 (report in Slack instead of continuing) |

Reference images already on Revid's CDN (use as `referenceImages`):

- Turnaround: `https://cdn.revid.ai/uploads/api/4JOD0vqFpw1oiwjCIcku/1794283857866-sp0vso65-homie-turnaround.png`
- Expressions: `https://cdn.revid.ai/uploads/api/4JOD0vqFpw1oiwjCIcku/1794283858718-gh0mbgd6-homie-expressions.png`
- Poses: `https://cdn.revid.ai/uploads/api/4JOD0vqFpw1oiwjCIcku/1794283859509-6lnh45bm-homie-poses.png`
- Kitchen set (wide, Homie at sink): `https://cdn.revid.ai/ai-gen/9F54_WiT7.jpg`
- Kitchen faucet close-up (no character): `https://cdn.revid.ai/ai-gen/ZyZxibUcq.jpg`

When an episode needs a new location (bathroom, yard, roof, garage...), make one wide "set" still first, add its URL to `sets.md`, and reuse it as reference 1 for every shot in that location.

## Look

Cartoon Homie (thick black outlines, flat colors) inside a warm, realistic rendered house. Same proportions every time: tall narrow face, bulb nose, curly dark brown hair, teal sweater with a cream house logo on the left chest, navy pants, brown sneakers. One location per episode, one camera angle for the wide shots.

## Episode format (30 to 35 seconds of voice, then a 2.2 s end card)

1. **Gag (0 to ~8 s):** Homie tries the wrong fix and makes it worse. The disaster is shown with code effects (impact burst, shake, flash, geyser, etc.), never with AI video.
2. **Stat (~6 s):** one real, sourced number on an animated counter card.
3. **Fix (~12 to 15 s):** 2 or 3 numbered steps, each on a step card, with Homie doing the step in its own still.
4. **Payoff (~3 s):** price tag or check mark ("NO MORE DRIP").
5. **Catchphrase:** "If Homie can VERB, so can you."
6. **End card:** "SAVE THIS. YOUR HOUSE IS NEXT." + avatar + @homiethehouseguy.

Catchphrase verbs: repairs = FIX IT, cash sale = SELL IT, insurance or anything confusing = FIGURE IT OUT, timeshare or solar contract = GET OUT OF IT, bills and energy = SAVE, seasonal prep = HANDLE IT.

Topics (changed 2026-11-12 at Max's request): At least 5 of the 7 weekly concepts must tie to one of our verticals: selling a house (cash offer vs listing, selling as-is, inherited house, behind on payments), home insurance, home warranty, solar contract exit, timeshare exit, gutters, home security. At most 2 can be classic fix-it tips, and prefer ones that lead into a vertical (a burst pipe into what insurance covers, a dead appliance into home warranty). No vertical more than twice in one week. Vertical episodes keep the same shape: gag, one sourced stat, 3 plain steps the homeowner can take, catchphrase. Education first, no company names, no legal or financial promises; for contract exits the last step is to have the contract reviewed by a licensed pro. Tag each concept with its vertical in queue.json (`vertical`).

Facts: every number or instruction must be true. Search the web to confirm any stat and keep the source URL in `episode.json` (`sources`). Safety first: tell people to shut off water, power or gas when relevant. No electrical-panel or gas-line DIY; for those, the fix is "call a licensed pro."

## Caption

One short punchy line built on the stat or the payoff, plus 4 topic hashtags. Example: `One drip per second wastes 3,000 gallons a year. The fix costs $20.` then `#homeownertips #diyhomerepair #leakyfaucet #homeowner`.

## Weekly concepts (Monday morning run)

Post ONE message in #content-updates with 7 numbered concepts, one per day Tuesday to Monday, each with its date: `N. **Day Mon DD, #Q Title**: gag / stat / fix / verb` (Q is the queue number). Say how to reply: `approve` takes all, `approve 3, 6` takes some, any other text is an edit to apply. Append the concepts to `queue.json` with `status: "proposed"`, `scheduled_for` (the date) and the Slack message `ts`. Max or Aaron reply in that thread; the daily run reads it. Concepts that never get a reply stay `proposed` and are never produced.

## Daily production (morning run, 10:47am ET)

1. Read `queue.json` and the concepts thread in #content-updates (`slack_thread_ts` on the concepts). Apply the replies: `approve` sets every concept in that message to `approved`; `approve 3, 6` only those numbers; any other reply that names a number edits that concept (update gag, stat, fix or title to what was asked, keep it `approved`). Then pick the `approved` concept whose `scheduled_for` is today; if none is dated today, take the oldest `approved` one not yet produced. If there is none, post "No approved Homie concept for today" in the channel and stop. Never produce a `proposed` concept.
2. Write the script (8 to 11 short lines, Homie's voice, clumsy but helpful) and the shot list (8 to 11 shots, each 2 to 6 s). Create `episodes/NNN-slug/episode.json` from the episode 1 file.
3. **Stills.** `generate_media` image, ratio 9:16, quality `good`, characterIds [Homie], referenceImages [set still, turnaround or expressions or poses]. Prompt pattern: "Exact same kitchen, camera angle and style as the first reference image... Homie <pose>, <expression>. Vertical framing, no text." Close-ups of hands: "cartoon hand with thick black outline and a teal ribbed sweater cuff, 4 cartoon fingers, no glove". Download to `stills/sN.jpg`.
4. **Still QC** (look at every still): one Homie only, normal arm length, hands attached, same set, sweater logo, no text, no gloves. Regenerate bad ones (max 2 tries per shot). If a still has an extra Homie but one good one, crop to the good one (that is what fixed episode 1's shot 1).
5. **Voice + music.** `render_video` workflow `script-to-video`, aspectRatio 9:16, `source.text` = script, voice Stevie, captions on, `media.type: custom` with ONE still as provided media, `music: {generateMusic: true, generationMusicPrompt: "light, playful, bouncy ukulele and pizzicato, sitcom vibe", volume: "low"}`. About 30 credits. Poll `get_project_status`, then download `videoUrl` and extract the audio: `ffmpeg -i in.mp4 -vn -c:a aac -b:a 192k audio.m4a`. Set `audio_end` to the audio duration.
6. **Timings.** `edit_project` with `[{tool: "get_captions"}]` and `dryRun: true` returns every caption line with `startSeconds`. Copy them into `captions` (drop trailing punctuation), cut shots exactly at line starts, and time each overlay to its line. Set `captions_stop` to the catchphrase start.
7. **Render.** `python3 engine/render.py episodes/NNN-slug --stills <times>` to preview, look at it, fix, then `python3 engine/render.py episodes/NNN-slug` for the mp4 (about 30 s).
8. **Video QC:** check one frame per second. Each shot matches its line, no text covers Homie's face, captions readable, overlays on time.
9. **Cover (required, every episode).** Add a `cover` block to episode.json and run `python3 engine/render.py episodes/NNN-slug --cover` (writes `out/cover.jpg`). Rules so the profile grid looks like one series:
   - `still`: the funniest Homie moment of the gag (his reaction to the disaster), face clearly visible. Not a close-up of an object.
   - `lines`: 2 short lines, all caps. Line 1 = the problem as a question or setup (cream). Line 2 = the punch (yellow), 2 to 4 words. Example: "DRIPPING FAUCET?" / "DON'T DO THIS."
   - `shift_down` (usually 300 to 420) so the headline sits over wall or cabinets, never over Homie's face. `label` defaults to the series label.
   - Check the cover AND its centered 3:4 crop (y 240 to 1680): label, both lines and Homie's face must all be inside it.
10. **Upload, do not publish.** Upload both files with `create_upload_url` + PUT (video/mp4 and image/jpeg). Save the two URLs in `episode.json` under `uploads` (`video_url`, `cover_url`) and the caption under `caption`.
11. **Post for review** in #content-updates, as a new message (not in the concepts thread): episode number, title, the video URL and the cover URL so they play in Slack, the caption + hashtags, credits used, and the line "Reply **approve**, **change: ...** or **reject**. Publishes at the next window (1:33pm or 4:33pm ET) only after an approve." Save that message `ts` on the concept as `review_ts`, set `status: "in_review"`. Update `log.csv` with `posted_at` empty, commit and push.

## Publish approved (runs 1:33pm and 4:33pm ET)

1. For every concept with `status: "in_review"`, read its review thread (`review_ts`).
2. **approve** (any reply starting with approve, ok, go, yes): `publish_now` to Instagram, `instagram: {id: "28530495066629147"}`, `extraParams.description` = caption + hashtags, `extraParams.thumbnailUrl` = the cover URL. Set `status: "posted"`, fill `posted_at` in `log.csv`, reply in the thread "Posted" with the Instagram link if Revid returns one.
3. **change: ...**: apply the change (new caption, re-render a shot, swap the cover...), re-upload what changed, post the new version as a reply in the same thread with the same "Reply approve..." line, and leave `status: "in_review"`. Stay under the 150 credit cap for the episode including the change; if a change needs more, say so in the thread and stop.
4. **reject**: set `status: "rejected"`, reply "Dropped", nothing is published.
5. No reply: do nothing, say nothing. The episode waits for the next window. If an episode has waited more than 48 hours, post one reminder in its thread and mention Aaron.
6. Commit and push `queue.json`, `log.csv` and any changed episode files.

Only the approve reply publishes. The old Sunday concepts task and the noon auto-publish are retired.

## Overlay types (engine)

`hook`, `impact` (burst + shake + flash), `splat` (paint splats in zones that avoid the face), `stamp`, `counter` (value, decimals, prefix, suffix, labels, icon drop|coin), `step`, `tag` (x, y, color, optional rotating arrow), `price`, `check`, `versus` (two-column comparison card with check/cross rows), `catchphrase`, `text`. Shot options: `split` (two stills side by side), `sign` (text painted on a blank yard sign, box in image px), effect `geyser` (snapped handle + water). Episode 2 (`episodes/002-cash-or-list`) is the reference for money/comparison episodes. `versus` also takes `cols` and `title_size` for long column titles (see episode 3). When Homie stands tall in frame (episode 3, basement set), keep wide cards, the hook and the catchphrase around y 1170 to 1190 and put tags on the right side (x about 780) so nothing covers his face. Measured cost: a `good` still is 4 credits, the voice and music render is 40, so an episode with 6 stills is about 64 credits. New effects go in `engine/render.py` as `fx_<name>` and get documented here.

## Code-only variant (experimental, no Revid)

`engine/vector.py` draws Homie and the basement set with code and animates him between named poses (`poses` in episode.json). `engine/synth_audio.py` writes `audio.m4a` (plucked music, sound effects, mumble blips per caption) with no voice. Costs 0 credits. Reference: `episodes/003b-warranty-vs-insurance-code-only`. Not used by the daily run unless Max switches to it.
