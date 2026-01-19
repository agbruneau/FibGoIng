package main

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/agbru/kafka-eda-lab/internal/kafka"
	"github.com/agbru/kafka-eda-lab/internal/models"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

//go:embed templates/*
var templatesFS embed.FS

//go:embed static/*
var staticFS embed.FS

const (
	defaultHTTPPort = "8080"
)

// EventBus gère la diffusion des événements SSE
type EventBus struct {
	clients    map[chan []byte]bool
	register   chan chan []byte
	unregister chan chan []byte
	broadcast  chan []byte
	mu         sync.RWMutex
}

// NewEventBus crée un nouveau bus d'événements
func NewEventBus() *EventBus {
	return &EventBus{
		clients:    make(map[chan []byte]bool),
		register:   make(chan chan []byte),
		unregister: make(chan chan []byte),
		broadcast:  make(chan []byte, 100),
	}
}

// Run démarre le bus d'événements
func (eb *EventBus) Run() {
	for {
		select {
		case client := <-eb.register:
			eb.mu.Lock()
			eb.clients[client] = true
			eb.mu.Unlock()
			log.Printf("[EventBus] Client connecté (%d clients)", len(eb.clients))

		case client := <-eb.unregister:
			eb.mu.Lock()
			if _, ok := eb.clients[client]; ok {
				delete(eb.clients, client)
				close(client)
			}
			eb.mu.Unlock()
			log.Printf("[EventBus] Client déconnecté (%d clients)", len(eb.clients))

		case message := <-eb.broadcast:
			eb.mu.RLock()
			for client := range eb.clients {
				select {
				case client <- message:
				default:
					// Client trop lent, on saute
				}
			}
			eb.mu.RUnlock()
		}
	}
}

// Broadcast envoie un événement à tous les clients
func (eb *EventBus) Broadcast(eventType string, data interface{}) {
	event := map[string]interface{}{
		"type":      eventType,
		"data":      data,
		"timestamp": time.Now().Format(time.RFC3339),
	}

	jsonData, err := json.Marshal(event)
	if err != nil {
		log.Printf("[EventBus] Erreur de sérialisation: %v", err)
		return
	}

	eb.broadcast <- jsonData
}

// Dashboard contient l'état du dashboard
type Dashboard struct {
	eventBus *EventBus
	consumer *kafka.Consumer
	tmpl     *template.Template
}

// NewDashboard crée un nouveau dashboard
func NewDashboard(eventBus *EventBus, consumer *kafka.Consumer) (*Dashboard, error) {
	// Parser les templates
	tmpl, err := template.ParseFS(templatesFS, "templates/*.html")
	if err != nil {
		return nil, fmt.Errorf("erreur lors du parsing des templates: %w", err)
	}

	return &Dashboard{
		eventBus: eventBus,
		consumer: consumer,
		tmpl:     tmpl,
	}, nil
}

// RegisterRoutes enregistre les routes HTTP
func (d *Dashboard) RegisterRoutes(mux *http.ServeMux) {
	// Pages
	mux.HandleFunc("/", d.handleIndex)
	mux.HandleFunc("/events", d.handleEvents)
	mux.HandleFunc("/stats", d.handleStats)
	mux.HandleFunc("/docs", d.handleDocs)
	mux.HandleFunc("/docs/", d.handleDocs)

	// SSE endpoint
	mux.HandleFunc("/api/sse", d.handleSSE)

	// API stats
	mux.HandleFunc("/api/stats", d.handleAPIStats)

	// Fichiers statiques
	mux.Handle("/static/", http.FileServer(http.FS(staticFS)))
}

// handleIndex affiche la page d'accueil
func (d *Dashboard) handleIndex(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{
		"Title": "Dashboard",
		"Page":  "index",
	}
	d.render(w, "index.html", data)
}

// handleEvents affiche la page des événements
func (d *Dashboard) handleEvents(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{
		"Title": "Événements",
		"Page":  "events",
	}
	d.render(w, "events.html", data)
}

// handleStats affiche la page des statistiques
func (d *Dashboard) handleStats(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{
		"Title": "Statistiques",
		"Page":  "stats",
	}
	d.render(w, "stats.html", data)
}

// handleDocs affiche la documentation
func (d *Dashboard) handleDocs(w http.ResponseWriter, r *http.Request) {
	data := map[string]interface{}{
		"Title": "Documentation",
		"Page":  "docs",
	}
	d.render(w, "docs.html", data)
}

// handleSSE gère les connexions Server-Sent Events
func (d *Dashboard) handleSSE(w http.ResponseWriter, r *http.Request) {
	// Configurer les headers SSE
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	// Créer un canal pour ce client
	clientChan := make(chan []byte, 10)
	d.eventBus.register <- clientChan

	// S'assurer de nettoyer quand le client se déconnecte
	defer func() {
		d.eventBus.unregister <- clientChan
	}()

	// Flusher pour envoyer immédiatement
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "SSE non supporté", http.StatusInternalServerError)
		return
	}

	// Envoyer un ping initial
	fmt.Fprintf(w, "event: ping\ndata: connected\n\n")
	flusher.Flush()

	// Boucle d'envoi des événements
	for {
		select {
		case <-r.Context().Done():
			return
		case msg := <-clientChan:
			fmt.Fprintf(w, "event: message\ndata: %s\n\n", msg)
			flusher.Flush()
		}
	}
}

