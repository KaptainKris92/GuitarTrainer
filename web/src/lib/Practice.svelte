<script lang="ts">
  import { onDestroy } from 'svelte'
  import { mic, playTone } from './audio.svelte'
  import { CHORD_TYPES, EXERCISES, INTERVAL_NAMES, modeLabel, noteKeyAt, type Part, type Question } from './exercises'
  import Fretboard, { type Marker } from './Fretboard.svelte'
  import { speak, stopSpeaking } from './speech'
  import { store } from './store.svelte'
  import { midiAt, pcName, pcOf } from './theory'
  import { mastery, NoteGate, pickKey, record, type Stat } from './trainer'

  const ROUND_LENGTH = 10

  const settings = store.settings
  let exercise = $state(EXERCISES[0])
  let phase = $state<'idle' | 'playing' | 'done'>('idle')

  let question = $state.raw<Question>()
  let results = $state<boolean[]>([])
  let feedback = $state<Marker[]>([])
  /** Notes of the current question found so far. */
  let found = $state<Marker[]>([])
  let remainingParts: Part[] = []
  let message = $state('')
  let score = $state(0)
  let streak = $state(0)
  let remaining = $state(1)
  /** True once the prompt has been spoken and the clock is running. */
  let listening = false
  let firstTry = true
  let startedAt = 0
  let lastAnswerMidi: number | null = null
  let advanceTimer: ReturnType<typeof setTimeout> | undefined
  let clock = 0
  const gate = new NoteGate()

  const heatColor = (stat: Stat | undefined) =>
    stat ? `hsl(${Math.round(mastery(stat) * 140)} 60% 38%)` : undefined

  const heatmap = $derived.by(() => {
    const markers: Marker[] = []
    for (const string of settings.strings) {
      for (let fret = 0; fret <= settings.maxFret; fret++) {
        const stat = store.player.stats[noteKeyAt(string, fret, settings.maxFret)]
        markers.push({ string, fret, label: pcName(pcOf(midiAt(string, fret))), tone: 'heat', color: heatColor(stat) })
      }
    }
    return markers
  })

  const mode = $derived(modeLabel(exercise, settings))
  const leaderboard = $derived(store.leaderboard(mode))
  let previousBest = $state(0)

  /** Average mastery across all of the exercise's questions whose key starts with `prefix`. */
  function groupColor(prefix: string) {
    const keys = exercise.keys(settings).filter((key) => key.startsWith(prefix))
    if (!keys.some((key) => store.player.stats[key])) return undefined
    const total = keys.reduce((sum, key) => sum + mastery(store.player.stats[key]), 0)
    return `hsl(${Math.round((total / keys.length) * 140)} 60% 38%)`
  }

  async function start() {
    if (settings.input === 'mic' && !mic.running) {
      await mic.start()
      if (!mic.running) return
    }
    settings.timeLimit = Math.max(0, Number(settings.timeLimit) || 0)
    results = []
    score = 0
    streak = 0
    lastAnswerMidi = null
    previousBest = store.bestScore(mode)
    phase = 'playing'
    next()
  }

  async function next() {
    const keys = exercise.keys(settings)
    let candidate: Question
    let tries = 0
    do {
      candidate = exercise.question(pickKey(keys, store.player.stats, Math.random, question?.key), settings)
      // A note still ringing from the last answer is ignored by the gate, so do not ask for it again.
    } while (candidate.parts[0].answers.some((a) => midiAt(a.string, a.fret) === lastAnswerMidi) && ++tries < 5)

    question = candidate
    remainingParts = [...candidate.parts]
    found = []
    feedback = []
    message = ''
    remaining = 1
    firstTry = true
    listening = false

    if (settings.voice) {
      await speak(candidate.speech)
      if (question !== candidate || phase !== 'playing') return
    }
    listening = true
    startedAt = performance.now()
    if (settings.timeLimit) clock = requestAnimationFrame(tick)
  }

  function tick() {
    remaining = 1 - (performance.now() - startedAt) / (settings.timeLimit * 1000)
    if (remaining <= 0) settle(false, 'Out of time.')
    else clock = requestAnimationFrame(tick)
  }

  const answerMarkers = (tone: Marker['tone']): Marker[] =>
    remainingParts.flatMap((part) => part.answers.map((position) => ({ ...position, label: part.label, tone })))

  /** Finish the current question and move on. */
  function settle(correct: boolean, note = '', played: Marker[] = []) {
    if (!listening) return
    cancelAnimationFrame(clock)
    listening = false
    const ms = performance.now() - startedAt
    const firstTryCorrect = correct && firstTry
    record(store.player.stats, question!.key, firstTryCorrect, ms)
    if (firstTryCorrect) {
      streak++
      const speedBonus = Math.round(100 * Math.max(0, 1 - ms / 8000))
      const points = Math.round((100 + speedBonus) * (1 + Math.min(streak - 1, 10) * 0.1))
      score += points
      store.player.xp += Math.round(points / 10)
    } else {
      streak = 0
    }
    results = [...results, firstTryCorrect]
    feedback = correct ? [] : [...answerMarkers('root'), ...played]
    message = note
    advanceTimer = setTimeout(() => (results.length >= ROUND_LENGTH ? finish() : next()), correct ? 700 : 1600)
  }

  function reveal() {
    if (!listening) return
    firstTry = false
    feedback = answerMarkers('root')
    message = settings.input === 'mic' ? 'Now play it.' : 'Now tap it.'
  }

  /** Handle a played note. `tapped` is set when it came from the on-screen fretboard. */
  function answer(midi: number, tapped?: { string: number; fret: number }) {
    if (!listening || !question) return
    const matches = (a: { string: number; fret: number }) =>
      tapped ? a.string === tapped.string && a.fret === tapped.fret : midiAt(a.string, a.fret) === midi
    const part = remainingParts.find((p) => p.answers.some(matches))
    if (part) {
      lastAnswerMidi = midi
      remainingParts = remainingParts.filter((p) => p !== part)
      found = [...found, { ...part.answers.find(matches)!, label: part.label, tone: 'good' }]
      feedback = []
      message = ''
      if (!remainingParts.length) settle(true)
      return
    }
    // Playing a chord note that has already been found is not a mistake.
    if (question.parts.some((p) => p.answers.some(matches))) return

    // Show where the wrong note was: the tapped spot, or the played pitch on the string being asked about.
    const string = tapped?.string ?? question.highlightString
    const fret = tapped?.fret ?? (string ? midi - midiAt(string, 0) : -1)
    const played: Marker[] =
      string && fret >= 0 && fret <= settings.maxFret ? [{ string, fret, label: pcName(pcOf(midi)), tone: 'bad' }] : []
    const note = `That was ${pcName(pcOf(midi))}.`
    if (settings.oneAttempt) {
      settle(false, note, played)
    } else {
      firstTry = false
      feedback = played
      message = note
    }
  }

  function finish() {
    phase = 'done'
    store.finishRound(mode, score, results.filter(Boolean).length)
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
    const selected = settings.strings.includes(string)
      ? settings.strings.filter((s) => s !== string)
      : [...settings.strings, string]
    if (selected.length) settings.strings = selected.sort()
  }

  $effect(() => {
    if (phase !== 'playing' || settings.input !== 'mic') return
    // Feed the gate even while the prompt is being spoken so it knows which notes are still ringing.
    return mic.subscribe((frame) => {
      const midi = gate.feed(frame.midi, frame.silent)
      if (midi !== null) answer(midi)
    })
  })

  onDestroy(quit)
