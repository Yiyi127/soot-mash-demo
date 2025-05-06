const SOOT_MIME_TYPE = 'text/soot-json';

export async function readSootClipboardData() {
  try {
    const items = await navigator.clipboard.read();
    for (const item of items) {
      if (item.types.includes(SOOT_MIME_TYPE)) {
        const blob = await item.getType(SOOT_MIME_TYPE);
        const jsonText = await blob.text();
        const parsed = JSON.parse(jsonText);
        console.log('[SOOT] Clipboard Data:', parsed);

        const imageURLs = parsed.spaces.flatMap(space =>
          space.entries.map(entry => entry.imageURL)
        );
        console.log('[SOOT] Image URLs:', imageURLs);

        return imageURLs;
      }
    }
    alert('No SOOT clipboard data found.');
  } catch (err) {
    console.error('[SOOT] Clipboard read failed:', err);
  }
}
