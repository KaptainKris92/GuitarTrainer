import { Key } from 'tonal'
import library from '../data/scale_library.json'
import type { Marker } from './Fretboard.svelte'
import type { Settings } from './store.svelte'
import { midiAt, NATURAL_PCS, pcName, pcOf, pcPromptName, scaleNotes, stringName } from './theory'
import { mastery, type Stats } from './trainer'

export type Position = { string: number; fret: number }

export type Part = {
  label: string
  /** Every position that counts as correct. */
  answers: Position[]
}

export type Question = {
  key: string
  title: string
  subtitle: string
  /** What the voice prompt says; empty for questions that must not be given away. */
  speech: string
  highlightString?: number
  /** Markers shown with the question, such as an interval's root. */
  given: Marker[]
  /** Notes to find on the fretboard; chords and scales have several. Empty for multiple-choice questions. */
  parts: Part[]
  /** Parts must be found in order (scales) rather than in any order (chords). */
  ordered?: boolean
  /** Multiple-choice answers, with the correct one. */
  choices?: string[]
  correct?: string
  /** MIDI notes played to the player before they answer. */
  listen?: number[]
  /** A written note to show on a staff, in VexFlow form such as "c/4". */
  staff?: string
}

export type Exercise = {
  id: string
  name: string
  blurb: string
  track: string
  /** The exercise that must be partly mastered before this one unlocks. */
  requires?: string
  /** Answered on the fretboard (guitar or tap) rather than by multiple choice. */
  usesBoard: boolean
  /** Everything this exercise can ask under the current settings; progress is tracked per key. */
  keys(settings: Settings): string[]
  question(key: string, settings: Settings, rand?: () => number): Question
  /** Settings beyond the shared ones that change this exercise's difficulty, for separating high scores. */
  modeDetails?(settings: Settings): string[]
  /** Label of the group a question belongs to, for showing progress as one chip per group. */
  groupOf?(key: string): string
}

const ORDINALS = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th']
const SPOKEN_ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']
const SPOKEN_PCS = ['C', 'C sharp', 'D', 'D sharp', 'E', 'F', 'F sharp', 'G', 'G sharp', 'A', 'A sharp', 'B']
const ROOTS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

const pretty = (text: string) => text.replaceAll('b', '♭').replaceAll('#', '♯')
const spokenRoot = (root: string) => root.replace('b', ' flat').replace('#', ' sharp')
const pick = <T>(items: T[], rand: () => number) => items[Math.floor(rand() * items.length)]

function shuffled<T>(items: T[], rand: () => number): T[] {
  const result = [...items]
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[result[i], result[j]] = [result[j], result[i]]
  }
  return result
}

/** Every position on the neck that satisfies `test`. */
function positionsWhere(maxFret: number, test: (midi: number) => boolean): Position[] {
  const positions: Position[] = []
  for (let string = 1; string <= 6; string++) {
    for (let fret = 0; fret <= maxFret; fret++) {
      if (test(midiAt(string, fret))) positions.push({ string, fret })
    }
  }
  return positions
}

/** Describes the exercise and difficulty settings of a round; high scores are kept per mode. */
export function modeLabel(exercise: Exercise, settings: Settings): string {
  return [
    exercise.name,
    ...(exercise.usesBoard ? [settings.input === 'mic' ? 'guitar' : 'tap', `${settings.maxFret} frets`] : []),
    ...(exercise.modeDetails?.(settings) ?? []),
    settings.timeLimit ? `${settings.timeLimit}s limit` : 'no time limit',
    ...(settings.oneAttempt ? ['one attempt'] : []),
  ].join(' · ')
}

// ---------------------------------------------------------------- Fretboard

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
  track: 'Fretboard',
  usesBoard: true,

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
      parts: [{ label: pcName(+pc), answers }],
    }
  },

  modeDetails: ({ naturalsOnly, strings }) => [
    naturalsOnly ? 'naturals' : 'all notes',
    strings.length === 6 ? 'all strings' : `strings ${strings.join(',')}`,
  ],
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
  ORDINALS.reduce((text, ordinal, i) => text.replace(ordinal, SPOKEN_ORDINALS[i]), name),
)

