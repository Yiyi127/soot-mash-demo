const SOOT_MIME_KEYWORD = 'soot-json';

function parseSootClipboardData(jsonString) {
  try {
    const parsed = JSON.parse(jsonString);
    if (!parsed || !Array.isArray(parsed.spaces)) throw new Error('Missing "spaces" array');
    return { ok: true, value: parsed };
  } catch (err) {
    return { ok: false, error: 'Malformed clipboard JSON' };
  }
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]); // remove 'data:image/png;base64,'
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function readSootClipboardData() {
  try {
    const items = await navigator.clipboard.read();
    const output = document.getElementById('output');
    output.innerHTML = '';

    for (const item of items) {
      const matchedType = item.types.find(type =>
        type.toLowerCase().includes(SOOT_MIME_KEYWORD)
      );

      let structuredJSON = null;

      if (matchedType) {
        const blob = await item.getType(matchedType);
        const jsonText = await blob.text();
        const result = parseSootClipboardData(jsonText);
        if (result.ok) structuredJSON = result.value;
      }

      if (item.types.includes('image/png')) {
        const blob = await item.getType('image/png');
        const base64Image = await blobToBase64(blob);

        const compositePayload = {
          metadata: structuredJSON,
          imageBase64: base64Image
        };

        console.log('[SOOT] 🧩 Gemini-Ready Payload:', compositePayload);

        const img = document.createElement('img');
        img.src = `data:image/png;base64,${base64Image}`;
        img.style.width = '200px';
        img.style.margin = '10px';
        img.style.border = '1px solid #0f0';
        output.appendChild(img);
      }
    }
  } catch (err) {
    console.error('[SOOT] Clipboard read failed:', err);
  }
}

document
  .getElementById('pasteButton')
  .addEventListener('click', readSootClipboardData);
