// time_machine.js - Time Machine Patrimonial
class TimeMachine {
    constructor() {
        this.slider = document.getElementById('epoca-slider');
        this.display = document.getElementById('epoca-display');
        this.originalImg = null;
        this.generatedImg = null;
        if (this.slider) {
            this.slider.addEventListener('input', (e) => this.updateEpoca(e.target.value));
        }
    }

    updateEpoca(val) {
        if (this.display) this.display.textContent = val;
        this.updateContexto(parseInt(val));
    }

    updateContexto(epoca) {
        const ctx = document.getElementById('contexto-info');
        if (!ctx) return;
        let info = '';
        if (epoca < 500) info = 'Epoca visigoda. Construcciones sencillas de piedra.';
        else if (epoca < 1000) info = 'Al-Andalus. Arte islamico y arquitectura mudéjar.';
        else if (epoca < 1300) info = 'Reconquista. Mezcla de estilos románico y gótico.';
        else if (epoca < 1500) info = 'Gótico tardío. Catedrales imponentes.';
        else if (epoca < 1700) info = 'Renacimiento. Proporción y simetría clásica.';
        else if (epoca < 1800) info = 'Barroco. Ornamentación exuberante.';
        else if (epoca < 1900) info = 'Neoclásico. Líneas puras y monumentales.';
        else if (epoca < 2000) info = 'Modernismo. Art Nouveau y regionalismo.';
        else info = 'Era digital. Tecnología y sostenibilidad.';
        ctx.innerHTML = `<p class="mb-0 small">${info}</p>`;
    }

    compararImagenes() {
        const container = document.getElementById('compare-container');
        if (!container) return;
        let offset = 50;
        const overlay = container.querySelector('.compare-overlay');
        const sliderLine = container.querySelector('.compare-slider');
        const move = (e) => {
            const rect = container.getBoundingClientRect();
            offset = ((e.clientX - rect.left) / rect.width) * 100;
            offset = Math.max(0, Math.min(100, offset));
            if (overlay) overlay.style.width = offset + '%';
            if (sliderLine) sliderLine.style.left = offset + '%';
        };
        container.addEventListener('mousemove', move);
        container.addEventListener('touchmove', (e) => {
            move(e.touches[0]);
        });
    }
}

window.TimeMachine = TimeMachine;