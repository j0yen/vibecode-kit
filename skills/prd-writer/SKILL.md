---
name: prd-writer
description: >
  Help anyone — hobbyist, maker, parent, artist, musician, retiree, small business owner — turn
  a vague idea into a clear, buildable plan for a personal software project. No technical
  background needed. Invoke when someone has something they wish existed, a problem they keep
  solving by hand, or a creative tool they imagine but can't find. Works by asking the right
  questions, not by demanding a filled-in form. Produces a concise spec that /pybuilder can
  build from. Covers: home life and automation, journalling and reflection, photography and
  art, music, child and elderly care, health and fitness, LinkedIn and networking, sales and
  freelance work, design and creative projects, and any personal or consumer software idea.
  Trigger on: "I wish there was an app that...", "can you help me figure out what I want to
  build?", "I want to track my...", "I need something that reminds me...", "help me write a
  spec for...", "I have this idea...", "can you help me describe what I want?". Skip: pure
  enterprise or B2B product features (use /atscale-prd-writer), purely technical architecture
  questions (no idea yet to shape), requests to build the thing directly (hand off to
  /pybuilder once the PRD is done).
version: 1.0.0
---

# prd-writer

## The idea behind this skill

Most software that changes people's lives starts as a frustrated thought: *"I wish something
existed that did this."* A nurse who wants a simple medication log for her father. A photographer
who wants their travel shots auto-sorted by destination. A musician who wants to track what they
practice so they stop repeating the same songs. A parent who wants a gentle nudge when the kids'
screen time is up.

The gap between that thought and a working app is rarely technical ability — it's the ability to
*describe clearly what you want*. That's what this skill does. It asks the right questions, helps
you see what you actually need versus what you think you need, and produces a short document that
/pybuilder can turn into real, working software.

You don't need to know how to code. You just need to know what you want.

---

## How it works

When you invoke `/prd-writer`, start by describing your idea in plain language — a sentence, a
paragraph, a ramble, anything. Don't worry about being precise yet. The skill will ask a small
number of focused questions to understand:

1. **What's the itch** — what problem keeps coming up, what do you do by hand that you wish
   happened automatically, what do you wish you had?
2. **Who uses it** — just you? you and your partner? your whole family? a client?
3. **The three things it must do** — not the full vision, just the core that makes it useful
   from day one.
4. **What done looks like** — how do you know it worked? What changes about your day, your work,
   your creative practice?
5. **What it doesn't do yet** — the honest boundary that keeps the first version shippable.

From those answers, the skill produces a **Personal Project PRD**: a short, plain-English
document /pybuilder can build from, and that you can actually read and recognize as your idea.

---

## The Personal Project PRD template

```
# [Project name — yours to name]

## The idea (one sentence)
[What it is, who it's for, and what problem it solves — the kind of thing you'd say
to a friend over coffee.]

## The person it's for
[You / you and your family / your elderly parent / your photography clients / etc.
Be specific — the more real the person, the better the software fits.]

## The problem it replaces
[What do you do today instead? A spreadsheet, a napkin, nothing, a reminder you
keep forgetting, a manual task you resent? Describe the friction.]

## The three things it must do (v1)
1. [Core behavior #1 — verb + object, plain language]
2. [Core behavior #2]
3. [Core behavior #3]
[Add a fourth or fifth if genuinely essential, but resist. The best v1 does three
things beautifully rather than ten things sloppily.]

## What good looks like
[How does your day / week / creative practice change? What do you stop doing? What
do you start doing? What would make you say "yes, this is it"?]

## Where it lives
[A desktop app, a web page I open in my browser, a script I run in the terminal,
a phone app, a home-server dashboard, a command I type, a widget on my desktop?
Pick one that fits your life.]

## The honest boundary
[What is explicitly NOT in v1? Name something a reasonable person might assume is
included. This is the constraint that makes it buildable.]

## The vibe (optional but useful)
[Simple and invisible / powerful and configurable / warm and personal / minimal /
playful / elegant? What feeling should using it have?]
```

---

## Domain inspirations

These are starting points — seeds for ideas you might not have put into words yet.
They're meant to spark, not constrain.

### Journalling & reflection
- A daily journal that auto-prompts you with one question based on the day of the week
- A mood tracker with a single emoji tap, plus a weekly summary you actually look forward to
- A "what did I learn today" log that searches and surfaces old entries when you write similar things
- A gratitude log that emails you a random past entry every morning
- A voice-note diary that transcribes and organizes by theme

### Home life & automation
- A chore rotation that texts the right person the right task, no nagging required
- A grocery list that learns your weekly patterns and pre-fills itself
- A household finance tracker that shows one number: how did this month compare to last?
- A home dashboard (Raspberry Pi, old tablet) that shows weather, today's calendar, and who's home
- A "where did I put it" log for items you always lose (passport, charger, spare keys)

### Home automation
- A plant watering reminder that accounts for recent rainfall and season
- A morning routine trigger: one button press starts the coffee, sets the thermostat, reads
  out your first meeting
