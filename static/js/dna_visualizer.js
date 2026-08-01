// dna_visualizer.js - DNA del Edificio con Chart.js
class DNAVisualizer {
    constructor(canvasId, data) {
        this.canvas = document.getElementById(canvasId);
        this.data = data || {};
        this.chart = null;
        if (this.canvas) this.initChart();
    }

    initChart() {
        const scores = [
            this.data.estructural || 50,
            this.data.ambiental || 50,
            this.data.historico || 50,
            this.data.accesibilidad || 50,
            this.data.tecnologico || 50,
            this.data.energetico || 50
        ];
        const labels = ['Estructural', 'Ambiental', 'Historico', 'Accesibilidad', 'Tecnologico', 'Energetico'];
        this.chart = new Chart(this.canvas, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: this.data.nombre || 'Edificio',
                    data: scores,
                    backgroundColor: 'rgba(233,69,96,0.2)',
                    borderColor: '#e94560',
                    pointBackgroundColor: '#e94560',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#e94560'
                }]
            },
            options: {
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { stepSize: 20, color: '#6c757d', backdropColor: 'transparent' },
                        grid: { color: 'rgba(0,0,0,0.1)' },
                        pointLabels: { color: '#1a1a2e', font: { size: 12, weight: '600' } }
                    }
                },
                plugins: {
                    legend: { display: false }
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutBounce'
                }
            }
        });
    }

    updateScore(index, value) {
        if (this.chart && this.chart.data.datasets[0]) {
            this.chart.data.datasets[0].data[index] = value;
            this.chart.update();
        }
    }

    calculateGlobal() {
        if (!this.chart) return 0;
        const data = this.chart.data.datasets[0].data;
        return Math.round(data.reduce((a, b) => a + b, 0) / data.length);
    }

    getEstado(score) {
        if (score >= 80) return { label: 'Excelente', color: '#2ecc71' };
        if (score >= 60) return { label: 'Bueno', color: '#3498db' };
        if (score >= 40) return { label: 'Regular', color: '#f39c12' };
        if (score >= 20) return { label: 'Malo', color: '#e74c3c' };
        return { label: 'Critico', color: '#8e44ad' };
    }

    generateFingerprint() {
        const data = this.chart ? this.chart.data.datasets[0].data : [];
        const str = data.join('-') + '-' + Date.now();
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(16).padStart(16, '0');
    }

    destroy() {
        if (this.chart) this.chart.destroy();
    }
}

window.DNAVisualizer = DNAVisualizer;