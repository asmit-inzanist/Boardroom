/* =============================================================
   BOARDROOM — Investment Research Terminal
   app.js — Live report state controller
   ============================================================= */

(function () {
  const API_BASE_URL = 'http://localhost:8000/report/';
  const FOLLOW_UP_URL = 'http://localhost:8000/follow-up';
  const loadingMessages = [
    'Fetching company data...',
    'Running independent analysis...',
    'Resolving disagreements...',
    'Finalizing report...'
  ];

  const landingStage = document.getElementById('landing-stage');
  const dossierStage = document.getElementById('dossier-stage');
  const dockedBar = document.getElementById('docked-search-bar');
  const heroInput = document.getElementById('hero-search-input');
  const heroSubmit = document.getElementById('hero-submit-btn');
  const dockedInput = document.getElementById('docked-search-input');
  const dockedSubmit = document.getElementById('docked-submit-btn');
  const resetBtn = document.getElementById('reset-to-landing-btn');
  const toggleStateBtn = document.getElementById('toggle-state-btn');
  const stateBtnText = document.getElementById('state-btn-text');
  const reportPanel = document.getElementById('report-panel');
  const reportContent = document.getElementById('report-content');
  const queryBubble = document.getElementById('query-bubble');
  const suggestionChips = document.querySelectorAll('.suggestion-chip');
  const followUpBtns = document.querySelectorAll('.follow-up-btn');
  const howItWorks = document.getElementById('how-it-works-toggle');

  let isDossierOpen = false;
  let activeRequest = 0;
  let loadingTimer;
  let currentReport = null;
  let followUpHistory = [];

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[character]));
  }

  function setDockVisibility(visible) {
    if (!dockedBar) return;
    dockedBar.classList.toggle('opacity-0', !visible);
    dockedBar.classList.toggle('opacity-100', visible);
    dockedBar.classList.toggle('pointer-events-none', !visible);
  }

  function showLoading(queryText) {
    let messageIndex = 0;
    clearInterval(loadingTimer);
    queryBubble.textContent = queryText;
    queryBubble.classList.add('is-visible');
    reportContent.innerHTML = `
      <div class="report-loading">
        <div class="report-loading__inner">
          <div class="report-loading__mark" aria-hidden="true"></div>
          <p class="report-eyebrow">SYNTHESIZING RESEARCH REPORT</p>
          <p class="report-loading__status" id="loading-status">${loadingMessages[0]}</p>
          <p class="text-[#9E9C96] mt-4">This analysis can take a few minutes while independent agents review the company.</p>
        </div>
      </div>`;
    loadingTimer = setInterval(() => {
      messageIndex = (messageIndex + 1) % loadingMessages.length;
      const status = document.getElementById('loading-status');
      if (status) status.textContent = loadingMessages[messageIndex];
    }, 12000);
  }

  function showError(message) {
    reportContent.innerHTML = `
      <div class="report-error">
        <div>
          <p class="report-eyebrow">REPORT UNAVAILABLE</p>
          <h2 class="text-2xl font-medium mt-2">We couldn't complete this research request.</h2>
          <p>${escapeHtml(message)}</p>
        </div>
      </div>`;
  }

  function formatValue(value) {
    if (value === null || value === undefined || value === '') return 'Not provided';
    if (typeof value === 'number') {
      if (Math.abs(value) < 1 && value !== 0) return `${(value * 100).toFixed(1)}%`;
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
    return String(value);
  }

  function renderMetricTable(title, values) {
    if (!values || typeof values !== 'object') return '';
    const rows = Object.entries(values)
      .filter(([, value]) => value !== null && value !== undefined && typeof value !== 'object')
      .map(([key, value]) => `<tr><td>${escapeHtml(key.replaceAll('_', ' '))}</td><td>${escapeHtml(formatValue(value))}</td></tr>`)
      .join('');
    if (!rows) return '';
    return `<section class="report-section report-card">
      <h3>${escapeHtml(title)}</h3>
      <table class="metric-table"><tbody>${rows}</tbody></table>
    </section>`;
  }

  function renderObjectSections(title, values) {
    if (!values || typeof values !== 'object') return '';
    const sections = Object.entries(values).map(([key, value]) => {
      if (!value || typeof value !== 'object' || Array.isArray(value)) return '';
      return renderMetricTable(key, value);
    }).join('');
    return sections ? `<div class="report-subgroup"><h3>${escapeHtml(title)}</h3>${sections}</div>` : '';
  }

  function renderReport(report) {
    const recommendations = ['aggressive', 'moderate', 'conservative'];
    const rows = recommendations.map((tier) => {
      const recommendation = report.recommendation?.[tier] || {};
      return `<tr>
        <td><strong>${escapeHtml(tier)}</strong></td>
        <td>${escapeHtml(recommendation.action || 'Not provided')}</td>
        <td>${escapeHtml(recommendation.price_range || 'Not provided')}</td>
      </tr>`;
    }).join('');
    const financialHealth = report.financial_health || {};
    const risks = Array.isArray(report.risks) ? report.risks : [];
    const scenarios = report.scenarios || {};
    const scenarioCards = ['bull', 'base', 'bear'].map((name) => {
      const scenario = scenarios[name] || {};
      const conditions = Array.isArray(scenario.conditions) ? scenario.conditions : [];
      return `<article class="scenario-card">
        <h4>${escapeHtml(name)} case</h4>
        <p>${escapeHtml(scenario.case || 'Not provided')}</p>
        ${conditions.length ? `<ul>${conditions.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
      </article>`;
    }).join('');

    reportContent.innerHTML = `
      <div class="report-header">
        <div>
          <p class="report-eyebrow">CONFIDENTIAL INSTITUTIONAL RESEARCH REPORT</p>
          <h1 class="report-title">${escapeHtml(report.company_name || report.ticker)} (${escapeHtml(report.ticker)}) — Consensus Analysis</h1>
        </div>
        <div class="report-score">
          <span class="report-label">COMPOSITE SCORE</span>
          <span class="report-score__value">${escapeHtml(report.composite_score)}</span>
        </div>
      </div>
      <div class="report-verdict">${escapeHtml(report.verdict)}</div>
      <section class="report-section">
        <h3>One-line conclusion</h3>
        <p>${escapeHtml(report.one_line_conclusion)}</p>
      </section>
      <section class="report-section">
        <h3>Disagreement summary</h3>
        <p>${escapeHtml(report.disagreement_summary)}</p>
      </section>
      <section class="report-section">
        <h3>Financial health</h3>
        <div class="report-grid">
          ${renderObjectSections('Financial metrics', financialHealth)}
        </div>
      </section>
      <section class="report-section">
        <h3>Valuation and consensus</h3>
        <div class="report-grid">
          ${renderMetricTable('Valuation', report.valuation)}
          ${renderMetricTable('Analyst consensus', report.analyst_consensus)}
          ${renderMetricTable('Target price', report.target_price)}
        </div>
      </section>
      <section class="report-section">
        <h3>Key risks</h3>
        ${risks.length ? `<ul class="risk-list">${risks.map((risk) => `<li>${escapeHtml(risk)}</li>`).join('')}</ul>` : '<p>Not provided</p>'}
      </section>
      <section class="report-section">
        <h3>Scenario analysis</h3>
        <div class="scenario-grid">${scenarioCards}</div>
      </section>
      <section class="report-section">
        <h3>Risk-tier recommendations</h3>
        <div class="overflow-x-auto">
          <table class="recommendation-table">
            <thead><tr><th>Profile</th><th>Action</th><th>Price range</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </section>`;
  }

  async function fetchReport(queryText) {
    const requestId = ++activeRequest;
    showLoading(queryText);
    setDockVisibility(false);

    try {
      const response = await fetch(`${API_BASE_URL}${encodeURIComponent(queryText)}`);
      if (!response.ok) {
        throw new Error(`The research service returned HTTP ${response.status}.`);
      }
      const report = await response.json();
      if (requestId !== activeRequest) return;
      currentReport = report;
      followUpHistory = [];
      renderFollowUpMessages();
      renderReport(report);
      window.scrollTo({ top: reportPanel.getBoundingClientRect().top + window.scrollY - 96, behavior: 'smooth' });
      setDockVisibility(true);
    } catch (error) {
      if (requestId !== activeRequest) return;
      showError(error instanceof Error ? error.message : 'Please try again.');
      setDockVisibility(true);
    } finally {
      if (requestId === activeRequest) clearInterval(loadingTimer);
    }
  }

  function openDossier(queryText) {
    const query = queryText.trim();
    if (!query) return;
    if (dockedInput) dockedInput.value = query;
    if (isDossierOpen) {
      fetchReport(query);
      return;
    }
    isDossierOpen = true;
    landingStage.classList.add('opacity-0', '-translate-y-8');
    setTimeout(() => {
      landingStage.classList.add('hidden');
      dossierStage.classList.remove('hidden');
      setTimeout(() => dossierStage.classList.remove('opacity-0', 'translate-y-6'), 50);
      if (stateBtnText) stateBtnText.textContent = 'Back to Blank Stage';
      fetchReport(query);
    }, 350);
  }

  function submitInput(input) {
    const query = input?.value.trim();
    if (query) openDossier(query);
  }

  function renderFollowUpMessages(shouldScroll = false) {
    const messages = document.getElementById('follow-up-messages');
    if (!messages) return;
    messages.innerHTML = followUpHistory.map((message) => `
      <div class="follow-up-message follow-up-message--${message.role}">
        <span class="follow-up-message__label">${message.role === 'user' ? 'You' : 'Boardroom'}</span>
        <p>${escapeHtml(message.content)}</p>
      </div>
    `).join('');
    if (shouldScroll) {
      requestAnimationFrame(() => {
        messages.scrollTop = messages.scrollHeight;
      });
    }
  }

  async function submitFollowUp() {
    const question = dockedInput?.value.trim();
    if (!question || !currentReport?.ticker) return;
    dockedInput.value = '';
    followUpHistory.push({ role: 'user', content: question });
    renderFollowUpMessages(true);
    dockedSubmit.disabled = true;
    dockedInput.disabled = true;

    try {
      const response = await fetch(FOLLOW_UP_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: currentReport.ticker,
          question,
          history: followUpHistory.slice(-8)
        })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `The research service returned HTTP ${response.status}.`);
      followUpHistory.push({ role: 'assistant', content: payload.answer });
    } catch (error) {
      followUpHistory.push({
        role: 'assistant',
        content: error instanceof Error ? error.message : 'Please try again.'
      });
    } finally {
      dockedSubmit.disabled = false;
      dockedInput.disabled = false;
      dockedInput.focus();
      renderFollowUpMessages(true);
    }
  }

  function returnToLanding() {
    activeRequest += 1;
    clearInterval(loadingTimer);
    isDossierOpen = false;
    currentReport = null;
    followUpHistory = [];
    dossierStage.classList.add('opacity-0', 'translate-y-6');
    queryBubble.classList.remove('is-visible');
    setDockVisibility(false);
    setTimeout(() => {
      dossierStage.classList.add('hidden');
      landingStage.classList.remove('hidden');
      setTimeout(() => landingStage.classList.remove('opacity-0', '-translate-y-8'), 50);
      if (stateBtnText) stateBtnText.textContent = 'Quick Switch: TSLA Memo';
      if (heroInput) heroInput.value = '';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 350);
  }

  heroSubmit?.addEventListener('click', () => submitInput(heroInput));
  heroInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') submitInput(heroInput);
  });
  dockedSubmit?.addEventListener('click', submitFollowUp);
  dockedInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') submitFollowUp();
  });
  suggestionChips.forEach((chip) => chip.addEventListener('click', () => openDossier(chip.dataset.query || '')));
  followUpBtns.forEach((button) => button.addEventListener('click', () => {
    dockedInput.value = button.innerText.trim();
    dockedInput.focus();
  }));
  resetBtn?.addEventListener('click', returnToLanding);
  toggleStateBtn?.addEventListener('click', () => {
    isDossierOpen ? returnToLanding() : openDossier('TSLA');
  });
  howItWorks?.addEventListener('click', () => openDossier('PLTR'));
})();
