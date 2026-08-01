// nft_marketplace.js - NFT Marketplace
class NFTMarketplace {
    constructor() {
        this.bidInterval = null;
        this.initBidding();
    }

    initBidding() {
        document.querySelectorAll('.nft-bid-form').forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.placeBid(form);
            });
        });
    }

    async placeBid(form) {
        const nftId = form.dataset.nftId;
        const monto = form.querySelector('input[name="monto"]').value;
        try {
            const response = await fetch(`/api/v1/nft/${nftId}/pujar/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.getCSRF() },
                body: JSON.stringify({ monto: parseFloat(monto) })
            });
            if (response.ok) {
                this.showNotification('Puja registrada correctamente', 'success');
                this.updateBidDisplay(nftId, monto);
            }
        } catch (err) {
            this.showNotification('Error al pujar', 'error');
        }
    }

    updateBidDisplay(nftId, monto) {
        const el = document.getElementById(`bid-display-${nftId}`);
        if (el) el.textContent = `${monto} EUR`;
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

    startLiveBids(nftId, intervalMs = 5000) {
        this.bidInterval = setInterval(() => this.refreshBids(nftId), intervalMs);
    }

    async refreshBids(nftId) {
        try {
            const resp = await fetch(`/api/v1/nft/${nftId}/pujas/`);
            if (resp.ok) {
                const data = await resp.json();
                this.renderBids(data.pujas);
            }
        } catch (e) {}
    }

    renderBids(pujas) {
        const container = document.getElementById('bid-list');
        if (!container || !pujas) return;
        container.innerHTML = pujas.map(p => `
            <div class="bid-item">
                <div class="d-flex justify-content-between">
                    <span>${p.usuario}</span>
                    <strong>${p.monto} EUR</strong>
                </div>
                <small class="text-muted">${new Date(p.fecha).toLocaleString()}</small>
            </div>
        `).join('');
    }

    destroy() {
        if (this.bidInterval) clearInterval(this.bidInterval);
    }
}

window.NFTMarketplace = NFTMarketplace;