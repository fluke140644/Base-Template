/* ==========================================================================
   NovaPulse Main JS — Session Timer, Dropdown, Sidebar, Alerts
   ========================================================================== */
'use strict';

document.addEventListener('DOMContentLoaded', () => {

    // ── 1. Mobile Sidebar Toggle ──────────────────────────────────────────
    const mobileToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebarNav');
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('show-sidebar');
        });
        document.addEventListener('click', (e) => {
            if (sidebar && !sidebar.contains(e.target) && !mobileToggle.contains(e.target)) {
                sidebar.classList.remove('show-sidebar');
            }
        });
    }

    // ── 2. User Dropdown Toggle ───────────────────────────────────────────
    const dropdownWrapper = document.getElementById('userDropdownWrapper');
    const dropdownToggle  = document.getElementById('userDropdownToggle');
    if (dropdownWrapper && dropdownToggle) {
        dropdownToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownWrapper.classList.toggle('open');
            dropdownToggle.setAttribute('aria-expanded', dropdownWrapper.classList.contains('open'));
        });
        document.addEventListener('click', () => {
            dropdownWrapper.classList.remove('open');
            dropdownToggle.setAttribute('aria-expanded', 'false');
        });
    }

    // ── 3. Auto-dismiss Alerts ────────────────────────────────────────────
    document.querySelectorAll('.alert').forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = 'opacity .5s ease, transform .5s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-8px)';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // ── 4. Session Idle Countdown Timer ──────────────────────────────────
    //   Reads SESSION_IDLE_TIMEOUT_MINUTES injected as data attribute on body
    //   or defaults to 60 minutes. Resets on user activity.
    const timerEl = document.getElementById('sessionTimer');
    const countdownEl = document.getElementById('sessionCountdown');

    if (timerEl && countdownEl) {
        // Default 60 min; server middleware is the real enforcer.
        const TIMEOUT_MINUTES = parseInt(
            document.body.dataset.sessionTimeout || '60', 10
        );
        let remainingSeconds = TIMEOUT_MINUTES * 60;

        const tick = setInterval(() => {
            remainingSeconds--;
            if (remainingSeconds <= 0) {
                clearInterval(tick);
                countdownEl.textContent = '00:00';
                window.location.href = '/accounts/login/?timeout=1';
                return;
            }
            const m = Math.floor(remainingSeconds / 60).toString().padStart(2, '0');
            const s = (remainingSeconds % 60).toString().padStart(2, '0');
            countdownEl.textContent = `${m}:${s}`;

            // Visual warnings
            if (remainingSeconds <= 60) {
                timerEl.classList.add('danger');
                timerEl.classList.remove('warn');
            } else if (remainingSeconds <= 300) {
                timerEl.classList.add('warn');
            }
        }, 1000);

        // Reset timer on real user activity (server-side middleware also resets)
        let resetQueued = false;
        const resetTimer = () => {
            if (!resetQueued) {
                resetQueued = true;
                setTimeout(() => {
                    remainingSeconds = TIMEOUT_MINUTES * 60;
                    timerEl.classList.remove('warn', 'danger');
                    resetQueued = false;
                }, 500);
            }
        };
        ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'].forEach(evt => {
            document.addEventListener(evt, resetTimer, { passive: true });
        });
    }

});
