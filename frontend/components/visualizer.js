/**
 * Job Visualizer Component - Displays job details and metrics
 */

class JobVisualizer {
    constructor(job) {
        this.job = job;
    }

    renderJobContext() {
        if (!this.job) {
            return '<div class="loading-skeleton"></div>';
        }

        const docId = this.job.documentId || '';
        const shortId = docId.substring(0, 8);

        return `
            <div class="job-card">
                <p class="job-title">${this.escapeHtml(this.job.projectTitle || 'Untitled Project')}</p>
                <p class="job-location">${this.escapeHtml(this.job.siteStreet || '')}, ${this.escapeHtml(this.job.siteCity || '')}</p>
                <span class="job-id">ID: ${this.escapeHtml(shortId)}...</span>
            </div>
        `;
    }

    render() {
        if (!this.job) {
            return '';
        }

        const totalEstimate = this.calculateTotal(this.job.estimate, 'total');
        const milestonesCompleted = this.countCompletedMilestones();
        const milestonesTotal = this.job.milestones?.length || 0;
        const paidAmount = this.calculatePaidAmount();

        let html = '';

        // Value Card
        html += `
            <div class="value-card">
                <div class="value-header">
                    <p class="value-label">Project Value</p>
                    <span class="estimate-type">${this.escapeHtml(this.job.estimateType || 'general')}</span>
                </div>
                <p class="value-amount">$${this.formatNumber(totalEstimate)}</p>
                <div class="value-grid">
                    <div>
                        <div class="value-item-label">Line Items</div>
                        <div class="value-item-value">${this.job.estimate?.length || 0}</div>
                    </div>
                    <div>
                        <div class="value-item-label">Paid to Date</div>
                        <div class="value-item-value paid">$${this.formatNumber(paidAmount)}</div>
                    </div>
                </div>
            </div>
        `;

        // Client Card
        const clientInitials = this.getInitials(this.job.clientName || 'NA');
        const statusClass = this.job.status === 'Production' ? 'production' : 'planning';

        html += `
            <div class="client-card">
                <p class="section-title">Client Details</p>
                <div class="client-info">
                    <div class="client-avatar">${this.escapeHtml(clientInitials)}</div>
                    <div class="client-details">
                        <p class="client-name">${this.escapeHtml(this.job.clientName || 'Unknown Client')}</p>
                        <p class="client-email">${this.escapeHtml(this.job.clientEmail1 || 'No email registered')}</p>
                        <p class="client-phone">${this.escapeHtml(this.job.clientPhone || '')}</p>
                    </div>
                </div>
                <div class="status-indicator">
                    <span class="status-dot ${statusClass}"></span>
                    <span class="status-text">${this.escapeHtml(this.job.status || 'Unknown')}</span>
                </div>
            </div>
        `;

        // Milestones Card
        html += `
            <div class="milestones-card">
                <div class="milestones-header">
                    <p class="section-title">Milestones</p>
                    <span class="milestones-count">${milestonesCompleted}/${milestonesTotal} Completed</span>
                </div>
                <div class="milestone-list">
                    ${this.renderMilestones()}
                </div>
            </div>
        `;

        return html;
    }

    renderMilestones() {
        if (!this.job.milestones || this.job.milestones.length === 0) {
            return '<p style="color: #9ca3af; font-size: 12px;">No milestones defined</p>';
        }

        const displayMilestones = this.job.milestones.slice(0, 4);
        const remaining = this.job.milestones.length - 4;

        let html = displayMilestones.map(milestone => {
            const completedClass = milestone.state ? 'completed' : '';
            const checkmark = milestone.state ? `
                <svg width="10" height="10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                </svg>
            ` : '';

            return `
                <div class="milestone-item">
                    <div class="milestone-left">
                        <div class="milestone-checkbox ${completedClass}">
                            ${checkmark}
                        </div>
                        <span class="milestone-title ${completedClass}">${this.escapeHtml(milestone.title || 'Untitled')}</span>
                    </div>
                    <span class="milestone-amount">$${this.formatNumber(milestone.amount || 0)}</span>
                </div>
            `;
        }).join('');

        if (remaining > 0) {
            html += `
                <div style="font-size: 10px; text-align: center; color: #9ca3af; padding-top: 8px; border-top: 1px solid #f3f4f6;">
                    + ${remaining} remaining
                </div>
            `;
        }

        return html;
    }

    calculateTotal(list, field) {
        if (!Array.isArray(list)) return 0;
        return list.reduce((sum, item) => sum + (parseFloat(item[field]) || 0), 0);
    }

    countCompletedMilestones() {
        if (!this.job.milestones) return 0;
        return this.job.milestones.filter(m => m.state === true).length;
    }

    calculatePaidAmount() {
        if (!this.job.milestones) return 0;
        return this.job.milestones
            .filter(m => m.state === true)
            .reduce((sum, m) => sum + (parseFloat(m.amount) || 0), 0);
    }

    getInitials(name) {
        if (!name) return 'NA';
        return name.substring(0, 2).toUpperCase();
    }

    formatNumber(num) {
        return num.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in app.js
window.JobVisualizer = JobVisualizer;