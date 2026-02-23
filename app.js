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

    const lines = [];
    lines.push(`📝 ${data.title || 'Daily News Summary'}`);
    if (data.summary) lines.push('', data.summary);
    if (Array.isArray(data.headlines) && data.headlines.length) {
      lines.push('', '主なトピック:');
      for (const h of data.headlines) {
        lines.push(`- ${h.title}${h.source ? ` (${h.source})` : ''}`);
      }
    }
    entryContent.textContent = lines.join('\n');
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
