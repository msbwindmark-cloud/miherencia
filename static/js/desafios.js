// desafios.js - Gamificación Avanzada
class DesafiosManager {
    constructor() {
        this.initAnimations();
    }

    initAnimations() {
        document.querySelectorAll('.challenge-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px)';
                card.style.boxShadow = '0 8px 30px rgba(233,69,96,0.2)';
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
                card.style.boxShadow = '';
            });
        });
    }

    updateProgressBar(element, targetProgress) {
        const fill = element.querySelector('.progress-fill');
        if (fill) {
            fill.style.width = '0%';
            setTimeout(() => {
                fill.style.width = targetProgress + '%';
            }, 100);
        }
    }

    showCompletionAnimation(element) {
        element.classList.add('completed');
        const colors = ['#d4a853', '#e94560', '#2ecc71', '#3498db'];
        for (let i = 0; i < 20; i++) {
            const confetti = document.createElement('div');
            confetti.style.cssText = `
                position: fixed; width: 10px; height: 10px; border-radius: 50%;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                left: ${element.getBoundingClientRect().left + element.offsetWidth / 2}px;
                top: ${element.getBoundingClientRect().top}px;
                pointer-events: none; z-index: 9999;
                animation: confetti-fall 1.5s ease-out forwards;
            `;
            document.body.appendChild(confetti);
            setTimeout(() => confetti.remove(), 1500);
        }
    }

    async unirseDesafio(desafioId) {
        try {
            const resp = await fetch(`/desafios/${desafioId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCSRF()
                },
                body: `desafio_id=${desafioId}`
            });
            if (resp.ok) {
                this.showNotification('Te has unido al desafio!', 'success');
                setTimeout(() => location.reload(), 1000);
            }
        } catch (e) {
            this.showNotification('Error al unirse', 'error');
        }
    }

    async updateProgreso(desafioUsuarioId, progreso) {
        try {
            const resp = await fetch(`/desafios/${desafioUsuarioId}/progreso/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCSRF()
                },
                body: `progreso=${progreso}`
            });
            if (resp.ok) {
                this.showNotification('Progreso actualizado', 'success');
                if (progreso >= 100) {
                    const el = document.querySelector(`[data-desafio-id="${desafioUsuarioId}"]`);
                    if (el) this.showCompletionAnimation(el);
                }
            }
        } catch (e) {}
    }

    getCSRF() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    showNotification(msg, type) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({ toast: true, position: 'top-end', icon: type, title: msg, showConfirmButton: false, timer: 3000 });
        }
    }
}

window.DesafiosManager = DesafiosManager;