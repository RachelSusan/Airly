// Major Indian cities (state capitals and large cities) with approximate city-centre
// coordinates, rounded to 2 decimals (~1 km). Used for the city picker, typeahead and for
// naming a GPS location after the nearest city.

export const COUNTRY = { code: "IN", name: "India" };

const RAW = [
  ["Agartala", "Tripura", 23.83, 91.29],
  ["Agra", "Uttar Pradesh", 27.18, 78.01],
  ["Ahmedabad", "Gujarat", 23.02, 72.57],
  ["Aizawl", "Mizoram", 23.73, 92.72],
  ["Amritsar", "Punjab", 31.63, 74.87],
  ["Bengaluru", "Karnataka", 12.97, 77.59],
  ["Bhopal", "Madhya Pradesh", 23.26, 77.41],
  ["Bhubaneswar", "Odisha", 20.3, 85.82],
  ["Chandigarh", "Chandigarh", 30.73, 76.78],
  ["Chennai", "Tamil Nadu", 13.08, 80.27],
  ["Chhatrapati Sambhajinagar", "Maharashtra", 19.88, 75.34],
  ["Coimbatore", "Tamil Nadu", 11.02, 76.96],
  ["Dehradun", "Uttarakhand", 30.32, 78.03],
  ["Delhi", "Delhi", 28.61, 77.21],
  ["Dhanbad", "Jharkhand", 23.8, 86.43],
  ["Faridabad", "Haryana", 28.41, 77.32],
  ["Gandhinagar", "Gujarat", 23.22, 72.65],
  ["Gangtok", "Sikkim", 27.33, 88.61],
  ["Ghaziabad", "Uttar Pradesh", 28.67, 77.45],
  ["Gurugram", "Haryana", 28.46, 77.03],
  ["Guwahati", "Assam", 26.14, 91.74],
  ["Gwalior", "Madhya Pradesh", 26.22, 78.18],
  ["Hyderabad", "Telangana", 17.39, 78.49],
  ["Imphal", "Manipur", 24.82, 93.94],
  ["Indore", "Madhya Pradesh", 22.72, 75.86],
  ["Itanagar", "Arunachal Pradesh", 27.08, 93.61],
  ["Jabalpur", "Madhya Pradesh", 23.18, 79.99],
  ["Jaipur", "Rajasthan", 26.91, 75.79],
  ["Jammu", "Jammu and Kashmir", 32.73, 74.86],
  ["Jamshedpur", "Jharkhand", 22.8, 86.2],
  ["Jodhpur", "Rajasthan", 26.24, 73.02],
  ["Kanpur", "Uttar Pradesh", 26.45, 80.33],
  ["Kochi", "Kerala", 9.93, 76.27],
  ["Kohima", "Nagaland", 25.67, 94.11],
  ["Kolkata", "West Bengal", 22.57, 88.36],
  ["Kota", "Rajasthan", 25.21, 75.86],
  ["Leh", "Ladakh", 34.15, 77.58],
  ["Lucknow", "Uttar Pradesh", 26.85, 80.95],
  ["Ludhiana", "Punjab", 30.9, 75.86],
  ["Madurai", "Tamil Nadu", 9.93, 78.12],
  ["Meerut", "Uttar Pradesh", 28.98, 77.71],
  ["Mumbai", "Maharashtra", 19.08, 72.88],
  ["Mysuru", "Karnataka", 12.3, 76.64],
  ["Nagpur", "Maharashtra", 21.15, 79.09],
  ["Nashik", "Maharashtra", 20.0, 73.79],
  ["Noida", "Uttar Pradesh", 28.54, 77.39],
  ["Panaji", "Goa", 15.49, 73.83],
  ["Patna", "Bihar", 25.59, 85.14],
  ["Prayagraj", "Uttar Pradesh", 25.44, 81.85],
  ["Puducherry", "Puducherry", 11.94, 79.81],
  ["Pune", "Maharashtra", 18.52, 73.86],
  ["Raipur", "Chhattisgarh", 21.25, 81.63],
  ["Ranchi", "Jharkhand", 23.34, 85.31],
  ["Shillong", "Meghalaya", 25.58, 91.89],
  ["Shimla", "Himachal Pradesh", 31.1, 77.17],
  ["Srinagar", "Jammu and Kashmir", 34.08, 74.8],
  ["Surat", "Gujarat", 21.17, 72.83],
  ["Thiruvananthapuram", "Kerala", 8.52, 76.94],
  ["Vadodara", "Gujarat", 22.31, 73.18],
  ["Varanasi", "Uttar Pradesh", 25.32, 82.97],
  ["Vijayawada", "Andhra Pradesh", 16.51, 80.65],
  ["Visakhapatnam", "Andhra Pradesh", 17.69, 83.22],
];

export const CITIES = RAW.map(([city, state, lat, lon]) => ({
  city,
  state,
  lat,
  lon,
  name: `${city}, ${state}, ${COUNTRY.name}`,
}));

/** Find a listed city by its full label or its city name (case-insensitive). */
export function findCity(text) {
  const q = text.trim().toLowerCase();
  return CITIES.find((c) => c.name.toLowerCase() === q || c.city.toLowerCase() === q) ?? null;
}

const NEAR_KM = 60;

/** Nearest listed city within ~60 km of a point, or null. */
export function nearestCity(lat, lon) {
  let best = null;
  for (const c of CITIES) {
    const km = distanceKm(lat, lon, c.lat, c.lon);
    if (km <= NEAR_KM && (!best || km < best.km)) best = { ...c, km };
  }
  return best;
}

function distanceKm(lat1, lon1, lat2, lon2) {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(a));
}
