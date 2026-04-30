/**
 * MediClear AI — Frontend Application
 *
 * Pure vanilla JS, no build step required.
 * Communicates with the FastAPI backend via fetch().
 */

/* ═══════════════════════════════════════════════════════════════════════════
   State
   ═══════════════════════════════════════════════════════════════════════════ */

const state = {
  sessionId: null,
  currentLanguage: 'en',      // Response/AI language
  uiLanguage: 'en',           // Interface display language
  translations: {},           // { langCode: { key: value } }
  languages: [],              // [{ code, name }]
  analysisText: '',           // Last analysis result text
  selectedFile: null,         // { file: File, type: 'pdf'|'image', previewUrl? }
  audioBlob: null,
  isLoading: false,
};

/* ═══════════════════════════════════════════════════════════════════════════
   DOM references
   ═══════════════════════════════════════════════════════════════════════════ */

const $ = id => document.getElementById(id);

const el = {
  uiLangSelect:      $('ui-language-select'),
  tabText:           $('tab-text'),
  tabFile:           $('tab-file'),
  panelText:         $('panel-text'),
  panelFile:         $('panel-file'),
  textInput:         $('text-input'),
  dropZone:          $('drop-zone'),
  fileInput:         $('file-input'),
  filePreview:       $('file-preview'),
  responseLang:      $('response-language'),
  btnAnalyze:        $('btn-analyze'),
  btnClear:          $('btn-clear'),
  loadingIndicator:  $('loading-indicator'),
  loadingText:       $('loading-text'),
  resultsSection:    $('results-section'),
  providerBadge:     $('provider-badge'),
  audioContainer:    $('audio-container'),
  audioPlayer:       $('audio-player'),
  analysisContent:   $('analysis-content'),
  btnListen:         $('btn-listen'),
  chatSection:       $('chat-section'),
  chatMessages:      $('chat-messages'),
  chatForm:          $('chat-form'),
  chatInput:         $('chat-input'),
  errorBanner:       $('error-banner'),
  errorMessage:      $('error-message'),
};

/* ═══════════════════════════════════════════════════════════════════════════
   i18n helpers
   ═══════════════════════════════════════════════════════════════════════════ */

function t(key) {
  const lang = state.translations[state.uiLanguage];
  if (lang && lang[key]) return lang[key];
  const fallback = state.translations['en'];
  return (fallback && fallback[key]) || key;
}

function applyTranslations() {
  // data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(node => {
    const key = node.getAttribute('data-i18n');
    const value = t(key);
    if (value) node.textContent = value;
  });

  // data-i18n-placeholder elements
  document.querySelectorAll('[data-i18n-placeholder]').forEach(node => {
    const key = node.getAttribute('data-i18n-placeholder');
    const value = t(key);
    if (value) node.placeholder = value;
  });

  // RTL support for Arabic
  document.documentElement.setAttribute('dir', state.uiLanguage === 'ar' ? 'rtl' : 'ltr');
  document.documentElement.setAttribute('lang', state.uiLanguage);
}

/* ═══════════════════════════════════════════════════════════════════════════
   API helpers
   ═══════════════════════════════════════════════════════════════════════════ */

async function apiFetch(path, options = {}) {
  const resp = await fetch(path, options);
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      detail = body.error || body.detail || detail;
    } catch (_) { /* ignore parse errors */ }
    throw new Error(detail);
  }
  return resp;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Initialisation
   ═══════════════════════════════════════════════════════════════════════════ */

