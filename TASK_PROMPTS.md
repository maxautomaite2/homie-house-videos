# Scheduled task prompts (copy into the Claude scheduled tasks)

Three tasks run this pipeline. Their schedules are in New York time. Each one needs the Slack, Revid_AI and Claude_Code_Remote connectors and the repo maxautomaite2/homie-house-videos attached.

## 1. Homie Fixes: weekly concepts (Monday, for approval)

Schedule: Monday 7:03am ET (`CRON_TZ=America/New_York 3 7 * * 1`)

```
You are writing next week's "Homie Fixes" episode concepts for @homiethehouseguy (Homie House, Max Beauchamp's homeowner-tips brand). The pipeline lives in the GitHub repo maxautomaite2/homie-house-videos. If it is not already cloned in this session, attach it with the add_repo tool (owner maxautomaite2, repo homie-house-videos, access push) and clone it. Read CLAUDE.md and PLAYBOOK.md and follow PLAYBOOK.md "Weekly concepts".

Steps:
1. Read queue.json and log.csv so you never repeat a topic already posted or still in the queue. Propose one concept per day for the next 7 days (Tuesday to Monday), normally 7 new ones.
2. Topic mix: At least 5 of the 7 weekly concepts must tie to one of our verticals: selling a house (cash offer vs listing, selling as-is, inherited house, behind on payments), home insurance, home warranty, solar contract exit, timeshare exit, gutters, home security. At most 2 can be classic fix-it tips, and prefer ones that lead into a vertical (a burst pipe into what insurance covers, a dead appliance into home warranty). No vertical more than twice in one week. Vertical episodes keep the same shape: gag, one sourced stat, 3 plain steps the homeowner can take, catchphrase. Education first, no company names, no legal or financial promises; for contract exits the last step is to have the contract reviewed by a licensed pro. Tag each concept with its vertical in queue.json (vertical). Keep it timely for US homeowners (season, weather, upcoming holidays). Nothing that tells people to DIY gas lines or electrical panels.
3. Post ONE message in Slack #content-updates (channel C0CGK7SHV0S) titled "Homie Fixes: concepts for this week", a numbered list with the date of each episode, in this format: "N. **Day Mon DD, #Q Title**: gag / stat / fix / VERB" (Q is the queue number, VERB from the catchphrase list in PLAYBOOK.md). Say how to reply: "approve" takes all, "approve 3, 6" takes some, any other text is an edit. Nothing is produced without a reply. Stats get fact-checked before production.
4. Add each concept to queue.json with status "proposed", scheduled_for (the date), the verb, the channel id and the message ts, bump next_number, commit and push to main.

Rules: never use em dashes in anything you write. Do not produce or publish any video in this task.
```

## 2. Homie Fixes: daily episode (review before posting)

Schedule: every day 10:47am ET (`CRON_TZ=America/New_York 47 10 * * *`)

