/**
 * MediClear AI — Frontend Application
 *
 * Vanilla JS, no build step, no external CDNs. The API returns a *structured*
 * analysis object, which we render directly into the DOM with textContent —
 * so there is no markdown parser and no innerHTML of model output, closing the
 * XSS vector entirely. Chat answers stream over Server-Sent Events.
 */

/* ── State ────────────────────────────────────────────────────────────────── */
const state = {
  sessionId: null,
  currentLanguage: 'en',
  uiLanguage: 'en',
  translations: {},
  languages: [],
  languagesByCode: {},
  analysisText: '',   // markdown convenience string, used for TTS
  selectedFile: null,
  audioBlob: null,
};

/* ── DOM refs ─────────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const el = {
  uiLangSelect: $('ui-language-select'),
  tabText: $('tab-text'),
  tabFile: $('tab-file'),
  panelText: $('panel-text'),
  panelFile: $('panel-file'),
  textInput: $('text-input'),
  dropZone: $('drop-zone'),
  fileInput: $('file-input'),
  filePreview: $('file-preview'),
  responseLang: $('response-language'),
  btnAnalyze: $('btn-analyze'),
  btnClear: $('btn-clear'),
  loadingIndicator: $('loading-indicator'),
  loadingText: $('loading-text'),
  resultsSection: $('results-section'),
  providerBadge: $('provider-badge'),
  audioContainer: $('audio-container'),
  audioPlayer: $('audio-player'),
  analysisContent: $('analysis-content'),
  btnListen: $('btn-listen'),
  chatSection: $('chat-section'),
  chatMessages: $('chat-messages'),
  chatForm: $('chat-form'),
  chatInput: $('chat-input'),
  errorBanner: $('error-banner'),
  errorMessage: $('error-message'),
};

/* ── i18n ─────────────────────────────────────────────────────────────────── */
function t(key) {
  const lang = state.translations[state.uiLanguage];
  if (lang && lang[key]) return lang[key];
  const fallback = state.translations['en'];
  return (fallback && fallback[key]) || key;
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(node => {
    const value = t(node.getAttribute('data-i18n'));
    if (value) node.textContent = value;
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(node => {
    const value = t(node.getAttribute('data-i18n-placeholder'));
    if (value) node.placeholder = value;
  });
  const rtl = isRtl(state.uiLanguage);
  document.documentElement.setAttribute('dir', rtl ? 'rtl' : 'ltr');
  document.documentElement.setAttribute('lang', state.uiLanguage);
}

function isRtl(code) {
  const lang = state.languagesByCode[code];
  return !!(lang && lang.rtl);
}

/* ── API helper ───────────────────────────────────────────────────────────── */
async function apiFetch(path, options = {}) {
  const resp = await fetch(path, options);
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      detail = body.error || body.detail || detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  return resp;
}

/* ── Init ─────────────────────────────────────────────────────────────────── */
async function init() {
  try {
    const [transResp, langResp] = await Promise.all([
      apiFetch('/api/v1/translations'),
      apiFetch('/api/v1/languages'),
    ]);
    state.translations = await transResp.json();
    state.languages = (await langResp.json()).languages;
    state.languages.forEach(l => { state.languagesByCode[l.code] = l; });

    for (const sel of [el.uiLangSelect, el.responseLang]) {
      state.languages.forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang.code;
        opt.textContent = lang.name;
        sel.appendChild(opt);
      });
    }
    el.uiLangSelect.value = state.uiLanguage;
    el.responseLang.value = state.currentLanguage;

    applyTranslations();
    bindEvents();
  } catch (err) {
    console.error('Init failed:', err);
    showError('Failed to load application. Please refresh the page.');
  }
}

