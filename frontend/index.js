// ========== INTERACTIVE PROCESS VISUALIZATION ========== 
document.addEventListener('DOMContentLoaded', function() {
  // Process stage interactions
  const processStages = document.querySelectorAll('.process-stage');
  processStages.forEach((stage, index) => {
    stage.addEventListener('mouseenter', function() {
      const stageType = this.dataset.stage;
      this.style.transform = 'translateY(-15px) scale(1.05)';
      
      // Add glow effect
      const icon = this.querySelector('.stage-icon');
      if (icon) {
        icon.style.boxShadow = '0 20px 50px rgba(37, 99, 235, 0.6)';
        icon.style.transform = 'scale(1.15) rotate(5deg)';
      }
      
      // Add ripple effect
      const ripple = document.createElement('div');
      ripple.style.cssText = `
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        background: rgba(37, 99, 235, 0.3);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        animation: ripple 0.6s ease-out;
        pointer-events: none;
        z-index: -1;
      `;
      this.appendChild(ripple);
      
      setTimeout(() => ripple.remove(), 600);
      
      console.log(`Hovering over ${stageType} stage`);
    });

    stage.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
      const icon = this.querySelector('.stage-icon');
      if (icon) {
        icon.style.boxShadow = '0 8px 25px rgba(37, 99, 235, 0.3)';
        icon.style.transform = 'scale(1) rotate(0deg)';
      }
    });

    stage.addEventListener('click', function() {
      const stageType = this.dataset.stage;
      console.log(`Clicked on ${stageType} stage - could show detailed analysis`);
      
      // Add click animation with bounce
      this.style.transform = 'translateY(-10px) scale(0.95)';
      setTimeout(() => {
        this.style.transform = 'translateY(-20px) scale(1.1)';
        setTimeout(() => {
          this.style.transform = 'translateY(-15px) scale(1.05)';
        }, 100);
      }, 100);
      
      // Add click particle effect
      for (let i = 0; i < 6; i++) {
        const particle = document.createElement('div');
        particle.style.cssText = `
          position: absolute;
          top: 50%;
          left: 50%;
          width: 4px;
          height: 4px;
          background: var(--blue-accent);
          border-radius: 50%;
          pointer-events: none;
          animation: particle-burst 0.8s ease-out forwards;
          animation-delay: ${i * 0.1}s;
        `;
        this.appendChild(particle);
        setTimeout(() => particle.remove(), 800);
      }
    });
  });

  // Smooth scroll for navigation links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  // Add scroll-triggered animations
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }
    });
  }, observerOptions);

  // Observe elements for scroll animations
  document.querySelectorAll('.service-card, .stat-item, .engineering-left, .engineering-right').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'all 0.6s ease-out';
    observer.observe(el);
  });
});
