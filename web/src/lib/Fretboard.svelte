<script lang="ts" module>
  export type Marker = {
    string: number
    fret: number
    label?: string
    tone?: 'note' | 'root' | 'good' | 'bad' | 'heat'
    /** Overrides the tone's fill colour (used for the mastery heatmap). */
    color?: string
  }
</script>

<script lang="ts">
  import { stringName } from './theory'

  type Props = {
    frets?: number
    markers?: Marker[]
    highlightString?: number | null
    onpick?: (string: number, fret: number) => void
  }
  let { frets = 12, markers = [], highlightString = null, onpick }: Props = $props()

  const OPEN_W = 46
  const FRET_W = 62
  const STRING_H = 32
  const PAD_T = 14
  const PAD_B = 26
  const STRINGS = [1, 2, 3, 4, 5, 6]
  const INLAYS = [3, 5, 7, 9, 15, 17, 19, 21]
  const DOUBLE_INLAYS = [12, 24]

  const width = $derived(OPEN_W + frets * FRET_W + 8)
  const boardH = STRING_H * 6
  const height = PAD_T + boardH + PAD_B
  const fretNumbers = $derived(Array.from({ length: frets }, (_, i) => i + 1))

  const stringY = (string: number) => PAD_T + (string - 0.5) * STRING_H
  const cellX = (fret: number) => (fret === 0 ? OPEN_W / 2 : OPEN_W + (fret - 0.5) * FRET_W)
</script>

<div class="scroll">
  <svg viewBox="0 0 {width} {height}" style:min-width="{frets * 44}px" role="img" aria-label="Guitar fretboard">
    <rect class="board" x={OPEN_W} y={PAD_T} width={frets * FRET_W} height={boardH} rx="4" />

    {#each fretNumbers as fret}
      {#if INLAYS.includes(fret)}
        <circle class="inlay" cx={cellX(fret)} cy={PAD_T + boardH / 2} r="6" />
      {:else if DOUBLE_INLAYS.includes(fret)}
        <circle class="inlay" cx={cellX(fret)} cy={PAD_T + STRING_H * 1.5} r="6" />
        <circle class="inlay" cx={cellX(fret)} cy={PAD_T + STRING_H * 4.5} r="6" />
      {/if}
      <line class="fret" x1={OPEN_W + fret * FRET_W} x2={OPEN_W + fret * FRET_W} y1={PAD_T} y2={PAD_T + boardH} />
      <text class="fret-number" x={cellX(fret)} y={height - 7}>{fret}</text>
    {/each}
    <rect class="nut" x={OPEN_W - 3} y={PAD_T} width="6" height={boardH} rx="2" />

    {#each STRINGS as string}
      <line
        class="string"
        class:highlight={string === highlightString}
        x1={OPEN_W}
        x2={OPEN_W + frets * FRET_W}
        y1={stringY(string)}
        y2={stringY(string)}
        stroke-width={1 + string * 0.35}
      />
      <text class="open-name" class:highlight={string === highlightString} x={OPEN_W / 2} y={stringY(string) + 4}>
        {stringName(string)}
      </text>
    {/each}

    {#each markers as marker (`${marker.string}:${marker.fret}:${marker.tone}`)}
      <g class="marker {marker.tone ?? 'note'}" class:colored={marker.color}>
        <circle cx={cellX(marker.fret)} cy={stringY(marker.string)} r="12.5" style:fill={marker.color} />
        {#if marker.label}
          <text x={cellX(marker.fret)} y={stringY(marker.string) + 4}>{marker.label}</text>
        {/if}
      </g>
    {/each}

    {#if onpick}
      {#each STRINGS as string}
        {#each [0, ...fretNumbers] as fret}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <rect
            class="hit"
            role="button"
            tabindex="-1"
            aria-label="String {string}, fret {fret}"
            x={fret === 0 ? 0 : OPEN_W + (fret - 1) * FRET_W}
            y={stringY(string) - STRING_H / 2}
            width={fret === 0 ? OPEN_W : FRET_W}
            height={STRING_H}
            onclick={() => onpick(string, fret)}
          />
        {/each}
      {/each}
    {/if}
  </svg>
</div>

<style>
  .scroll {
    overflow-x: auto;
  }
  svg {
    display: block;
    width: 100%;
    user-select: none;
  }
  .board {
    fill: var(--board);
  }
  .inlay {
    fill: var(--inlay);
  }
  .fret {
    stroke: var(--fret);
    stroke-width: 2;
  }
  .nut {
    fill: var(--string);
  }
  .string {
    stroke: var(--string);
    transition: stroke 0.15s;
  }
  .string.highlight {
    stroke: var(--accent);
    filter: drop-shadow(0 0 4px var(--accent));
  }
  text {
    text-anchor: middle;
    font-size: 12px;
    font-weight: 700;
  }
  .fret-number,
  .open-name {
    fill: var(--muted);
  }
  .open-name.highlight {
    fill: var(--accent);
  }
  .marker {
    pointer-events: none;
  }
  .marker circle {
    fill: var(--surface-2);
    stroke: var(--accent);
    stroke-width: 2;
  }
  .marker text {
    fill: var(--text);
    font-size: 11px;
  }
  .marker.heat circle {
    stroke: var(--border);
  }
  .marker.root circle {
    fill: var(--accent);
  }
  .marker.root text {
    fill: var(--accent-ink);
  }
  .marker.good text,
  .marker.bad text {
    fill: #111;
  }
  .marker.colored text {
    fill: #fff;
  }
  .marker.good circle {
    fill: var(--good);
    stroke: var(--good);
  }
  .marker.bad circle {
    fill: var(--bad);
    stroke: var(--bad);
  }
  .hit {
    fill: transparent;
    cursor: pointer;
    outline: none;
  }
  .hit:hover {
    fill: rgb(255 255 255 / 0.08);
  }
</style>
