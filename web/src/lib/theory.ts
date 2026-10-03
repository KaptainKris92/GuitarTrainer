import { Note } from 'tonal'

/** Open-string MIDI numbers in standard tuning, string 1 (high E) to string 6 (low E). */
export const TUNING = [64, 59, 55, 50, 45, 40]

const SHARP_NAMES = ['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B']
const FLAT_NAMES = ['C', 'D♭', 'D', 'E♭', 'E', 'F', 'G♭', 'G', 'A♭', 'A', 'B♭', 'B']
export const NATURAL_PCS = [0, 2, 4, 5, 7, 9, 11]

export const midiAt = (string: number, fret: number) => TUNING[string - 1] + fret

export const pcOf = (midi: number) => ((midi % 12) + 12) % 12

export const pcName = (pc: number) => SHARP_NAMES[pc]

/** Name for prompts, showing both spellings for accidentals: "C♯ / D♭". */
export const pcPromptName = (pc: number) =>
  SHARP_NAMES[pc] === FLAT_NAMES[pc] ? SHARP_NAMES[pc] : `${SHARP_NAMES[pc]} / ${FLAT_NAMES[pc]}`

export const stringName = (string: number) => pcName(pcOf(TUNING[string - 1]))

/** Nearest MIDI note and the offset from it in cents. */
export function freqToNote(freq: number, a4 = 440): { midi: number; cents: number } {
  const exact = 69 + 12 * Math.log2(freq / a4)
  const midi = Math.round(exact)
  return { midi, cents: (exact - midi) * 100 }
}

export const midiToFreq = (midi: number, a4 = 440) => a4 * 2 ** ((midi - 69) / 12)

/** Convert a degree label such as "b3" or "#4" to a tonal interval name ("3m", "4A"). */
export function degreeToInterval(label: string): string {
  const match = /^([b#]*)(\d)$/.exec(label)
  if (!match) throw new Error(`Invalid degree label: ${label}`)
  const degree = Number(match[2])
  const alteration = [...match[1]].reduce((sum, ch) => sum + (ch === '#' ? 1 : -1), 0)
  const perfect = degree === 1 || degree === 4 || degree === 5
  const qualities = perfect
    ? { '-2': 'dd', '-1': 'd', '0': 'P', '1': 'A' }
    : { '-2': 'd', '-1': 'm', '0': 'M', '1': 'A' }
  const quality = (qualities as Record<string, string>)[String(alteration)]
  if (!quality) throw new Error(`Unsupported degree label: ${label}`)
  return `${degree}${quality}`
}

export type ScaleNote = { name: string; pc: number; degree: string }

/** Spell a scale from its root and degree formula, e.g. A + [1, 2, b3] -> A, B, C. */
export function scaleNotes(root: string, degreeLabels: string[]): ScaleNote[] {
  return degreeLabels.map((degree) => {
    const name = Note.transpose(root, degreeToInterval(degree))
    return { name: name.replaceAll('#', '♯').replaceAll('b', '♭'), pc: Note.chroma(name) as number, degree }
  })
}
