// AskMe - JavaScript for theme and language switching

// Global functions
function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Update theme immediately for better UX
    document.body.setAttribute('data-theme', newTheme);
    
    // Send update to server
    const form = new FormData();
    form.append('theme', newTheme);
    
    // Get current language and nickname if they exist
    const langSelect = document.querySelector('#language');
    const nicknameInput = document.querySelector('#nickname');
    
    if (langSelect) {
        form.append('language', langSelect.value);
    } else {
        form.append('language', 'en'); // Default
    }
    
    if (nicknameInput && nicknameInput.value) {
        form.append('nickname', nicknameInput.value);
    }
    
    fetch('/preferences', {
        method: 'POST',
        body: form
    }).then(response => {
        if (response.ok) {
            location.reload();
        }
    }).catch(error => {
        console.error('Error updating theme:', error);
        // Revert theme on error
        document.body.setAttribute('data-theme', currentTheme);
    });
}

function switchLanguage(lang) {
    const form = new FormData();
    form.append('language', lang);
    
    // Get current theme and nickname if they exist
    const currentTheme = document.body.getAttribute('data-theme') || 'light';
    const nicknameInput = document.querySelector('#nickname');
    
    form.append('theme', currentTheme);
    
    if (nicknameInput && nicknameInput.value) {
        form.append('nickname', nicknameInput.value);
    }
    
    fetch('/preferences', {
        method: 'POST',
        body: form
    }).then(response => {
        if (response.ok) {
            location.reload();
        }
    }).catch(error => {
        console.error('Error updating language:', error);
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Theme is already set by the server-side script in the template
    
    // Add event listeners for chat message forms to auto-scroll
    const chatContainers = document.querySelectorAll('.chat-container');
    chatContainers.forEach(container => {
        // Scroll to bottom when new messages are added
        container.scrollTop = container.scrollHeight;
    });
});
