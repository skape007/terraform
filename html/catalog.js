/* Minimal catalog viewer script.
   Adjust CATALOG_URL if you host catalog.json elsewhere (CloudFront, API Gateway, etc.)
*/
const CATALOG_URL = "jobs/catalog.json"; // Relative path (same bucket) or full URL.

let catalog = [];
let sortState = { column: null, direction: null };

function setError(msg) {
  const box = document.getElementById('errorBox');
  if (!msg) {
    box.style.display='none';
    box.textContent='';
  } else {
    box.style.display='block';
    box.textContent=msg;
  }
}

function showLoader(on) {
  document.getElementById('loader').style.display = on ? 'inline' : 'none';
}

async function loadCatalog() {
  setError(null);
  showLoader(true);
  try {
    const resp = await fetch(CATALOG_URL, { cache:"no-store" });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    catalog = data.job_groups || [];
    document.getElementById('lastFetch').textContent = new Date().toLocaleString();
    renderTable();
  } catch (e) {
    setError("Failed to load catalog: " + e.message);
  } finally {
    showLoader(false);
  }
}

function applyFilters(raw) {
  const enabledF = document.getElementById('enabledFilter').value;
  const intervalF = document.getElementById('intervalFilter').value;
  const searchTerm = document.getElementById('searchBox').value.trim().toLowerCase();
  return raw.filter(j => {
    if (enabledF === 'enabled' && !j.enabled_any) return false;
    if (enabledF === 'disabled' && j.enabled_any) return false;
    if (intervalF !== 'any' && String(j.interval_days) !== intervalF) return false;
    if (searchTerm) {
      const hay = (j.group_id + ' ' + (j.description || '')).toLowerCase();
      if (!hay.includes(searchTerm)) return false;
    }
    return true;
  });
}

function sortData(arr) {
  const { column, direction } = sortState;
  if (!column || !direction) return arr;
  const sorted = [...arr];
  sorted.sort((a,b) => {
    let av = a[column], bv = b[column];
    if (Array.isArray(av)) av = av.join(',');
    if (Array.isArray(bv)) bv = bv.join(',');
    if (typeof av === 'string') av = av.toLowerCase();
    if (typeof bv === 'string') bv = bv.toLowerCase();
    if (av < bv) return direction === 'asc' ? -1 : 1;
    if (av > bv) return direction === 'asc' ? 1 : -1;
    return 0;
  });
  return sorted;
}

function renderTable() {
  const filtered = applyFilters(catalog);
  const data = sortData(filtered);
  document.getElementById('groupCount').textContent = `Visible groups: ${data.length} / Total: ${catalog.length}`;
  const container = document.getElementById('tableContainer');

  if (!data.length) {
    container.innerHTML = "<div class='empty'>No jobs match filters.</div>";
    return;
  }

  const cols = [
    { key:'group_id', label:'Group ID' },
    { key:'weekdays', label:'Weekdays' },
    { key:'hours', label:'Hours' },
    { key:'interval_days', label:'Interval' },
    { key:'anchor_date', label:'Anchor Date' },
    { key:'enabled_any', label:'Enabled?' },
    { key:'description', label:'Description' }
  ];

  let thead = "<thead><tr>";
  for (const c of cols) {
    const cls = (sortState.column === c.key) ? 'sort-' + sortState.direction : '';
    thead += `<th data-col="${c.key}" class="${cls}">${c.label}</th>`;
  }
  thead += "</tr></thead>";

  let tbody = "<tbody>";
  data.forEach(row => {
    tbody += "<tr>";
    cols.forEach(c => {
      let val = row[c.key];
      if (c.key === 'enabled_any') {
        val = `<span class="badge ${val ? '' : 'off'}">${val ? 'ENABLED' : 'DISABLED'}</span>`;
      } else if (Array.isArray(val)) {
        val = val.map(x => `<span class="pill">${x}</span>`).join(' ');
      } else if (val === null || val === undefined || val === '') {
        val = "<span style='color:#999;'>—</span>";
      }
      tbody += `<td>${val}</td>`;
    });
    tbody += "</tr>";
  });
  tbody += "</tbody>";

  container.innerHTML = `<table>${thead}${tbody}</table>`;

  container.querySelectorAll('th[data-col]').forEach(th => {
    th.onclick = () => {
      const col = th.getAttribute('data-col');
      if (sortState.column === col) {
        sortState.direction = sortState.direction === 'asc' ? 'desc' :
                              (sortState.direction === 'desc' ? null : 'asc');
        if (!sortState.direction) sortState.column = null;
      } else {
        sortState.column = col;
        sortState.direction = 'asc';
      }
      renderTable();
    };
  });
}

document.getElementById('refreshBtn').onclick = loadCatalog;
document.getElementById('enabledFilter').onchange = renderTable;
document.getElementById('intervalFilter').onchange = renderTable;
document.getElementById('searchBox').oninput = renderTable;

loadCatalog();