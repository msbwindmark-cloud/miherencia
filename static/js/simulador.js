// simulador.js - Simulador de Desastres
class SimuladorDesastres {
    constructor() {
        this.tipo = 'terremoto';
        this.intensidad = 5;
        this.canvas = null;
        this.ctx = null;
        this.animating = false;
    }

    setTipo(tipo) { this.tipo = tipo; }
    setIntensidad(val) { this.intensidad = parseFloat(val); }

    initCanvas(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (this.canvas) this.ctx = this.canvas.getContext('2d');
    }

    simular() {
        if (this.animating) return;
        this.animating = true;
        switch (this.tipo) {
            case 'terremoto': this.simularTerremoto(); break;
            case 'incendio': this.simularIncendio(); break;
            case 'inundacion': this.simularInundacion(); break;
        }
    }

    simularTerremoto() {
        if (!this.ctx) return;
        const canvas = this.canvas;
        const ctx = this.ctx;
        let frame = 0;
        const maxFrames = 60 * 3;
        const amplitude = this.intensidad * 3;
        const animate = () => {
            if (frame >= maxFrames) { this.animating = false; return; }
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.save();
            const shakeX = Math.sin(frame * 0.5) * amplitude * Math.random();
            const shakeY = Math.cos(frame * 0.3) * amplitude * 0.5 * Math.random();
            ctx.translate(shakeX, shakeY);
            ctx.fillStyle = '#d4a853';
            ctx.fillRect(canvas.width / 2 - 100, canvas.height / 2 - 80, 200, 160);
            ctx.fillStyle = '#e94560';
            ctx.beginPath();
            ctx.moveTo(canvas.width / 2 - 120, canvas.height / 2 - 80);
            ctx.lineTo(canvas.width / 2, canvas.height / 2 - 130);
            ctx.lineTo(canvas.width / 2 + 120, canvas.height / 2 - 80);
            ctx.fill();
            if (this.intensidad > 5 && Math.random() > 0.7) {
                ctx.strokeStyle = '#8B4513';
                ctx.lineWidth = 2;
                const x = canvas.width / 2 + (Math.random() - 0.5) * 150;
                const y = canvas.height / 2 + (Math.random() - 0.5) * 100;
                ctx.beginPath();
                ctx.moveTo(x, y);
                ctx.lineTo(x + (Math.random() - 0.5) * 30, y + 20);
                ctx.lineTo(x + (Math.random() - 0.5) * 30, y + 40);
                ctx.stroke();
            }
            ctx.restore();
            frame++;
            requestAnimationFrame(animate);
        };
        animate();
    }

    simularIncendio() {
        if (!this.ctx) return;
        const canvas = this.canvas;
        const ctx = this.ctx;
        const particles = [];
        for (let i = 0; i < this.intensidad * 10; i++) {
            particles.push({
                x: canvas.width / 2 + (Math.random() - 0.5) * 100,
                y: canvas.height / 2,
                vx: (Math.random() - 0.5) * 3,
                vy: -Math.random() * 5 - 2,
                size: Math.random() * 8 + 2,
                life: 1
            });
        }
        const animate = () => {
            if (particles.every(p => p.life <= 0)) { this.animating = false; return; }
            ctx.fillStyle = 'rgba(0,0,0,0.1)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#d4a853';
            ctx.fillRect(canvas.width / 2 - 80, canvas.height / 2 - 60, 160, 120);
            particles.forEach(p => {
                if (p.life <= 0) return;
                p.x += p.vx;
                p.y += p.vy;
                p.life -= 0.01;
                p.size *= 0.99;
                const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
                gradient.addColorStop(0, `rgba(255,${Math.floor(100 + Math.random() * 100)},0,${p.life})`);
                gradient.addColorStop(1, `rgba(200,0,0,0)`);
                ctx.fillStyle = gradient;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            });
            requestAnimationFrame(animate);
        };
        animate();
    }

    simularInundacion() {
        if (!this.ctx) return;
        const canvas = this.canvas;
        const ctx = this.ctx;
        let waterLevel = canvas.height;
        const targetLevel = canvas.height * (1 - this.intensidad / 20);
        const animate = () => {
            if (waterLevel <= targetLevel) { this.animating = false; return; }
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#d4a853';
            ctx.fillRect(canvas.width / 2 - 80, canvas.height / 2 - 60, 160, 120);
            waterLevel -= 2;
            ctx.fillStyle = 'rgba(52,152,219,0.6)';
            ctx.fillRect(0, waterLevel, canvas.width, canvas.height - waterLevel);
            for (let i = 0; i < 5; i++) {
                const x = Math.random() * canvas.width;
                ctx.fillStyle = 'rgba(52,152,219,0.3)';
                ctx.beginPath();
                ctx.arc(x, waterLevel + 5, 3, 0, Math.PI * 2);
                ctx.fill();
            }
            requestAnimationFrame(animate);
        };
        animate();
    }

    calcularDano() {
        let dano = { costo: 0, zonas: [], severidad: 'leve', recomendaciones: '' };
        switch (this.tipo) {
            case 'terremoto':
                if (this.intensidad > 7) {
                    dano.costo = 500000; dano.zonas = ['Fachada', 'Cupula', 'Torre']; dano.severidad = 'critico';
                    dano.recomendaciones = 'Evacuacion inmediata. Revision estructural.';
                } else if (this.intensidad > 5) {
                    dano.costo = 150000; dano.zonas = ['Grietas', 'Campanas']; dano.severidad = 'severo';
                } else {
                    dano.costo = 20000; dano.zonas = ['Grietas menores']; dano.severidad = 'leve';
                }
                break;
            case 'incendio':
                if (this.intensidad > 80) {
                    dano.costo = 800000; dano.zonas = ['Techos', 'Retablos']; dano.severidad = 'critico';
                } else if (this.intensidad > 50) {
                    dano.costo = 300000; dano.zonas = ['Electrico', 'Madera']; dano.severidad = 'severo';
                } else {
                    dano.costo = 50000; dano.zonas = ['Zona puntual']; dano.severidad = 'leve';
                }
                break;
            case 'inundacion':
                dano.costo = this.intensidad > 1000 ? 400000 : 80000;
                dano.zonas = this.intensidad > 1000 ? ['Sotano', 'Cimentacion'] : ['Zona baja'];
                dano.severidad = this.intensidad > 1000 ? 'critico' : 'moderado';
                break;
        }
        return dano;
    }
}

window.SimuladorDesastres = SimuladorDesastres;