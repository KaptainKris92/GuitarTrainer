<script lang="ts">
  import library from '../data/scale_library.json'
  import Fretboard, { type Marker } from './Fretboard.svelte'
  import { midiAt, pcOf, scaleNotes } from './theory'

  type ScaleDef = { category: string; aliases?: string[]; degree_labels: string[] }
  const scales = library.scales as Record<string, ScaleDef>

  const categories = [...new Set([...library.category_order, ...Object.values(scales).map((s) => s.category)])]
  const grouped = categories.map((category) => ({
    category,
    names: Object.keys(scales)
      .filter((name) => scales[name].category === category)
      .sort(),
  }))

  let key = $state('A')
  let scaleName = $state('Natural Minor')
  let labels = $state<'notes' | 'degrees'>('notes')
  let frets = $state(12)

  const scale = $derived(scales[scaleName])
  const notes = $derived(scaleNotes(key, scale.degree_labels))
  const markers = $derived.by(() => {
    const byPc = new Map(notes.map((note) => [note.pc, note]))
    const result: Marker[] = []
    for (let string = 1; string <= 6; string++) {
      for (let fret = 0; fret <= frets; fret++) {
        const note = byPc.get(pcOf(midiAt(string, fret)))
        if (!note) continue
        result.push({
          string,
          fret,
          label: labels === 'notes' ? note.name : note.degree,
          tone: note.degree === '1' ? 'root' : 'note',
        })
      }
    }
    return result
  })
</script>

<section class="card">
  <div class="controls">
    <label>
      Key
      <select bind:value={key}>
        {#each library.default_keys as option}
          <option value={option}>{option.replace('b', '♭').replace('#', '♯')}</option>
        {/each}
      </select>
    </label>
    <label>
      Scale
      <select bind:value={scaleName}>
        {#each grouped as group}
          <optgroup label={group.category}>
            {#each group.names as name}
              <option>{name}</option>
            {/each}
          </optgroup>
        {/each}
      </select>
    </label>
    <label>
      Show
      <select bind:value={labels}>
        <option value="notes">Note names</option>
        <option value="degrees">Scale degrees</option>
      </select>
    </label>
    <label>
      Frets
      <select bind:value={frets}>
        <option value={12}>12</option>
        <option value={24}>24</option>
      </select>
    </label>
  </div>

  <div class="formula">
    {#each notes as note}
      <div class="chip" class:root={note.degree === '1'}>
        <strong>{note.name}</strong>
        <span class="muted">{note.degree.replaceAll('b', '♭').replaceAll('#', '♯')}</span>
      </div>
    {/each}
    {#if scale.aliases?.length}
      <span class="muted aliases">Also known as {scale.aliases.join(', ')}</span>
    {/if}
  </div>

  <Fretboard {frets} {markers} />
</section>

<style>
  .formula {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin: 1.2rem 0;
  }
  .chip {
    display: grid;
    justify-items: center;
    min-width: 2.6rem;
    padding: 0.3rem 0.4rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-2);
    line-height: 1.25;
  }
  .chip.root {
    border-color: var(--accent);
  }
  .chip span {
    font-size: 0.75rem;
  }
  .aliases {
    margin-left: 0.5rem;
    font-size: 0.85rem;
  }
</style>
