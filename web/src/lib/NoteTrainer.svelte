<script lang="ts">
  import { onDestroy } from 'svelte'
  import { mic, playTone } from './audio.svelte'
  import Fretboard, { type Marker } from './Fretboard.svelte'
  import { fretsFor, midiAt, pcName, pcOf, pcPromptName, stringName } from './theory'
  import {
    allItems,
    itemKey,
    loadStats,
    mastery,
    NoteGate,
    pickItem,
    record,
    saveStats,
    type Item,
  } from './trainer'

  const MAX_FRET = 12
  const ROUND_LENGTH = 10
  const BEST_KEY = 'guitar-trainer.note-best'
  const ORDINALS = ['1st', '2nd', '3rd', '4th', '5th', '6th']

  let phase = $state<'idle' | 'playing' | 'done'>('idle')
  let input = $state<'mic' | 'tap'>('mic')
  let strings = $state([1, 2, 3, 4, 5, 6])
  let naturalsOnly = $state(true)
  let stats = $state(loadStats())
  let best = $state(Number(localStorage.getItem(BEST_KEY) ?? 0))

  let item = $state<Item>({ string: 1, pc: 0 })
  let results = $state<boolean[]>([])
  let feedback = $state<Marker[]>([])
  let message = $state('')
  let score = $state(0)
  let streak = $state(0)
  let firstTry = true
  let locked = false
  let startedAt = 0
  let advanceTimer: ReturnType<typeof setTimeout> | undefined
  const gate = new NoteGate()

  const items = $derived(allItems(strings, naturalsOnly))
  const heatmap = $derived.by(() => {
    const markers: Marker[] = []
    for (const string of strings) {
      for (let fret = 0; fret <= MAX_FRET; fret++) {
        const pc = pcOf(midiAt(string, fret))
        const stat = stats[itemKey({ string, pc })]
        markers.push({
          string,
          fret,
          label: pcName(pc),
          tone: 'heat',
          color: stat ? `hsl(${Math.round(mastery(stat) * 140)} 60% 38%)` : undefined,
        })
      }
    }
    return markers
  })

  async function start() {
    if (input === 'mic' && !mic.running) {
      await mic.start()
      if (!mic.running) return
    }
    results = []
    score = 0
    streak = 0
    phase = 'playing'
    next()
  }

  function next() {
    item = pickItem(items, stats, Math.random, results.length ? item.pc : undefined)
    feedback = []
    message = ''
    firstTry = true
    locked = false
    startedAt = performance.now()
  }

  function miss() {
    firstTry = false
    streak = 0
  }

  function reveal() {
    if (locked) return
    miss()
    feedback = fretsFor(item.string, item.pc, MAX_FRET).map((fret) => ({
      string: item.string,
      fret,
      label: pcName(item.pc),
      tone: 'root',
    }))
    message = input === 'mic' ? 'Now play it.' : 'Now tap it.'
  }

  /** Handle an answer, given as a position (tap) or just a pitch (mic). */
  function answer(midi: number, string = item.string) {
    if (locked) return
    const fret = midi - midiAt(string, 0)
    const onBoard = fret >= 0 && fret <= MAX_FRET
    const position: Marker = { string, fret, label: pcName(pcOf(midi)) }

    if (string !== item.string || !onBoard || pcOf(midi) !== item.pc) {
      miss()
      feedback = onBoard ? [{ ...position, tone: 'bad' }] : []
      message = string === item.string ? `That was ${pcName(pcOf(midi))}.` : 'Wrong string.'
      return
    }

    const ms = performance.now() - startedAt
    stats = record(stats, item, firstTry, ms)
    saveStats(stats)
    if (firstTry) {
      streak++
      const speedBonus = Math.round(100 * Math.max(0, 1 - ms / 8000))
      score += Math.round((100 + speedBonus) * (1 + Math.min(streak - 1, 10) * 0.1))
    }
    results = [...results, firstTry]
    feedback = [{ ...position, tone: 'good' }]
    message = ''
    locked = true
    advanceTimer = setTimeout(() => (results.length >= ROUND_LENGTH ? finish() : next()), 700)
  }

  function finish() {
    phase = 'done'
    if (score > best) {
      best = score
      localStorage.setItem(BEST_KEY, String(best))
    }
  }

  function quit() {
    clearTimeout(advanceTimer)
    phase = 'idle'
  }

  function pick(string: number, fret: number) {
    playTone(midiAt(string, fret))
    answer(midiAt(string, fret), string)
  }

  function toggleString(string: number) {
    const selected = strings.includes(string) ? strings.filter((s) => s !== string) : [...strings, string]
    if (selected.length) strings = selected.sort()
  }

  $effect(() => {
    if (phase !== 'playing' || input !== 'mic') return
    return mic.subscribe((frame) => {
      const midi = gate.feed(frame.midi, frame.silent)
      if (midi !== null) answer(midi)
    })
  })

  onDestroy(() => clearTimeout(advanceTimer))
</script>

{#if phase === 'idle'}
  <section class="card">
    <h2>Find the note</h2>
    <p class="muted">
      You are given a note and a string. Play it on your guitar, or tap it on the fretboard. Notes you find hard come
      up more often.
    </p>
    <div class="controls">
      <label>
        Answer with
        <select bind:value={input}>
          <option value="mic">Guitar (microphone)</option>
          <option value="tap">Tap the fretboard</option>
        </select>
      </label>
      <label>
        Notes
        <select bind:value={naturalsOnly}>
          <option value={true}>Naturals only</option>
          <option value={false}>All 12 notes</option>
        </select>
      </label>
      <div class="field">
        Strings
        <div class="toggles">
          {#each [6, 5, 4, 3, 2, 1] as string}
            <button class="toggle" class:on={strings.includes(string)} onclick={() => toggleString(string)}>
              {string}
            </button>
          {/each}
        </div>
      </div>
      <button class="primary" onclick={start}>Start round</button>
    </div>
    {#if mic.error}<p class="error">{mic.error}</p>{/if}
  </section>

  <section class="card">
    <h3>Your fretboard</h3>
    <p class="muted">Red is shaky, green is solid, dark notes have not come up yet.</p>
    <Fretboard frets={MAX_FRET} markers={heatmap} />
  </section>
{:else if phase === 'playing'}
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

    <div class="prompt">
      <div class="target">{pcPromptName(item.pc)}</div>
      <div class="where">on the {ORDINALS[item.string - 1]} string ({stringName(item.string)})</div>
      <div class="message muted">{message}&nbsp;</div>
    </div>

    <Fretboard
      frets={MAX_FRET}
      markers={feedback}
      highlightString={item.string}
      onpick={input === 'tap' ? pick : undefined}
    />

    <div class="actions">
      <button onclick={reveal}>Show me</button>
      <button onclick={quit}>End round</button>
    </div>
  </section>
{:else}
  <section class="card summary">
    <h2>Round complete</h2>
    <div class="target">{results.filter(Boolean).length} / {ROUND_LENGTH}</div>
    <p class="muted">first-try correct</p>
    <p>Score <strong>{score}</strong> · {score >= best ? 'New best!' : `Best ${best}`}</p>
    <div class="actions centred">
      <button class="primary" onclick={start}>Play again</button>
      <button onclick={quit}>Done</button>
    </div>
  </section>
{/if}

<style>
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
  .error {
    color: var(--bad);
  }
</style>
