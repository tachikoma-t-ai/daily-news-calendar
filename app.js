let current = new Date();
let selectedDate = null;
let indexMap = {};

const monthLabel = document.getElementById('monthLabel');
const grid = document.getElementById('calendarGrid');
const entryDate = document.getElementById('entryDate');
const entryContent = document.getElementById('entryContent');

document.getElementById('prevMonth').addEventListener('click', () => {
  current.setMonth(current.getMonth() - 1);
  renderCalendar();
});

document.getElementById('nextMonth').addEventListener('click', () => {
  current.setMonth(current.getMonth() + 1);
  renderCalendar();
});

async function loadIndex() {
  try {
    const res = await fetch('data/index.json?_=' + Date.now());
    if (!res.ok) throw new Error('index not found');
    const data = await res.json();
    indexMap = data.entries || {};
  } catch (e) {
    indexMap = {};
  }
}

function renderCalendar() {
  const y = current.getFullYear();
  const m = current.getMonth();
  monthLabel.textContent = `${y}年 ${m + 1}月`;

  const firstDay = new Date(y, m, 1).getDay();
  const daysInMonth = new Date(y, m + 1, 0).getDate();

  grid.innerHTML = '';

  for (let i = 0; i < firstDay; i++) {
    const d = document.createElement('div');
    d.className = 'day empty';
    grid.appendChild(d);
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const cell = document.createElement('button');
    cell.className = 'day';
    const date = `${y}-${String(m + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

    const has = Boolean(indexMap[date]);
    if (has) cell.classList.add('has-entry');
    if (selectedDate === date) cell.classList.add('selected');

    cell.innerHTML = `${day}${has ? '<span class="dot"></span>' : ''}`;
    cell.addEventListener('click', () => showEntry(date));
    grid.appendChild(cell);
  }
}

async function showEntry(date) {
  selectedDate = date;
  renderCalendar();

  entryDate.textContent = date;
  const path = indexMap[date];
  if (!path) {
    entryContent.textContent = 'この日のエントリはまだありません。';
    return;
  }

  try {
    const res = await fetch(path + '?_=' + Date.now());
    const data = await res.json();

    const esc = (s = '') => String(s)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');

    let html = `<h4>📝 ${esc(data.title || 'Daily News Summary')}</h4>`;
    if (data.summary) html += `<p>${esc(data.summary)}</p>`;

    if (Array.isArray(data.top3) && data.top3.length) {
      html += '<h5>🌟 今日の注目3点</h5><ul>';
      for (const t of data.top3.slice(0, 3)) {
        html += `<li>${esc(t)}</li>`;
      }
      html += '</ul>';
    }

    if (Array.isArray(data.sections) && data.sections.length) {
      for (const sec of data.sections) {
        html += `<h5>■ ${esc(sec.name || 'カテゴリ')}</h5>`;
        const items = Array.isArray(sec.items) ? sec.items : [];
        if (!items.length) {
          html += '<p><small>項目なし</small></p>';
          continue;
        }
        html += '<ul>';
        for (const i of items) {
          const title = esc(i.title || 'untitled');
          const link = i.link && /^https?:\/\//.test(i.link) ? i.link : null;
          const source = i.source ? ` <small>(${esc(i.source)})</small>` : '';
          const lines = Array.isArray(i.summaryLines) ? i.summaryLines : [];
          const why = i.whyImportant ? `<br><small><b>なぜ重要か:</b> ${esc(i.whyImportant)}</small>` : '';
          const summary = lines.length
            ? `<br><small>${lines.map(esc).join('<br>')}</small>`
            : '';
          html += `<li>${link ? `<a href="${link}" target="_blank" rel="noopener noreferrer">${title}</a>` : title}${source}${summary}${why}</li>`;
        }
        html += '</ul>';
      }
    } else if (Array.isArray(data.headlines) && data.headlines.length) {
      html += '<h5>主なトピック</h5><ul>';
      for (const h of data.headlines) {
        const title = esc(h.title || 'untitled');
        const source = h.source ? ` <small>(${esc(h.source)})</small>` : '';
        const link = h.link && /^https?:\/\//.test(h.link) ? h.link : null;
        html += `<li>${link ? `<a href="${link}" target="_blank" rel="noopener noreferrer">${title}</a>` : title}${source}</li>`;
      }
      html += '</ul>';
    }

    entryContent.innerHTML = html;
  } catch (e) {
    entryContent.textContent = 'エントリの読み込みに失敗しました。';
  }
}

(async function init() {
  await loadIndex();
  renderCalendar();

  const today = new Date();
  const t = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  if (indexMap[t]) showEntry(t);
})();
