// Wait for DOM to be fully loaded before attaching event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Get current page
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    // ============ Account Type Selection ============
    const accountTypes = document.querySelectorAll('.account-type');
    if (accountTypes.length > 0) {
    // Add click event listener to each account type
    accountTypes.forEach(type => {
    type.addEventListener('click', function() {
    // Remove 'selected' class from all account types
    accountTypes.forEach(t => t.classList.remove('selected'));
    
    // Add 'selected' class to clicked account type
    this.classList.add('selected');
    
    // Store selected account type in local storage
    localStorage.setItem('selectedAccountType', this.getAttribute('data-type'));
    });
    });
    
    // Check if there's a previously selected account type in local storage
    const selectedType = localStorage.getItem('selectedAccountType');
    if (selectedType) {
    // Find the element with the stored type
    const typeElement = document.querySelector(`.account-type[data-type="${selectedType}"]`);
    if (typeElement) {
    // Remove 'selected' class from all account types
    accountTypes.forEach(t => t.classList.remove('selected'));
    
    // Add 'selected' class to the stored account type
    typeElement.classList.add('selected');
    }
    }
    }
    
    // ============ Login Form Handling ============
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
    loginForm.addEventListener('submit', function(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const accountType = document.querySelector('.account-type.selected')?.getAttribute('data-type') || 
   'student';
    
    // In a real application, you would send these credentials to a server
    console.log(`Attempting to login as ${accountType}`);
    console.log(`Username: ${username}`);
    
    // Store username in local storage for dashboard display
    localStorage.setItem('username', username);
    
    // Simulate successful login (in a real app, this would be an API call)
    setTimeout(() => {
    // Redirect to dashboard
    window.location.href = 'dashboard.html';
    }, 500);
    });
    }
    
    // ============ Signup Form Handling ============
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
    signupForm.addEventListener('submit', function(event) {
    event.preventDefault();
    
    const fullname = document.getElementById('fullname').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const accountType = document.querySelector('.account-type.selected')?.getAttribute('data-type') || 
   'student';
    
    // Simple password validation
    if (password !== confirmPassword) {
    alert("Passwords don't match!");
    return;
    }
    
    // In a real application, you would send registration data to a server
    console.log(`Registering new ${accountType}`);
    console.log(`Name: ${fullname}`);
    console.log(`Email: ${email}`);
    
    // Store username in local storage for dashboard display
    localStorage.setItem('username', fullname);
    
    // Simulate successful registration (in a real app, this would be an API call)
    setTimeout(() => {
    alert('Registration successful! You can now login.');
    // Redirect to login page
    window.location.href = 'index.html';
    }, 500);
    });
    }
    
    // ============ Forgot Password Form Handling ============
    const forgotPasswordForm = document.getElementById('forgot-password-form');
    if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener('submit', function(event) {
    event.preventDefault();
    
    const email = document.getElementById('recovery-email').value;
    
    // In a real application, you would send this email to a server
    console.log(`Password reset requested for: ${email}`);
    
    // Simulate successful request (in a real app, this would be an API call)
    setTimeout(() => {
    alert(`Reset link sent to ${email}. Please check your inbox.`);
    // Redirect to login page
    window.location.href = 'index.html';
    }, 500);
    });
    }
    
    // ============ Dashboard Personalization ============
    if (currentPage === 'dashboard.html') {
    // Display username if available
    const username = localStorage.getItem('username');
    if (username) {
    const userNameElement = document.getElementById('user-name');
    if (userNameElement) {
    userNameElement.textContent = username;
    }
    }
    
    // Handle logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
    logoutBtn.addEventListener('click', function(event) {
    event.preventDefault();
    
    // In a real application, you would perform a logout API call here
    
    // Clear stored user data
    localStorage.removeItem('username');
    
    // Redirect to login page
    window.location.href = 'index.html';
    });
    }
    }
   });