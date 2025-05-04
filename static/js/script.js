document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Profile image preview
    const profilePicInput = document.getElementById('profile_pic');
    if (profilePicInput) {
        profilePicInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewContainer = document.createElement('div');
                    previewContainer.className = 'mt-2';
                    previewContainer.id = 'image-preview';
                    
                    const previewImage = document.createElement('img');
                    previewImage.src = e.target.result;
                    previewImage.className = 'img-thumbnail';
                    previewImage.style.maxHeight = '200px';
                    
                    // Remove existing preview if any
                    const existingPreview = document.getElementById('image-preview');
                    if (existingPreview) {
                        existingPreview.remove();
                    }
                    
                    previewContainer.appendChild(previewImage);
                    profilePicInput.parentNode.appendChild(previewContainer);
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Age calculator for DOB field
    const dobInput = document.getElementById('dob');
    if (dobInput) {
        dobInput.addEventListener('change', function() {
            const dob = new Date(this.value);
            const today = new Date();
            let age = today.getFullYear() - dob.getFullYear();
            const monthDiff = today.getMonth() - dob.getMonth();
            
            if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
                age--;
            }
            
            // Display age
            const ageDisplay = document.getElementById('age-display');
            if (!ageDisplay) {
                const ageElement = document.createElement('div');
                ageElement.id = 'age-display';
                ageElement.className = 'form-text';
                ageElement.textContent = `You are ${age} years old`;
                dobInput.parentNode.appendChild(ageElement);
            } else {
                ageDisplay.textContent = `You are ${age} years old`;
            }
        });
    }
    
    // Interest tags input enhancement
    const interestsInput = document.getElementById('interests');
    if (interestsInput) {
        interestsInput.addEventListener('keydown', function(e) {
            if (e.key === ',') {
                e.preventDefault();
                this.value = this.value.trim() + ', ';
            }
        });
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            if (this.getAttribute('href') !== '#') {
                e.preventDefault();
                
                document.querySelector(this.getAttribute('href')).scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Add animation to feature cards on scroll
    const animateOnScroll = function() {
        const elements = document.querySelectorAll('.feature-card, .testimonial-card, .step-card');
        
        elements.forEach(element => {
            const elementPosition = element.getBoundingClientRect().top;
            const screenPosition = window.innerHeight / 1.3;
            
            if (elementPosition < screenPosition) {
                element.classList.add('animate__animated', 'animate__fadeInUp');
            }
        });
    };
    
    // Call on page load
    animateOnScroll();
    
    // Call on scroll
    window.addEventListener('scroll', animateOnScroll);
});