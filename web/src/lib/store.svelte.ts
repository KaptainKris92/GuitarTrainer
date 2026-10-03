import { nextDayStreak, type Stats } from './trainer'

/** One completed round. `mode` identifies the exercise and difficulty settings it was played with. */
export type Round = { at: string; mode: string; score: number; correct: number }

export type Player = {
  stats: Stats
  rounds: Round[]
  xp: number
  dayStreak: number
  lastDay: string
  /** The last day a daily session was completed. */
  lastDaily: string
}

export type Settings = {
  theme: string
  voice: boolean
  sfx: boolean
  /** Ignore the skill tree's locks. */
  unlockAll: boolean
  input: 'mic' | 'tap'
  maxFret: 12 | 24
  naturalsOnly: boolean
  strings: number[]
  /** The first note played settles the question, right or wrong. */
  oneAttempt: boolean
  /** Seconds allowed per question; 0 means no limit. */
  timeLimit: number
}

type Save = { current: string; players: Record<string, Player> }

const SAVE_KEY = 'guitar-trainer.save'
const SETTINGS_KEY = 'guitar-trainer.settings'

const newPlayer = (): Player => ({ stats: {}, rounds: [], xp: 0, dayStreak: 0, lastDay: '', lastDaily: '' })

const DEFAULT_SETTINGS: Settings = {
  theme: 'midnight',
  voice: true,
  sfx: true,
  unlockAll: false,
  input: 'mic',
  maxFret: 12,
  naturalsOnly: true,
  strings: [1, 2, 3, 4, 5, 6],
  oneAttempt: false,
  timeLimit: 0,
}

function read<T>(key: string): T | null {
  try {
    return JSON.parse(localStorage.getItem(key) ?? 'null')
  } catch {
    return null
  }
}

function isSave(value: unknown): value is Save {
  const save = value as Save
  return !!save && typeof save.current === 'string' && !!save.players?.[save.current]
}

/** Fill in fields added since the save was written. */
function withDefaults(save: Save): Save {
  for (const [name, player] of Object.entries(save.players)) save.players[name] = { ...newPlayer(), ...player }
  return save
}

function loadSave(): Save {
  const saved = read<Save>(SAVE_KEY)
  if (isSave(saved)) return withDefaults(saved)
  // Carry over progress from before player profiles existed.
  const player = newPlayer()
  player.stats = read<Stats>('guitar-trainer.note-stats') ?? {}
  return { current: 'Player 1', players: { 'Player 1': player } }
}

class Store {
  save = $state(loadSave())
  settings = $state<Settings>({ ...DEFAULT_SETTINGS, ...read<Partial<Settings>>(SETTINGS_KEY) })

  get player() {
    return this.save.players[this.save.current]
  }

  get playerNames() {
    return Object.keys(this.save.players)
  }

  /** Write everything to browser storage; called from a root effect whenever state changes. */
  persist() {
    localStorage.setItem(SAVE_KEY, JSON.stringify(this.save))
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(this.settings))
  }

  addPlayer(name: string) {
    if (!name || this.save.players[name]) return
    this.save.players[name] = newPlayer()
    this.save.current = name
  }

  renamePlayer(name: string) {
    if (!name || this.save.players[name]) return
    this.save.players[name] = this.player
    delete this.save.players[this.save.current]
    this.save.current = name
  }

  /** Top scores for a mode across all players, best first. */
  leaderboard(mode: string, limit = 5) {
    return Object.entries(this.save.players)
      .flatMap(([name, player]) => player.rounds.filter((round) => round.mode === mode).map((round) => ({ name, ...round })))
      .sort((a, b) => b.score - a.score || a.at.localeCompare(b.at))
      .slice(0, limit)
  }

  bestScore(mode: string) {
    return Math.max(0, ...this.player.rounds.filter((round) => round.mode === mode).map((round) => round.score))
  }

  finishRound(mode: string, score: number, correct: number) {
    this.player.rounds.push({ at: new Date().toISOString(), mode, score, correct })
    const today = new Date().toLocaleDateString('sv')
    this.player.dayStreak = nextDayStreak(this.player.lastDay, this.player.dayStreak, today)
    this.player.lastDay = today
  }

  exportJson() {
    return JSON.stringify(this.save, null, 2)
  }

  /** Replace all players with a previously exported backup. Returns false if the file is not a backup. */
  importJson(json: string) {
    let parsed: unknown
    try {
      parsed = JSON.parse(json)
    } catch {
      return false
    }
    if (!isSave(parsed)) return false
    this.save = withDefaults(parsed)
    return true
  }
}

export const store = new Store()
