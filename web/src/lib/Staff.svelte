<script lang="ts">
  /** A single note on a treble staff, in VexFlow form such as "c/4". */
  let { note }: { note: string } = $props()
  let host: HTMLDivElement

  $effect(() => {
    const key = note
    // Notation is only needed by the reading exercises, so load the library on demand.
    import('vexflow/bravura').then(async ({ Formatter, Renderer, Stave, StaveNote, Voice }) => {
      await document.fonts.load('30px Bravura')
      if (key !== note) return
      host.replaceChildren()
      const renderer = new Renderer(host, Renderer.Backends.SVG)
      renderer.resize(200, 230)
      const context = renderer.getContext()
      const stave = new Stave(10, 70, 180)
      stave.addClef('treble').setContext(context).draw()
      const voice = new Voice({ numBeats: 4, beatValue: 4 }).addTickables([new StaveNote({ keys: [key], duration: 'w' })])
      new Formatter().joinVoices([voice]).format([voice], 90)
      voice.draw(context, stave)
    })
  })
</script>

<div class="staff" bind:this={host} aria-label="Note on a staff"></div>

<style>
  /* Notation is drawn in black, so it sits on its own sheet of paper in every theme. */
  .staff {
    display: inline-block;
    width: 200px;
    height: 230px;
    margin-bottom: 0.75rem;
    border-radius: 12px;
    background: #f7f4ec;
  }
</style>
