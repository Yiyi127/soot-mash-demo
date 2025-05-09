//scripts/clipboard.js
import { getAuthToken } from './auth.js';

const SOOT_MIME_KEYWORD = 'soot-json';
const MASH_SERVER_URL = 'http://localhost:8000';

function parseSootClipboardData(jsonString) {
  try {
    const parsed = JSON.parse(jsonString);
    if (!parsed || !Array.isArray(parsed.spaces)) throw new Error('Missing "spaces" array');
    return { ok: true, value: parsed };
  } catch {
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

export async function processSootClipboard() {
  console.log('[SOOT] 🚀 Script started: processSootClipboard');
  const payloads = [];

  try {
    const items = await navigator.clipboard.read();
    console.log(`[SOOT] 📋 Clipboard contains ${items.length} items`);

    let allEntries = [];

    for (const item of items) {
      const matchedType = item.types.find(type =>
        type.toLowerCase().includes(SOOT_MIME_KEYWORD)
      );
      if (matchedType) {
        console.log(`[SOOT] ✨ Found metadata of type "${matchedType}"`);
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
          console.log(`[SOOT] ✅ Extracted ${allEntries.length} metadata entries`);
        } else {
          console.warn('[SOOT] ⚠️ Failed to parse metadata:', result.error);
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
      }

      const payload = {
        metadata: allEntries[i],
        imageBase64: base64Image
      };
      payloads.push(payload);

      console.log(`[SOOT] 🧩 Structured Payload ${i + 1}:`, {
        ...payload,
        imageBase64Summary: base64Image ? `length=${base64Image.length}` : 'null'
      });
    }

    console.log('[SOOT] ✅ All Payloads Ready:', payloads.length);
  } catch (err) {
    console.error('[SOOT] ❌ Clipboard read failed:', err);
    return [];
  }

  try {
    console.log('[SOOT] 🔁 Sending metadata to backend...');
    
    // Get auth token
    const token = getAuthToken();
    
    const res = await fetch(`${MASH_SERVER_URL}/api/mash/process-entries`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(payloads.map(p => p.metadata))
    });

    const data = await res.json();
    console.log('[SOOT] ✅ Backend responded with', data.length, 'items');

    data.forEach((item, index) => {
      const img = document.createElement('img');
      img.src = `data:image/png;base64,${item.imageBase64}`;
      img.alt = item.metadata.filename || `Image ${index + 1}`;
      img.style.width = '200px';
      img.style.margin = '8px';
      document.body.appendChild(img);
    
      console.log(`[SOOT] 🧠 Displayed image: ${img.alt}`);
    });
    

    console.log('[SOOT] 🎉 Done displaying images');
    return data;
  } catch (sendErr) {
    console.error('[SOOT] ❌ Failed to send to backend:', sendErr);
    return [];
  }
}