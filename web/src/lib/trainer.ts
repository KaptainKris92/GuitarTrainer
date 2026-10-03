import { NATURAL_PCS } from './theory'

/** One thing to learn: a pitch class on a string. */
export type Item = { string: number; pc: number }
export type Stat = { seen: number; correct: number; avgMs: number }
export type Stats = Record<string, Stat>

const STORAGE_KEY = 'guitar-trainer.note-stats'
const FAST_MS = 1500
const SLOW_MS = 6000

export const itemKey = (item: Item) => `${item.string}:${item.pc}`

export function allItems(strings: number[], naturalsOnly: boolean): Item[] {
  const pcs = naturalsOnly ? NATURAL_PCS : [...Array(12).keys()]
  return strings.flatMap((string) => pcs.map((pc) => ({ string, pc })))
}

/** 0 (unknown) to 1 (answered reliably and quickly). */
export function mastery(stat: Stat | undefined): number {
  if (!stat || stat.seen === 0) return 0
  const accuracy = stat.correct / stat.seen
  const confidence = Math.min(1, stat.seen / 5)
  const speed = Math.min(1, Math.max(0, (SLOW_MS - stat.avgMs) / (SLOW_MS - FAST_MS)))
  return accuracy * confidence * (0.5 + 0.5 * speed)
}

/** Weighted random pick favouring weak items; never repeats the previous pitch class. */
export function pickItem(items: Item[], stats: Stats, rand = Math.random, avoidPc?: number): Item {
  const candidates = items.filter((item) => item.pc !== avoidPc)
  const pool = candidates.length ? candidates : items
  const weights = pool.map((item) => 1 + 4 * (1 - mastery(stats[itemKey(item)])))
  let roll = rand() * weights.reduce((a, b) => a + b, 0)
  for (let i = 0; i < pool.length; i++) {
    roll -= weights[i]
    if (roll < 0) return pool[i]
  }
  return pool[pool.length - 1]
}

export function record(stats: Stats, item: Item, correct: boolean, ms: number): Stats {
  const prev = stats[itemKey(item)] ?? { seen: 0, correct: 0, avgMs: ms }
  return {
    ...stats,
    [itemKey(item)]: {
      seen: prev.seen + 1,
      correct: prev.correct + (correct ? 1 : 0),
      avgMs: prev.seen === 0 ? ms : prev.avgMs * 0.7 + ms * 0.3,
    },
  }
}

export function loadStats(): Stats {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
  } catch {
    return {}
  }
}

export function saveStats(stats: Stats) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stats))
}

/**
 * Turns a stream of per-frame pitch readings into discrete "note played" events.
 * A note is reported once it has been stable for `need` frames, and is not
 * reported again while it keeps ringing; silence re-arms it.
 */
export class NoteGate {
  private candidate: number | null = null
  private count = 0
  private blocked: number | null = null
  private need: number

  constructor(need = 4) {
    this.need = need
  }

  feed(midi: number | null, silent: boolean): number | null {
    if (silent) this.blocked = null
    if (midi === null) {
      this.candidate = null
      this.count = 0
      return null
    }
    if (midi === this.candidate) this.count++
    else {
      this.candidate = midi
      this.count = 1
    }
    if (this.count === this.need && midi !== this.blocked) {
      this.blocked = midi
      return midi
    }
    return null
  }
}
