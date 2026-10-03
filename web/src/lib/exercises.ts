import type { Marker } from './Fretboard.svelte'
import type { Settings } from './store.svelte'
import { midiAt, NATURAL_PCS, pcName, pcOf, pcPromptName, stringName } from './theory'

export type Position = { string: number; fret: number }

export type Question = {
  key: string
  title: string
  subtitle: string
  /** What the voice prompt says. */
  speech: string
  highlightString?: number
  /** Markers shown with the question, such as an interval's root. */
  given: Marker[]
  /** Every position that counts as correct. */
  answers: Position[]
  answerLabel: string
}

export type Exercise = {
  id: string
  name: string
  blurb: string
  /** Everything this exercise can ask under the current settings; progress is tracked per key. */
  keys(settings: Settings): string[]
  question(key: string, settings: Settings, rand?: () => number): Question
}

const ORDINALS = ['1st', '2nd', '3rd', '4th', '5th', '6th']
const SPOKEN_ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth']
const SPOKEN_PCS = ['C', 'C sharp', 'D', 'D sharp', 'E', 'F', 'F sharp', 'G', 'G sharp', 'A', 'A sharp', 'B']

/** Key for a note on a string. With 24 frets each note is asked separately below and above fret 12. */
export const noteKey = (string: number, pc: number, high: boolean) => `${string}:${pc}${high ? ':h' : ''}`

/** The note-exercise key that a fretboard position belongs to. */
export function noteKeyAt(string: number, fret: number, maxFret: number) {
  return noteKey(string, pcOf(midiAt(string, fret)), maxFret > 12 && fret >= 12)
}

export const findTheNote: Exercise = {
  id: 'notes',
  name: 'Find the note',
  blurb: 'You are given a note and a string. Find it on the fretboard.',

  keys({ strings, naturalsOnly, maxFret }) {
    const pcs = naturalsOnly ? NATURAL_PCS : [...Array(12).keys()]
    const registers = maxFret > 12 ? [false, true] : [false]
    return strings.flatMap((string) => pcs.flatMap((pc) => registers.map((high) => noteKey(string, pc, high))))
  },

  question(key, { maxFret }) {
    const [string, pc, register] = key.split(':')
    const high = register === 'h'
    const answers: Position[] = []
    for (let fret = 0; fret <= maxFret; fret++) {
      if (noteKeyAt(+string, fret, maxFret) === key) answers.push({ string: +string, fret })
    }
    const where = maxFret > 12 ? (high ? ', 12th fret or above' : ', below the 12th fret') : ''
    const spokenWhere = maxFret > 12 ? (high ? ', high' : ', low') : ''
    return {
      key,
      title: pcPromptName(+pc),
      subtitle: `on the ${ORDINALS[+string - 1]} string (${stringName(+string)})${where}`,
      speech: `${SPOKEN_PCS[+pc]}. ${SPOKEN_ORDINALS[+string - 1]} string${spokenWhere}`,
      highlightString: +string,
      given: [],
      answers,
      answerLabel: pcName(+pc),
    }
  },
}

export const INTERVAL_NAMES = [
  'Minor 2nd',
  'Major 2nd',
  'Minor 3rd',
  'Major 3rd',
  'Perfect 4th',
  'Tritone',
  'Perfect 5th',
  'Minor 6th',
  'Major 6th',
  'Minor 7th',
  'Major 7th',
  'Octave',
]
const SPOKEN_INTERVALS = INTERVAL_NAMES.map((name) =>
  name.replace('2nd', 'second').replace('3rd', 'third').replace('4th', 'fourth').replace('5th', 'fifth')
    .replace('6th', 'sixth').replace('7th', 'seventh'),
)

export const findTheInterval: Exercise = {
  id: 'intervals',
  name: 'Find the interval',
  blurb: 'A root note is marked. Find the note the given interval above it, anywhere on the neck.',

  keys: () => INTERVAL_NAMES.map((_, i) => `iv:${i + 1}`),

  question(key, { maxFret }, rand = Math.random) {
    const semitones = Number(key.split(':')[1])
    const highest = midiAt(1, maxFret)
    let root: Position
    do {
      root = { string: 1 + Math.floor(rand() * 6), fret: Math.floor(rand() * (maxFret + 1)) }
    } while (midiAt(root.string, root.fret) + semitones > highest)

    const target = midiAt(root.string, root.fret) + semitones
    const answers: Position[] = []
    for (let string = 1; string <= 6; string++) {
      const fret = target - midiAt(string, 0)
      if (fret >= 0 && fret <= maxFret) answers.push({ string, fret })
    }
    const rootPc = pcOf(midiAt(root.string, root.fret))
    return {
      key,
      title: INTERVAL_NAMES[semitones - 1],
      subtitle: `above the marked ${pcName(rootPc)}`,
      speech: `${SPOKEN_INTERVALS[semitones - 1]} above ${SPOKEN_PCS[rootPc]}`,
      given: [{ ...root, label: pcName(rootPc), tone: 'root' }],
      answers,
      answerLabel: pcName(pcOf(target)),
    }
  },
}

export const EXERCISES = [findTheNote, findTheInterval]
