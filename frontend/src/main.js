import axios from 'axios';

document.getElementById('getCities').addEventListener('click', async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/cities');
    const cities = response.data;
    console.log(response);
    const citiesDiv = document.getElementById('cities');
    citiesDiv.innerHTML = '';

    // Check if cities is an object, and display its entries
    if (typeof cities === 'object' && cities !== null) {
      for (const [key, value] of Object.entries(cities)) {
        const cityElement = document.createElement('div');
        cityElement.textContent = `${key}: ${value}`;
        citiesDiv.appendChild(cityElement);
        console.log(`${key}: ${value}`);
      }
    }
    // If cities is an array, iterate through the array
    else if (Array.isArray(cities)) {
      cities.forEach(city => {
        const cityElement = document.createElement('div');

        // If city is an object, stringify it
        if (typeof city === 'object' && city !== null) {
          cityElement.textContent = JSON.stringify(city);
        } else {
          cityElement.textContent = city;
        }

        citiesDiv.appendChild(cityElement);
      });
    }
    // If cities is something else (like a string), just display it
    else {
      const cityElement = document.createElement('div');
      cityElement.textContent = cities;
      citiesDiv.appendChild(cityElement);
    }
  } catch (error) {
    console.error('Error fetching cities:', error);
    const citiesDiv = document.getElementById('cities');
    citiesDiv.innerHTML = `<div class="error">Error fetching cities: ${error.message}</div>`;
  }
});

document.getElementById('clear').addEventListener('click', () => {
  document.getElementById('cities').innerHTML = '';
});