const SOOT_MIME_KEYWORD = 'soot-json';

function parseSootClipboardData(jsonString) {
  try {
    console.log('[SOOT] Raw JSON from clipboard:', jsonString);
    const parsed = JSON.parse(jsonString);

    if (!parsed || !Array.isArray(parsed.spaces)) {
      throw new Error('Missing "spaces" array');
    }

    return { ok: true, value: parsed };
  } catch (err) {
    console.warn('[SOOT] Failed to parse JSON:', err.message);
    return { ok: false, error: 'Malformed clipboard JSON' };
  }
}

async function readSootClipboardData() {
  try {
    console.log('[SOOT] Button clicked, starting clipboard read');

    if (!navigator.clipboard || !navigator.clipboard.read) {
      alert('Your browser does not support navigator.clipboard.read().');
      return;
    }

    const items = await navigator.clipboard.read();
    console.log(`[SOOT] Clipboard read returned ${items.length} item(s)`);

    const output = document.getElementById('output');
    output.innerHTML = '';

    for (const item of items) {
      console.log('[SOOT] Clipboard item types:', item.types);

      // ✅ 精确找出 "soot-json" 类型（可能带前缀）
      const matchedType = item.types.find(type =>
        type.toLowerCase().includes(SOOT_MIME_KEYWORD)
      );

      if (matchedType) {
        console.log(`[SOOT] Found matching custom type: "${matchedType}"`);

        const blob = await item.getType(matchedType);
        const jsonText = await blob.text();
        const result = parseSootClipboardData(jsonText);

        if (!result.ok) {
          alert('Clipboard format is invalid.');
          continue;
        }

        const parsed = result.value;
        const imageURLs = parsed.spaces.flatMap(space =>
          space.entries.map(entry => entry.imageURL)
        );

        console.log('[SOOT] Parsed clipboard data:', parsed);
        console.log('[SOOT] Extracted image URLs:', imageURLs);

        imageURLs.forEach(url => {
          const img = document.createElement('img');
          img.src = url;
          img.style.width = '200px';
          img.style.margin = '10px';
          img.style.border = '1px solid #ccc';
          output.appendChild(img);
        });
      } else {
        console.log('[SOOT] No matching "soot-json" type found in:', item.types);
      }

      // ✅ 显示剪贴板中的原始 PNG 图片
      if (item.types.includes('image/png')) {
        const blob = await item.getType('image/png');
        const url = URL.createObjectURL(blob);
        const img = document.createElement('img');
        img.src = url;
        img.style.width = '200px';
        img.style.margin = '10px';
        img.style.border = '1px dashed #aaa';
        output.appendChild(img);
        console.log('[SOOT] image/png content rendered.');
      }
    }
  } catch (err) {
    console.error('[SOOT] Clipboard read failed:', err);
    alert('Clipboard read failed: ' + err.message);
  }
}

document
  .getElementById('pasteButton')
  .addEventListener('click', readSootClipboardData);
