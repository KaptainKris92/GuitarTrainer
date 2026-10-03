<script lang="ts">
  import { mic } from './lib/audio.svelte'
  import Practice from './lib/Practice.svelte'
  import ScaleExplorer from './lib/ScaleExplorer.svelte'
  import { store } from './lib/store.svelte'
  import { levelFor, xpForLevel } from './lib/trainer'
  import Tuner from './lib/Tuner.svelte'

  const tabs = [
    { id: 'practice', label: 'Practice' },
    { id: 'scales', label: 'Scales' },
    { id: 'tuner', label: 'Tuner' },
  ] as const
  const themes = ['midnight', 'neon', 'mono', 'paper']
  let tab = $state<(typeof tabs)[number]['id']>('practice')
  let importInput: HTMLInputElement
  let menu: HTMLDetailsElement

  const level = $derived(levelFor(store.player.xp))
  const levelProgress = $derived(
    (store.player.xp - xpForLevel(level)) / (xpForLevel(level + 1) - xpForLevel(level)),
  )

  $effect(() => store.persist())
  $effect(() => {
    document.documentElement.dataset.theme = store.settings.theme
  })
  // Ask the browser not to evict saved progress when disk space runs low.
  void navigator.storage?.persist?.()

  function choosePlayer(value: string) {
    if (value !== '+') return (store.save.current = value)
    const name = prompt('Name for the new player?')?.trim()
    if (name) store.addPlayer(name)
  }

  function rename() {
    const name = prompt('New name?', store.save.current)?.trim()
    if (name) store.renamePlayer(name)
  }

  function exportBackup() {
    const link = document.createElement('a')
    link.href = URL.createObjectURL(new Blob([store.exportJson()], { type: 'application/json' }))
    link.download = 'guitar-trainer-backup.json'
    link.click()
    URL.revokeObjectURL(link.href)
  }

  async function importBackup() {
    const file = importInput.files?.[0]
    importInput.value = ''
    if (!file || !confirm('Replace all players and progress with this backup?')) return
    if (!store.importJson(await file.text())) alert('That file is not a Guitar Trainer backup.')
  }
</script>

<svelte:window
  onclick={(event) => {
    if (!menu.contains(event.target as Node)) menu.open = false
  }}
/>

<header>
  <span class="brand">Guitar<b>Trainer</b></span>
  <nav>
    {#each tabs as { id, label }}
      <button class="tab" class:active={tab === id} onclick={() => (tab = id)}>{label}</button>
    {/each}
  </nav>

  <div class="player" title="{store.player.xp} XP">
    <span class="level">Lv {level}</span>
    <span class="xp"><span style:width="{levelProgress * 100}%"></span></span>
    <span class="streak" class:lit={store.player.dayStreak > 0}>{store.player.dayStreak} day streak</span>
  </div>

  {#if mic.running}
    <span class="meter" title="Microphone level"><span style:width="{Math.min(100, mic.frame.rms * 600)}%"></span></span>
  {/if}

  <details class="menu" bind:this={menu}>
    <summary>{store.save.current}</summary>
    <div class="panel">
      <label>
        Player
        <select onchange={(event) => choosePlayer(event.currentTarget.value)}>
          {#each store.playerNames as name (name)}
            <option selected={name === store.save.current}>{name}</option>
          {/each}
          <option value="+">New player…</option>
        </select>
      </label>
      <button onclick={rename}>Rename player</button>
      <label>
        Theme
        <select bind:value={store.settings.theme}>
          {#each themes as theme}
            <option>{theme}</option>
          {/each}
        </select>
      </label>
      <label>
        Microphone
        {#if mic.running}
          <select value={mic.deviceId} onchange={(event) => mic.selectDevice(event.currentTarget.value)}>
            <option value="">Default input</option>
            {#each mic.devices as device}
              <option value={device.deviceId}>{device.label}</option>
            {/each}
          </select>
          <button onclick={() => mic.stop()}>Turn mic off</button>
        {:else}
          <button onclick={() => mic.start()}>Enable mic</button>
        {/if}
      </label>
      <div class="backup">
        <button onclick={exportBackup}>Export backup</button>
        <button onclick={() => importInput.click()}>Import backup</button>
        <input type="file" accept="application/json" hidden bind:this={importInput} onchange={importBackup} />
      </div>
    </div>
  </details>
</header>

<main>
  {#if tab === 'practice'}
    {#key store.save.current}
      <Practice />
    {/key}
  {:else if tab === 'scales'}
    <ScaleExplorer />
  {:else}
    <Tuner />
  {/if}
</main>

<style>
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem 1.5rem;
    padding: 0.8rem 1.5rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .brand {
    font-size: 1.1rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .brand b {
    color: var(--accent);
  }
  nav {
    display: flex;
    gap: 0.25rem;
    flex: 1;
  }
  .tab {
    border-color: transparent;
    background: none;
    color: var(--muted);
  }
  .tab.active {
    color: var(--text);
    background: var(--surface-2);
  }
  .player {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.85rem;
    color: var(--muted);
  }
  .level {
    font-weight: 700;
    color: var(--text);
  }
  .xp,
  .meter {
    width: 90px;
    height: 6px;
    border-radius: 3px;
    background: var(--surface-2);
    overflow: hidden;
  }
  .meter {
    width: 50px;
  }
  .xp span,
  .meter span {
    display: block;
    height: 100%;
    background: var(--accent);
    transition: width 0.3s;
  }
  .meter span {
    background: var(--good);
    transition: none;
  }
  .streak.lit {
    color: var(--accent);
  }
  .menu {
    position: relative;
  }
  summary {
    cursor: pointer;
    padding: 0.45rem 0.9rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-weight: 600;
  }
  .panel {
    position: absolute;
    right: 0;
    z-index: 1;
    display: grid;
    /* minmax(0, …) stops long option text, such as device names, widening the column. */
    grid-template-columns: minmax(0, 1fr);
    gap: 0.8rem;
    width: 16rem;
    margin-top: 0.5rem;
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    box-shadow: 0 12px 30px rgb(0 0 0 / 0.35);
  }
  .panel label {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 0.25rem;
    font-size: 0.85rem;
    color: var(--muted);
  }
  .panel select {
    text-transform: capitalize;
  }
  .backup {
    display: flex;
    gap: 0.5rem;
  }
  .backup button {
    flex: 1;
    min-width: 0;
    padding-inline: 0.4rem;
    font-size: 0.85rem;
  }
  main {
    display: grid;
    gap: 1rem;
    max-width: 1280px;
    margin: 0 auto;
    padding: 1.5rem;
  }
</style>