export const findTheInterval: Exercise = {
  id: 'intervals',
  name: 'Find the interval',
  blurb: 'A root note is marked. Find the note the given interval above it, anywhere on the neck.',
  track: 'Fretboard',
  requires: 'notes',
  usesBoard: true,

  keys: () => INTERVAL_NAMES.map((_, i) => `iv:${i + 1}`),
  groupOf: (key) => INTERVAL_NAMES[Number(key.split(':')[1]) - 1],

  question(key, { maxFret }, rand = Math.random) {
    const semitones = Number(key.split(':')[1])
    const highest = midiAt(1, maxFret)
    let root: Position
    do {
      root = { string: 1 + Math.floor(rand() * 6), fret: Math.floor(rand() * (maxFret + 1)) }
    } while (midiAt(root.string, root.fret) + semitones > highest)

    const target = midiAt(root.string, root.fret) + semitones
    const rootPc = pcOf(midiAt(root.string, root.fret))
    return {
      key,
      title: INTERVAL_NAMES[semitones - 1],
      subtitle: `above the marked ${pcName(rootPc)}`,
      speech: `${SPOKEN_INTERVALS[semitones - 1]} above ${SPOKEN_PCS[rootPc]}`,
      given: [{ ...root, label: pcName(rootPc), tone: 'root' }],
      parts: [{ label: pcName(pcOf(target)), answers: positionsWhere(maxFret, (midi) => midi === target) }],
    }
  },
}

export const CHORD_TYPES: Record<string, string[]> = {
  major: ['1', '3', '5'],
  minor: ['1', 'b3', '5'],
  diminished: ['1', 'b3', 'b5'],
  augmented: ['1', '3', '#5'],
  'major 7th': ['1', '3', '5', '7'],
  'dominant 7th': ['1', '3', '5', 'b7'],
  'minor 7th': ['1', 'b3', '5', 'b7'],
}

/** Parts for a set of scale degrees from a root, each accepted anywhere on the neck. */
const degreeParts = (root: string, degrees: string[], maxFret: number): Part[] =>
  scaleNotes(root, degrees).map((note) => ({
    label: note.name,
    answers: positionsWhere(maxFret, (midi) => pcOf(midi) === note.pc),
  }))

export const buildTheChord: Exercise = {
  id: 'chords',
  name: 'Build the chord',
  blurb: 'You are given a chord. Find each of its notes, one at a time, anywhere on the neck and in any order.',
  track: 'Fretboard',
  requires: 'intervals',
  usesBoard: true,

  keys: () => Object.keys(CHORD_TYPES).flatMap((type) => ROOTS.map((root) => `ch:${type}:${root}`)),
  groupOf: (key) => key.split(':')[1],

  question(key, { maxFret }) {
    const [, type, root] = key.split(':')
    return {
      key,
      title: `${pretty(root)} ${type}`,
      subtitle: `find its notes: ${CHORD_TYPES[type].map(pretty).join(' – ')}`,
      speech: `${spokenRoot(root)} ${type}`,
      given: [],
      parts: degreeParts(root, CHORD_TYPES[type], maxFret),
    }
  },
}

const scaleLibrary = library.scales as Record<string, { category: string; degree_labels: string[] }>
/** Scales used for practice: the common ones, without the modes that duplicate Major and Natural Minor. */
export const PRACTICE_SCALES = Object.keys(scaleLibrary).filter(
  (name) =>
    ['Diatonic', 'Modes of Major', 'Pentatonic and Blues'].includes(scaleLibrary[name].category) &&
    !['Ionian', 'Aeolian'].includes(name),
)

export const playTheScale: Exercise = {
  id: 'scales',
  name: 'Play the scale',
  blurb: 'You are given a scale. Play its notes in order, starting from the root, anywhere on the neck.',
  track: 'Fretboard',
  requires: 'chords',
  usesBoard: true,

  keys: () => PRACTICE_SCALES.flatMap((name) => ROOTS.map((root) => `sc:${name}:${root}`)),
  groupOf: (key) => key.split(':')[1],

  question(key, { maxFret }) {
    const [, name, root] = key.split(':')
    const degrees = scaleLibrary[name].degree_labels
    return {
      key,
      title: `${pretty(root)} ${name}`,
      subtitle: `play it in order: ${degrees.map(pretty).join(' – ')}`,
      speech: `${spokenRoot(root)} ${name}`,
      given: [],
      parts: degreeParts(root, degrees, maxFret),
      ordered: true,
    }
  },
}