async function init() {
  try {
    // Load translations and language list in parallel
    const [transResp, langResp] = await Promise.all([
      apiFetch('/api/v1/translations'),
      apiFetch('/api/v1/languages'),
    ]);

    state.translations = await transResp.json();
    const langData = await langResp.json();
    state.languages = langData.languages;

    // Populate UI language selector (header)
    state.languages.forEach(lang => {
      const opt = document.createElement('option');
      opt.value = lang.code;
      opt.textContent = lang.name;
      el.uiLangSelect.appendChild(opt);
    });
    el.uiLangSelect.value = state.uiLanguage;

    // Populate response language selector (input card)
    state.languages.forEach(lang => {
      const opt = document.createElement('option');
      opt.value = lang.code;
      opt.textContent = lang.name;
      el.responseLang.appendChild(opt);
    });
    el.responseLang.value = state.currentLanguage;

    applyTranslations();
    bindEvents();
  } catch (err) {
    console.error('Init failed:', err);
    showError('Failed to load application. Please refresh the page.');
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Event binding
   ═══════════════════════════════════════════════════════════════════════════ */

function bindEvents() {
  // UI language change (header)
  el.uiLangSelect.addEventListener('change', () => {
    state.uiLanguage = el.uiLangSelect.value;
    applyTranslations();
  });

  // Response language change
  el.responseLang.addEventListener('change', () => {
    state.currentLanguage = el.responseLang.value;
  });

  // Tab switching
  el.tabText.addEventListener('click', () => switchTab('text'));
  el.tabFile.addEventListener('click', () => switchTab('file'));

  // File drop zone
  el.dropZone.addEventListener('click', () => el.fileInput.click());
  el.dropZone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      el.fileInput.click();
    }
  });
  el.dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    el.dropZone.classList.add('drag-over');
  });
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

  // Analyze
  el.btnAnalyze.addEventListener('click', handleAnalyze);

  // Clear
  el.btnClear.addEventListener('click', resetAll);

  // Listen (TTS)
  el.btnListen.addEventListener('click', handleListen);

  // Chat form
  el.chatForm.addEventListener('submit', e => {
    e.preventDefault();
    handleChat();
  });

  // Allow Ctrl+Enter to submit chat
  el.chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleChat();
    }
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   Tab switching
   ═══════════════════════════════════════════════════════════════════════════ */

function switchTab(tab) {
  const isText = tab === 'text';
  el.tabText.classList.toggle('active', isText);
  el.tabFile.classList.toggle('active', !isText);
  el.tabText.setAttribute('aria-selected', String(isText));
  el.tabFile.setAttribute('aria-selected', String(!isText));
  el.panelText.classList.toggle('hidden', !isText);
  el.panelFile.classList.toggle('hidden', isText);
}

/* ═══════════════════════════════════════════════════════════════════════════
   File handling
   ═══════════════════════════════════════════════════════════════════════════ */

