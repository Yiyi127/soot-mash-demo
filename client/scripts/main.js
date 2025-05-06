const SOOT_MIME_KEYWORD = 'soot-json';
const BASE_URL_PREFIX = 'https://static.soot.com/r/';
const BEARER_TOKEN = 'Bearer ' + (import.meta.env?.VITE_SOOT_ACCESS_TOKEN ?? ''); // or hardcode your token here

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
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function fetchImageWithAuth(imageURL) {
  try {
    const res = await fetch(imageURL, {
      headers: {
        Authorization: BEARER_TOKEN,
        Accept: 'image/*'
      }
    });
    if (!res.ok) throw new Error(`Failed to fetch ${imageURL}`);
    const blob = await res.blob();
    return await blobToBase64(blob);
  } catch (err) {
    console.error(`[SOOT] Auth fetch failed for ${imageURL}:`, err);
    return null;
  }
}

async function readSootClipboardData() {
  try {
    const items = await navigator.clipboard.read();
    const output = document.getElementById('output');
    output.innerHTML = '';

    const payloads = [];
    let allEntries = [];

    for (const item of items) {
      const matchedType = item.types.find(type =>
        type.toLowerCase().includes(SOOT_MIME_KEYWORD)
      );

      if (matchedType) {
        const blob = await item.getType(matchedType);
        const jsonText = await blob.text();
        const result = parseSootClipboardData(jsonText);
        if (result.ok) {
          const structuredJSON = result.value;
          allEntries = structuredJSON.spaces.flatMap(space =>
            space.entries.map(entry => ({
              imageURL: entry.imageURL,
              instanceId: entry.instanceId,
              filename: entry.filename || null,
              spaceId: space.spaceId,
              operation: space.operation
            }))
          );
        }
      }
    }

    const allPngBlobs = [];
    for (const item of items) {
      const pngTypes = item.types.filter(type => type === 'image/png');
      for (const pngType of pngTypes) {
        const blob = await item.getType(pngType);
        allPngBlobs.push(blob);
      }
    }

    for (let i = 0; i < allEntries.length; i++) {
      let base64Image = null;

      if (allPngBlobs[i]) {
        base64Image = await blobToBase64(allPngBlobs[i]);
      } else if (allEntries[i].imageURL) {
        base64Image = await fetchImageWithAuth(allEntries[i].imageURL);
      }

      const payload = {
        metadata: allEntries[i],
        imageBase64: base64Image
      };

      payloads.push(payload);

      console.log(`[SOOT] 🧩 Payload ${i + 1}:`, {
        ...payload,
        imageBase64Summary: base64Image ? `length=${base64Image.length}` : 'null'
      });

      if (base64Image) {
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${base64Image}`;
        img.style.width = '150px';    
        img.style.height = 'auto';  
        img.style.margin = '10px';
     
        output.appendChild(img);
      }

      const label = document.createElement('div');
      label.textContent = `imageURL: ${allEntries[i].imageURL}`;
      label.style.fontSize = '12px';
      label.style.marginBottom = '10px';
      output.appendChild(label);
    }

    console.log('[SOOT] ✅ All Composite Payloads:', payloads);
  } catch (err) {
    console.error('[SOOT] Clipboard read failed:', err);
  }
}

document
  .getElementById('pasteButton')
  .addEventListener('click', readSootClipboardData);