// handleAPIStats retourne les statistiques en JSON
func (d *Dashboard) handleAPIStats(w http.ResponseWriter, r *http.Request) {
	stats := map[string]interface{}{
		"timestamp": time.Now().Format(time.RFC3339),
		"services": map[string]interface{}{
			"quotation": map[string]interface{}{
				"status": "running",
				"url":    "http://localhost:8081",
			},
			"souscription": map[string]interface{}{
				"status": "running",
				"url":    "http://localhost:8082",
			},
			"reclamation": map[string]interface{}{
				"status": "running",
				"url":    "http://localhost:8083",
			},
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// render affiche un template
func (d *Dashboard) render(w http.ResponseWriter, name string, data interface{}) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := d.tmpl.ExecuteTemplate(w, name, data); err != nil {
		log.Printf("[Dashboard] Erreur de rendu template %s: %v", name, err)
		http.Error(w, "Erreur interne", http.StatusInternalServerError)
	}
}

// setupKafkaHandlers configure les handlers Kafka pour la diffusion SSE
func setupKafkaHandlers(consumer *kafka.Consumer, eventBus *EventBus) {
	topics := []string{
		models.TopicDevisGenere,
		models.TopicDevisExpire,
		models.TopicContratEmis,
		models.TopicContratModifie,
		models.TopicContratResilie,
		models.TopicSinistreDeclare,
		models.TopicSinistreEvalue,
		models.TopicIndemnisationEffectuee,
	}

	for _, topic := range topics {
		t := topic // Capture pour la closure
		consumer.RegisterHandler(t, func(ctx context.Context, msg *kafka.ReceivedMessage) error {
			// Décoder le message
			var event map[string]interface{}
			if err := json.Unmarshal(msg.Value, &event); err != nil {
				return err
			}

			// Extraire le type d'événement
			eventType, _ := event["type"].(string)

			// Diffuser via SSE
			eventBus.Broadcast(eventType, event)

			return nil
		})
	}
}

func main() {
	log.SetOutput(os.Stdout)
	log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)

	fmt.Println("=======================================")
	fmt.Println("  kafka-eda-lab - Dashboard")
	fmt.Println("  Simulation EDA avec Apache Kafka")
	fmt.Println("=======================================")
	fmt.Println()

	// Configuration
	httpPort := getEnv("HTTP_PORT", defaultHTTPPort)

	// Créer le bus d'événements
	eventBus := NewEventBus()
	go eventBus.Run()

	// Configuration Kafka (optionnel, le dashboard peut fonctionner sans)
	var consumer *kafka.Consumer
	kafkaConfig := kafka.NewConfigFromEnv()
	kafkaConfig.ClientID = "dashboard"
	kafkaConfig.GroupID = "dashboard-group"

	consumer, err := kafka.NewConsumer(kafkaConfig)
	if err != nil {
		log.Printf("[Dashboard] Kafka non disponible: %v", err)
		log.Println("[Dashboard] Le dashboard fonctionnera sans flux temps réel")
	} else {
		setupKafkaHandlers(consumer, eventBus)

		// Démarrer la consommation
		ctx := context.Background()
		topics := []string{
			models.TopicDevisGenere,
			models.TopicDevisExpire,
			models.TopicContratEmis,
			models.TopicContratModifie,
			models.TopicContratResilie,
			models.TopicSinistreDeclare,
			models.TopicSinistreEvalue,
			models.TopicIndemnisationEffectuee,
		}
		if err := consumer.Start(ctx, topics); err != nil {
			log.Printf("[Dashboard] Erreur démarrage Kafka consumer: %v", err)
		}
	}

	// Créer le dashboard
	dashboard, err := NewDashboard(eventBus, consumer)
	if err != nil {
		log.Fatalf("Erreur lors de la création du dashboard: %v", err)
	}

	// Configurer le router
	mux := http.NewServeMux()
	dashboard.RegisterRoutes(mux)

	// Ajouter l'endpoint des métriques Prometheus
	mux.Handle("/metrics", promhttp.Handler())

	// Créer le serveur HTTP
	server := &http.Server{
		Addr:         ":" + httpPort,
		Handler:      loggingMiddleware(mux),
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 0, // Pas de timeout pour SSE
		IdleTimeout:  60 * time.Second,
	}

	// Démarrer le serveur HTTP
	go func() {
		log.Printf("[Dashboard] Serveur HTTP démarré sur le port %s", httpPort)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Erreur du serveur HTTP: %v", err)
		}
	}()

	fmt.Println("Dashboard prêt!")
	fmt.Printf("  - Dashboard:       http://localhost:%s\n", httpPort)
	fmt.Println("  - Grafana:         http://localhost:3000")
	fmt.Println("  - Jaeger:          http://localhost:16686")
	fmt.Println("  - Kafka UI:        http://localhost:8090")
	fmt.Println("  - Prometheus:      http://localhost:9090")
	fmt.Println()
	fmt.Println("Services:")
	fmt.Println("  - Quotation:       http://localhost:8081")
	fmt.Println("  - Souscription:    http://localhost:8082")
	fmt.Println("  - Réclamation:     http://localhost:8083")
	fmt.Println()

	// Attendre un signal d'arrêt
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	fmt.Println()
	log.Println("[Dashboard] Arrêt en cours...")

	// Arrêter proprement
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("Erreur lors de l'arrêt du serveur HTTP: %v", err)
	}

	if consumer != nil {
		consumer.Close()
	}

	log.Println("[Dashboard] Arrêté")
}

// getEnv retourne la valeur d'une variable d'environnement ou une valeur par défaut
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// loggingMiddleware ajoute le logging des requêtes
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Ne pas logger les requêtes SSE (trop verbeux)
		if r.URL.Path != "/api/sse" {
			start := time.Now()
			next.ServeHTTP(w, r)
			log.Printf("[HTTP] %s %s - %v", r.Method, r.URL.Path, time.Since(start))
		} else {
			next.ServeHTTP(w, r)
		}
	})
}
