# PRD — FibGo Enterprise Readiness

**Projet :** agbruneau/FibGo
**Version :** Post-évaluation Gemini 3.1
**Date :** 20 février 2026
**Auteur :** Andre-Guy Bruneau
**Statut :** Brouillon

---

## Énoncé du problème

FibGo est un outil de calcul de Fibonacci haute performance en Go, évalué à **8.6/10** par l'audit Gemini 3.1. Malgré une architecture et un code de qualité excellente, le projet présente des lacunes en **testabilité** (7.5/10) et **gouvernance open-source** (7.5/10) qui freinent son adoption en environnement entreprise. Sans ces améliorations, FibGo reste un « prototype mature » incapable d'intégrer des pipelines de calcul tiers ou des serveurs de calcul distribués avec les garanties de fiabilité exigées en production.

---

## Objectifs

1. **Atteindre une couverture de tests ≥ 90%** sur le code critique (`internal/fibonacci/`, `internal/bigfft/`) avec validation par fuzzing natif Go.
2. **Institutionnaliser la collaboration** via des templates GitHub standardisés et une gouvernance OSS complète.
3. **Rendre les métriques exportables** aux formats industriels (Prometheus/OpenTelemetry) pour intégration dans des stacks d'observabilité existantes.
4. **Améliorer l'extensibilité** en extrayant les interfaces des stratégies algorithmiques dans un package partagé.
5. **Documenter l'API publique** avec des exemples d'utilisation en tant que bibliothèque Go et un diagramme C4.

---

## Non-objectifs

1. **Réécriture architecturale** — L'architecture existante (score 9.5/10) est solide. On l'étend, on ne la refond pas.
2. **Support multi-langage** — FibGo reste un projet Go pur. Pas de bindings Python/Rust à ce stade.
3. **Interface web ou API REST** — Le périmètre reste CLI et bibliothèque Go importable.
4. **Marketing / croissance communautaire active** — On pose les bases de gouvernance, sans campagne d'acquisition de contributeurs.
5. **Certification de sécurité formelle** — L'audit `unsafe` est documenté, mais aucune certification FIPS ou équivalente n'est visée.

---

## User Stories

### Développeur intégrateur

- **En tant que** développeur backend, **je veux** importer FibGo comme bibliothèque dans mon projet Go **afin de** calculer des nombres de Fibonacci massifs sans réimplémenter les algorithmes optimisés.
- **En tant que** développeur, **je veux** des interfaces claires pour les stratégies algorithmiques **afin de** pouvoir injecter mes propres algorithmes sans modifier le code source de FibGo.

### Ingénieur SRE / Ops

- **En tant qu'** ingénieur SRE, **je veux** que FibGo exporte ses métriques au format Prometheus **afin de** l'intégrer dans mon stack Grafana existant.
- **En tant qu'** ingénieur Ops, **je veux** des logs structurés JSON via `slog` **afin de** les ingérer dans mon pipeline ELK/Loki.

### Contributeur open-source

- **En tant que** contributeur potentiel, **je veux** des templates d'issues et de PR clairs **afin de** soumettre mes contributions dans un cadre structuré.
- **En tant que** nouveau contributeur, **je veux** un Code of Conduct **afin de** comprendre les normes de comportement attendues.

### Architecte / Évaluateur

- **En tant qu'** architecte, **je veux** un diagramme C4 dans le README **afin de** comprendre rapidement les interactions internes du système.
- **En tant qu'** évaluateur, **je veux** une couverture de tests ≥ 90% avec fuzzing **afin de** valider la fiabilité arithmétique pour des cas limites massifs.

---

## Exigences

### P0 — Must-Have (Phase 1)

| # | Exigence | Critères d'acceptation |
|---|----------|----------------------|
| R1 | **Fuzz testing natif Go** sur Fast Doubling et FFT | Pipeline CI avec `go test -fuzz` couvrant les entrées pseudo-aléatoires massives. Aucune panique ou erreur de précision détectée sur 10 000 itérations. |
| R2 | **Templates GitHub** : issue (bug report, feature request) + PR template | Fichiers `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/pull_request_template.md` créés et fonctionnels. |
| R3 | **Couverture de code ≥ 90%** sur `internal/fibonacci/` et `internal/bigfft/` | Badge de couverture mis à jour. Rapport `go test -cover` montrant ≥ 90% par package. |

### P1 — Nice-to-Have (Phase 2)

| # | Exigence | Critères d'acceptation |
|---|----------|----------------------|
| R4 | **Extraction des interfaces algorithmiques** dans un package `internal/strategy/` | Interface `Calculator` définie. Fast Doubling et Strassen l'implémentent. Un exemple de stratégie custom compile et passe les tests. |
| R5 | **Audit de complexité cyclomatique** sur `internal/bigfft/` | Rapport `gocyclo` ou équivalent. Fonctions > 15 de complexité refactorées ou documentées avec justification. |
| R6 | **Diagramme C4** (Context + Container) dans le README | Diagramme Mermaid ou image SVG intégré. Revue par un pair validant la fidélité au code. |
| R7 | **Export métriques Prometheus/OpenTelemetry** depuis `internal/metrics/` | Endpoint `/metrics` ou exporter configuré. Métriques visibles dans un Prometheus local de test. |

