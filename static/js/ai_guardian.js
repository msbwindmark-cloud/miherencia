// ai_guardian.js - AI Heritage Guardian Dashboard
class AIGuardian {
    constructor() {
        this.refreshInterval = null;
        this.initAutoRefresh();
    }

    initAutoRefresh() {
        this.refreshInterval = setInterval(() => this.refreshAlerts(), 30000);
    }

    async refreshAlerts() {
        try {
            const resp = await fetch('/api/guardian/alertas/');
            if (resp.ok) {
                const data = await resp.json();
                this.updateAlertCount(data.count);
                this.updateAlertList(data.alertas);
            }
        } catch (e) {}
    }

    updateAlertCount(count) {
        const el = document.getElementById('alert-count');
        if (el) el.textContent = count;
    }

    updateAlertList(alertas) {
        const container = document.getElementById('alert-list');
        if (!container || !alertas) return;
        container.innerHTML = alertas.map(a => `
            <div class="alert-card ${a.severidad}">
                <div class="d-flex justify-content-between">
                    <div>
                        <strong>${a.titulo}</strong>
                        <p class="mb-1">${a.mensaje}</p>
                        <small class="text-muted">${a.edificio} - ${new Date(a.fecha).toLocaleString()}</small>
                    </div>
                    <span class="badge bg-${a.severidad === 'critical' ? 'danger' : 'warning'}">${a.severidad}</span>
                </div>
            </div>
        `).join('');
    }

    async resolverAlerta(alertaId) {
        try {
            const resp = await fetch(`/api/guardian/alertas/${alertaId}/resolver/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': this.getCSRF() }
            });
            if (resp.ok) {
                this.showNotification('Alerta resuelta', 'success');
                this.refreshAlerts();
            }
        } catch (e) {
            this.showNotification('Error al resolver', 'error');
        }
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

    destroy() {
        if (this.refreshInterval) clearInterval(this.refreshInterval);
    }
}

window.AIGuardian = AIGuardian;