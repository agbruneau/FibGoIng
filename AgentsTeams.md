## Scénarios d'utilisation d'Agent Teams pour FibGo

Basé sur la documentation Agent Teams et l'architecture de votre repo, voici les scénarios concrets identifiés :

---

### 1. Revue de code parallèle multi-domaines

Le repo a des couches très distinctes (algorithmes, FFT/assembleur, orchestration, CLI/TUI). Une revue de code classique ne peut pas couvrir tous les angles en profondeur.

```
Crée une équipe d'agents pour reviewer le code du repo FibGo :
- Un reviewer "performance" : analyse bigfft/, fibonacci/, l'assembleur amd64, 
  les stratégies de multiplication, les sync.Pool
- Un reviewer "architecture" : évalue les interfaces, le couplage entre couches, 
  les patterns (Factory, Observer, Strategy, Decorator)
- Un reviewer "fiabilité" : examine la gestion d'erreurs, les race conditions, 
  la propagation de contexte, les fuites de goroutines
- Un reviewer "tests" : évalue la couverture, les cas limites manquants, 
  la qualité des fuzz/property-based tests
```

**Pourquoi Agent Teams** : Chaque domaine nécessite une expertise différente et un contexte indépendant. Les reviewers peuvent se challenger mutuellement (ex: le reviewer perf signale un hot path, le reviewer fiabilité vérifie sa thread-safety).

---

### 2. Debugging avec hypothèses concurrentes

Quand un bug de performance ou de précision apparaît sur de très grands N, les causes possibles sont multiples et indépendantes.

```
Les utilisateurs rapportent des résultats incorrects pour F(10^9) avec l'algo FFT.
Crée une équipe de 4 agents pour investiguer en parallèle :
- Hypothèse 1 : erreur de précision dans les transformées FFT (fermat.go, fft_core.go)
- Hypothèse 2 : race condition dans le pool d'objets (pool.go, allocator.go)
- Hypothèse 3 : overflow dans l'assembleur AVX2 (arith_amd64.s, carry propagation)
- Hypothèse 4 : bug dans le seuil Karatsuba→FFT (strategy.go, SmartStrategy)
Les agents doivent activement réfuter les hypothèses des autres.
```

**Pourquoi Agent Teams** : L'investigation séquentielle souffre d'anchoring bias. Avec des agents adversariaux qui testent et réfutent mutuellement leurs théories, la vraie cause survit.

---

### 3. Implémentation d'un nouvel algorithme en parallèle

Ajouter un nouvel algorithme (ex: Lucas sequence, Zeckendorf) touche plusieurs couches indépendantes.

```
Crée une équipe pour ajouter l'algorithme "Lucas" au calculateur :
- Agent "algo" : implémenter coreCalculator dans internal/fibonacci/lucas.go
- Agent "tests" : écrire les tests unitaires, property-based, fuzz, 
  et mettre à jour fibonacci_golden.json
- Agent "intégration" : enregistrer dans registry.go, ajouter au CLI/TUI, 
  mettre à jour la config
- Agent "docs" : mettre à jour CLAUDE.md, README.md, Docs/algorithms/

Exiger l'approbation du plan avant implémentation pour chaque agent.
```

**Pourquoi Agent Teams** : Chaque agent possède un ensemble de fichiers distinct (pas de conflits). L'agent tests peut commencer à écrire les tests pendant que l'algo est en cours (TDD inversé avec les golden values connues).

---

### 4. Optimisation cross-layer coordonnée

L'optimisation de performance dans FibGo traverse toutes les couches : assembleur → bigfft → fibonacci → orchestration.

```
Crée une équipe pour optimiser le calcul de F(10^8) :
- Agent "profiling" : exécuter les benchmarks, générer les profils CPU/mémoire, 
  identifier les hotspots. Partager les résultats avec les autres agents.
- Agent "bigfft" : optimiser les allocations dans pool.go, améliorer le bump 
  allocator, réduire les copies dans fft_core.go
- Agent "fibonacci" : optimiser le seuil de parallélisation dans common.go, 
  améliorer le fast path dans calculator.go
- Agent "orchestration" : optimiser l'errgroup, réduire la contention 
  sur les channels de progress

L'agent profiling doit broadcaster les résultats aux autres agents 
avant qu'ils commencent leurs optimisations.
```

