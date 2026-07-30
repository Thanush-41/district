const API_BASE_URL = window.API_BASE_URL || 'http://127.0.0.1:8001';

const PRIORITY_WEIGHT = { HIGH: 3, MEDIUM: 2, LOW: 1 };

const state = {
  restaurants: [],
  filter: 'all',
  sortKey: null,
  sortDir: 1, // 1 = ascending, -1 = descending
};

async function loadDashboard() {
  const statsResponse = await fetch(`${API_BASE_URL}/dashboard/stats`);
  const stats = await statsResponse.json();
  const restaurantsResponse = await fetch(`${API_BASE_URL}/restaurants`);
  state.restaurants = await restaurantsResponse.json();

  document.getElementById('stats').innerHTML = `
    <div class="card"><h3>Total</h3><p>${stats.total_restaurants}</p></div>
    <div class="card"><h3>New Restaurants</h3><p>${stats.new_restaurants ?? 0}</p></div>
    <div class="card"><h3>Not Onboarded</h3><p>${stats.not_onboarded}</p></div>
    <div class="card"><h3>Running Ads</h3><p>${stats.running_ads}</p></div>
    <div class="card"><h3>High Priority</h3><p>${stats.high_priority_leads}</p></div>
  `;

  renderTable();
}

function getSortValue(restaurant, key) {
  switch (key) {
    case 'name':
      return (restaurant.google?.name || '').toLowerCase();
    case 'isNew':
      return restaurant.isNew ? 1 : 0;
    case 'priority':
      return PRIORITY_WEIGHT[restaurant.lead?.priority] || 0;
    case 'district':
      return restaurant.district?.onboarded ? 1 : 0;
    case 'ads':
      return restaurant.metaAds?.runningAds ? 1 : 0;
    case 'swiggy':
      return restaurant.swiggy?.available ? 1 : 0;
    case 'zomato':
      return restaurant.zomato?.listed ? 1 : 0;
    case 'important':
      return restaurant.lead?.important ? 1 : 0;
    case 'read':
      return restaurant.lead?.read ? 1 : 0;
    case 'saved':
      return restaurant.lead?.saved ? 1 : 0;
    default:
      return 0;
  }
}

// District/Ads/Swiggy/Zomato all default to "No" for every newly discovered
// restaurant until someone manually verifies it (we can't automate checking
// those platforms - see their Terms of Service). Rendering plain "No" for an
// unverified restaurant looks indistinguishable from a confirmed "No", so we
// show a neutral "pending" state instead until it's actually been checked.
function verifiedCell(isChecked, isTrue) {
  if (!isChecked) {
    return '<span class="pending" title="Not verified yet">\u2014</span>';
  }
  return isTrue ? 'Yes' : 'No';
}

function applyFilter(list) {
  switch (state.filter) {
    case 'notOnboarded':
      return list.filter((r) => !r.district?.onboarded);
    case 'runningAds':
      return list.filter((r) => r.metaAds?.runningAds);
    case 'important':
      return list.filter((r) => r.lead?.important);
    case 'unread':
      return list.filter((r) => !r.lead?.read);
    case 'saved':
      return list.filter((r) => r.lead?.saved);
    default:
      return list;
  }
}

function applySort(list) {
  if (!state.sortKey) {
    return list;
  }
  const sorted = [...list].sort((a, b) => {
    const va = getSortValue(a, state.sortKey);
    const vb = getSortValue(b, state.sortKey);
    if (va < vb) return -1 * state.sortDir;
    if (va > vb) return 1 * state.sortDir;
    return 0;
  });
  return sorted;
}

function renderTable() {
  const visible = applySort(applyFilter(state.restaurants));

  const rows = visible.map((restaurant) => `
    <tr>
      <td>${restaurant.google?.name || 'Unnamed'}</td>
      <td>${restaurant.isNew ? '<span class="badge badge-new">NEW</span>' : ''}</td>
      <td><span class="badge badge-priority-${(restaurant.lead?.priority || 'LOW').toLowerCase()}">${restaurant.lead?.priority || 'LOW'}</span></td>
      <td>${verifiedCell(restaurant.district?.checked, restaurant.district?.onboarded)}</td>
      <td>${verifiedCell(Boolean(restaurant.metaAds?.lastSeen), restaurant.metaAds?.runningAds)}</td>
      <td>${verifiedCell(Boolean(restaurant.swiggy?.lastChecked), restaurant.swiggy?.available)}</td>
      <td>${verifiedCell(Boolean(restaurant.zomato?.lastChecked), restaurant.zomato?.listed)}</td>
      <td><input type="checkbox" class="flag-toggle" data-id="${restaurant._id}" data-field="important" ${restaurant.lead?.important ? 'checked' : ''} /></td>
      <td><input type="checkbox" class="flag-toggle" data-id="${restaurant._id}" data-field="read" ${restaurant.lead?.read ? 'checked' : ''} /></td>
      <td><button class="cart-toggle ${restaurant.lead?.saved ? 'in-cart' : ''}" data-id="${restaurant._id}" title="${restaurant.lead?.saved ? 'Remove from cart' : 'Add to cart'}">${restaurant.lead?.saved ? '✅' : '🛒'}</button></td>
      <td>${buildMapsLink(restaurant)}</td>
    </tr>
  `).join('');

  document.getElementById('restaurant-table').innerHTML = rows || '<tr><td colspan="11" class="empty-row">No restaurants match this filter.</td></tr>';
  updateSortIndicators();
  updateCartCount();
}

