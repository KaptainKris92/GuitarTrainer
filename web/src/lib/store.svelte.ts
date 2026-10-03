import { nextDayStreak, type Stats } from './trainer'

export type Player = {
  stats: Stats
  /** Best round score per exercise. */
  best: Record<string, number>
  xp: number
  dayStreak: number
  lastDay: string
}

export type Settings = {
  theme: string
  voice: boolean
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

const newPlayer = (): Player => ({ stats: {}, best: {}, xp: 0, dayStreak: 0, lastDay: '' })

const DEFAULT_SETTINGS: Settings = {
  theme: 'midnight',
  voice: true,
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

function loadSave(): Save {
  const saved = read<Save>(SAVE_KEY)
  if (isSave(saved)) return saved
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

  markPracticed() {
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
    this.save = parsed
    return true
  }
}

export const store = new Store()
