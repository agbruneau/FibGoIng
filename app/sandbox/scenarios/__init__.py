"""Gestion des scénarios Sandbox."""
from typing import Optional


# Définition des scénarios
SCENARIOS = {
    # Scénarios Introduction
    "INTRO-01": {
        "id": "INTRO-01",
        "title": "Explorer l'écosystème",
        "description": "Découvrez les différents systèmes de l'écosystème d'assurance",
        "pillar": None,
        "complexity": 1,
        "steps": [
            {"id": 1, "title": "Découvrir les systèmes", "instruction": "Observez les systèmes disponibles dans l'écosystème"},
            {"id": 2, "title": "Identifier les connexions", "instruction": "Repérez comment les systèmes sont interconnectés"},
            {"id": 3, "title": "Comprendre les flux", "instruction": "Suivez un flux de données du début à la fin"},
            {"id": 4, "title": "Observer les événements", "instruction": "Identifiez les événements échangés"},
            {"id": 5, "title": "Analyser les patterns", "instruction": "Reconnaissez les patterns d'intégration utilisés"},
            {"id": 6, "title": "Synthèse", "instruction": "Résumez ce que vous avez appris"}
        ],
        "initial_state": {"services": [], "events": []}
    },
    "INTRO-02": {
        "id": "INTRO-02",
        "title": "Cartographie des flux",
        "description": "Cartographiez les flux de données entre systèmes",
        "pillar": None,
        "complexity": 1,
        "steps": [
            {"id": 1, "title": "Identifier les sources", "instruction": "Listez les systèmes sources de données"},
            {"id": 2, "title": "Identifier les cibles", "instruction": "Listez les systèmes consommateurs"},
            {"id": 3, "title": "Tracer les flux sync", "instruction": "Identifiez les appels API synchrones"},
            {"id": 4, "title": "Tracer les flux async", "instruction": "Identifiez les messages asynchrones"},
            {"id": 5, "title": "Tracer les flux data", "instruction": "Identifiez les flux de données batch"},
            {"id": 6, "title": "Documenter", "instruction": "Créez une vue d'ensemble"}
        ],
        "initial_state": {}
    },
    # Scénarios Applications
    "APP-01": {
        "id": "APP-01",
        "title": "Créer l'API Quote Engine",
        "description": "Concevez et implémentez l'API REST du moteur de devis",
        "pillar": "applications",
        "complexity": 1,
        "steps": [
            {"id": 1, "title": "Définir les ressources", "instruction": "Identifiez les ressources REST (quotes, customers...)"},
            {"id": 2, "title": "Concevoir les endpoints", "instruction": "Définissez les endpoints CRUD"},
            {"id": 3, "title": "Définir les payloads", "instruction": "Spécifiez les structures de données"},
            {"id": 4, "title": "Implémenter POST /quotes", "instruction": "Créez l'endpoint de création de devis"},
            {"id": 5, "title": "Implémenter GET /quotes/{id}", "instruction": "Créez l'endpoint de lecture"},
            {"id": 6, "title": "Tester l'API", "instruction": "Vérifiez que l'API fonctionne correctement"},
            {"id": 7, "title": "Documenter (OpenAPI)", "instruction": "Générez la documentation OpenAPI"}
        ],
        "initial_state": {"api_endpoints": []}
    },
    "APP-02": {
        "id": "APP-02",
        "title": "Gateway multi-partenaires",
        "description": "Implémentez un API Gateway avec routing et rate limiting",
        "pillar": "applications",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Configurer le routing", "instruction": "Définissez les règles de routage"},
            {"id": 2, "title": "Ajouter l'authentification", "instruction": "Implémentez la vérification des API keys"},
            {"id": 3, "title": "Configurer rate limiting", "instruction": "Limitez le nombre de requêtes"},
            {"id": 4, "title": "Ajouter logging", "instruction": "Tracez toutes les requêtes"},
            {"id": 5, "title": "Transformer les réponses", "instruction": "Adaptez les réponses si nécessaire"},
            {"id": 6, "title": "Tester le gateway", "instruction": "Vérifiez le bon fonctionnement"}
        ],
        "initial_state": {}
    },
    "APP-03": {
        "id": "APP-03",
        "title": "BFF Mobile vs Portail",
        "description": "Créez des APIs adaptées pour mobile et portail courtier",
        "pillar": "applications",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Analyser les besoins mobile", "instruction": "Identifiez les données nécessaires pour l'app mobile"},
            {"id": 2, "title": "Analyser les besoins courtier", "instruction": "Identifiez les données pour le portail courtier"},
            {"id": 3, "title": "Concevoir BFF Mobile", "instruction": "Créez l'API optimisée pour mobile"},
            {"id": 4, "title": "Concevoir BFF Courtier", "instruction": "Créez l'API complète pour courtiers"},
            {"id": 5, "title": "Implémenter les deux BFFs", "instruction": "Codez les deux versions"},
            {"id": 6, "title": "Comparer les réponses", "instruction": "Observez les différences"}
        ],
        "initial_state": {}
    },
    "APP-04": {
        "id": "APP-04",
        "title": "Vue 360° client",
        "description": "Agrégez les données de plusieurs sources pour une vue complète",
        "pillar": "applications",
        "complexity": 3,
        "steps": [
            {"id": 1, "title": "Identifier les sources", "instruction": "Listez tous les systèmes contenant des données client"},
            {"id": 2, "title": "Définir le schéma cible", "instruction": "Concevez la structure de la vue 360°"},
            {"id": 3, "title": "Implémenter les appels", "instruction": "Appelez chaque source de données"},
            {"id": 4, "title": "Gérer les erreurs partielles", "instruction": "Continuez même si une source échoue"},
            {"id": 5, "title": "Agréger les résultats", "instruction": "Fusionnez les données"},
            {"id": 6, "title": "Optimiser (parallélisme)", "instruction": "Appelez les sources en parallèle"},
            {"id": 7, "title": "Mettre en cache", "instruction": "Ajoutez du caching si approprié"}
        ],
        "initial_state": {}
    },
    "APP-05": {
        "id": "APP-05",
        "title": "Migration Strangler Fig",
        "description": "Migrez progressivement du legacy vers le nouveau système",
        "pillar": "applications",
        "complexity": 3,
        "steps": [
            {"id": 1, "title": "Identifier le périmètre", "instruction": "Choisissez la fonctionnalité à migrer"},
            {"id": 2, "title": "Créer l'ACL", "instruction": "Implémentez l'Anti-Corruption Layer"},
            {"id": 3, "title": "Router vers legacy", "instruction": "Configurez le routing initial vers le legacy"},
            {"id": 4, "title": "Implémenter le nouveau", "instruction": "Créez la nouvelle implémentation"},
            {"id": 5, "title": "Basculer progressivement", "instruction": "Routez une partie du trafic"},
            {"id": 6, "title": "Valider et finaliser", "instruction": "Complétez la migration"}
        ],
        "initial_state": {}
    },
    # Scénarios Événements
    "EVT-01": {
        "id": "EVT-01",
        "title": "Pub/Sub PolicyCreated",
        "description": "Publiez et consommez un événement de création de police",
        "pillar": "events",
        "complexity": 1,
        "steps": [
            {"id": 1, "title": "Définir l'événement", "instruction": "Spécifiez la structure de PolicyCreated"},
            {"id": 2, "title": "Créer le topic", "instruction": "Configurez le topic policies"},
            {"id": 3, "title": "Publier l'événement", "instruction": "Émettez PolicyCreated"},
            {"id": 4, "title": "Abonner Billing", "instruction": "Le service Billing s'abonne"},
            {"id": 5, "title": "Abonner Notifications", "instruction": "Le service Notifications s'abonne"},
            {"id": 6, "title": "Observer la diffusion", "instruction": "Vérifiez que tous reçoivent l'événement"}
        ],
        "initial_state": {}
    },
    "EVT-02": {
        "id": "EVT-02",
        "title": "Queue traitement claims",
        "description": "Traitez les réclamations via une queue point-à-point",
        "pillar": "events",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Créer la queue", "instruction": "Configurez la queue claims"},
            {"id": 2, "title": "Envoyer un claim", "instruction": "Ajoutez une réclamation à la queue"},
            {"id": 3, "title": "Traiter le claim", "instruction": "Un worker consomme et traite"},
            {"id": 4, "title": "Envoyer plusieurs claims", "instruction": "Ajoutez 5 réclamations"},
            {"id": 5, "title": "Ajouter des workers", "instruction": "Scaling horizontal des consommateurs"},
            {"id": 6, "title": "Observer le traitement parallèle", "instruction": "Vérifiez la distribution"}
        ],
        "initial_state": {}
    },
    "EVT-03": {
        "id": "EVT-03",
        "title": "Event Sourcing police",
        "description": "Reconstruisez l'état d'une police depuis ses événements",
        "pillar": "events",
        "complexity": 3,
        "steps": [
            {"id": 1, "title": "Définir les événements", "instruction": "PolicyCreated, Activated, Modified, Cancelled"},
            {"id": 2, "title": "Créer une police", "instruction": "Émettez PolicyCreated"},
            {"id": 3, "title": "Modifier la police", "instruction": "Émettez PolicyModified plusieurs fois"},
            {"id": 4, "title": "Visualiser le journal", "instruction": "Affichez la séquence d'événements"},
            {"id": 5, "title": "Reconstruire l'état", "instruction": "Rejouez pour obtenir l'état actuel"},
            {"id": 6, "title": "Remonter le temps", "instruction": "Reconstituez un état passé"}
        ],
        "initial_state": {}
    },
    "EVT-04": {
        "id": "EVT-04",
        "title": "Saga souscription",
        "description": "Orchestrez une souscription multi-étapes avec compensation",
        "pillar": "events",
        "complexity": 3,
        "steps": [
            {"id": 1, "title": "Définir les étapes", "instruction": "Quote→Policy→Billing→Documents"},
            {"id": 2, "title": "Définir les compensations", "instruction": "Rollback pour chaque étape"},
            {"id": 3, "title": "Exécuter avec succès", "instruction": "Complétez toutes les étapes"},
            {"id": 4, "title": "Simuler un échec", "instruction": "Faites échouer l'étape Billing"},
            {"id": 5, "title": "Observer la compensation", "instruction": "Vérifiez le rollback automatique"},
            {"id": 6, "title": "Analyser les logs", "instruction": "Suivez le workflow complet"}
        ],
        "initial_state": {}
    },
    "EVT-05": {
        "id": "EVT-05",
        "title": "CQRS reporting",
        "description": "Séparez le modèle transactionnel du modèle de lecture",
        "pillar": "events",
        "complexity": 3,
        "steps": [
            {"id": 1, "title": "Définir le modèle write", "instruction": "Structure pour les commandes"},
            {"id": 2, "title": "Définir le modèle read", "instruction": "Structure optimisée pour les requêtes"},
            {"id": 3, "title": "Créer les projections", "instruction": "Transformez événements en vues"},
            {"id": 4, "title": "Exécuter des commandes", "instruction": "Modifiez via le modèle write"},
            {"id": 5, "title": "Synchroniser les projections", "instruction": "Mettez à jour le modèle read"},
            {"id": 6, "title": "Comparer les performances", "instruction": "Mesurez les temps de réponse"}
        ],
        "initial_state": {}
    },
    "EVT-06": {
        "id": "EVT-06",
        "title": "Outbox pattern",
        "description": "Garantissez l'atomicité entre DB et publication d'événement",
        "pillar": "events",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Créer la table outbox", "instruction": "Table pour les événements en attente"},
            {"id": 2, "title": "Transaction atomique", "instruction": "Écrivez données ET outbox ensemble"},
            {"id": 3, "title": "Configurer le polling", "instruction": "Processus qui lit l'outbox"},
            {"id": 4, "title": "Publier et marquer", "instruction": "Publiez puis marquez comme traité"},
            {"id": 5, "title": "Gérer les doublons", "instruction": "Idempotence côté consommateur"},
            {"id": 6, "title": "Simuler une panne", "instruction": "Vérifiez la récupération"}
        ],
        "initial_state": {}
    },
    "EVT-07": {
        "id": "EVT-07",
        "title": "Dead Letter handling",
        "description": "Gérez les messages qui ne peuvent être traités",
        "pillar": "events",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Configurer la DLQ", "instruction": "Créez la Dead Letter Queue"},
            {"id": 2, "title": "Définir la politique retry", "instruction": "3 tentatives avec backoff"},
            {"id": 3, "title": "Envoyer un message valide", "instruction": "Traitement normal"},
            {"id": 4, "title": "Envoyer un message poison", "instruction": "Message qui échoue toujours"},
            {"id": 5, "title": "Observer les retries", "instruction": "Suivez les tentatives"},
            {"id": 6, "title": "Analyser la DLQ", "instruction": "Inspectez les messages en erreur"},
            {"id": 7, "title": "Retraiter manuellement", "instruction": "Corrigez et rejouez"}
        ],
        "initial_state": {}
    },
    # Scénarios Data
    "DATA-01": {
        "id": "DATA-01",
        "title": "ETL batch sinistres",
        "description": "Pipeline ETL classique pour exporter les sinistres",
        "pillar": "data",
        "complexity": 1,
        "steps": [
            {"id": 1, "title": "Définir la source", "instruction": "Claims Management comme source"},
            {"id": 2, "title": "Définir la cible", "instruction": "Data Warehouse comme destination"},
            {"id": 3, "title": "Extract", "instruction": "Extrayez les données source"},
            {"id": 4, "title": "Transform", "instruction": "Nettoyez et transformez"},
            {"id": 5, "title": "Load", "instruction": "Chargez dans la cible"},
            {"id": 6, "title": "Valider", "instruction": "Vérifiez l'intégrité"}
        ],
        "initial_state": {}
    },
    "DATA-02": {
        "id": "DATA-02",
        "title": "CDC temps réel polices",
        "description": "Capturez les changements en temps réel",
        "pillar": "data",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Configurer le CDC", "instruction": "Activez la capture sur la table policies"},
            {"id": 2, "title": "Créer une police", "instruction": "INSERT déclenche un événement"},
            {"id": 3, "title": "Modifier une police", "instruction": "UPDATE déclenche un événement"},
            {"id": 4, "title": "Observer le stream", "instruction": "Visualisez les changements capturés"},
            {"id": 5, "title": "Consumer le stream", "instruction": "Appliquez à la cible"},
            {"id": 6, "title": "Vérifier la latence", "instruction": "Mesurez le délai de propagation"}
        ],
        "initial_state": {}
    },
    "DATA-03": {
        "id": "DATA-03",
        "title": "Pipeline renouvellements",
        "description": "Orchestrez un pipeline de données complexe",
        "pillar": "data",
        "complexity": 3,
        "steps": [
            {"id": 1, "title": "Identifier les polices à renouveler", "instruction": "Extract polices expirant"},
            {"id": 2, "title": "Enrichir avec données clients", "instruction": "Join avec Customer Hub"},
            {"id": 3, "title": "Calculer nouvelles primes", "instruction": "Appliquer règles tarifaires"},
            {"id": 4, "title": "Générer les courriers", "instruction": "Créer documents de renouvellement"},
            {"id": 5, "title": "Créer les factures prévisionnelles", "instruction": "Alimenter Billing"},
            {"id": 6, "title": "Notifier les clients", "instruction": "Déclencher les notifications"},
            {"id": 7, "title": "Monitorer le pipeline", "instruction": "Vérifier l'exécution complète"}
        ],
        "initial_state": {}
    },
    "DATA-04": {
        "id": "DATA-04",
        "title": "MDM client",
        "description": "Master Data Management pour avoir un golden record client",
        "pillar": "data",
        "complexity": 3,
        "steps": [
            {"id": 1, "title": "Identifier les sources", "instruction": "PAS, Claims, Billing ont des données client"},
            {"id": 2, "title": "Définir les règles de matching", "instruction": "Comment identifier le même client"},
            {"id": 3, "title": "Définir les règles de merge", "instruction": "Quelle valeur garder en cas de conflit"},
            {"id": 4, "title": "Créer le golden record", "instruction": "Fusionnez les données"},
            {"id": 5, "title": "Propager les mises à jour", "instruction": "Synchronisez vers les sources"},
            {"id": 6, "title": "Gérer un conflit", "instruction": "Résolvez un cas d'homonymie"}
        ],
        "initial_state": {}
    },
    "DATA-05": {
        "id": "DATA-05",
        "title": "Contrôle qualité",
        "description": "Implémentez des contrôles de qualité de données",
        "pillar": "data",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Définir les règles", "instruction": "Complétude, validité, cohérence"},
            {"id": 2, "title": "Profiler les données", "instruction": "Analysez les distributions"},
            {"id": 3, "title": "Exécuter les contrôles", "instruction": "Détectez les anomalies"},
            {"id": 4, "title": "Générer le rapport", "instruction": "Visualisez les résultats"},
            {"id": 5, "title": "Alerter sur les seuils", "instruction": "Notification si qualité dégradée"},
            {"id": 6, "title": "Corriger les données", "instruction": "Appliquez des corrections"}
        ],
        "initial_state": {}
    },
    "DATA-06": {
        "id": "DATA-06",
        "title": "Data virtualization",
        "description": "Créez une vue fédérée sans copie de données",
        "pillar": "data",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Définir la vue virtuelle", "instruction": "Schéma unifié des sources"},
            {"id": 2, "title": "Configurer les connecteurs", "instruction": "Accès aux sources"},
            {"id": 3, "title": "Exécuter une requête simple", "instruction": "Lecture depuis une source"},
            {"id": 4, "title": "Exécuter une requête fédérée", "instruction": "Join entre sources"},
            {"id": 5, "title": "Comparer avec copie physique", "instruction": "ETL vs virtualisation"},
            {"id": 6, "title": "Analyser la performance", "instruction": "Quand utiliser chaque approche"}
        ],
        "initial_state": {}
    },
    "DATA-07": {
        "id": "DATA-07",
        "title": "Data lineage",
        "description": "Tracez l'origine et les transformations des données",
        "pillar": "data",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Identifier un KPI", "instruction": "Ex: taux de sinistralité"},
            {"id": 2, "title": "Tracer vers les sources", "instruction": "D'où viennent les données"},
            {"id": 3, "title": "Documenter les transformations", "instruction": "Calculs appliqués"},
            {"id": 4, "title": "Visualiser le lineage", "instruction": "Graphe de dépendances"},
            {"id": 5, "title": "Impact analysis", "instruction": "Que se passe-t-il si une source change"},
            {"id": 6, "title": "Audit trail", "instruction": "Qui a modifié quoi et quand"}
        ],
        "initial_state": {}
    },
    # Scénarios Cross-cutting
    "CROSS-01": {
        "id": "CROSS-01",
        "title": "Panne tarificateur externe",
        "description": "Gérez la panne du service de tarification externe",
        "pillar": "cross_cutting",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Appel normal", "instruction": "Le tarificateur répond correctement"},
            {"id": 2, "title": "Simuler une lenteur", "instruction": "Timeout sur l'appel"},
            {"id": 3, "title": "Activer le circuit breaker", "instruction": "Ouvrez le circuit après N échecs"},
            {"id": 4, "title": "Utiliser le fallback", "instruction": "Utilisez un tarif par défaut"},
            {"id": 5, "title": "Restaurer le service", "instruction": "Le tarificateur revient"},
            {"id": 6, "title": "Fermer le circuit", "instruction": "Reprenez les appels normaux"}
        ],
        "initial_state": {}
    },
    "CROSS-02": {
        "id": "CROSS-02",
        "title": "Tracing distribué",
        "description": "Suivez une requête à travers tous les services",
        "pillar": "cross_cutting",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Générer un trace ID", "instruction": "ID unique pour la requête"},
            {"id": 2, "title": "Propager le contexte", "instruction": "Headers entre services"},
            {"id": 3, "title": "Instrumenter les appels", "instruction": "Log avec trace ID"},
            {"id": 4, "title": "Visualiser la trace", "instruction": "Waterfall des appels"},
            {"id": 5, "title": "Identifier un goulot", "instruction": "Trouvez le service lent"},
            {"id": 6, "title": "Corréler les logs", "instruction": "Tous les logs d'une requête"}
        ],
        "initial_state": {}
    },
    "CROSS-03": {
        "id": "CROSS-03",
        "title": "Sécuriser gateway",
        "description": "Implémentez l'authentification et l'autorisation",
        "pillar": "cross_cutting",
        "complexity": 2,
        "steps": [
            {"id": 1, "title": "Configurer OAuth", "instruction": "Provider d'identité"},
            {"id": 2, "title": "Générer un JWT", "instruction": "Token avec claims"},
            {"id": 3, "title": "Valider le token", "instruction": "Vérification signature"},
            {"id": 4, "title": "Extraire les droits", "instruction": "Rôles et permissions"},
            {"id": 5, "title": "Appliquer RBAC", "instruction": "Autorisation basée rôles"},
            {"id": 6, "title": "Refuser un accès", "instruction": "403 si non autorisé"}
        ],
        "initial_state": {}
    },
    "CROSS-04": {
        "id": "CROSS-04",
        "title": "Écosystème complet",
        "description": "Intégrez les trois piliers dans un scénario complet",
        "pillar": "cross_cutting",
        "complexity": 4,
        "steps": [
            {"id": 1, "title": "Réception demande devis", "instruction": "API Gateway reçoit la requête"},
            {"id": 2, "title": "Calcul du devis", "instruction": "Quote Engine calcule (API)"},
            {"id": 3, "title": "Création de la police", "instruction": "PAS crée la police"},
            {"id": 4, "title": "Publication PolicyCreated", "instruction": "Événement publié (Events)"},
            {"id": 5, "title": "Facturation déclenchée", "instruction": "Billing reçoit et facture"},
            {"id": 6, "title": "Notification client", "instruction": "Email envoyé"},
            {"id": 7, "title": "Sync Data Warehouse", "instruction": "CDC propage au DWH (Data)"},
            {"id": 8, "title": "Mise à jour reporting", "instruction": "Dashboard mis à jour"},
            {"id": 9, "title": "Panne simulée", "instruction": "Billing tombe, circuit breaker"},
            {"id": 10, "title": "Récupération", "instruction": "Reprise après panne"}
        ],
        "initial_state": {}
    }
}


def get_scenario(scenario_id: str) -> Optional[dict]:
    """Retourne un scénario par son ID."""
    return SCENARIOS.get(scenario_id)


def get_all_scenarios() -> list:
    """Retourne tous les scénarios."""
    return list(SCENARIOS.values())


def get_scenarios_by_pillar(pillar: str) -> list:
    """Retourne les scénarios d'un pilier."""
    return [s for s in SCENARIOS.values() if s.get("pillar") == pillar]
