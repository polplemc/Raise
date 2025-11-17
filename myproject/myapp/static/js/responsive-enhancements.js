/**
 * Responsive Enhancements JavaScript
 * Provides dynamic responsive behavior and device-specific optimizations
 */

class ResponsiveManager {
  constructor() {
    this.breakpoints = {
      mobile: 479,
      mobileLandscape: 767,
      tablet: 1023,
      tabletLandscape: 1199,
      laptop: 1439,
      desktop: 1440
    };
    
    this.currentDevice = this.detectDevice();
    this.currentOrientation = this.detectOrientation();
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.optimizeForDevice();
    this.handleOrientationChange();
    this.setupTouchOptimizations();
    this.setupKeyboardOptimizations();
  }

  detectDevice() {
    const width = window.innerWidth;
    
    if (width <= this.breakpoints.mobile) return 'mobile-portrait';
    if (width <= this.breakpoints.mobileLandscape) return 'mobile-landscape';
    if (width <= this.breakpoints.tablet) return 'tablet-portrait';
    if (width <= this.breakpoints.tabletLandscape) return 'tablet-landscape';
    if (width <= this.breakpoints.laptop) return 'laptop';
    return 'desktop';
  }

  detectOrientation() {
    return window.innerHeight > window.innerWidth ? 'portrait' : 'landscape';
  }