/* ── Events ───────────────────────────────────────────────────────────────── */
function bindEvents() {
  el.uiLangSelect.addEventListener('change', () => {
    state.uiLanguage = el.uiLangSelect.value;
    applyTranslations();
  });
  el.responseLang.addEventListener('change', () => {
    state.currentLanguage = el.responseLang.value;
  });
  el.tabText.addEventListener('click', () => switchTab('text'));
  el.tabFile.addEventListener('click', () => switchTab('file'));

  el.dropZone.addEventListener('click', () => el.fileInput.click());
  el.dropZone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.fileInput.click(); }
  });
  el.dropZone.addEventListener('dragover', e => { e.preventDefault(); el.dropZone.classList.add('drag-over'); });
  el.dropZone.addEventListener('dragleave', () => el.dropZone.classList.remove('drag-over'));
  el.dropZone.addEventListener('drop', e => {
    e.preventDefault();
    el.dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelected(file);
  });
  el.fileInput.addEventListener('change', () => {
    if (el.fileInput.files[0]) handleFileSelected(el.fileInput.files[0]);
  });

  el.btnAnalyze.addEventListener('click', handleAnalyze);
  el.btnClear.addEventListener('click', resetAll);
  el.btnListen.addEventListener('click', handleListen);
  el.chatForm.addEventListener('submit', e => { e.preventDefault(); handleChat(); });
  el.chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleChat(); }
  });
}

/* ── Tabs & files ─────────────────────────────────────────────────────────── */
function switchTab(tab) {
  const isText = tab === 'text';
  el.tabText.classList.toggle('active', isText);
  el.tabFile.classList.toggle('active', !isText);
  el.tabText.setAttribute('aria-selected', String(isText));
  el.tabFile.setAttribute('aria-selected', String(!isText));
  el.panelText.classList.toggle('hidden', !isText);
  el.panelFile.classList.toggle('hidden', isText);
}

function handleFileSelected(file) {
  const isImage = file.type.startsWith('image/');
  const isPdf = file.type === 'application/pdf';
  if (!isImage && !isPdf) { showError(t('err_file_type')); return; }

  state.selectedFile = { file, type: isImage ? 'image' : 'pdf' };
  el.filePreview.classList.remove('hidden');
  el.filePreview.textContent = '';

  const label = document.createElement('span');
  label.textContent = `${isImage ? '📷' : '📄'} ${file.name} (${formatBytes(file.size)})`;
  if (isImage) {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    img.alt = `Preview of ${file.name}`;
    el.filePreview.appendChild(img);
  }
  el.filePreview.appendChild(label);
}

/* ── Analysis ─────────────────────────────────────────────────────────────── */
async function handleAnalyze() {
  const activeTab = el.tabText.classList.contains('active') ? 'text' : 'file';
  const textValue = el.textInput.value.trim();
  if (activeTab === 'text' && !textValue) { showError(t('err_no_input')); return; }
  if (activeTab === 'file' && !state.selectedFile) { showError(t('err_no_input')); return; }

  setLoading(true, t('loading_analyze'));
  hideError();
  hideResults();
  try {
    const formData = new FormData();
    formData.append('language', state.currentLanguage);
    if (activeTab === 'text') formData.append('text', textValue);
    else formData.append('file', state.selectedFile.file);

    const resp = await apiFetch('/api/v1/analyze', { method: 'POST', body: formData });
    const data = await resp.json();

    state.sessionId = data.session_id;
    state.analysisText = data.markdown;
    state.audioBlob = null;
    showResults(data);
  } catch (err) {
    showError(err.message || t('err_generic'));
  } finally {
    setLoading(false);
  }
}

