document.addEventListener('DOMContentLoaded', function() {
    const recommendBtn = document.getElementById('recommendBtn');
    const loadingDiv = document.getElementById('loading');
    const resultsDiv = document.getElementById('results');
    const errorDiv = document.getElementById('error');
    
    recommendBtn.addEventListener('click', async function() {
        const userPrompt = document.getElementById('userPrompt').value.trim();
        
        if (!userPrompt) {
            showError('Please describe what you need');
            return;
        }
        
        loadingDiv.classList.remove('hidden');
        resultsDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');
        
        try {
            const response = await fetch('/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_prompt: userPrompt
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get recommendations');
            }
            
            const data = await response.json();
            displayResults(data);
            
        } catch (error) {
            showError(error.message);
        } finally {
            loadingDiv.classList.add('hidden');
        }
    });
    
    function displayResults(data) {
        // Display text recommendations
        const textRecsDiv = document.getElementById('textRecommendations');
        textRecsDiv.innerHTML = data.text_recommendations 
            ? data.text_recommendations.replace(/\n/g, '<br>') 
            : '<p>No recommendations generated</p>';
        
        // Display products
        const productsGrid = document.getElementById('productsGrid');
        productsGrid.innerHTML = '';
        
        if (data.products && data.products.length > 0) {
            data.products.forEach(product => {
                const productCard = document.createElement('div');
                productCard.className = 'product-card';
                productCard.innerHTML = `
                    <div class="product-image-container">
                        <img src="${product.thumbnail}" alt="${product.title}" class="product-image" onerror="this.src='/static/no-image.png'">
                    </div>
                    <div class="product-details">
                        <h3 class="product-title">${product.title}</h3>
                        <div class="product-brand">Brand: ${product.brand}</div>
                        <div class="product-price">${product.price}</div>
                        <div class="product-stock">Stock: ${product.stock}</div>
                        <div class="product-rating">
                            ${'★'.repeat(Math.round(product.rating))}${'☆'.repeat(5 - Math.round(product.rating))} 
                            (${product.rating.toFixed(1)})
                        </div>
                        <p class="product-description">${product.description}</p>
                    </div>
                `;
                productsGrid.appendChild(productCard);
            });
        } else {
            productsGrid.innerHTML = '<p class="no-products">No product details found</p>';
        }
        
        resultsDiv.classList.remove('hidden');
    }
    
    function showError(message) {
        errorDiv.querySelector('.error-message').textContent = message;
        errorDiv.classList.remove('hidden');
    }
});