document.addEventListener('DOMContentLoaded', function() {
    const challengeTypeField = document.querySelector('#id_challenge_type');
    const decayPercentageField = document.querySelector('.field-decay_percentage');
    const requiredChallengesField = document.querySelector('.field-required_challenges');
    const categoryField = document.querySelector('#id_category');
    const requiredChallengesSelect = document.querySelector('#id_required_challenges');
    
    console.log('Challenge admin JS loaded'); // Debug
    console.log('Fields found:', {
        challengeType: !!challengeTypeField,
        requiredChallenges: !!requiredChallengesField,
        category: !!categoryField,
        select: !!requiredChallengesSelect
    });
    
    function toggleConditionalFields() {
        console.log('Toggling fields, current type:', challengeTypeField?.value); // Debug
        
        if (challengeTypeField) {
            // Remove all challenge type classes
            document.body.classList.remove('decreasing-challenge-type', 'unlocking-challenge-type');
            
            // Add class based on current selection
            if (challengeTypeField.value === 'decreasing') {
                document.body.classList.add('decreasing-challenge-type');
            } else if (challengeTypeField.value === 'unlocking') {
                document.body.classList.add('unlocking-challenge-type');
                console.log('Showing required challenges field'); // Debug
                filterRequiredChallenges(); // Filter when showing
            }
        }
    }
    
    function filterRequiredChallenges() {
        if (!categoryField || !requiredChallengesSelect || !challengeTypeField) {
            console.log('Missing elements for filtering'); // Debug
            return;
        }
        
        const selectedCategory = categoryField.value;
        const currentChallengeId = getCurrentChallengeId();
        
        console.log('Filtering challenges:', {
            challengeType: challengeTypeField.value,
            selectedCategory: selectedCategory,
            currentId: currentChallengeId
        }); // Debug
        
        // Only filter if challenge type is unlocking and category is selected
        if (challengeTypeField.value !== 'unlocking' || !selectedCategory) {
            requiredChallengesSelect.innerHTML = '';
            return;
        }
        
        // Store currently selected values
        const selectedValues = Array.from(requiredChallengesSelect.selectedOptions).map(option => option.value);
        console.log('Currently selected:', selectedValues); // Debug
        
        // Clear current options and show loading
        requiredChallengesSelect.innerHTML = '<option disabled>Loading...</option>';
        
        // Make AJAX call to get challenges in the selected category
        const url = `/admin/main/challenge/get_category_challenges/?category_id=${selectedCategory}`;
        console.log('Fetching from:', url); // Debug
        
        fetch(url)
            .then(response => {
                console.log('Response status:', response.status); // Debug
                return response.json();
            })
            .then(data => {
                console.log('Received data:', data); // Debug
                
                // Clear loading message
                requiredChallengesSelect.innerHTML = '';
                
                // Add challenges from the same category
                data.challenges.forEach(challenge => {
                    // Don't include the current challenge being edited
                    if (String(challenge.id) !== String(currentChallengeId)) {
                        const option = new Option(challenge.name, challenge.id);
                        
                        // Restore selection if this option was previously selected
                        if (selectedValues.includes(String(challenge.id))) {
                            option.selected = true;
                        }
                        
                        requiredChallengesSelect.appendChild(option);
                        console.log('Added challenge:', challenge.name); // Debug
                    }
                });
                
                // Ensure the select is set to multiple
                requiredChallengesSelect.multiple = true;
            })
            .catch(error => {
                console.error('Error fetching challenges:', error);
                requiredChallengesSelect.innerHTML = '<option disabled>Error loading challenges</option>';
            });
    }
    
    function getCurrentChallengeId() {
        const currentUrl = window.location.pathname;
        const match = currentUrl.match(/\/(\d+)\/change\/$/);
        return match ? match[1] : null;
    }
    
    // Initial state
    console.log('Setting initial state'); // Debug
    toggleConditionalFields();
    
    // If page loads with category already selected and unlocking type, filter immediately
    if (challengeTypeField && challengeTypeField.value === 'unlocking' && categoryField && categoryField.value) {
        console.log('Initial filtering for existing challenge'); // Debug
        filterRequiredChallenges();
    }
    
    // Listen for changes
    if (challengeTypeField) {
        challengeTypeField.addEventListener('change', toggleConditionalFields);
    }
    
    if (categoryField) {
        categoryField.addEventListener('change', filterRequiredChallenges);
    }
});