</script>

{#if phase === 'idle'}
  <div class="modes">
    {#each EXERCISES as option}
      <button class="mode" class:active={exercise === option} onclick={() => (exercise = option)}>
        <strong>{option.name}</strong>
        <span class="muted">Best {store.bestScore(modeLabel(option, settings))}</span>
      </button>
    {/each}
  </div>

  <section class="card">
    <h2>{exercise.name}</h2>
    <p class="muted">
      {exercise.blurb} Play it on your guitar or tap it on the fretboard. Questions you find hard come up more often.
    </p>
    <div class="controls">
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
      {#if exercise.id === 'notes'}
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
    </div>
    <div class="controls difficulty">
      <label>
        Time limit (seconds, 0 = none)
        <input type="number" min="0" max="120" step="any" bind:value={settings.timeLimit} />
      </label>
      <label class="check">
        <input type="checkbox" bind:checked={settings.oneAttempt} />
        One attempt: the first note you play is your answer
      </label>
      <label class="check">
        <input type="checkbox" bind:checked={settings.voice} />
        Voice prompts
      </label>
      <button class="primary" onclick={start}>Start round</button>
    </div>
    {#if mic.error}<p class="error">{mic.error}</p>{/if}
  </section>

  <section class="card">
    <h3>Your progress</h3>
    {#if exercise.id === 'notes'}
      <p class="muted">Red is shaky, green is solid, dark notes have not come up yet.</p>
      <Fretboard frets={settings.maxFret} markers={heatmap} />
    {:else if exercise.id === 'intervals'}
      <div class="chips">
        {#each INTERVAL_NAMES as name, i}
          {@const color = heatColor(store.player.stats[`iv:${i + 1}`])}
          <span class="chip" class:colored={color} style:background={color}>{name}</span>
        {/each}
      </div>
    {:else}
      <div class="chips">
        {#each Object.keys(CHORD_TYPES) as type}
          {@const color = groupColor(`ch:${type}:`)}
          <span class="chip" class:colored={color} style:background={color}>{type}</span>
        {/each}
      </div>
    {/if}
  </section>

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

    <div class="prompt">
      <div class="target">{question.title}</div>
      <div class="where">{question.subtitle}</div>
      <div class="message muted">{message}&nbsp;</div>
    </div>

    <Fretboard
      frets={settings.maxFret}
      markers={[...question.given, ...found, ...feedback]}
      highlightString={question.highlightString}
      onpick={settings.input === 'tap' ? pick : undefined}
    />

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
    <p class="muted">{mode}</p>
    <p>
      Score <strong>{score}</strong> ·
      {score > previousBest ? 'New best for these settings!' : `Best ${previousBest}`}
    </p>
    <div class="actions centred">
      <button class="primary" onclick={start}>Play again</button>
      <button onclick={quit}>Done</button>
    </div>
  </section>
{/if}

<style>
  .modes {
    display: flex;
    gap: 0.75rem;
  }
  .mode {
    display: grid;
    gap: 0.1rem;
    flex: 1;
    padding: 0.8rem 1rem;
    text-align: left;
    border-radius: 14px;
    background: var(--surface);
  }
  .mode span {
    font-size: 0.8rem;
    font-weight: 400;
  }
  .mode.active {
    border-color: var(--accent);
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  .difficulty {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    align-items: center;
  }
  .difficulty .primary {
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
    margin-top: 0.4rem;
  }
  .actions {
    display: flex;
    gap: 0.6rem;
    margin-top: 1rem;
  }
  .actions.centred {
    justify-content: center;
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
  .modes {
    flex-wrap: wrap;
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
