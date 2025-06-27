document.addEventListener('DOMContentLoaded', function() {
    const recommendBtn = document.getElementById('recommendBtn');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const errorDiv = document.getElementById('error');
    
    recommendBtn.addEventListener('click', async function() {
        const userPrompt = document.getElementById('userPrompt').value.trim();
        const location = document.getElementById('location').value.trim();
        const date = document.getElementById('date').value;
        
        if (!userPrompt || !location) {
            showError('Please fill in both the trip description and destination fields');
            return;
        }
        
        loadingDiv.classList.remove('hidden');
        resultsDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');
        
        try {
            const response = await fetch('/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    user_prompt: userPrompt,
                    location: location,
                    date: date || null
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'API request failed');
            }
            
            const data = await response.json();
            displayResults(data);
            
        } catch (error) {
            console.error('Error:', error);
            showError(error.message || 'Failed to get recommendations. Please try again.');
        } finally {
            loadingDiv.classList.add('hidden');
        }
    });
    
    function displayResults(data) {
        const recommendationsDiv = document.getElementById('recommendations');
        const weatherDiv = document.getElementById('weatherDetails');
        
        // Format recommendations
        recommendationsDiv.innerHTML = data.recommendations 
            ? data.recommendations.replace(/\n/g, '<br>') 
            : '<p>No recommendations generated</p>';
        
        // Format weather info
        weatherDiv.innerHTML = `
            <p><strong>Location:</strong> ${data.location}</p>
            <p><strong>Season:</strong> ${data.season}</p>
            ${
                data.weather.temperature !== 'unknown'
                ? `
                    <p><strong>Temperature:</strong> ${data.weather.temperature}°C (Feels like ${data.weather.feels_like}°C)</p>
                    <p><strong>Conditions:</strong> ${data.weather.conditions}</p>
                    <p><strong>Humidity:</strong> ${data.weather.humidity}%</p>
                    <p><strong>Wind Speed:</strong> ${data.weather.wind_speed} km/h</p>
                    ${data.weather.precipitation > 0 ? `<p><strong>Precipitation:</strong> ${data.weather.precipitation} mm</p>` : ''}
                  `
                : '<p>Weather data unavailable</p>'
            }
        `;
        
        resultsDiv.classList.remove('hidden');
    }
    
    function showError(message) {
        errorDiv.querySelector('.error-message').textContent = message;
        errorDiv.classList.remove('hidden');
    }
});