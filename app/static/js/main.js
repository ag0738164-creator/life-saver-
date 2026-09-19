// Blood Bank Management System - Main JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alert messages after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Initialize tooltips if Bootstrap is present
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Interactive Eligibility Checker Logic
    const quizForm = document.getElementById('eligibilityQuizForm');
    if (quizForm) {
        quizForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const age = parseInt(document.getElementById('quizAge').value, 10);
            const weight = parseFloat(document.getElementById('quizWeight').value);
            const donatedRecently = document.querySelector('input[name="quizDonatedRecently"]:checked')?.value;
            const healthCondition = document.querySelector('input[name="quizHealthCondition"]:checked')?.value;
            const tattooRecent = document.querySelector('input[name="quizTattoo"]:checked')?.value;

            const resultBox = document.getElementById('quizResult');
            const resultTitle = document.getElementById('quizResultTitle');
            const resultDesc = document.getElementById('quizResultDesc');
            const actionBtn = document.getElementById('quizActionBtn');

            let eligible = true;
            let reasons = [];

            if (isNaN(age) || age < 18 || age > 65) {
                eligible = false;
                reasons.push('Must be between 18 and 65 years of age.');
            }
            if (isNaN(weight) || weight < 50) {
                eligible = false;
                reasons.push('Must weigh at least 50 kg (110 lbs).');
            }
            if (donatedRecently === 'yes') {
                eligible = false;
                reasons.push('A 90-day waiting period is mandatory between blood donations.');
            }
            if (healthCondition === 'yes') {
                eligible = false;
                reasons.push('Must be free from acute illnesses, fever, or chronic uncontrolled conditions.');
            }
            if (tattooRecent === 'yes') {
                eligible = false;
                reasons.push('Tattoos, piercings, or dental surgery within the last 6 months require a deferral period.');
            }

            resultBox.classList.remove('d-none', 'alert-success', 'alert-danger');

            if (eligible) {
                resultBox.classList.add('alert-success');
                resultTitle.innerHTML = '<i class="bi bi-check-circle-fill me-2 text-success"></i>Congratulations! You Are Eligible to Donate Blood.';
                resultDesc.innerHTML = 'You meet the standard health requirements to safely donate whole blood and save up to three lives.';
                actionBtn.classList.remove('d-none');
            } else {
                resultBox.classList.add('alert-danger');
                resultTitle.innerHTML = '<i class="bi bi-x-circle-fill me-2 text-danger"></i>You Are Currently Deferred from Donating.';
                resultDesc.innerHTML = '<strong>Reason(s):</strong><ul class="mb-0 mt-2">' + reasons.map(r => `<li>${r}</li>`).join('') + '</ul>';
                actionBtn.classList.add('d-none');
            }

            resultBox.scrollIntoView({ behavior: 'smooth' });
        });
    }
});

// Confirmation helper for admin operations
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to perform this action?');
}
