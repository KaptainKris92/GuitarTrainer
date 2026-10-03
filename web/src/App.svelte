<script lang="ts">
  import { mic } from './lib/audio.svelte'
  import NoteTrainer from './lib/NoteTrainer.svelte'
  import ScaleExplorer from './lib/ScaleExplorer.svelte'
  import Tuner from './lib/Tuner.svelte'

  const tabs = [
    { id: 'practice', label: 'Practice' },
    { id: 'scales', label: 'Scales' },
    { id: 'tuner', label: 'Tuner' },
  ] as const
  let tab = $state<(typeof tabs)[number]['id']>('practice')
</script>

<header>
  <span class="brand">Guitar Trainer</span>
  <nav>
    {#each tabs as { id, label }}
      <button class="tab" class:active={tab === id} onclick={() => (tab = id)}>{label}</button>
    {/each}
  </nav>
  <div class="mic">
    {#if mic.running}
      <span class="level"><span style:width="{Math.min(100, mic.frame.rms * 600)}%"></span></span>
      {#if mic.devices.length > 1}
        <select
          aria-label="Microphone"
          value={mic.deviceId}
          onchange={(event) => mic.selectDevice(event.currentTarget.value)}
        >
          <option value="">Default input</option>
          {#each mic.devices as device}
            <option value={device.deviceId}>{device.label}</option>
          {/each}
        </select>
      {/if}
      <button onclick={() => mic.stop()}>Mic off</button>
    {:else}
      <button onclick={() => mic.start()}>Enable mic</button>
    {/if}
  </div>
</header>

<main>
  {#if tab === 'practice'}
    <NoteTrainer />
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
    gap: 1rem 2rem;
    padding: 0.8rem 1.5rem;
    border-bottom: 1px solid var(--border);
  }
  .brand {
    font-weight: 800;
    font-size: 1.15rem;
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
  .mic {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  .mic select {
    max-width: 14rem;
  }
  .level {
    width: 60px;
    height: 6px;
    border-radius: 3px;
    background: var(--surface-2);
    overflow: hidden;
  }
  .level span {
    display: block;
    height: 100%;
    background: var(--good);
  }
  main {
    display: grid;
    gap: 1rem;
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.5rem;
  }
</style>