function updateCartCount() {
  const count = state.restaurants.filter((r) => r.lead?.saved).length;
  document.getElementById('cart-count').textContent = count;
}

function updateSortIndicators() {
  document.querySelectorAll('th[data-sort-key]').forEach((th) => {
    th.classList.remove('sort-asc', 'sort-desc');
    if (th.dataset.sortKey === state.sortKey) {
      th.classList.add(state.sortDir === 1 ? 'sort-asc' : 'sort-desc');
    }
  });
}

async function toggleFlag(restaurantId, field, value) {
  const restaurant = state.restaurants.find((r) => r._id === restaurantId);
  if (restaurant) {
    restaurant.lead = restaurant.lead || {};
    restaurant.lead[field] = value; // optimistic update
  }
  try {
    await fetch(`${API_BASE_URL}/restaurants/${encodeURIComponent(restaurantId)}/flags`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [field]: value }),
    });
  } catch (error) {
    console.error(`Failed to update ${field} for ${restaurantId}`, error);
  }
}

// A real Google place_id (e.g. "ChIJ...") reliably pins the exact place. Our
// own seed/test data uses placeholder ids like "place-1" which are not real
// Google place_ids, so linking with query_place_id for those would just show
// a "can't find this place" / generic search result instead of a pin.
function isRealGooglePlaceId(placeId) {
  return Boolean(placeId) && !/^(place|restaurant)-/i.test(placeId);
}

function buildMapsLink(restaurant) {
  const placeId = restaurant.google?.placeId;
  const name = restaurant.google?.name || restaurant.google?.address;

  if (isRealGooglePlaceId(placeId)) {
    // Documented Google Maps "place" URL scheme opens the exact pinned
    // location directly, rather than a list of search suggestions.
    // https://developers.google.com/maps/documentation/urls/get-started
    const url = `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(placeId)}`;
    return `<a class="map-pin" href="${url}" target="_blank" rel="noopener noreferrer" title="Open exact place in Google Maps">📍</a>`;
  }

  if (!name) {
    return '';
  }
  // Fallback for records without a real place_id (e.g. seed data): a plain
  // text search, which may show suggestions since there's no exact id to pin.
  const url = `https://www.google.com/maps/search/?${new URLSearchParams({ api: '1', query: name }).toString()}`;
  return `<a class="map-pin" href="${url}" target="_blank" rel="noopener noreferrer" title="Search this place in Google Maps">📍</a>`;
}

async function searchNearby() {
  const input = document.getElementById('place-input');
  const status = document.getElementById('search-status');
  const place = input.value.trim();
  if (!place) {
    status.textContent = 'Enter a place first.';
    return;
  }

  status.textContent = 'Searching within 60km...';
  try {
    const response = await fetch(`${API_BASE_URL}/search-nearby`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ place, radius_km: 60 }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Request failed (${response.status})`);
    }
    const result = await response.json();
    status.textContent = `Found ${result.created + result.updated} places (${result.created} new) near "${place}".`;
    await loadDashboard();
  } catch (error) {
    status.textContent = `Search failed: ${error.message}`;
  }
}

document.getElementById('search-btn').addEventListener('click', searchNearby);
document.getElementById('place-input').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    searchNearby();
  }
});

// Sortable column headers.
document.querySelectorAll('th[data-sort-key]').forEach((th) => {
  th.addEventListener('click', () => {
    const key = th.dataset.sortKey;
    if (state.sortKey === key) {
      state.sortDir *= -1;
    } else {
      state.sortKey = key;
      state.sortDir = 1;
    }
    renderTable();
  });
});

// Quick filter / sort toolbar.
document.getElementById('filter-bar').addEventListener('click', (event) => {
  const button = event.target.closest('button');
  if (!button) return;

  if (button.dataset.action === 'reset') {
    state.filter = 'all';
    state.sortKey = null;
    state.sortDir = 1;
  } else if (button.dataset.sort) {
    state.sortKey = button.dataset.sort;
    state.sortDir = -1; // "X First" buttons mean descending by that value
  } else if (button.dataset.filter) {
    state.filter = button.dataset.filter;
  }

  document.querySelectorAll('#filter-bar button').forEach((btn) => btn.classList.remove('active'));
  button.classList.add('active');
  renderTable();
});

// Delegate checkbox changes for the Important/Read columns.
document.getElementById('restaurant-table').addEventListener('change', (event) => {
  const target = event.target;
  if (target.classList.contains('flag-toggle')) {
    toggleFlag(target.dataset.id, target.dataset.field, target.checked);
  }
});

// Delegate Add to Cart / Remove from Cart button clicks.
document.getElementById('restaurant-table').addEventListener('click', (event) => {
  const button = event.target.closest('.cart-toggle');
  if (!button) return;
  const restaurant = state.restaurants.find((r) => r._id === button.dataset.id);
  const nextValue = !(restaurant?.lead?.saved);
  toggleFlag(button.dataset.id, 'saved', nextValue).then(renderTable);
});

loadDashboard();
