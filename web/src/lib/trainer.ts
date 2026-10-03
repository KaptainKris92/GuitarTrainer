/** Per-question history, keyed by the exercise's question key. */
export type Stat = { seen: number; correct: number; avgMs: number }
export type Stats = Record<string, Stat>

const FAST_MS = 1500
const SLOW_MS = 6000

/** 0 (unknown) to 1 (answered reliably and quickly). */
export function mastery(stat: Stat | undefined): number {
  if (!stat || stat.seen === 0) return 0
  const accuracy = stat.correct / stat.seen
  const confidence = Math.min(1, stat.seen / 5)
  const speed = Math.min(1, Math.max(0, (SLOW_MS - stat.avgMs) / (SLOW_MS - FAST_MS)))
  return accuracy * confidence * (0.5 + 0.5 * speed)
}

/** Weighted random pick favouring weak questions; never repeats `avoid`. */
export function pickKey(keys: string[], stats: Stats, rand = Math.random, avoid?: string): string {
  const candidates = keys.filter((key) => key !== avoid)
  const pool = candidates.length ? candidates : keys
  const weights = pool.map((key) => 1 + 4 * (1 - mastery(stats[key])))
  let roll = rand() * weights.reduce((a, b) => a + b, 0)
  for (let i = 0; i < pool.length; i++) {
    roll -= weights[i]
    if (roll < 0) return pool[i]
  }
  return pool[pool.length - 1]
}

/** Update the history for one question in place. */
export function record(stats: Stats, key: string, correct: boolean, ms: number) {
  const prev = stats[key]
  stats[key] = {
    seen: (prev?.seen ?? 0) + 1,
    correct: (prev?.correct ?? 0) + (correct ? 1 : 0),
    avgMs: prev ? prev.avgMs * 0.7 + ms * 0.3 : ms,
  }
}

export const levelFor = (xp: number) => Math.floor(Math.sqrt(xp / 150)) + 1
export const xpForLevel = (level: number) => 150 * (level - 1) ** 2

/** Day streak after practising on `today` (dates as YYYY-MM-DD). */
export function nextDayStreak(lastDay: string, streak: number, today: string): number {
  if (lastDay === today) return streak
  const yesterday = new Date(`${today}T12:00:00`)
  yesterday.setDate(yesterday.getDate() - 1)
  return lastDay === yesterday.toLocaleDateString('sv') ? streak + 1 : 1
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
