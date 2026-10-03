<script lang="ts">
  import { onDestroy } from 'svelte'
  import { fly } from 'svelte/transition'
  import { mic, playTone, sfx } from './audio.svelte'
  import {
    EXERCISES,
    isUnlocked,
    mixedSession,
    modeLabel,
    noteKeyAt,
    skill,
    TRACKS,
    UNLOCK_AT,
    type Exercise,
    type Part,
    type Position,
    type Question,
  } from './exercises'
  import Fretboard, { type Marker } from './Fretboard.svelte'
  import { speak, stopSpeaking } from './speech'
  import Staff from './Staff.svelte'
  import { store } from './store.svelte'
  import { midiAt, pcName, pcOf } from './theory'
  import { levelFor, mastery, NoteGate, pickKey, record } from './trainer'

  const ROUND_LENGTH = 10
  const NOTE_GAP_MS = 700

  const settings = store.settings
  /** The exercise chosen in the skill tree. */
  let selected = $state.raw(EXERCISES[0])
  /** The exercise being played: the selected one, or a mixed daily session. */
  let active = $state.raw(EXERCISES[0])
  let phase = $state<'idle' | 'playing' | 'done'>('idle')

  let question = $state.raw<Question>()
  let results = $state<boolean[]>([])
  let feedback = $state<Marker[]>([])
  /** Notes of the current question found so far. */
  let found = $state<Marker[]>([])
  let wrongChoices = $state<string[]>([])
  let revealed = $state(false)
  let message = $state('')
  let score = $state(0)
  let streak = $state(0)
  let remaining = $state(1)
  let previousBest = $state(0)
  let xpEarned = $state(0)
  let levelBefore = $state(1)
  let remainingParts: Part[] = []
  /** True once the prompt has been given and the clock is running. */
  let listening = false
  let firstTry = true
  let startedAt = 0
  let lastAnswerMidi: number | null = null
  /** Microphone input is ignored until this time, while the app itself is making sound. */
  let muteUntil = 0
  let advanceTimer: ReturnType<typeof setTimeout> | undefined
  let clock = 0
  const gate = new NoteGate()

  const today = () => new Date().toLocaleDateString('sv')
  const unlocked = (exercise: Exercise) => settings.unlockAll || isUnlocked(exercise, store.player.stats)
  const heatColor = (value: number) => `hsl(${Math.round(value * 140)} 60% 38%)`

  const mode = $derived(modeLabel(selected, settings))
  const leaderboard = $derived(store.leaderboard(mode))

  const heatmap = $derived.by(() => {
    const markers: Marker[] = []
    for (const string of settings.strings) {
      for (let fret = 0; fret <= settings.maxFret; fret++) {
        const stat = store.player.stats[noteKeyAt(string, fret, settings.maxFret)]
        const color = stat ? heatColor(mastery(stat)) : undefined
        markers.push({ string, fret, label: pcName(pcOf(midiAt(string, fret))), tone: 'heat', color })
      }
    }
    return markers
  })

  /** Progress chips for the selected exercise: one per group of questions, coloured by mastery. */
  const groups = $derived.by(() => {
    const { groupOf } = selected
    if (!groupOf) return []
    const byLabel = new Map<string, string[]>()
    for (const key of selected.keys(settings)) {
      byLabel.set(groupOf(key), [...(byLabel.get(groupOf(key)) ?? []), key])
    }
    return [...byLabel].map(([label, keys]) => ({
      label,
      color: keys.some((key) => store.player.stats[key])
        ? heatColor(keys.reduce((sum, key) => sum + mastery(store.player.stats[key]), 0) / keys.length)
        : undefined,
    }))
  })

  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

  async function start(exercise: Exercise) {
    if (exercise.usesBoard && settings.input === 'mic' && !mic.running) {
      await mic.start()
      if (!mic.running) return
    }
    active = exercise
    settings.timeLimit = Math.max(0, Number(settings.timeLimit) || 0)
    results = []
    score = 0
    streak = 0
    xpEarned = 0
    levelBefore = levelFor(store.player.xp)
    lastAnswerMidi = null
    previousBest = store.bestScore(modeLabel(exercise, settings))
    phase = 'playing'
    next()
  }

  const startDaily = () => start(mixedSession(EXERCISES.filter(unlocked)))

  function playListen() {
    const notes = question?.listen ?? []
    notes.forEach((midi, i) => playTone(midi, (i * NOTE_GAP_MS) / 1000))
    const duration = notes.length * NOTE_GAP_MS + 300
    muteUntil = performance.now() + duration
    return sleep(duration)
  }

  async function next() {
    const keys = active.keys(settings)
    let candidate: Question
    let tries = 0
    do {
      candidate = active.question(pickKey(keys, store.player.stats, Math.random, question?.key), settings)
      // A note still ringing from the last answer is ignored by the gate, so do not ask for it again.
    } while (candidate.parts[0]?.answers.some((a) => midiAt(a.string, a.fret) === lastAnswerMidi) && ++tries < 5)

    question = candidate
    remainingParts = [...candidate.parts]
    found = []
    feedback = []
    wrongChoices = []
    revealed = false
    message = ''
    remaining = 1
    firstTry = true
    listening = false
    const stale = () => question !== candidate || phase !== 'playing'

    if (settings.voice && candidate.speech) await speak(candidate.speech)
    if (stale()) return
    if (candidate.listen) await playListen()
    if (stale()) return
    listening = true
    startedAt = performance.now()
    if (settings.timeLimit) clock = requestAnimationFrame(tick)
  }

  function tick() {
    remaining = 1 - (performance.now() - startedAt) / (settings.timeLimit * 1000)
    if (remaining <= 0) settle(false, 'Out of time.')
    else clock = requestAnimationFrame(tick)
  }

  /** Where the answer is: every remaining note, or just the next one when they must be played in order. */
  const answerMarkers = (): Marker[] =>
    (question?.ordered ? remainingParts.slice(0, 1) : remainingParts).flatMap((part) =>
      part.answers.map((position) => ({ ...position, label: part.label, tone: 'root' })),
    )

  /** Finish the current question and move on. */
  function settle(correct: boolean, note = '', played: Marker[] = []) {
    if (!listening || !question) return
    cancelAnimationFrame(clock)
    listening = false
    const ms = performance.now() - startedAt
    const firstTryCorrect = correct && firstTry
    record(store.player.stats, question.key, firstTryCorrect, ms)
    if (firstTryCorrect) {
      streak++
      const speedBonus = Math.round(100 * Math.max(0, 1 - ms / 8000))
      const points = Math.round((100 + speedBonus) * (1 + Math.min(streak - 1, 10) * 0.1))
      score += points
      xpEarned += Math.round(points / 10)
      store.player.xp += Math.round(points / 10)
    } else {
      streak = 0
    }
    results = [...results, firstTryCorrect]
    if (!correct) {
      feedback = [...answerMarkers(), ...played]
      revealed = true
    }
    message = [note, !correct && question.correct ? `It was ${question.correct}.` : ''].filter(Boolean).join(' ')
    if (settings.sfx) sfx(correct ? 'good' : 'bad')
    advanceTimer = setTimeout(() => (results.length >= ROUND_LENGTH ? finish() : next()), correct ? 700 : 1800)
  }

  function reveal() {
    if (!listening) return
    firstTry = false
    feedback = answerMarkers()
    revealed = true
    if (question?.parts.length) message = settings.input === 'mic' ? 'Now play it.' : 'Now tap it.'
  }

  /** Handle a played note. `tapped` is set when it came from the on-screen fretboard. */
  function answer(midi: number, tapped?: Position) {
    if (!listening || !question?.parts.length) return
    const matches = (a: Position) =>
      tapped ? a.string === tapped.string && a.fret === tapped.fret : midiAt(a.string, a.fret) === midi
    const candidates = question.ordered ? remainingParts.slice(0, 1) : remainingParts
    const part = candidates.find((p) => p.answers.some(matches))
    if (part) {
      lastAnswerMidi = midi
      remainingParts = remainingParts.filter((p) => p !== part)
      found = [...found.filter((m) => !matches(m)), { ...part.answers.find(matches)!, label: part.label, tone: 'good' }]
      feedback = []
      message = ''
      if (!remainingParts.length) settle(true)
      return
    }
    // Repeating a note that has already been found is not a mistake.
    if (question.parts.some((p) => !remainingParts.includes(p) && p.answers.some(matches))) return

    // Show where the wrong note was: the tapped spot, or the played pitch on the string being asked about.
    const string = tapped?.string ?? question.highlightString
    const fret = tapped?.fret ?? (string ? midi - midiAt(string, 0) : -1)
    const played: Marker[] =
      string && fret >= 0 && fret <= settings.maxFret ? [{ string, fret, label: pcName(pcOf(midi)), tone: 'bad' }] : []
    // Never name the note in ear and reading questions: that would give the answer away.
    const note = question.listen || question.staff ? 'Not that one.' : `That was ${pcName(pcOf(midi))}.`
    if (settings.oneAttempt) {
      settle(false, note, played)
    } else {
      firstTry = false
      feedback = played
      message = note
    }
  }

  function choose(choice: string) {
    if (!listening || !question || wrongChoices.includes(choice)) return
    if (choice === question.correct) return settle(true)
    if (settings.oneAttempt) return settle(false)
    firstTry = false
    wrongChoices = [...wrongChoices, choice]
  }

  function finish() {
    phase = 'done'
    store.finishRound(modeLabel(active, settings), score, results.filter(Boolean).length)
    if (active.id === 'daily') store.player.lastDaily = today()
    if (settings.sfx) sfx('done')
  }

  function quit() {
    clearTimeout(advanceTimer)
    cancelAnimationFrame(clock)
    stopSpeaking()
    listening = false
    phase = 'idle'
  }

  function pick(string: number, fret: number) {
    playTone(midiAt(string, fret))
    answer(midiAt(string, fret), { string, fret })
  }

  function toggleString(string: number) {
    const chosen = settings.strings.includes(string)
      ? settings.strings.filter((s) => s !== string)
      : [...settings.strings, string]
    if (chosen.length) settings.strings = chosen.sort()
  }

  $effect(() => {
    if (phase !== 'playing' || settings.input !== 'mic') return
    // Feed the gate even while not listening so it knows which notes are still ringing.
    return mic.subscribe((frame) => {
      const midi = gate.feed(frame.midi, frame.silent)
      if (midi !== null && performance.now() > muteUntil) answer(midi)
    })
  })

  onDestroy(quit)
