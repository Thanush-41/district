async function loadDashboard() {
  const statsResponse = await fetch('http://127.0.0.1:8000/dashboard/stats');
  const stats = await statsResponse.json();
  const restaurantsResponse = await fetch('http://127.0.0.1:8000/restaurants');
  const restaurants = await restaurantsResponse.json();

  document.getElementById('stats').innerHTML = `
    <div class="card"><h3>Total</h3><p>${stats.total_restaurants}</p></div>
    <div class="card"><h3>Not Onboarded</h3><p>${stats.not_onboarded}</p></div>
    <div class="card"><h3>Running Ads</h3><p>${stats.running_ads}</p></div>
    <div class="card"><h3>High Priority</h3><p>${stats.high_priority_leads}</p></div>
  `;

  const rows = restaurants.map((restaurant) => `
    <tr>
      <td>${restaurant.google?.name || 'Unnamed'}</td>
      <td>${restaurant.lead?.priority || 'LOW'}</td>
      <td>${restaurant.district?.onboarded ? 'Yes' : 'No'}</td>
      <td>${restaurant.metaAds?.runningAds ? 'Yes' : 'No'}</td>
    </tr>
  `).join('');

  document.getElementById('restaurant-table').innerHTML = rows;
}

loadDashboard();