/* ── Structured, XSS-safe rendering ───────────────────────────────────────── */
function showResults(data) {
  el.providerBadge.textContent =
    `🤖 ${data.provider} · ${data.model} · ${data.language.toUpperCase()}${data.cached ? ' · cached' : ''}`;
  el.providerBadge.classList.remove('hidden');

  renderAnalysis(el.analysisContent, data.analysis, data.language);

  el.audioContainer.classList.add('hidden');
  el.chatMessages.textContent = '';
  el.resultsSection.classList.remove('hidden');
  el.chatSection.classList.toggle('hidden', !data.session_id);
  el.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderAnalysis(container, analysis, language) {
  container.textContent = '';
  container.setAttribute('dir', isRtl(language) ? 'rtl' : 'ltr');

  const h = (level, text) => { const n = document.createElement('h' + level); n.textContent = text; return n; };
  const p = text => { const n = document.createElement('p'); n.textContent = text; return n; };

  if (analysis.document_type === 'not_medical') {
    container.appendChild(h(3, t('not_medical') || 'This does not look like a medical document'));
    container.appendChild(p(analysis.summary || analysis.explanation || ''));
    return;
  }

  if (analysis.readability && analysis.readability.estimated_cefr) {
    const badge = document.createElement('div');
    badge.className = 'readability-badge';
    const meets = analysis.readability.meets_target;
    badge.textContent = `📖 ${t('reading_level') || 'Reading level'}: ${analysis.readability.estimated_cefr}` +
      (meets === false ? ' ⚠︎' : ' ✓');
    container.appendChild(badge);
  }

  if (analysis.summary) { container.appendChild(h(2, t('sec_summary') || 'Summary')); container.appendChild(p(analysis.summary)); }
  if (analysis.explanation) {
    container.appendChild(h(2, t('sec_explanation') || 'Explanation'));
    analysis.explanation.split(/\n{2,}/).forEach(par => { if (par.trim()) container.appendChild(p(par.trim())); });
  }

  if (analysis.lab_values && analysis.lab_values.length) {
    container.appendChild(h(2, t('sec_labs') || 'Lab Values'));
    container.appendChild(buildTable(
      ['Test', 'Result', 'Reference', 'Flag'],
      analysis.lab_values.map(lv => [lv.name, `${lv.value}${lv.unit ? ' ' + lv.unit : ''}`, lv.reference_range || '—', lv.flag || '—'])
    ));
  }

  if (analysis.medications && analysis.medications.length) {
    container.appendChild(h(2, t('sec_meds') || 'Medications'));
    container.appendChild(buildList(analysis.medications.map(m =>
      `${m.name}${m.dose ? ' — ' + m.dose : ''}${m.frequency ? ', ' + m.frequency : ''}${m.purpose ? ' (' + m.purpose + ')' : ''}`)));
  }

  if (analysis.key_terms && analysis.key_terms.length) {
    container.appendChild(h(2, t('sec_terms') || 'Key Medical Terms'));
    const ul = document.createElement('ul');
    analysis.key_terms.forEach(kt => {
      const li = document.createElement('li');
      const strong = document.createElement('strong');
      strong.textContent = kt.term + ' ';
      li.appendChild(strong);
      li.appendChild(document.createTextNode('— ' + kt.definition));
      if (kt.found_in_source === false) {
        const note = document.createElement('em');
        note.className = 'term-note';
        note.textContent = ' (not found verbatim in your document)';
        li.appendChild(note);
      }
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  if (analysis.action_items && analysis.action_items.length) {
    container.appendChild(h(2, t('sec_actions') || 'What This Means for You'));
    container.appendChild(buildList(analysis.action_items));
  }

  if (analysis.disclaimer) {
    const hr = document.createElement('hr');
    const disc = document.createElement('p');
    disc.className = 'analysis-disclaimer';
    disc.textContent = analysis.disclaimer;
    container.appendChild(hr);
    container.appendChild(disc);
  }
}

function buildList(items) {
  const ul = document.createElement('ul');
  items.forEach(text => { const li = document.createElement('li'); li.textContent = text; ul.appendChild(li); });
  return ul;
}

function buildTable(headers, rows) {
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const htr = document.createElement('tr');
  headers.forEach(hdr => { const th = document.createElement('th'); th.textContent = hdr; htr.appendChild(th); });
  thead.appendChild(htr);
  const tbody = document.createElement('tbody');
  rows.forEach(row => {
    const tr = document.createElement('tr');
    row.forEach(cell => { const td = document.createElement('td'); td.textContent = cell; tr.appendChild(td); });
    tbody.appendChild(tr);
  });
  table.appendChild(thead);
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

function hideResults() {
  el.resultsSection.classList.add('hidden');
  el.chatSection.classList.add('hidden');
}

/* ── Text-to-speech ───────────────────────────────────────────────────────── */
async function handleListen() {
  if (!state.analysisText) return;
  setLoading(true, t('loading_audio'));
  el.btnListen.disabled = true;
  try {
    if (state.audioBlob) { playAudio(state.audioBlob); return; }
    const resp = await apiFetch('/api/v1/audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: state.analysisText, language: state.currentLanguage }),
    });
    state.audioBlob = await resp.blob();
    playAudio(state.audioBlob);
  } catch (err) {
    showError(err.message || t('err_generic'));
  } finally {
    setLoading(false);
    el.btnListen.disabled = false;
  }
}

function playAudio(blob) {
  el.audioPlayer.src = URL.createObjectURL(blob);
  el.audioContainer.classList.remove('hidden');
  el.audioPlayer.play().catch(() => {});
}

/* ── Chat (streaming) ─────────────────────────────────────────────────────── */
async function handleChat() {
  const message = el.chatInput.value.trim();
  if (!message || !state.sessionId) return;

  appendChatMessage('user', message, t('chat_you') || 'You');
  el.chatInput.value = '';
  el.chatInput.disabled = true;
  const btnSend = $('btn-chat-send');
  btnSend.disabled = true;

  const bubble = appendChatMessage('assistant', '', t('chat_assistant') || 'MediClear AI');
  bubble.setAttribute('dir', isRtl(state.currentLanguage) ? 'rtl' : 'ltr');

  try {
    const resp = await fetch(`/api/v1/chat/${state.sessionId}/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, language: state.currentLanguage }),
    });
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);
    await consumeSSE(resp.body, evt => {
      if (evt.delta) { bubble.textContent += evt.delta; el.chatMessages.scrollTop = el.chatMessages.scrollHeight; }
      if (evt.error) throw new Error(evt.error);
    });
  } catch (err) {
    bubble.textContent = (err.message || t('err_generic'));
    showError(err.message || t('err_generic'));
  } finally {
    el.chatInput.disabled = false;
    btnSend.disabled = false;
    el.chatInput.focus();
  }
}

async function consumeSSE(stream, onEvent) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop();
    for (const chunk of events) {
      const line = chunk.split('\n').find(l => l.startsWith('data:'));
      if (!line) continue;
      try { onEvent(JSON.parse(line.slice(5).trim())); } catch (_) { /* ignore */ }
    }
  }
}

function appendChatMessage(role, content, label) {
  const wrapper = document.createElement('div');
  wrapper.className = `chat-message ${role}`;
  const labelEl = document.createElement('div');
  labelEl.className = 'chat-message-label';
  labelEl.textContent = label;
  const bubble = document.createElement('div');
  bubble.className = 'chat-message-bubble';
  bubble.textContent = content;
  wrapper.appendChild(labelEl);
  wrapper.appendChild(bubble);
  el.chatMessages.appendChild(wrapper);
  el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
  return bubble;
}

/* ── Reset / loading / errors ─────────────────────────────────────────────── */
function resetAll() {
  state.sessionId = null;
  state.analysisText = '';
  state.selectedFile = null;
  state.audioBlob = null;
  el.textInput.value = '';
  el.fileInput.value = '';
  el.filePreview.classList.add('hidden');
  el.filePreview.textContent = '';
  el.audioContainer.classList.add('hidden');
  el.chatMessages.textContent = '';
  el.chatInput.value = '';
  hideResults();
  hideError();
  switchTab('text');
  el.textInput.focus();
}

function setLoading(active, message) {
  el.loadingIndicator.classList.toggle('hidden', !active);
  el.btnAnalyze.disabled = active;
  if (message) el.loadingText.textContent = message;
}

function showError(message) {
  el.errorMessage.textContent = message;
  el.errorBanner.classList.remove('hidden');
}
function hideError() {
  el.errorBanner.classList.add('hidden');
  el.errorMessage.textContent = '';
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

document.addEventListener('DOMContentLoaded', init);