</script>

{#if phase === 'idle'}
  <section class="card daily">
    <div>
      <h2>Daily session</h2>
      <p class="muted">
        {store.player.lastDaily === today()
          ? 'Done for today. Come back tomorrow to keep your streak, or go again.'
          : 'Ten mixed questions from everything you have unlocked, weighted towards your weak spots.'}
      </p>
    </div>
    <button class="primary" onclick={startDaily}>
      {store.player.lastDaily === today() ? 'Play again' : 'Start daily session'}
    </button>
  </section>

  <section class="card">
    <h3>Skill tree</h3>
    <p class="muted">Reach {UNLOCK_AT * 100}% in an exercise to unlock the next one in its track.</p>
    <div class="tree">
      {#each TRACKS as track}
        <div class="track-name">{track}</div>
        <div class="track">
          {#each EXERCISES.filter((exercise) => exercise.track === track) as exercise, i}
            {@const open = unlocked(exercise)}
            {@const level = skill(exercise, store.player.stats)}
            {#if i > 0}<span class="link" class:open></span>{/if}
            <button class="node" class:active={selected === exercise} disabled={!open} onclick={() => (selected = exercise)}>
              <strong>{exercise.name}</strong>
              {#if open}
                <span class="bar"><span style:width="{level * 100}%"></span></span>
                <span class="muted">{Math.round(level * 100)}% mastered</span>
              {:else}
                <span class="muted">Locked</span>
              {/if}
            </button>
          {/each}
        </div>
      {/each}
    </div>
  </section>

  <section class="card">
    <h2>{selected.name}</h2>
    <p class="muted">{selected.blurb} Questions you find hard come up more often.</p>
    <div class="controls">
      {#if selected.usesBoard}
        <label>
          Answer with
          <select bind:value={settings.input}>
            <option value="mic">Guitar (microphone)</option>
            <option value="tap">Tap the fretboard</option>
          </select>
        </label>
        <label>
          Frets
          <select bind:value={settings.maxFret}>
            <option value={12}>First 12</option>
            <option value={24}>All 24</option>
          </select>
        </label>
      {/if}
      {#if selected.id === 'notes'}
        <label>
          Notes
          <select bind:value={settings.naturalsOnly}>
            <option value={true}>Naturals only</option>
            <option value={false}>All 12 notes</option>
          </select>
        </label>
        <div class="field">
          Strings
          <div class="toggles">
            {#each [6, 5, 4, 3, 2, 1] as string}
              <button class="toggle" class:on={settings.strings.includes(string)} onclick={() => toggleString(string)}>
                {string}
              </button>
            {/each}
          </div>
        </div>
      {/if}
      <label>
        Time limit (seconds, 0 = none)
        <input type="number" min="0" max="120" step="any" bind:value={settings.timeLimit} />
      </label>
      <label class="check">
        <input type="checkbox" bind:checked={settings.oneAttempt} />
        One attempt: your first answer counts
      </label>
      <button class="primary" onclick={() => start(selected)}>Start round</button>
    </div>
    {#if mic.error}<p class="error">{mic.error}</p>{/if}
  </section>

  {#if selected.id === 'notes' || groups.length}
    <section class="card">
      <h3>Your progress</h3>
      <p class="muted">Red is shaky, green is solid, dark ones have not come up yet.</p>
      {#if selected.id === 'notes'}
        <Fretboard frets={settings.maxFret} markers={heatmap} />
      {:else}
        <div class="chips">
          {#each groups as group}
            <span class="chip" class:colored={group.color} style:background={group.color}>{group.label}</span>
          {/each}
        </div>
      {/if}
    </section>
  {/if}

  <section class="card">
    <h3>High scores</h3>
    <p class="muted">{mode}</p>
    {#if leaderboard.length}
      <table>
        <tbody>
          {#each leaderboard as row, i}
            <tr>
              <td class="muted">{i + 1}</td>
              <td>{row.name}</td>
              <td><strong>{row.score}</strong></td>
              <td class="muted">{row.correct} / {ROUND_LENGTH}</td>
              <td class="muted">{new Date(row.at).toLocaleDateString()}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p class="muted">No rounds played with these settings yet.</p>
    {/if}
  </section>
{:else if phase === 'playing' && question}
  <section class="card">
    <div class="hud">
      <div class="dots">
        {#each Array(ROUND_LENGTH) as _, i}
          <span class="dot" class:good={results[i] === true} class:bad={results[i] === false}></span>
        {/each}
      </div>
      <span class="stat">Streak <strong>{streak}</strong></span>
      <span class="stat">Score <strong>{score}</strong></span>
    </div>
    {#if settings.timeLimit}
      <div class="timer"><span style:width="{Math.max(0, remaining) * 100}%"></span></div>
    {/if}

    {#key question}
      <div class="prompt" in:fly={{ y: 12, duration: 180 }}>
        {#if question.staff}<Staff note={question.staff} />{/if}
        {#if question.title}<div class="target">{question.title}</div>{/if}
        <div class="where">{question.subtitle}</div>
        <div class="message muted">{message}&nbsp;</div>
        {#if question.listen}
          <button onclick={playListen}>Hear it again</button>
        {/if}
      </div>
    {/key}

    {#if question.choices}
      <div class="choices" class:many={question.choices.length > 8}>
        {#each question.choices as choice}
          <button
            class="choice"
            class:wrong={wrongChoices.includes(choice)}
            class:right={revealed && choice === question.correct}
            onclick={() => choose(choice)}
          >
            {choice}
          </button>
        {/each}
      </div>
    {/if}

    {#if question.parts.length}
      <Fretboard
        frets={settings.maxFret}
        markers={[...question.given, ...found, ...feedback]}
        highlightString={question.highlightString}
        onpick={settings.input === 'tap' ? pick : undefined}
      />
    {/if}

    <div class="actions">
      {#if !settings.oneAttempt}<button onclick={reveal}>Show me</button>{/if}
      <button onclick={quit}>End round</button>
    </div>
  </section>
{:else}
  <section class="card summary">
    <h2>Round complete</h2>
    <div class="target">{results.filter(Boolean).length} / {ROUND_LENGTH}</div>
    <p class="muted">first-try correct</p>
    <p>
      Score <strong>{score}</strong> ·
      {score > previousBest ? 'New best for these settings!' : `Best ${previousBest}`}
    </p>
    <p>
      +{xpEarned} XP
      {#if levelFor(store.player.xp) > levelBefore}
        · <strong class="levelup">Level up! You are now level {levelFor(store.player.xp)}</strong>
      {/if}
    </p>
    <p class="muted">{modeLabel(active, settings)}</p>
    <div class="actions centred">
      <button class="primary" onclick={() => start(active)}>Play again</button>
      <button onclick={quit}>Done</button>
    </div>
  </section>
{/if}

<style>
  .daily {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    border-color: var(--accent);
  }
  .daily p {
    margin: 0;
  }
  .daily button {
    flex-shrink: 0;
  }
  .tree {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.75rem 1rem;
    align-items: center;
  }
  .track-name {
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .track {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    row-gap: 0.5rem;
  }
  .link {
    width: 1.5rem;
    height: 2px;
    background: var(--border);
  }
  .link.open {
    background: var(--accent);
  }
  .node {
    display: grid;
    gap: 0.25rem;
    width: 11.5rem;
    padding: 0.6rem 0.8rem;
    text-align: left;
    border-radius: 12px;
  }
  .node span {
    font-size: 0.75rem;
    font-weight: 400;
  }
  .node.active {
    border-color: var(--accent);
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  .node:disabled {
    cursor: default;
    opacity: 0.5;
  }
  .bar {
    height: 5px;
    border-radius: 3px;
    background: var(--border);
    overflow: hidden;
  }
  .bar span {
    display: block;
    height: 100%;
    background: var(--accent);
  }
  .controls .primary {
    margin-left: auto;
  }
  .hud {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }
  .dots {
    display: flex;
    gap: 6px;
    flex: 1;
  }
  .dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--surface-2);
    border: 1px solid var(--border);
  }
  .dot.good {
    background: var(--good);
    border-color: var(--good);
  }
  .dot.bad {
    background: var(--bad);
    border-color: var(--bad);
  }
  .stat {
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .stat strong {
    color: var(--text);
  }
  .timer {
    height: 6px;
    margin-top: 0.9rem;
    border-radius: 3px;
    background: var(--surface-2);
    overflow: hidden;
  }
  .timer span {
    display: block;
    height: 100%;
    background: var(--accent);
  }
  .prompt,
  .summary {
    text-align: center;
  }
  .prompt {
    padding: 1.5rem 0 0.75rem;
  }
  .target {
    font-size: 4.5rem;
    font-weight: 800;
    line-height: 1.1;
    color: var(--accent);
  }
  .where {
    font-size: 1.3rem;
  }
  .message {
    margin: 0.4rem 0;
  }
  .choices {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
    gap: 0.6rem;
    max-width: 36rem;
    margin: 0 auto 1rem;
  }
  .choices.many {
    max-width: 52rem;
  }
  .choice {
    padding: 0.9rem 0.5rem;
    font-size: 1.05rem;
  }
  .choice.wrong {
    border-color: var(--bad);
    color: var(--bad);
    opacity: 0.6;
  }
  .choice.right {
    border-color: var(--good);
    background: var(--good);
    color: #111;
  }
  .actions {
    display: flex;
    gap: 0.6rem;
    margin-top: 1rem;
  }
  .actions.centred {
    justify-content: center;
  }
  .levelup {
    color: var(--accent);
  }
  .toggles {
    display: flex;
    gap: 4px;
  }
  .toggle {
    width: 2.3rem;
    padding-inline: 0;
  }
  .toggle.on {
    border-color: var(--accent);
    color: var(--accent);
  }
  input[type='number'] {
    width: 6rem;
    font: inherit;
    color: var(--text);
    padding: 0.45rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-2);
  }
  table {
    border-collapse: collapse;
  }
  td {
    padding: 0.25rem 1.5rem 0.25rem 0;
    font-variant-numeric: tabular-nums;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .chip {
    padding: 0.35rem 0.8rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface-2);
  }
  .chip.colored {
    color: #fff;
  }
  .error {
    color: var(--bad);
    margin-top: 0.8rem;
  }
</style>
