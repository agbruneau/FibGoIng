/**
 * Visualiseur de Flux D3.js pour l'intégration événementielle
 *
 * Fonctionnalités:
 * - Layout force-directed pour les nœuds
 * - Animation de particules pour les messages
 * - Zoom et pan
 * - Timeline avec replay
 * - Couleurs par pilier
 * - Connexion SSE pour temps réel
 */

// Couleurs par pilier
const PILLAR_COLORS = {
    applications: '#3b82f6',  // Bleu
    events: '#f97316',        // Orange
    data: '#22c55e'           // Vert
};

// Couleurs des statuts de service
const STATUS_COLORS = {
    running: '#22c55e',
    degraded: '#eab308',
    error: '#ef4444',
    stopped: '#6b7280'
};

/**
 * Classe principale du visualiseur de flux
 */
class FlowVisualizer {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);

        if (!this.container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        // Options par défaut
        this.options = {
            width: options.width || this.container.clientWidth || 800,
            height: options.height || this.container.clientHeight || 600,
            nodeRadius: options.nodeRadius || 40,
            linkDistance: options.linkDistance || 150,
            chargeStrength: options.chargeStrength || -300,
            animationDuration: options.animationDuration || 500,
            ...options
        };

        // État
        this.nodes = [];
        this.links = [];
        this.messages = [];
        this.timeline = [];
        this.isPlaying = false;
        this.currentTime = 0;

        // Éléments D3
        this.svg = null;
        this.simulation = null;
        this.zoom = null;
        this.mainGroup = null;

        // SSE connection
        this.eventSource = null;

        this.init();
    }

    /**
     * Initialise le visualiseur
     */
    init() {
        // Créer le SVG avec un fond visible
        this.svg = d3.select(`#${this.containerId}`)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${this.options.width} ${this.options.height}`)
            .attr('class', 'flow-visualizer')
            .style('background-color', '#111827');  // bg-gray-900 pour contraste

        // Définir les marqueurs de flèches
        this.defineMarkers();

        // Groupe principal pour le zoom
        this.mainGroup = this.svg.append('g').attr('class', 'main-group');

        // Couches
        this.linksGroup = this.mainGroup.append('g').attr('class', 'links');
        this.nodesGroup = this.mainGroup.append('g').attr('class', 'nodes');
        this.particlesGroup = this.mainGroup.append('g').attr('class', 'particles');
        this.labelsGroup = this.mainGroup.append('g').attr('class', 'labels');

        // Configurer le zoom
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.mainGroup.attr('transform', event.transform);
            });

        this.svg.call(this.zoom);

        // Créer la simulation force-directed
        this.simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.id).distance(this.options.linkDistance))
            .force('charge', d3.forceManyBody().strength(this.options.chargeStrength))
            .force('center', d3.forceCenter(this.options.width / 2, this.options.height / 2))
            .force('collision', d3.forceCollide().radius(this.options.nodeRadius + 10));

        // Listener pour resize
        window.addEventListener('resize', () => this.handleResize());
    }

    /**
     * Définit les marqueurs SVG (flèches)
     */
    defineMarkers() {
        const defs = this.svg.append('defs');

        // Marqueur de flèche pour chaque pilier
        Object.entries(PILLAR_COLORS).forEach(([pillar, color]) => {
            defs.append('marker')
                .attr('id', `arrow-${pillar}`)
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 20)
                .attr('refY', 0)
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .attr('orient', 'auto')
                .append('path')
                .attr('fill', color)
                .attr('d', 'M0,-5L10,0L0,5');
        });

        // Marqueur par défaut
        defs.append('marker')
            .attr('id', 'arrow-default')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('fill', '#94a3b8')
            .attr('d', 'M0,-5L10,0L0,5');
    }

    /**
     * Ajoute un nœud (service)
     */
    addNode(node) {
        const existingIndex = this.nodes.findIndex(n => n.id === node.id);

        const newNode = {
            id: node.id,
            name: node.name || node.id,
            type: node.type || 'service',
            pillar: node.pillar || 'applications',
            status: node.status || 'running',
            x: node.x || this.options.width / 2 + (Math.random() - 0.5) * 100,
            y: node.y || this.options.height / 2 + (Math.random() - 0.5) * 100,
            ...node
        };

        if (existingIndex >= 0) {
            this.nodes[existingIndex] = { ...this.nodes[existingIndex], ...newNode };
        } else {
            this.nodes.push(newNode);
        }

        this.update();
        return newNode;
    }

    /**
     * Supprime un nœud
     */
    removeNode(nodeId) {
        this.nodes = this.nodes.filter(n => n.id !== nodeId);
        this.links = this.links.filter(l => l.source.id !== nodeId && l.target.id !== nodeId);
        this.update();
    }

    /**
     * Ajoute un lien entre deux nœuds
     */
    addLink(link) {
        const existingIndex = this.links.findIndex(
            l => l.source.id === link.source && l.target.id === link.target
        );

        const newLink = {
            source: link.source,
            target: link.target,
            pillar: link.pillar || 'applications',
            type: link.type || 'sync',
            ...link
        };

        if (existingIndex < 0) {
            this.links.push(newLink);
            this.update();
        }

        return newLink;
    }

    /**
     * Met à jour la visualisation
     */
    update() {
        // Mise à jour des liens
        const link = this.linksGroup
            .selectAll('.link')
            .data(this.links, d => `${d.source.id || d.source}-${d.target.id || d.target}`);

        link.exit().remove();

        const linkEnter = link.enter()
            .append('line')
            .attr('class', 'link')
            .attr('stroke', d => PILLAR_COLORS[d.pillar] || '#94a3b8')
            .attr('stroke-width', 3)
            .attr('stroke-opacity', 0.8)
            .attr('marker-end', d => `url(#arrow-${d.pillar || 'default'})`);

        // Mise à jour des nœuds
        const node = this.nodesGroup
            .selectAll('.node')
            .data(this.nodes, d => d.id);

        node.exit().remove();

        const nodeEnter = node.enter()
            .append('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', (event, d) => this.dragStarted(event, d))
                .on('drag', (event, d) => this.dragged(event, d))
                .on('end', (event, d) => this.dragEnded(event, d)));

        // Rectangle pour le service
        nodeEnter.append('rect')
            .attr('width', this.options.nodeRadius * 2)
            .attr('height', this.options.nodeRadius * 1.5)
            .attr('x', -this.options.nodeRadius)
            .attr('y', -this.options.nodeRadius * 0.75)
            .attr('rx', 8)
            .attr('ry', 8)
            .attr('fill', d => PILLAR_COLORS[d.pillar] || '#3b82f6')
            .attr('stroke', d => STATUS_COLORS[d.status] || '#22c55e')
            .attr('stroke-width', 3);

        // Indicateur de statut
        nodeEnter.append('circle')
            .attr('class', 'status-indicator')
            .attr('cx', this.options.nodeRadius - 8)
            .attr('cy', -this.options.nodeRadius * 0.75 + 8)
            .attr('r', 6)
            .attr('fill', d => STATUS_COLORS[d.status] || '#22c55e');

        // Label du nœud
        nodeEnter.append('text')
            .attr('class', 'node-label')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .attr('fill', 'white')
            .attr('font-size', '12px')
            .attr('font-weight', 'bold')
            .text(d => d.name.substring(0, 12));

        // Mise à jour des propriétés
        this.nodesGroup.selectAll('.node')
            .select('rect')
            .attr('stroke', d => STATUS_COLORS[d.status] || '#22c55e');

        this.nodesGroup.selectAll('.node')
            .select('.status-indicator')
            .attr('fill', d => STATUS_COLORS[d.status] || '#22c55e');

        // Démarrer la simulation
        this.simulation.nodes(this.nodes);
        this.simulation.force('link').links(this.links);
        this.simulation.alpha(0.3).restart();

        // Callback tick
        this.simulation.on('tick', () => {
            this.linksGroup.selectAll('.link')
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            this.nodesGroup.selectAll('.node')
                .attr('transform', d => `translate(${d.x}, ${d.y})`);
        });
    }

    /**
     * Anime un message entre deux nœuds
     */
    animateMessage(from, to, payload = {}, options = {}) {
        const sourceNode = this.nodes.find(n => n.id === from);
        const targetNode = this.nodes.find(n => n.id === to);

        if (!sourceNode || !targetNode) {
            console.warn(`Cannot animate message: node not found (${from} -> ${to})`);
            return;
        }

        const duration = options.duration || this.options.animationDuration;
        const pillar = options.pillar || 'events';
        const color = PILLAR_COLORS[pillar] || '#f97316';

        // Créer la particule avec effet de brillance
        const particle = this.particlesGroup.append('circle')
            .attr('class', 'message-particle')
            .attr('r', 12)
            .attr('fill', color)
            .attr('cx', sourceNode.x)
            .attr('cy', sourceNode.y)
            .attr('opacity', 1)
            .style('filter', 'drop-shadow(0 0 6px ' + color + ')');

        // Effet de halo plus visible
        const halo = this.particlesGroup.append('circle')
            .attr('class', 'message-halo')
            .attr('r', 12)
            .attr('fill', 'none')
            .attr('stroke', color)
            .attr('stroke-width', 3)
            .attr('cx', sourceNode.x)
            .attr('cy', sourceNode.y)
            .attr('opacity', 1);

        // Animation
        particle.transition()
            .duration(duration)
            .attr('cx', targetNode.x)
            .attr('cy', targetNode.y)
            .on('end', () => {
                // Flash sur le nœud cible
                this.flashNode(to, color);
                particle.remove();
            });

        halo.transition()
            .duration(duration)
            .attr('cx', targetNode.x)
            .attr('cy', targetNode.y)
            .attr('r', 30)
            .attr('opacity', 0)
            .on('end', () => halo.remove());

        // Ajouter à la timeline
        this.timeline.push({
            type: 'message',
            from,
            to,
            payload,
            timestamp: Date.now()
        });
    }

    /**
     * Flash effet sur un nœud
     */
    flashNode(nodeId, color = '#ffffff') {
        const node = this.nodesGroup.selectAll('.node')
            .filter(d => d.id === nodeId);

        node.select('rect')
            .transition()
            .duration(100)
            .attr('fill', color)
            .transition()
            .duration(200)
            .attr('fill', d => PILLAR_COLORS[d.pillar] || '#3b82f6');
    }

    /**
     * Met à jour le statut d'un nœud
     */
    updateNodeStatus(nodeId, status) {
        const node = this.nodes.find(n => n.id === nodeId);
        if (node) {
            node.status = status;
            this.update();
        }
    }

    /**
     * Handlers de drag
     */
    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    /**
     * Gère le redimensionnement
     */
    handleResize() {
        const newWidth = this.container.clientWidth;
        const newHeight = this.container.clientHeight;

        this.options.width = newWidth;
        this.options.height = newHeight;

        this.svg.attr('viewBox', `0 0 ${newWidth} ${newHeight}`);
        this.simulation.force('center', d3.forceCenter(newWidth / 2, newHeight / 2));
        this.simulation.alpha(0.3).restart();
    }

    /**
     * Zoom sur un nœud spécifique
     */
    zoomToNode(nodeId) {
        const node = this.nodes.find(n => n.id === nodeId);
        if (!node) return;

        const scale = 1.5;
        const x = this.options.width / 2 - node.x * scale;
        const y = this.options.height / 2 - node.y * scale;

        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
    }

    /**
     * Reset du zoom
     */
    resetZoom() {
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity);
    }

    /**
     * Connecte au flux SSE
     */
    connectSSE(url = '/events/stream') {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource(url);

        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleSSEEvent(event.type || 'message', data);
        };

        // Handlers spécifiques par type d'événement
        ['queue_message', 'topic_publish', 'topic_delivered', 'dlq_message'].forEach(eventType => {
            this.eventSource.addEventListener(eventType, (event) => {
                const data = JSON.parse(event.data);
                this.handleSSEEvent(eventType, data);
            });
        });

        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
        };
    }

    /**
     * Gère les événements SSE
     */
    handleSSEEvent(eventType, data) {
        switch (eventType) {
            case 'queue_message':
            case 'topic_publish':
                if (data.message && data.message.source) {
                    const target = data.queue || data.topic;
                    this.animateMessage(data.message.source, target, data.message.payload, { pillar: 'events' });
                }
                break;

            case 'topic_delivered':
                this.flashNode(data.subscription_id, PILLAR_COLORS.events);
                break;

            case 'dlq_message':
                this.flashNode(data.dlq, '#ef4444');
                break;
        }
    }

    /**
     * Déconnecte du flux SSE
     */
    disconnectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    /**
     * Replay de la timeline
     */
    async replayTimeline(speed = 1) {
        this.isPlaying = true;

        for (const event of this.timeline) {
            if (!this.isPlaying) break;

            if (event.type === 'message') {
                this.animateMessage(event.from, event.to, event.payload);
                await new Promise(resolve => setTimeout(resolve, 1000 / speed));
            }
        }

        this.isPlaying = false;
    }

    /**
     * Arrête le replay
     */
    stopReplay() {
        this.isPlaying = false;
    }

    /**
     * Efface la timeline
     */
    clearTimeline() {
        this.timeline = [];
        this.currentTime = 0;
    }

    /**
     * Réinitialise le visualiseur
     */
    reset() {
        this.nodes = [];
        this.links = [];
        this.messages = [];
        this.timeline = [];
        this.nodesGroup.selectAll('.node').remove();
        this.linksGroup.selectAll('.link').remove();
        this.particlesGroup.selectAll('*').remove();
        this.resetZoom();
    }

    /**
     * Exporte l'état actuel
     */
    exportState() {
        return {
            nodes: this.nodes.map(n => ({ ...n, x: n.x, y: n.y })),
            links: this.links.map(l => ({
                source: l.source.id || l.source,
                target: l.target.id || l.target,
                pillar: l.pillar
            })),
            timeline: this.timeline
        };
    }

    /**
     * Importe un état
     */
    importState(state) {
        this.reset();

        if (state.nodes) {
            state.nodes.forEach(n => this.addNode(n));
        }

        if (state.links) {
            state.links.forEach(l => this.addLink(l));
        }

        if (state.timeline) {
            this.timeline = state.timeline;
        }
    }
}

/**
 * Initialise un visualiseur de flux
 */
function initFlowVisualizer(containerId, options = {}) {
    return new FlowVisualizer(containerId, options);
}

// Export pour utilisation globale
window.FlowVisualizer = FlowVisualizer;
window.initFlowVisualizer = initFlowVisualizer;
