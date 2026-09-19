# Founder note — 2026-09-18

## Today’s problem

AI coding tools can leave a visible session title even when a canceled resume never
received a user or assistant message. That makes history less trustworthy and can send a
user back into an empty context.

The concrete trigger is [Claude Code issue #60390](https://github.com/anthropics/claude-code/issues/60390),
which describes “phantom sessions” created by a canceled `/resume`; a separate
[resume-list report](https://github.com/anthropics/claude-code/issues/37474) shows that
session discovery itself is already a recurring pain.

## Four innovation questions

Scores are out of 5 for pain, novelty, buildability today, organic shareability, and
open-source fit. A score is a hypothesis, not a market result.

| Candidate | Score | Facts and hypothesis | Difference | Smallest 7-day experiment | Decision |
| --- | ---: | --- | --- | --- | --- |
| GhostSweep | 24/25 | Fact: canceled resumes can leave title-only files. Hypothesis: a hash-checked, reversible cleanup restores trust in history. | Repairs the empty-session residue instead of archiving or analyzing every session. | Have 10 AI-coding users run `scan` after one canceled resume; count valid ghosts and false positives. | **Build** |
| Session handoff card | 21/25 | Fact: [AgentsView](https://github.com/kenn-io/agentsview), [reheat](https://github.com/chadthornton/reheat), and [SessionFS](https://github.com/SessionFS/sessionfs) already cover broad search, resume, or handoff. Hypothesis: a smaller handoff card could reduce context loss. | Human-readable handoff rather than a dashboard. | Ask 5 users to resume a task across two agents using one generated card. | Reject: crowded and overlaps existing user projects. |
| Clipboard provenance | 19/25 | Fact: clipboard history remains a requested workflow, as shown by the [Zed issue](https://github.com/zed-industries/zed/issues/4562). Hypothesis: a source/hash receipt reduces “where did I copy this from?” anxiety. | Provenance receipt, not another clipboard manager. | Capture 20 snippets and ask users to recover the source in under 10 seconds. | Reject: overlaps SourceStamp and a crowded category. |
| Reversible Downloads sorter | 20/25 | Fact: destructive file handling causes real trust issues, including the [Warp Downloads report](https://github.com/warpdotdev/warp/issues/7750). Hypothesis: preview + undo can make sorting safe enough to adopt. | Every move is a visible receipt with undo. | Sort one Downloads folder for 5 users and measure manual corrections. | Reject: overlaps CopyHomes/TomorrowTax and broad file-organizer territory. |

## Innovation hypothesis

If a tool only acts on a narrow, observable failure — a title event with no
conversation events — and refuses anything changed, symlinked, malformed, or ambiguous,
then users may trust it enough to run locally after a failed AI session. The 10x claim is
not “more AI”; it is “one command to turn a confusing ghost into a reviewable receipt.”

## First users and distribution

- First users: people who use Claude Code or another JSONL-based coding agent and have
  noticed empty entries in resume history.
- First ten users: small open-source AI-coding communities, issue reporters who mention
  resume/session corruption, and contributors who already use local session tooling.
- Free-to-paid hypothesis: keep the CLI MIT-licensed; a future paid layer could offer
  team policy packs or managed audit retention, but there is no revenue evidence yet.

## Why this can survive

The pain has a concrete artifact, a safe local MVP can be tested without credentials, and
the before/after is easy to demonstrate. The main uncertainty is format coverage across
agents and whether users experience enough ghosts to return.
