import { processSootClipboard } from './clipboard.js';

document
  .getElementById('pasteButton')
  .addEventListener('click', () => {
    const output = document.getElementById('output');
    processSootClipboard(output);
  });