// ------------------------------------------------------------------- Theory

const MAJOR_KEYS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'Db', 'Ab', 'Eb', 'Bb', 'F']
const MINOR_KEYS = ['A', 'E', 'B', 'F#', 'C#', 'G#', 'Eb', 'Bb', 'F', 'C', 'G', 'D']
const SIGNATURES = [
  'None',
  ...[1, 2, 3, 4, 5, 6].map((n) => `${n} sharp${n > 1 ? 's' : ''}`),
  ...[1, 2, 3, 4, 5, 6].map((n) => `${n} flat${n > 1 ? 's' : ''}`),
]

export const keySignatures: Exercise = {
  id: 'signatures',
  name: 'Key signatures',
  blurb: 'How many sharps or flats does each key have?',
  track: 'Theory',
  usesBoard: false,

  keys: () => [...MAJOR_KEYS.map((tonic) => `ks:${tonic}:major`), ...MINOR_KEYS.map((tonic) => `ks:${tonic}:minor`)],
  groupOf: (key) => `${pretty(key.split(':')[1])} ${key.split(':')[2]}`,

  question(key) {
    const [, tonic, quality] = key.split(':')
    const alteration = quality === 'major' ? Key.majorKey(tonic).alteration : Key.minorKey(tonic).alteration
    return {
      key,
      title: `${pretty(tonic)} ${quality}`,
      subtitle: 'How many sharps or flats?',
      speech: `${spokenRoot(tonic)} ${quality}`,
      given: [],
      parts: [],
      choices: SIGNATURES,
      correct: SIGNATURES[alteration > 0 ? alteration : alteration < 0 ? 6 - alteration : 0],
    }
  },
}

export const chordsInKey: Exercise = {
  id: 'keychords',
  name: 'Chords in a key',
  blurb: 'Which chord is built on each degree of a major key?',
  track: 'Theory',
  requires: 'signatures',
  usesBoard: false,

  keys: () => MAJOR_KEYS.flatMap((tonic) => [2, 3, 4, 5, 6, 7].map((degree) => `kc:${tonic}:${degree}`)),
  groupOf: (key) => `${pretty(key.split(':')[1])} major`,

  question(key, _settings, rand = Math.random) {
    const [, tonic, degree] = key.split(':')
    const { triads, scale } = Key.majorKey(tonic)
    const correct = triads[+degree - 1]
    const root = scale[+degree - 1]
    // Distractors: the same root with the other qualities, plus a neighbouring degree's chord.
    const neighbour = triads[+degree % 7]
    const choices = shuffled([...new Set([root, `${root}m`, `${root}dim`, neighbour])], rand)
    return {
      key,
      title: `${pretty(tonic)} major`,
      subtitle: `Which chord is built on the ${ORDINALS[+degree - 1]} degree?`,
      speech: `${spokenRoot(tonic)} major. ${SPOKEN_ORDINALS[+degree - 1]} chord`,
      given: [],
      parts: [],
      choices: choices.map(pretty),
      correct: pretty(correct),
    }
  },
}

// ---------------------------------------------------------------------- Ear

export const hearTheInterval: Exercise = {
  id: 'earintervals',
  name: 'Hear the interval',
  blurb: 'Two notes are played one after the other. Name the interval between them.',
  track: 'Ear',
  usesBoard: false,

  keys: () => INTERVAL_NAMES.map((_, i) => `ear:${i + 1}`),
  groupOf: (key) => INTERVAL_NAMES[Number(key.split(':')[1]) - 1],

  question(key, _settings, rand = Math.random) {
    const semitones = Number(key.split(':')[1])
    const root = 48 + Math.floor(rand() * 17)
    return {
      key,
      title: 'Which interval?',
      subtitle: 'Listen, then choose',
      speech: '',
      given: [],
      parts: [],
      choices: INTERVAL_NAMES,
      correct: INTERVAL_NAMES[semitones - 1],
      listen: [root, root + semitones],
    }
  },
}