**Pourquoi Agent Teams** : L'agent profiling identifie les bottlenecks et communique directement aux agents concernés. Les optimisations sont indépendantes par fichier mais doivent être informées par les mêmes données de profiling.

---

### 5. Migration / Refactoring architectural

Par exemple, migrer le système de logging (les fichiers `internal/logging/` supprimés dans le diff actuel) ou restructurer les interfaces.

```
Crée une équipe pour migrer le système de logging vers zerolog :
- Agent "core" : remplacer les appels de logging dans fibonacci/ et bigfft/
- Agent "presentation" : adapter les loggers dans cli/ et tui/
- Agent "infrastructure" : mettre à jour orchestration/, config/, app/
- Agent "validation" : s'assurer que tous les tests passent après chaque 
  changement, vérifier qu'aucun import de l'ancien package ne reste

L'agent validation doit challenger les autres quand leurs changements 
cassent les tests.
```

**Pourquoi Agent Teams** : Le refactoring touche beaucoup de fichiers dans des packages distincts. La communication inter-agents permet à l'agent validation de donner du feedback en temps réel.

---

### 6. Mise en place CI/CD + quality gates

Le repo n'a pas de CI/CD actuellement. La mise en place touche plusieurs domaines indépendants.

```
Crée une équipe pour mettre en place la CI/CD GitHub Actions :
- Agent "pipeline" : créer les workflows (build, test, lint, security)
  avec la matrice OS (linux, windows, darwin) et Go versions
- Agent "qualité" : configurer les quality gates (couverture >75%, 
  golangci-lint, gosec), badges README
- Agent "release" : automatiser les releases (goreleaser), builds PGO, 
  cross-compilation, build tag gmp
- Agent "hooks" : configurer les pre-commit hooks, Dependabot, CodeQL

Utiliser le mode délégué pour que le lead coordonne sans implémenter.
```

**Pourquoi Agent Teams** : Les fichiers YAML de workflows, les configs de release, et les hooks sont totalement indépendants. Chaque agent peut travailler sans attendre les autres.

---

### 7. Recherche exploratoire comparative

Explorer des approches alternatives pour un composant critique.

```
Crée une équipe de recherche pour évaluer des alternatives au système 
de multiplication dans bigfft/ :
- Agent "NTT" : évaluer Number Theoretic Transform comme alternative à FFT
- Agent "Montgomery" : évaluer la multiplication de Montgomery pour les grands entiers
- Agent "Schönhage-Strassen" : évaluer cet algorithme vs l'implémentation actuelle
- Agent "devil's advocate" : challenger chaque proposition sur la complexité 
  d'intégration, les régressions de performance, et la maintenabilité

Chaque agent doit produire un rapport avec : complexité théorique, 
estimation de performance pour F(10^6) à F(10^10), et effort d'intégration.
```

**Pourquoi Agent Teams** : La recherche parallèle avec un agent contradicteur évite le biais de confirmation. Les agents peuvent débattre des mérites relatifs de chaque approche.

---

### Résumé des correspondances

| Scénario                | Pattern Agent Teams       | Fichiers concernés                                 |
| ------------------------ | ------------------------- | --------------------------------------------------- |
| Revue multi-domaines     | Review parallèle         | Tout le repo                                        |
| Debug hypothèses        | Competing hypotheses      | `bigfft/`, `fibonacci/`, assembly               |
| Nouvel algorithme        | New modules/features      | `fibonacci/`, `registry.go`, tests              |
| Optimisation cross-layer | Cross-layer coordination  | `bigfft/` → `fibonacci/` → `orchestration/` |
| Migration logging        | Refactoring parallèle    | Tous les packages `internal/`                     |
| CI/CD                    | New modules indépendants | `.github/workflows/`, configs                     |
| Recherche comparative    | Research & review         | `bigfft/`, documentation                          |

Les scénarios les plus immédiatement utiles pour votre repo seraient le **#1** (revue de code) et le **#6** (CI/CD), car ils correspondent à des besoins actuels visibles (pas de CI, codebase complexe multi-couches).
