let MASH_SERVER_URL = null;

async function loadConfig() {
  if (MASH_SERVER_URL) return MASH_SERVER_URL;

  const res = await fetch('./config.json');
  const config = await res.json();
  MASH_SERVER_URL = config.MASH_SERVER_URL;
  return MASH_SERVER_URL;
}

export async function sendPromptToBackend(promptText) {
  const baseUrl = await loadConfig();
  try {
    const res = await fetch(`${baseUrl}/user-prompt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: promptText })
    });

    if (!res.ok) throw new Error('Failed to send prompt');

    const result = await res.json();
    console.log('[🟢] Server received:', result);
  } catch (err) {
    console.error('[🔴] Prompt send failed:', err);
  }
}