```
You are producing today's "Homie Fixes" Instagram Reel for @homiethehouseguy (Homie House, Max Beauchamp's homeowner-tips brand) and handing it to Aaron for review. You do NOT publish anything in this task. The whole pipeline lives in the GitHub repo maxautomaite2/homie-house-videos. If it is not already cloned in this session, attach it with the add_repo tool (owner maxautomaite2, repo homie-house-videos, access push) and clone it. Read CLAUDE.md and PLAYBOOK.md there and follow PLAYBOOK.md "Daily production" exactly. Episode 1 (episodes/001-the-drip) is the reference for look, pacing, cover and the episode.json format.

Summary of the job:
1. Read queue.json and the concepts thread in Slack #content-updates (channel C0CGK7SHV0S, slack_thread_ts on the concepts). Apply the replies from Max or Aaron: "approve" sets every concept in that message to approved, "approve 3, 6" only those numbers, any other reply naming a number is an edit to that concept (apply it, keep it approved). Produce the approved concept whose scheduled_for is today (America/New_York); if none is dated today, the oldest approved one not yet produced. If nothing is approved, post one short line in #content-updates saying there is no approved Homie concept for today, and stop. Never produce a concept that is still "proposed".
2. Fact-check the stat with a web search and keep the source URL in episode.json.
3. Write the script (Homie voice: clumsy but helpful, gag first, then the real fix, ending "If Homie can <verb>, so can you.") and the shot list, then make the stills in Revid with the Homie character and the reference images listed in PLAYBOOK.md. Check every still (one Homie, normal arms, same set, no gloves, no text) and redo bad ones.
4. Get the voice and music from one Revid script-to-video render (Stevie voice IvUJKFyjVb5hItY9dJAT), extract audio.m4a, and pull exact line timings with edit_project get_captions (dryRun true).
5. Fill episode.json, preview with engine/render.py --stills, fix anything off, then render the mp4 and check one frame per second.
6. Make the cover per PLAYBOOK.md (funniest Homie reaction still, 2 short all-caps lines, shift_down so the text never covers his face), run engine/render.py --cover, and check both the full cover and its centered 3:4 grid crop. Every episode must have a cover.
7. Upload the mp4 and cover.jpg to Revid (create_upload_url + PUT for each) and save both URLs plus the caption (one short punchy line on the stat or payoff plus 4 topic hashtags) in episode.json under uploads and caption. Do NOT call schedule_publish or publish_now.
8. Post the review message in #content-updates as a NEW message (not in the concepts thread): episode number, title, the video URL and the cover URL, the caption + hashtags, Revid credits used, and the line "Reply approve, change: ... or reject. Publishes at the next window (1:33pm or 4:33pm ET) only after an approve." Save that message ts on the concept as review_ts, set its status to in_review, add the log.csv row with posted_at empty, commit and push to main.

Rules: never use em dashes in anything you write. Stay under 150 Revid credits for the episode; if it would go over, stop and report in #content-updates instead. Nothing goes to Instagram from this task. If a step fails in a way you cannot fix, report the problem in #content-updates.
```

## 3. Homie Fixes: publish approved (new task)

Schedule: every day 1:33pm and 4:33pm ET (`CRON_TZ=America/New_York 33 13,16 * * *`)

```
You are the publish step for "Homie Fixes" Instagram Reels (@homiethehouseguy, Homie House, Max Beauchamp's homeowner-tips brand). Your only job: publish the videos that Max or Aaron approved in Slack, and nothing else. The pipeline lives in the GitHub repo maxautomaite2/homie-house-videos. If it is not already cloned in this session, attach it with the add_repo tool (owner maxautomaite2, repo homie-house-videos, access push) and clone it. Read CLAUDE.md and PLAYBOOK.md and follow PLAYBOOK.md "Publish approved" exactly.

Steps:
1. Read queue.json. For every concept with status "in_review", read its review thread in Slack #content-updates (channel C0CGK7SHV0S, thread ts = review_ts). The video URL, cover URL and caption are in that episode's episode.json (uploads and caption).
2. If the latest reply from Max or Aaron starts with approve, ok, go or yes: publish_now with Revid to Instagram account id 28530495066629147, extraParams.description = caption + hashtags, extraParams.thumbnailUrl = the cover URL. Set status "posted", fill posted_at in log.csv, reply "Posted" in the thread with the Instagram link if Revid returns one.
3. If the reply starts with "change:": apply the change (caption, a shot, the cover...), re-upload what changed, post the new version as a reply in the same thread ending with "Reply approve, change: ... or reject.", keep status "in_review". Stay under 150 Revid credits total for the episode; if the change needs more, say so in the thread and stop.
4. If the reply is reject: set status "rejected", reply "Dropped", publish nothing.
5. No reply yet: do nothing and post nothing for that episode. If it has been in_review for more than 48 hours, post one reminder in its thread mentioning Aaron.
6. If nothing is in_review, stop silently. Commit and push queue.json, log.csv and any changed episode files.

Rules: never use em dashes in anything you write. Only an approve reply in the review thread publishes; never publish on the strength of the concepts thread alone. If publishing fails, say so in the review thread and leave the status in_review.
```
