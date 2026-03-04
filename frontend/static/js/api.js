/**
 * SalesCast AI — API Helper
 * Central JS utility for all backend calls
 */

const API = {
  BASE: '',

  async get(path) {
    const res = await fetch(this.BASE + path);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async post(path, body) {
    const res = await fetch(this.BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async upload(path, formData) {
    const res = await fetch(this.BASE + path, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async delete(path) {
    const res = await fetch(this.BASE + path, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async put(path, body) {
    const res = await fetch(this.BASE + path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};

// UI Helpers
function showAlert(containerId, message, type = 'success') {
  const icons = { success: '✓', error: '✗', warning: '⚠' };
  document.getElementById(containerId).innerHTML = `
    <div class="alert alert-${type}">
      <span>${icons[type]}</span>
      <span>${message}</span>
    </div>
  `;
  setTimeout(() => {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = '';
  }, 5000);
}

function formatCurrency(val) {
  if (val >= 1e6) return '₹' + (val / 1e6).toFixed(2) + 'M';
  if (val >= 1e3) return '₹' + (val / 1e3).toFixed(1) + 'K';
  return '₹' + val.toFixed(0);
}

function formatNumber(val) {
  return new Intl.NumberFormat('en-IN').format(Math.round(val));
}

function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (loading) {
    btn.dataset.original = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span> Processing...';
    btn.disabled = true;
  } else {
    btn.textContent = btn.dataset.original || 'Submit';
    btn.disabled = false;
  }
}
