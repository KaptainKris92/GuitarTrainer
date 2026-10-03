<script lang="ts">
  import { mic } from './audio.svelte'
  import { pcName, pcOf } from './theory'

  const IN_TUNE_CENTS = 5

  const frame = $derived(mic.frame)
  const inTune = $derived(frame.midi !== null && Math.abs(frame.cents) <= IN_TUNE_CENTS)
  const needle = $derived(Math.max(-50, Math.min(50, frame.cents)))
</script>

<section class="card tuner">
  {#if !mic.running}
    <p class="muted">Enable the microphone to use the tuner.</p>
    <button onclick={() => mic.start()}>Enable microphone</button>
  {:else}
    <div class="note" class:in-tune={inTune}>{frame.midi === null ? '–' : pcName(pcOf(frame.midi))}</div>
    <div class="meter">
      <div class="centre"></div>
      {#if frame.midi !== null}
        <div class="needle" class:in-tune={inTune} style:left="{50 + needle}%"></div>
      {/if}
    </div>
    <div class="scale muted"><span>♭ tune up</span><span>tune down ♯</span></div>
    <p class="muted readout">
      {#if frame.freq !== null}
        {frame.freq.toFixed(1)} Hz · {frame.cents >= 0 ? '+' : ''}{frame.cents.toFixed(0)} cents
      {:else}
        Play one string at a time
      {/if}
    </p>
  {/if}
</section>

<style>
  .tuner {
    text-align: center;
    padding: 2.5rem 1.5rem;
  }
  .note {
    font-size: 8rem;
    font-weight: 800;
    line-height: 1.1;
    transition: color 0.15s;
  }
  .note.in-tune {
    color: var(--good);
  }
  .meter {
    position: relative;
    height: 18px;
    max-width: 520px;
    margin: 1.5rem auto 0.4rem;
    border-radius: 9px;
    background: var(--surface-2);
  }
  .centre {
    position: absolute;
    left: 45%;
    width: 10%;
    height: 100%;
    background: rgb(74 222 128 / 0.25);
  }
  .needle {
    position: absolute;
    top: -5px;
    width: 6px;
    height: 28px;
    margin-left: -3px;
    border-radius: 3px;
    background: var(--accent);
    transition: left 0.08s linear;
  }
  .needle.in-tune {
    background: var(--good);
  }
  .scale {
    display: flex;
    justify-content: space-between;
    max-width: 520px;
    margin: 0 auto;
    font-size: 0.8rem;
  }
  .readout {
    margin-top: 1.2rem;
    font-variant-numeric: tabular-nums;
  }
</style>
