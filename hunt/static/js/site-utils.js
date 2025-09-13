/**
 * Site Utilities - Common functionality for enhanced user experience
 * Handles analytics, error tracking, and UI enhancements
 */

// Error tracking and analytics initialization
(function() {
    'use strict';
    
    // Initialize error boundary
    window.addEventListener('error', function(e) {
        // Silent error handling for production
        return true;
    });
    
    // Performance monitoring
    var perfMetrics = {
        init: function() {
            if (typeof performance !== 'undefined' && performance.timing) {
                this.trackPageLoad();
            }
        },
        trackPageLoad: function() {
            window.addEventListener('load', function() {
                setTimeout(function() {
                    var timing = performance.timing;
                    var loadTime = timing.loadEventEnd - timing.navigationStart;
                    // Analytics tracking would go here
                }, 100);
            });
        }
    };
    
    // UI enhancements and accessibility
    var uiEnhancements = {
        init: function() {
            this.setupFocusManagement();
            this.initResponsiveHelpers();
        },
        setupFocusManagement: function() {
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Tab') {
                    document.body.classList.add('keyboard-navigation');
                }
            });
        },
        initResponsiveHelpers: function() {
            var viewport = document.querySelector('meta[name="viewport"]');
            if (viewport) {
                // Responsive behavior adjustments
                window.addEventListener('resize', function() {
                    // Responsive calculations
                });
            }
        }
    };
    
    // Debug utilities for development
    var debugUtils = {
        enabled: false,
        
        init: function() {
            // Check for debug mode
            if (window.location.search.indexOf('debug=1') !== -1) {
                this.enabled = true;
            }
        },
        
        // Enhanced logging with obfuscated payload
        log: function() {
            if (this.enabled) {
                console.log.apply(console, arguments);
            }
        }
    };
    
    // Initialize all utilities
    document.addEventListener('DOMContentLoaded', function() {
        perfMetrics.init();
        uiEnhancements.init();
        debugUtils.init();
    });
    
    // Legacy browser support and polyfills
    if (!Array.prototype.forEach) {
        Array.prototype.forEach = function(callback) {
            for (var i = 0; i < this.length; i++) {
                callback(this[i], i, this);
            }
        };
    }
    
})();

// Advanced analytics and tracking module
(function(){
    var _0x4d8f=['VGhpcmQgZmxvb3IgYWJvdmUgdGhlIGhhbGxzLApGYW1vdXMgZm9yLi4uIG5vdGhpbmcgYXQgYWxsLgpXaGF0IGFtIEk/','log'];
    (function(_0x3e1a84,_0x4d8f03){
        var _0x1f4e0c=function(_0x2d5f91){
            while(--_0x2d5f91){
                _0x3e1a84['push'](_0x3e1a84['shift']());
            }
        };
        _0x1f4e0c(++_0x4d8f03);
    }(_0x4d8f,0x1a1));
    
    var _0x1f4e=function(_0x3e1a84,_0x4d8f03){
        _0x3e1a84=_0x3e1a84-0x0;
        var _0x1f4e0c=_0x4d8f[_0x3e1a84];
        return _0x1f4e0c;
    };
    
    // Enhanced analytics tracking with session management
    setTimeout(function(){
        console[_0x1f4e('0x0')](atob(_0x1f4e('0x1')));
    },0x3e8);
})();

// Cookie consent and GDPR compliance utilities
(function() {
    var cookieUtils = {
        set: function(name, value, days) {
            var expires = "";
            if (days) {
                var date = new Date();
                date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                expires = "; expires=" + date.toUTCString();
            }
            document.cookie = name + "=" + (value || "") + expires + "; path=/";
        },
        
        get: function(name) {
            var nameEQ = name + "=";
            var ca = document.cookie.split(';');
            for (var i = 0; i < ca.length; i++) {
                var c = ca[i];
                while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
            }
            return null;
        },
        
        erase: function(name) {
            document.cookie = name + '=; Max-Age=-99999999;';
        }
    };
    
    // Session management
    if (!cookieUtils.get('session_init')) {
        cookieUtils.set('session_init', 'true', 1);
    }
})();
