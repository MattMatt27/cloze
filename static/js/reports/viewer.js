// Report viewer page behavior: download menu + regenerate-with-progress.
import { enqueueReport, pollJob, progressLabel } from './jobs.js';

const downloadBtn = document.getElementById('downloadBtn');
const downloadMenu = document.getElementById('downloadMenu');
if (downloadBtn && downloadMenu) {
  downloadBtn.addEventListener('click', () => downloadMenu.classList.toggle('hidden'));
  document.addEventListener('click', (event) => {
    if (!downloadBtn.contains(event.target) && !downloadMenu.contains(event.target)) {
      downloadMenu.classList.add('hidden');
    }
  });
}

const regenerateBtn = document.getElementById('regenerateBtn');
const statusBox = document.getElementById('regenStatus');
if (regenerateBtn) {
  regenerateBtn.addEventListener('click', async () => {
    regenerateBtn.disabled = true;
    statusBox.classList.remove('hidden');
    statusBox.textContent = 'Queued…';
    try {
      const job = await enqueueReport(
        regenerateBtn.dataset.scope,
        Number(regenerateBtn.dataset.scopeId),
      );
      const finished = await pollJob(job.id, (j) => {
        statusBox.textContent = progressLabel(j);
      });
      if (finished.status === 'done') {
        window.location.reload();
      } else {
        statusBox.textContent = `Generation ${finished.status}: ${finished.error || 'unknown error'}`;
        regenerateBtn.disabled = false;
      }
    } catch (error) {
      statusBox.textContent = `Error: ${error.message}`;
      regenerateBtn.disabled = false;
    }
  });
}