export const playItBack: Exercise = {
  id: 'playback',
  name: 'Play it back',
  blurb: 'A note is played. Find the same note on your guitar.',
  track: 'Ear',
  requires: 'earintervals',
  usesBoard: true,

  keys: () => [...Array(12).keys()].map((pc) => `echo:${pc}`),
  groupOf: (key) => pcName(Number(key.split(':')[1])),

  question(key, { maxFret }, rand = Math.random) {
    const pc = Number(key.split(':')[1])
    const { string, fret } = pick(positionsWhere(maxFret, (midi) => pcOf(midi) === pc), rand)
    const target = midiAt(string, fret)
    return {
      key,
      title: 'Play it back',
      subtitle: 'Find the note you just heard',
      speech: '',
      given: [],
      parts: [{ label: pcName(pc), answers: positionsWhere(maxFret, (midi) => midi === target) }],
      listen: [target],
    }
  },
}

// ------------------------------------------------------------------ Reading

const LETTERS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
/** Natural notes from the open low E string to the 12th fret of the high E string. */
const READING_RANGE = [...Array(37).keys()].map((i) => 40 + i).filter((midi) => NATURAL_PCS.includes(pcOf(midi)))

/** Guitar music is written an octave above where it sounds. */
const writtenNote = (midi: number) => `${pcName(pcOf(midi)).toLowerCase()}/${Math.floor(midi / 12)}`

export const readNameIt: Exercise = {
  id: 'readname',
  name: 'Read: name the note',
  blurb: 'A note is shown on the staff. Name it.',
  track: 'Reading',
  usesBoard: false,

  keys: () => READING_RANGE.map((midi) => `rn:${midi}`),

  question(key) {
    const midi = Number(key.split(':')[1])
    return {
      key,
      title: '',
      subtitle: 'Name this note',
      speech: '',
      given: [],
      parts: [],
      choices: LETTERS,
      correct: pcName(pcOf(midi)),
      staff: writtenNote(midi),
    }
  },
}

export const readPlayIt: Exercise = {
  id: 'readplay',
  name: 'Read: play the note',
  blurb: 'A note is shown on the staff. Play it on your guitar. Guitar music sounds an octave lower than written.',
  track: 'Reading',
  requires: 'readname',
  usesBoard: true,

  keys: () => READING_RANGE.map((midi) => `rp:${midi}`),

  question(key, { maxFret }) {
    const midi = Number(key.split(':')[1])
    return {
      key,
      title: '',
      subtitle: 'Play this note',
      speech: '',
      given: [],
      parts: [{ label: pcName(pcOf(midi)), answers: positionsWhere(maxFret, (m) => m === midi) }],
      staff: writtenNote(midi),
    }
  },
}

// --------------------------------------------------------------- Skill tree

export const EXERCISES = [
  findTheNote,
  findTheInterval,
  buildTheChord,
  playTheScale,
  keySignatures,
  chordsInKey,
  hearTheInterval,
  playItBack,
  readNameIt,
  readPlayIt,
]
export const TRACKS = [...new Set(EXERCISES.map((exercise) => exercise.track))]

/** Mastery needed in an exercise before the next one in its track unlocks. */
export const UNLOCK_AT = 0.25

/** Settings that skill progress is measured against, whatever the player currently has selected. */
const SKILL_SETTINGS = { maxFret: 12, naturalsOnly: true, strings: [1, 2, 3, 4, 5, 6] } as Settings

/** 0 to 1: average mastery across everything an exercise can ask. */
export function skill(exercise: Exercise, stats: Stats): number {
  const keys = exercise.keys(SKILL_SETTINGS)
  return keys.reduce((sum, key) => sum + mastery(stats[key]), 0) / keys.length
}

export function isUnlocked(exercise: Exercise, stats: Stats): boolean {
  const required = EXERCISES.find((other) => other.id === exercise.requires)
  return !required || skill(required, stats) >= UNLOCK_AT
}

/** A mixed round drawn from several exercises, favouring whatever the player is weakest at. */
export function mixedSession(exercises: Exercise[]): Exercise {
  return {
    id: 'daily',
    name: 'Daily session',
    blurb: 'A mixed round from everything you have unlocked.',
    track: '',
    usesBoard: exercises.some((exercise) => exercise.usesBoard),
    keys: (settings) => exercises.flatMap((exercise) => exercise.keys(settings)),
    question(key, settings, rand) {
      const owner = exercises.find((exercise) => exercise.keys(settings).includes(key))!
      return owner.question(key, settings, rand)
    },
  }
}