function handleFileSelected(file) {
  const isImage = file.type.startsWith('image/');
  const isPdf = file.type === 'application/pdf';

  if (!isImage && !isPdf) {
    showError(t('err_file_type'));
    return;
  }

  state.selectedFile = { file, type: isImage ? 'image' : 'pdf' };
  el.filePreview.classList.remove('hidden');

  if (isImage) {
    const url = URL.createObjectURL(file);
    el.filePreview.innerHTML = `
      <img src="${url}" alt="Preview of ${escHtml(file.name)}" />
      <span>📷 ${escHtml(file.name)} (${formatBytes(file.size)})</span>
    `;
  } else {
    el.filePreview.innerHTML = `
      <span style="font-size:1.5rem">📄</span>
      <span>${escHtml(file.name)} (${formatBytes(file.size)})</span>
    `;
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Analysis
   ═══════════════════════════════════════════════════════════════════════════ */

async function handleAnalyze() {
  const activeTab = el.tabText.classList.contains('active') ? 'text' : 'file';
  const textValue = el.textInput.value.trim();

  if (activeTab === 'text' && !textValue) {
    showError(t('err_no_input'));
    return;
  }
  if (activeTab === 'file' && !state.selectedFile) {
    showError(t('err_no_input'));
    return;
  }

  setLoading(true, t('loading_analyze'));
  hideError();
  hideResults();

  try {
    const formData = new FormData();
    formData.append('language', state.currentLanguage);

    if (activeTab === 'text') {
      formData.append('text', textValue);
    } else {
      formData.append('file', state.selectedFile.file);
    }

    const resp = await apiFetch('/api/v1/analyze', { method: 'POST', body: formData });
    const data = await resp.json();

    state.sessionId = data.session_id;
    state.analysisText = data.analysis;
    state.audioBlob = null;

    showResults(data);
  } catch (err) {
    showError(err.message || t('err_generic'));
  } finally {
    setLoading(false);
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Results display
   ═══════════════════════════════════════════════════════════════════════════ */

function showResults(data) {
  // Provider badge
  el.providerBadge.textContent = `🤖 ${data.provider} · ${data.model} · ${data.language.toUpperCase()}`;
  el.providerBadge.classList.remove('hidden');

  // Render markdown
  el.analysisContent.innerHTML = marked.parse(data.analysis);

  // Reset audio
  el.audioContainer.classList.add('hidden');

  // Reset chat
  el.chatMessages.innerHTML = '';

  el.resultsSection.classList.remove('hidden');
  el.chatSection.classList.remove('hidden');
  el.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function hideResults() {
  el.resultsSection.classList.add('hidden');
  el.chatSection.classList.add('hidden');
}

/* ═══════════════════════════════════════════════════════════════════════════
   Text-to-speech
   ═══════════════════════════════════════════════════════════════════════════ */

async function handleListen() {
  if (!state.analysisText) return;

  setLoading(true, t('loading_audio'));
  el.btnListen.disabled = true;

  try {
    if (state.audioBlob) {
      playAudio(state.audioBlob);
      return;
    }

    const resp = await apiFetch('/api/v1/audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: state.analysisText, language: state.currentLanguage }),
    });

    const blob = await resp.blob();
    state.audioBlob = blob;
    playAudio(blob);
  } catch (err) {
    showError(err.message || t('err_generic'));
  } finally {
    setLoading(false);
    el.btnListen.disabled = false;
  }
}

function playAudio(blob) {
  const url = URL.createObjectURL(blob);
  el.audioPlayer.src = url;
  el.audioContainer.classList.remove('hidden');
  el.audioPlayer.play().catch(() => {
    // Autoplay might be blocked — the controls are visible so the user can press play
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
   Chat
   ═══════════════════════════════════════════════════════════════════════════ */

async function handleChat() {
  const message = el.chatInput.value.trim();
  if (!message || !state.sessionId) return;

  appendChatMessage('user', message, t('chat_you') || 'You');
  el.chatInput.value = '';
  el.chatInput.disabled = true;
  const btnSend = $('btn-chat-send');
  btnSend.disabled = true;

  // Show typing indicator
  const typingId = appendTypingIndicator();

  try {
    const resp = await apiFetch(`/api/v1/chat/${state.sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, language: state.currentLanguage }),
    });
    const data = await resp.json();

    removeTypingIndicator(typingId);
    appendChatMessage('assistant', data.response, t('chat_assistant') || 'MediClear AI');
  } catch (err) {
    removeTypingIndicator(typingId);
    showError(err.message || t('err_generic'));
  } finally {
    el.chatInput.disabled = false;
    btnSend.disabled = false;
    el.chatInput.focus();
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

  if (role === 'assistant') {
    const inner = document.createElement('div');
    inner.className = 'prose';
    inner.innerHTML = marked.parse(content);
    bubble.appendChild(inner);
  } else {
    bubble.textContent = content;
  }

  wrapper.appendChild(labelEl);
  wrapper.appendChild(bubble);
  el.chatMessages.appendChild(wrapper);
  el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
  return wrapper;
}

function appendTypingIndicator() {
  const id = 'typing-' + Date.now();
  const wrapper = document.createElement('div');
  wrapper.id = id;
  wrapper.className = 'chat-message assistant';
  wrapper.setAttribute('aria-label', t('loading_chat') || 'Thinking…');

  const bubble = document.createElement('div');
  bubble.className = 'chat-message-bubble';
  bubble.innerHTML = `<span style="color:var(--color-text-muted);font-style:italic">${t('loading_chat') || 'Thinking…'}</span>`;

  wrapper.appendChild(bubble);
  el.chatMessages.appendChild(wrapper);
  el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

/* ═══════════════════════════════════════════════════════════════════════════
   Reset
   ═══════════════════════════════════════════════════════════════════════════ */

function resetAll() {
  state.sessionId = null;
  state.analysisText = '';
  state.selectedFile = null;
  state.audioBlob = null;

  el.textInput.value = '';
  el.fileInput.value = '';
  el.filePreview.classList.add('hidden');
  el.filePreview.innerHTML = '';
  el.audioContainer.classList.add('hidden');
  el.chatMessages.innerHTML = '';
  el.chatInput.value = '';

  hideResults();
  hideError();
  switchTab('text');

  el.textInput.focus();
}

/* ═══════════════════════════════════════════════════════════════════════════
   Loading state
   ═══════════════════════════════════════════════════════════════════════════ */

function setLoading(active, message) {
  state.isLoading = active;
  el.loadingIndicator.classList.toggle('hidden', !active);
  el.btnAnalyze.disabled = active;
  if (message) el.loadingText.textContent = message;
}

/* ═══════════════════════════════════════════════════════════════════════════
   Error handling
   ═══════════════════════════════════════════════════════════════════════════ */

function showError(message) {
  el.errorMessage.textContent = message;
  el.errorBanner.classList.remove('hidden');
}

function hideError() {
  el.errorBanner.classList.add('hidden');
  el.errorMessage.textContent = '';
}

/* ═══════════════════════════════════════════════════════════════════════════
   Utilities
   ═══════════════════════════════════════════════════════════════════════════ */

function escHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/* ═══════════════════════════════════════════════════════════════════════════
   Bootstrap
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', init);
