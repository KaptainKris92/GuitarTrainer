import { PitchDetector } from 'pitchy'
import { freqToNote, midiToFreq } from './theory'

export type Frame = {
  /** Detected frequency in Hz, or null when no clear pitch is present. */
  freq: number | null
  midi: number | null
  cents: number
  rms: number
  /** True while the input is below the note-off level. */
  silent: boolean
}

const DEVICE_KEY = 'guitar-trainer.mic-device'
const WINDOW = 4096
const MIN_CLARITY = 0.9
const NOTE_ON_RMS = 0.01
const NOTE_OFF_RMS = NOTE_ON_RMS / 2
const MIN_FREQ = 70
const MAX_FREQ = 1400

let context: AudioContext | undefined
const audioContext = () => (context ??= new AudioContext())

class Mic {
  running = $state(false)
  error = $state('')
  devices = $state<MediaDeviceInfo[]>([])
  deviceId = $state(localStorage.getItem(DEVICE_KEY) ?? '')
  frame = $state<Frame>({ freq: null, midi: null, cents: 0, rms: 0, silent: true })

  private stream?: MediaStream
  private source?: MediaStreamAudioSourceNode
  private raf = 0
  private listeners = new Set<(frame: Frame) => void>()

  async start(): Promise<void> {
    this.stop()
    this.error = ''
    try {
      // Browser voice processing mangles instrument signals, so turn it all off.
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: this.deviceId ? { exact: this.deviceId } : undefined,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      })
    } catch (err) {
      if (this.deviceId && err instanceof DOMException && err.name === 'OverconstrainedError') {
        // The remembered device is gone; fall back to the default input.
        this.deviceId = ''
        localStorage.removeItem(DEVICE_KEY)
        return this.start()
      }
      this.error = 'Could not access the microphone. Check browser permissions and try again.'
      return
    }

    const ctx = audioContext()
    await ctx.resume()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = WINDOW
    this.source = ctx.createMediaStreamSource(this.stream)
    this.source.connect(analyser)

    const input = new Float32Array(WINDOW)
    const detector = PitchDetector.forFloat32Array(WINDOW)
    let active = false

    const tick = () => {
      analyser.getFloatTimeDomainData(input)
      let sum = 0
      for (const sample of input) sum += sample * sample
      const rms = Math.sqrt(sum / WINDOW)
      active = active ? rms > NOTE_OFF_RMS : rms > NOTE_ON_RMS

      let frame: Frame = { freq: null, midi: null, cents: 0, rms, silent: !active }
      if (active) {
        const [freq, clarity] = detector.findPitch(input, ctx.sampleRate)
        if (clarity >= MIN_CLARITY && freq >= MIN_FREQ && freq <= MAX_FREQ) {
          frame = { ...frame, freq, ...freqToNote(freq) }
        }
      }
      this.frame = frame
      for (const listener of this.listeners) listener(frame)
      this.raf = requestAnimationFrame(tick)
    }
    this.raf = requestAnimationFrame(tick)
    this.running = true

    // Device labels are only available once permission has been granted.
    const all = await navigator.mediaDevices.enumerateDevices()
    this.devices = all.filter((device) => device.kind === 'audioinput')
  }

  stop() {
    cancelAnimationFrame(this.raf)
    this.source?.disconnect()
    this.stream?.getTracks().forEach((track) => track.stop())
    this.stream = undefined
    this.running = false
  }

  async selectDevice(deviceId: string) {
    this.deviceId = deviceId
    localStorage.setItem(DEVICE_KEY, deviceId)
    await this.start()
  }

  subscribe(listener: (frame: Frame) => void) {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }
}

export const mic = new Mic()

/** Play a short plucked tone at the given MIDI pitch. */
export function playTone(midi: number) {
  const ctx = audioContext()
  void ctx.resume()
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.type = 'triangle'
  osc.frequency.value = midiToFreq(midi)
  gain.gain.setValueAtTime(0.25, ctx.currentTime)
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8)
  osc.connect(gain).connect(ctx.destination)
  osc.start()
  osc.stop(ctx.currentTime + 0.8)
}