  setupEventListeners() {
    // Resize handler with debouncing
    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        this.handleResize();
      }, 150);
    });

    // Orientation change handler
    window.addEventListener('orientationchange', () => {
      setTimeout(() => {
        this.handleOrientationChange();
      }, 100);
    });

    // Device motion for mobile optimizations
    if (window.DeviceMotionEvent) {
      window.addEventListener('devicemotion', (e) => {
        this.handleDeviceMotion(e);
      });
    }
  }

  handleResize() {
    const newDevice = this.detectDevice();
    const newOrientation = this.detectOrientation();
    
    if (newDevice !== this.currentDevice || newOrientation !== this.currentOrientation) {
      this.currentDevice = newDevice;
      this.currentOrientation = newOrientation;
      this.optimizeForDevice();
      this.handleOrientationChange();
    }
    
    this.adjustTableResponsiveness();
    this.adjustModalSizes();
    this.adjustNotificationPosition();
  }

  optimizeForDevice() {
    const body = document.body;
    
    // Remove existing device classes
    body.classList.remove('mobile-portrait', 'mobile-landscape', 'tablet-portrait', 
                         'tablet-landscape', 'laptop', 'desktop');
    
    // Add current device class
    body.classList.add(this.currentDevice);
    
    // Device-specific optimizations
    switch (this.currentDevice) {
      case 'mobile-portrait':
        this.optimizeMobilePortrait();
        break;
      case 'mobile-landscape':
        this.optimizeMobileLandscape();
        break;
      case 'tablet-portrait':
        this.optimizeTabletPortrait();
        break;
      case 'tablet-landscape':
        this.optimizeTabletLandscape();
        break;
      case 'laptop':
        this.optimizeLaptop();
        break;
      case 'desktop':
        this.optimizeDesktop();
        break;
    }
  }

  optimizeMobilePortrait() {
    // Ensure sidebar is hidden by default
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.remove('show');
    }
    
    // Optimize form inputs for mobile
    this.optimizeFormInputs();
    
    // Enable swipe gestures
    this.enableSwipeGestures();
    
    // Optimize table display
    this.enableMobileTableView();
  }

  optimizeMobileLandscape() {
    // Compact header for landscape
    const mobileNavbar = document.querySelector('.mobile-navbar');
    if (mobileNavbar) {
      mobileNavbar.style.height = '50px';
      mobileNavbar.style.padding = '5px 15px';
    }
    
    // Adjust main content margin
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.style.marginTop = '50px';
    }
  }

  optimizeTabletPortrait() {
    // Show sidebar for tablets
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.remove('show');
      sidebar.style.transform = 'translateX(0)';
    }
    
    // Optimize grid layout
    this.optimizeGridLayout('tablet');
  }

  optimizeTabletLandscape() {
    // Enhanced sidebar for tablet landscape
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.style.width = '250px';
    }
    
    // Optimize dashboard layout
    this.optimizeDashboardLayout('tablet-landscape');
  }

  optimizeLaptop() {
    // Enhanced sidebar for laptop
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.style.width = '260px';
    }
    
    // Optimize content width
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.style.marginLeft = '260px';
    }
    
    this.optimizeDashboardLayout('laptop');
  }

  optimizeDesktop() {
    // Premium sidebar for desktop
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.style.width = '280px';
    }
    
    // Optimize content width with max-width
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.style.marginLeft = '280px';
      mainContent.style.maxWidth = 'calc(100% - 280px)';
    }
    
    this.optimizeDashboardLayout('desktop');
  }

  handleOrientationChange() {
    const body = document.body;
    body.classList.remove('portrait', 'landscape');
    body.classList.add(this.currentOrientation);
    
    // Handle specific orientation changes
    if (this.currentOrientation === 'landscape' && this.isMobile()) {
      this.handleMobileLandscape();
    } else if (this.currentOrientation === 'portrait' && this.isMobile()) {
      this.handleMobilePortrait();
    }
  }

  handleMobileLandscape() {
    // Compact UI for mobile landscape
    const elements = document.querySelectorAll('.stat-card');
    elements.forEach(el => {
      el.style.padding = '15px';
      el.style.marginBottom = '10px';
    });
  }

  handleMobilePortrait() {
    // Restore normal padding for mobile portrait
    const elements = document.querySelectorAll('.stat-card');
    elements.forEach(el => {
      el.style.padding = '20px';
      el.style.marginBottom = '15px';
    });
  }

  setupTouchOptimizations() {
    if ('ontouchstart' in window) {
      document.body.classList.add('touch-device');
      
      // Optimize touch targets
      const buttons = document.querySelectorAll('.btn');
      buttons.forEach(btn => {
        if (!btn.style.minHeight) {
          btn.style.minHeight = '44px';
        }
      });
      
      // Add touch feedback
      this.addTouchFeedback();
    }
  }

  addTouchFeedback() {
    const touchElements = document.querySelectorAll('.btn, .nav-link, .card');
    
    touchElements.forEach(element => {
      element.addEventListener('touchstart', function() {
        this.style.opacity = '0.7';
      });
      
      element.addEventListener('touchend', function() {
        setTimeout(() => {
          this.style.opacity = '';
        }, 150);
      });
    });
  }

  setupKeyboardOptimizations() {
    // Handle virtual keyboard on mobile
    if (this.isMobile()) {
      const inputs = document.querySelectorAll('input, textarea, select');
      
      inputs.forEach(input => {
        input.addEventListener('focus', () => {
          // Scroll element into view when keyboard appears
          setTimeout(() => {
            input.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }, 300);
        });
      });
    }
  }

  enableSwipeGestures() {
    if (!this.isMobile()) return;
    
    let startX, startY, endX, endY;
    
    document.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    });
    
    document.addEventListener('touchend', (e) => {
      endX = e.changedTouches[0].clientX;
      endY = e.changedTouches[0].clientY;
      
      this.handleSwipe(startX, startY, endX, endY);
    });
  }

  handleSwipe(startX, startY, endX, endY) {
    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const minSwipeDistance = 50;
    
    // Horizontal swipe
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
      const sidebar = document.getElementById('sidebar');
      const sidebarOverlay = document.getElementById('sidebarOverlay');
      
      if (deltaX > 0 && startX < 50) {
        // Swipe right from left edge - open sidebar
        if (sidebar) {
          sidebar.classList.add('show');
          if (sidebarOverlay) sidebarOverlay.classList.add('show');
        }
      } else if (deltaX < 0 && sidebar && sidebar.classList.contains('show')) {
        // Swipe left - close sidebar
        sidebar.classList.remove('show');
        if (sidebarOverlay) sidebarOverlay.classList.remove('show');
      }
    }
  }

  adjustTableResponsiveness() {
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
      const wrapper = table.closest('.table-responsive, .table-responsive-custom');
      
      if (this.isMobile()) {
        // Enable mobile table view
        table.classList.add('table-mobile-stack');
        
        // Add data labels for mobile view
        const headers = table.querySelectorAll('thead th');
        const cells = table.querySelectorAll('tbody td');
        
        cells.forEach((cell, index) => {
          const headerIndex = index % headers.length;
          if (headers[headerIndex]) {
            cell.setAttribute('data-label', headers[headerIndex].textContent.trim());
          }
        });
      } else {
        table.classList.remove('table-mobile-stack');
      }
    });
  }

  adjustModalSizes() {
    const modals = document.querySelectorAll('.modal-dialog');
    
    modals.forEach(modal => {
      if (this.isMobile()) {
        modal.style.margin = '10px';
        modal.style.maxWidth = 'calc(100% - 20px)';
      } else {
        modal.style.margin = '';
        modal.style.maxWidth = '';
      }
    });
  }

  adjustNotificationPosition() {
    const notificationContainer = document.getElementById('notificationContainer');
    
    if (notificationContainer) {
      if (this.isMobile()) {
        notificationContainer.style.top = '70px';
        notificationContainer.style.left = '10px';
        notificationContainer.style.right = '10px';
        notificationContainer.style.maxWidth = 'none';
      } else {
        notificationContainer.style.top = '20px';
        notificationContainer.style.left = '';
        notificationContainer.style.right = '20px';
        notificationContainer.style.maxWidth = '400px';
      }
    }
  }

  enableMobileTableView() {
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
      if (!table.closest('.table-responsive-mobile')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive-mobile';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
      }
    });
  }

  optimizeFormInputs() {
    const inputs = document.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
      // Prevent zoom on iOS
      if (input.type !== 'range' && input.type !== 'checkbox' && input.type !== 'radio') {
        input.style.fontSize = '16px';
      }
      
      // Ensure minimum touch target size
      input.style.minHeight = '44px';
    });
  }

  optimizeGridLayout(device) {
    const rows = document.querySelectorAll('.row');
    
    rows.forEach(row => {
      const cols = row.querySelectorAll('[class*="col-"]');
      
      cols.forEach(col => {
        // Add responsive classes based on device
        if (device === 'tablet') {
          if (cols.length > 2) {
            col.classList.add('col-tablet-6');
          }
        }
      });
    });
  }

  optimizeDashboardLayout(device) {
    const dashboard = document.querySelector('.dashboard, .row');
    
    if (dashboard) {
      dashboard.classList.remove('dashboard-mobile', 'dashboard-tablet', 
                                'dashboard-laptop', 'dashboard-desktop');
      dashboard.classList.add(`dashboard-${device.replace('-', '')}`);
    }
  }

  isMobile() {
    return this.currentDevice.includes('mobile');
  }

  isTablet() {
    return this.currentDevice.includes('tablet');
  }

  isDesktop() {
    return this.currentDevice === 'desktop' || this.currentDevice === 'laptop';
  }

  // Public method to manually trigger optimization
  refresh() {
    this.currentDevice = this.detectDevice();
    this.currentOrientation = this.detectOrientation();
    this.optimizeForDevice();
    this.handleOrientationChange();
  }

  // Method to get current device info
  getDeviceInfo() {
    return {
      device: this.currentDevice,
      orientation: this.currentOrientation,
      width: window.innerWidth,
      height: window.innerHeight,
      isMobile: this.isMobile(),
      isTablet: this.isTablet(),
      isDesktop: this.isDesktop()
    };
  }
}

// Initialize responsive manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  window.responsiveManager = new ResponsiveManager();
  
  // Add device info to console for debugging
  console.log('Responsive Manager initialized:', window.responsiveManager.getDeviceInfo());
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ResponsiveManager;
}
