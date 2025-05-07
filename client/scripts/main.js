import { processSootClipboard } from './clipboard.js';
import { sendPromptToBackend } from './prompt.js';

document
  .getElementById('pasteButton')
  .addEventListener('click', () => {
    const output = document.getElementById('output');
    processSootClipboard(output);
  });

document
  .getElementById('cliInput')
  .addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
      const raw = e.target.value.trim();
      console.log('🟡 Received command:', `mash: ${raw}`);
      e.target.value = '';
      await sendPromptToBackend(raw);
    }
  });
