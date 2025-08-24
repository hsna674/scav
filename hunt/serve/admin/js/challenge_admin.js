document.addEventListener('DOMContentLoaded', function() {
    const challengeTypeField = document.querySelector('#id_challenge_type');
    const decayPercentageField = document.querySelector('.field-decay_percentage');
    
    function toggleDecayPercentageField() {
        if (challengeTypeField && decayPercentageField) {
            if (challengeTypeField.value === 'decreasing') {
                decayPercentageField.style.display = 'block';
            } else {
                decayPercentageField.style.display = 'none';
            }
        }
    }
    
    // Initial state
    toggleDecayPercentageField();
    
    // Listen for changes
    if (challengeTypeField) {
        challengeTypeField.addEventListener('change', toggleDecayPercentageField);
    }
});