- An energy tracker that shows which device is costing the most
- A presence detector that turns lights off when rooms have been empty for N minutes
- A window-open alert when rain is forecast

### Photography & visual memory
- A photo organizer that sorts by GPS location and creates a trip gallery automatically
- A "best of" picker that flags the sharpest, best-exposed shot from each burst
- A photo journal that attaches one photo per day to a calendar
- A client delivery tracker: which shoots have been delivered, paid, and archived
- A watermarking + export tool that applies your signature and resizes in one command

### Music
- A practice session logger: instrument, pieces, duration, notes — with a weekly heatmap
- A setlist manager that tracks what you've played at each gig and suggests what to repeat
- A chord progression idea pad: strum, tap, type — save ideas before they evaporate
- A song learning tracker with a mastery percentage per song
- A listening journal: what you're listening to, why, what you notice — like a reading log
  for music

### Art & design
- A commission tracker: client, brief, deadline, status, invoice — all in one view
- A project gallery that shows work-in-progress shots alongside the finished piece
- A color palette extractor: drop in a photo, get its dominant palette as hex codes
- A reference image organizer with tags and a mood-board view
- A "what am I working on" dashboard that keeps your active projects visible and honest

### Child monitoring & support
- A screen-time tracker per child and per app, with a visual summary for bedtime review
- A homework reminder that escalates gently (first the child, then the parent)
- A reading progress log: books read, pages, dates, and a reading-age estimate over time
- A chore chart with a star system the kids can check themselves
- A pickup tracker: who picked up whom, when, and from where — for shared-custody families

### Elderly care & monitoring
- A medication reminder with a daily confirmation tap — and an alert to caregivers if missed
- An activity log a family member updates after visits, readable by all siblings
- A daily check-in: one tap ("I'm okay") that notifies the family if not tapped by 10am
- A fall-detection alert that triggers when a wearable sensor detects an impact
- A contact list with large text and one-tap calling for the ten most-called people

### LinkedIn & networking
- A connection follow-up tracker: who you met, when, what you said you'd do, what you did
- A post engagement log: what you posted, when, how it performed, what you'd do differently
- A "keep in touch" reminder: flag connections you want to ping every 90 days
- A job search tracker: company, role, date applied, status, next step, notes
- A conversation starter bank: save interesting things you've read to use as icebreakers

### Sales & freelance
- A prospect pipeline: name, company, last contact, next action, deal size — simple kanban
- A follow-up reminder that escalates: day 3, day 7, day 14 — then flags as cold
- A win/loss journal: what you won, why; what you lost, why — patterns over time
- A rate tracker: what you charged, for what, for whom — so you know your real average rate
- A client health score: last contact, open invoices, upcoming renewals — one view

### Health & fitness
- A workout log with personal records highlighted automatically
- A water intake tracker with a gentle mid-day nudge if you're behind
- A sleep journal: bedtime, wake time, quality rating, notes — weekly pattern view
- A medication tracker with a morning confirmation and a missed-dose alert
- A mood-energy log that looks for correlations (sleep vs mood, exercise vs energy)

---

## Principles for a good personal PRD

**Name the real person.** "My 78-year-old father who lives alone" is far more useful than
"elderly user." The more real the person, the more real the software.

**Start with the friction.** The best personal software solves something that is currently
annoying. Don't start with features — start with the thing that makes you sigh or reach for a
sticky note.

**Three behaviors, not thirty.** A personal project that does three things well is almost always
more useful — and more likely to get built and used — than one that does everything. You can
always add more later.

**The vibe is real information.** "Simple and invisible" leads to very different software than
"powerful and configurable." Say what you mean. A parent's medication reminder should feel warm
and reassuring. An artist's commission tracker should feel organized and calm. A musician's
practice log should feel motivating. These aren't fluffy preferences — they shape every design
decision.

**Where it lives matters as much as what it does.** A web page you bookmark is different from a
desktop app you open every day, which is different from a terminal command you run before bed.
Be honest about your habits.

**Name the boundary.** Say out loud: "In v1, it does NOT do X." This is the sentence that makes
the project achievable. Without it, scope creep turns a weekend project into an abandoned repo.

---

## Handing off to /pybuilder

Once the PRD is complete, the natural next step is `/pybuilder`. It takes the PRD and drives a
full build loop: scaffold → iterate → prove → gate. You don't need to do anything between the
two skills — the PRD this skill produces is exactly the input format /pybuilder expects.

If this is your first build, start with `--target cli` (a command-line tool) regardless of your
eventual goal. It's the fastest path to something working that you can actually use. Once it
works, you can build a web UI or phone interface on top of it.

---

## Out of scope

- Enterprise or B2B product features (use `/atscale-prd-writer`)
- Pure technical architecture decisions (this skill shapes *what*, not *how*)
- Building the project (hand off to `/pybuilder` once done here)
- UX/visual design specs (this produces a behavioral spec, not a wireframe)
