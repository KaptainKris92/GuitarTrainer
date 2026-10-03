<script lang="ts">
  import { onDestroy } from 'svelte'
  import { mic, playTone } from './audio.svelte'
  import { EXERCISES, INTERVAL_NAMES, noteKeyAt, type Question } from './exercises'
  import Fretboard, { type Marker } from './Fretboard.svelte'
  import { speak, stopSpeaking } from './speech'
  import { store } from './store.svelte'
  import { midiAt, pcName, pcOf } from './theory'
  import { mastery, NoteGate, pickKey, record, type Stat } from './trainer'

  const ROUND_LENGTH = 10
  const TIME_LIMITS = [0, 10, 5, 3]

  const settings = store.settings
  let exercise = $state(EXERCISES[0])
  let phase = $state<'idle' | 'playing' | 'done'>('idle')

  let question = $state.raw<Question>()
  let results = $state<boolean[]>([])
  let feedback = $state<Marker[]>([])
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

  async function start() {
    if (settings.input === 'mic' && !mic.running) {
      await mic.start()
      if (!mic.running) return
    }
    results = []
    score = 0
    streak = 0
    lastAnswerMidi = null
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
    } while (candidate.answers.some((a) => midiAt(a.string, a.fret) === lastAnswerMidi) && ++tries < 5)

    question = candidate
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
    question!.answers.map((position) => ({ ...position, label: question!.answerLabel, tone }))

  /** Finish the current question and move on. */
  function settle(correct: boolean, note = '', played: Marker[] = []) {
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
    feedback = correct ? played : [...answerMarkers('root'), ...played]
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
    const hit = question.answers.find((a) => (tapped ? a.string === tapped.string && a.fret === tapped.fret : midiAt(a.string, a.fret) === midi))
    if (hit) {
      lastAnswerMidi = midi
      settle(true, '', [{ ...hit, label: question.answerLabel, tone: 'good' }])
      return
    }

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
    store.markPracticed()
    if (score > (store.player.best[exercise.id] ?? 0)) store.player.best[exercise.id] = score
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
        <span class="muted">Best {store.player.best[option.id] ?? 0}</span>
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
        Time limit
        <select bind:value={settings.timeLimit}>
          {#each TIME_LIMITS as seconds}
            <option value={seconds}>{seconds ? `${seconds} seconds` : 'None'}</option>
          {/each}
        </select>
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
    {:else}
      <div class="chips">
        {#each INTERVAL_NAMES as name, i}
          {@const color = heatColor(store.player.stats[`iv:${i + 1}`])}
          <span class="chip" class:colored={color} style:background={color}>{name}</span>
        {/each}
      </div>
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
      markers={[...question.given, ...feedback]}
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
    <p>
      Score <strong>{score}</strong> ·
      {score > 0 && score >= (store.player.best[exercise.id] ?? 0) ? 'New best!' : `Best ${store.player.best[exercise.id] ?? 0}`}
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