### P2 — Future Considerations (Phase 3)

| # | Exigence | Critères d'acceptation |
|---|----------|----------------------|
| R8 | **Isolation du bump allocator** en module autonome | Package `internal/allocator/` utilisable indépendamment. Tests unitaires dédiés. Documentation API. |
| R9 | **Documentation des usages `unsafe`** | Chaque appel `unsafe` documenté avec justification, risques et invariants. Revue de sécurité mémoire. |
| R10 | **Exemples d'utilisation bibliothèque** dans le README | Section « Library Usage » avec ≥ 2 exemples exécutables (`go run`). |
| R11 | **Logs structurés JSON via `slog`** | Mode `--log-format=json` fonctionnel. Sortie parsable par `jq`. |
| R12 | **Code of Conduct** (Contributor Covenant) | Fichier `CODE_OF_CONDUCT.md` à la racine. Référencé dans `CONTRIBUTING.md`. |

---

## Métriques de succès

### Indicateurs avancés (leading)

| Métrique | Cible | Mesure |
|----------|-------|--------|
| Couverture de code globale | ≥ 90% | `go test -cover ./...` |
| Couverture fuzz (itérations sans crash) | 10 000 | Rapport CI fuzz testing |
| Nombre de fonctions à complexité cyclomatique > 15 | 0 (ou documentées) | `gocyclo` report |

### Indicateurs retardés (lagging)

| Métrique | Cible (6 mois) | Mesure |
|----------|----------------|--------|
| Issues ouvertes par des contributeurs externes | ≥ 5 | GitHub Insights |
| PRs soumises par des contributeurs externes | ≥ 2 | GitHub Insights |
| Intégrations documentées utilisant FibGo comme bibliothèque | ≥ 1 | Recherche GitHub / go.pkg.dev |

---

## Questions ouvertes

| # | Question | Responsable |
|---|----------|-------------|
| Q1 | Le bump allocator justifie-t-il un module Go séparé (hors monorepo) ou reste-t-il `internal/` ? | **Engineering** |
| Q2 | Quel format de diagramme C4 privilégier : Mermaid (maintenable en code) ou SVG exporté (plus lisible) ? | **Engineering / Design** |
| Q3 | Faut-il exposer un endpoint HTTP pour les métriques Prometheus, ou se limiter à un exporter en mode push ? | **Engineering / Ops** |
| Q4 | Le fuzzing doit-il être exécuté en CI à chaque PR (coût en temps) ou uniquement en nightly build ? | **Engineering** |

---

## Considérations de calendrier

### Phase 1 — Fondations (Semaines 1-3)

- **R1** Fuzz testing natif Go
- **R2** Templates GitHub
- **R3** Couverture ≥ 90%

*Dépendance :* Aucune. Travail parallélisable.

### Phase 2 — Extensibilité & Observabilité (Semaines 4-6)

- **R4** Interfaces algorithmiques
- **R5** Audit complexité cyclomatique
- **R6** Diagramme C4
- **R7** Export métriques Prometheus/OTel

*Dépendance :* R4 bénéficie de R5 (refactoring préalable). R7 dépend de la réponse à Q3.

### Phase 3 — Polish & Communauté (Semaines 7-9)

- **R8** Isolation allocator
- **R9** Documentation `unsafe`
- **R10** Exemples bibliothèque
- **R11** Logs structurés
- **R12** Code of Conduct

*Dépendance :* R8 dépend de R4 (extraction interfaces). R10 dépend de R4 (API publique stabilisée).

---

## Annexe — Traçabilité vers le rapport Gemini 3.1

| Recommandation Gemini | Priorité Gemini | Exigence PRD | Phase |
|----------------------|----------------|-------------|-------|
| Fuzz testing Fast Doubling / FFT | P1 | R1 | 1 |
| Templates GitHub Issues / PRs | P1 | R2 | 1 |
| Couverture > 90% fibonacci / bigfft | P2 | R3 | 1 |
| Extraire interfaces stratégies algorithmiques | P2 | R4 | 2 |
| Audit complexité cyclomatique bigfft | P2 | R5 | 2 |
| Diagramme C4 dans README | P2 | R6 | 2 |
| Export métriques Prometheus / OTel | P2 | R7 | 2 |
| Isoler bump allocator | P3 | R8 | 3 |
| Documenter usages unsafe | P3 | R9 | 3 |
| Exemples bibliothèque Go | P3 | R10 | 3 |
| Logs structurés JSON / slog | P3 | R11 | 3 |
| Code of Conduct | P3 | R12 | 3 |
