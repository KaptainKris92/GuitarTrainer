import { describe, expect, it } from 'vitest'
import library from '../data/scale_library.json'
import { fretsFor, freqToNote, midiAt, pcOf, scaleNotes } from './theory'
import { allItems, mastery, NoteGate, pickItem, record, type Stats } from './trainer'

describe('theory', () => {
  it('finds every fret for a pitch class on a string', () => {
    expect(fretsFor(6, 4, 12)).toEqual([0, 12]) // E on low E
    expect(fretsFor(3, 0, 12)).toEqual([5]) // C on G
    for (const fret of fretsFor(2, 1, 24)) expect(pcOf(midiAt(2, fret))).toBe(1)
  })

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
  const items = allItems([1, 2], true)

  it('favours weak items and avoids repeating a pitch class', () => {
    let stats: Stats = {}
    for (const item of items) {
      for (let i = 0; i < 5; i++) stats = record(stats, item, !(item.string === 2 && item.pc === 0), 1000)
    }
    const weak = { string: 2, pc: 0 }
    expect(mastery(stats['2:0'])).toBe(0)
    expect(mastery(stats['1:0'])).toBe(1)

    let weakPicks = 0
    let seed = 0
    const rand = () => (seed = (seed * 9301 + 49297) % 233280) / 233280
    for (let i = 0; i < 1400; i++) if (pickItem(items, stats, rand).pc === weak.pc) weakPicks++
    // C appears on both strings: weights 5 (weak) + 1 out of a total of 18.
    expect(weakPicks / 1400).toBeGreaterThan(0.28)
    for (let i = 0; i < 50; i++) expect(pickItem(items, stats, rand, 0).pc).not.toBe(0)
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
})
