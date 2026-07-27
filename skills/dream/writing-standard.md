# Writing standard — the prose voice for PRDs and visions

How every PRD and vision doc this skill produces should read. The PRD format (sections,
frontmatter) is defined in SKILL.md and `/atscale-prd-writer`; this file governs the
prose inside those sections. Read it before drafting; grade every draft against it
before committing.

## The prime rule — understandability above all

Write as simply and clearly as possible, at all times. Every other rule in this file
serves this one, and when any of them pulls against being understood, understandability
wins. The plain word beats the impressive one. The short sentence beats the clever one.
The explained term beats the compact one. The measure of a PRD is not how polished it
reads to its author — it is how fast a reader who wasn't in the room understands it,
correctly, on the first pass. If a reviewer has to reread a sentence, the sentence
failed, whatever else it did well.

## The quality gate — four axes

Every draft is graded on four axes before it ships. They pull against each other;
a PRD leans craftsman + scientist. No axis ever justifies prose the reader must
decode — all four serve the prime rule.

- **Craftsman (construction):** every word earns its place; structure before prose;
  order by importance and front-load the takeaway. Revise until nothing can be cut.
  The test for any sentence: remove it — did a *thought* disappear, or only rhythm?
  If only rhythm, it stays cut.
- **Scientist (precision):** claims grounded in evidence; quantify ("p95 latency 340ms",
  not "much faster"); hedge exactly as much as the uncertainty warrants and no more.
  Separate measured from inferred — and separate **built from planned**: continuity
  verbs ("keep", "continue", "maintain") assert a capability exists; intent verbs
  ("build", "add", "deliver") assert a plan. For every capability named, ask "does
  this exist today?" and give it the verb its status earns.
- **Statesman (audience):** read who's reading; lead with what matters to *them*;
  persuade by letting the evidence and the idea carry the conclusion. Know what to
  leave unsaid.
- **Artist (clarity as beauty):** elegant constructions and the clarifying analogy —
  in service of comprehension, never decoration. An analogy that makes an idea click
  is content; a term whose only job is to sound smart is flourish, and goes.

## The three-step method

Never ship a first draft, however small the piece.

1. **Outline before prose.** Decide the lead (the claim or the ask, first), the order
   of points (by importance), and the close. Gather the real facts first — a PRD claim
   without evidence behind it is fiction.
2. **Draft in one motion.** Write the version, not options. Rough is allowed;
   unfounded is not.
3. **Proofread and workshop.** Read it cold, as a reader who wasn't in the room.
   Grade on four things by name: simplicity, clarity, understandability, human
   readability. Every term the widest expected reader can't define gets defined at
   first use or cut; every acronym unpacks once. One idea per paragraph; parallel
   content (constraints, findings, options) gets a bolded plain-English lead label
   so a skimmer navigates by labels alone. Fix what the pass found, then stop —
   if the point is made, don't keep polishing.

## Sentence and structure rules

- **Lead with the point.** The reader should know where the section is going by the
  end of its first sentence. No throat-clearing, no wind-up.
- **Claim → reasoning → implication.** Show the structure of the thought; earn the
  conclusion rather than assert it. Name the mechanism beneath the symptom
  ("modeling is slow because six of seven time sinks are reconstruction", not
  "modeling is slow").
- **Vary sentence length deliberately:** a flowing sentence that develops the idea,
  then a short one to land it.
- **Lists and tables for genuinely enumerable content;** don't bullet-ize an argument
  that should flow as prose — and don't prose-ify a table.
- **Close on the consequence, not the thesis.** The last sentence of an argument cashes
  it out into what it enables for the reader — never into a verdict on the argument
  itself ("which proves the point" is the writer admiring the proof).
- **Emphasis is scarce.** At most one emphasized claim-sentence per section; bolding a
  whole block marks nothing.

## Vocabulary rules

- The exact technical term when it's the right word; never a buzzword for color.
- **Banned:** hype inflation (revolutionary, game-changing, disruptive, unprecedented);
  corporate speak (synergize, leverage our learnings, align on deliverables); false
  humility; "excited" as a default emotion; exclamation marks in professional prose.
  And the PRD bans: seamless, robust, scalable, enterprise-grade, intuitive — unless
  quantified.
- **Calendar acronyms banned in prose:** spell out "the second half of 2026", not "H2".
  Domain acronyms that name product concepts (SML, MCP, DAX) stay.
- **Borrowed flourish banned:** figurative math/physics jargon ("orthogonal", "at the
  limit"), classical allusions, word-chimes. The reader pays a decoding tax and gets
  nothing back.
- **Write in the reader's vocabulary, not the system's.** If decompressing a sentence
  requires knowing the design's internal vocabulary, it isn't written yet. Plain
  who-does-what-to-what beats abstract noun phrases from the architecture.
- **Scope promises honestly:** "build *for* X's needs" states a direction and lets the
  list be examples; "build *what X needs*" promises exhaustive coverage no plan can
  fund.

## Evidence discipline

- **Never write past the facts.** Every claim cites Phase 1 evidence or is labeled
  inferred.
- **The welded conclusion is banned:** fact, em-dash, then a conclusion the fact
  doesn't support. Say the inference chain out loud; if it needs steps the sentence
  doesn't state, cut the weld and argue the claim by its own mechanism.
- **Struck evidence takes its sentence with it.** When a number is removed as
  untrusted, delete or re-found the sentence that carried it — don't soften to
  "a large share".
- **Verbatim customer quotes are not evidence.** Cite a record the reader can check —
  a ticket count, a survey number, a contract — or state the claim as inferred.
- **Success metrics run claim → number → falsifier:** every objective carries its
  baseline and target; every hypothesis carries the test that would kill it. Land an
  uncomfortable number without a cushioning clause after it.

## Anti-patterns (never)

1. Throat-clearing openings ("In today's rapidly evolving landscape…").
2. Burying the takeaway under context or reasoning.
3. Padding for length — if the point is made, stop.
4. Hedging a measured result, or asserting an unmeasured one.
5. Manufacturing significance ("here's the crux", "make no mistake") — earn it instead.
6. Announcing instead of saying — colon-headed labels that classify rather than
   deliver ("Bottom line:", "Key point:"). Delete the label; lead with the fact.
7. Narrating process instead of stating results ("after reviewing the options we
   concluded…"). Write the decision, cut the deciding.
8. Metadata in reader-facing prose — provenance stamps, edit-history notes, session
   references. (The PRD frontmatter block is exempt: it is machine-read by `/build`
   and part of the house format, not prose.)
9. Compression that costs comprehension — semicolon walls, fragment stacks, arrow
   chains, insider shorthand. The writer saves keystrokes; the reader pays decoding
   time, and the reader's cost is the one that counts.
10. Unsupportable superlatives ("THE biggest") — calibrate even the rhetorical lines;
    a punchy sentence must survive scrutiny.
