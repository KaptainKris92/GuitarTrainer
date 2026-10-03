/** Speak a prompt with the browser's built-in voice. Resolves when it has finished. */
export function speak(text: string): Promise<void> {
  return new Promise((resolve) => {
    if (!('speechSynthesis' in window)) return resolve()
    speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'en-GB'
    utterance.rate = 1.1
    // Some browsers never fire `end`, so never wait longer than a few seconds.
    const timeout = setTimeout(resolve, 4000)
    utterance.onend = utterance.onerror = () => {
      clearTimeout(timeout)
      resolve()
    }
    speechSynthesis.speak(utterance)
  })
}

export function stopSpeaking() {
  if ('speechSynthesis' in window) speechSynthesis.cancel()
}
