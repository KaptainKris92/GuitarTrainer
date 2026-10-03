import { describe, expect, it } from 'vitest'
import library from '../data/scale_library.json'
import { buildTheChord, findTheInterval, findTheNote, modeLabel } from './exercises'
import type { Settings } from './store.svelte'
import { freqToNote, midiAt, scaleNotes } from './theory'
import { mastery, nextDayStreak, NoteGate, pickKey, record, type Stats } from './trainer'

describe('theory', () => {
  it('maps frequencies to notes and cents', () => {
    expect(freqToNote(82.41).midi).toBe(40)
    const sharp = freqToNote(440 * 2 ** (20 / 1200))
    expect(sharp.midi).toBe(69)
    expect(sharp.cents).toBeCloseTo(20)
  })

  it('spells scales with correct accidentals', () => {
    const names = (root: string, degrees: string[]) => scaleNotes(root, degrees).map((n) => n.name)
    expect(names('A', ['1', '2', 'b3', '4', '5', 'b6', 'b7'])).toEqual(['A', 'B', 'C', 'D', 'E', 'F', 'G'])
    expect(names('Eb', ['1', '2', '3', '#4', '5', '6', '7'])).toEqual(['E♭', 'F', 'G', 'A', 'B♭', 'C', 'D'])
  })

  it('spells every library scale to match its semitone intervals', () => {
    for (const [name, scale] of Object.entries(library.scales)) {
      const pcs = scaleNotes('C', scale.degree_labels).map((n) => n.pc)
      expect(pcs, name).toEqual(scale.intervals)
    }
  })
})

describe('trainer', () => {
  it('favours weak questions and never repeats the previous one', () => {
    const keys = ['a', 'b', 'c', 'd']
    const stats: Stats = {}
    for (const key of keys) for (let i = 0; i < 5; i++) record(stats, key, key !== 'a', 1000)
    expect(mastery(stats.a)).toBe(0)
    expect(mastery(stats.b)).toBe(1)

    let seed = 0
    const rand = () => (seed = (seed * 9301 + 49297) % 233280) / 233280
    let weakPicks = 0
    for (let i = 0; i < 1600; i++) if (pickKey(keys, stats, rand) === 'a') weakPicks++
    expect(weakPicks / 1600).toBeGreaterThan(0.55) // weight 5 of 8
    for (let i = 0; i < 50; i++) expect(pickKey(keys, stats, rand, 'a')).not.toBe('a')
  })

  it('reports a held note once and re-arms after silence', () => {
    const gate = new NoteGate(3)
    const feedAll = (frames: (number | null)[], silent = false) => frames.map((f) => gate.feed(f, silent))
    expect(feedAll([60, 60, 60, 60, 60])).toEqual([null, null, 60, null, null])
    // A glitch frame while the note rings must not re-trigger it.
    expect(feedAll([61, 60, 60, 60, 60])).toEqual([null, null, null, null, null])
    expect(feedAll([62, 62, 62])).toEqual([null, null, 62])
    feedAll([null], true)
    expect(feedAll([62, 62, 62])).toEqual([null, null, 62])
  })

  it('counts day streaks across consecutive days only', () => {
    expect(nextDayStreak('', 0, '2026-03-01')).toBe(1)
    expect(nextDayStreak('2026-02-28', 4, '2026-03-01')).toBe(5)
    expect(nextDayStreak('2026-03-01', 5, '2026-03-01')).toBe(5)
    expect(nextDayStreak('2026-02-27', 5, '2026-03-01')).toBe(1)
  })
})

describe('exercises', () => {
  const settings = { maxFret: 24, naturalsOnly: false, strings: [1, 2, 3, 4, 5, 6] } as Settings

  it('covers every fret of every string exactly once across the note questions', () => {
    for (const maxFret of [12, 24] as const) {
      const positions = findTheNote
        .keys({ ...settings, maxFret })
        .flatMap((key) => findTheNote.question(key, { ...settings, maxFret }).parts[0].answers)
      expect(positions).toHaveLength(6 * (maxFret + 1))
      expect(new Set(positions.map((p) => `${p.string}:${p.fret}`)).size).toBe(positions.length)
    }
  })

  it('asks for low and high octaves separately on 24 frets', () => {
    const low = findTheNote.question('6:9', settings) // A on the low E string
    const high = findTheNote.question('6:9:h', settings)
    expect(low.parts[0].answers).toEqual([{ string: 6, fret: 5 }])
    expect(high.parts[0].answers).toEqual([{ string: 6, fret: 17 }])
  })

  it('builds interval questions whose answers are the right distance from the root', () => {
    for (const key of findTheInterval.keys(settings)) {
      const question = findTheInterval.question(key, settings)
      const root = question.given[0]
      const { answers } = question.parts[0]
      expect(answers.length).toBeGreaterThan(0)
      for (const answer of answers) {
        expect(midiAt(answer.string, answer.fret) - midiAt(root.string, root.fret)).toBe(Number(key.slice(3)))
      }
    }
  })

  it('spells chords and accepts their notes anywhere on the neck', () => {
    const question = buildTheChord.question('ch:minor 7th:Eb', settings)
    expect(question.parts.map((part) => part.label)).toEqual(['E♭', 'G♭', 'B♭', 'D♭'])
    expect(question.parts[1].answers).toContainEqual({ string: 6, fret: 2 })
    expect(buildTheChord.keys(settings)).toHaveLength(84)
  })

  it('separates high scores by difficulty settings', () => {
    const base = { ...settings, input: 'tap', timeLimit: 0, oneAttempt: false } as Settings
    const variants = [base, { ...base, timeLimit: 2.5 }, { ...base, oneAttempt: true }, { ...base, naturalsOnly: true }]
    expect(new Set(variants.map((s) => modeLabel(findTheNote, s))).size).toBe(4)
  })
})
