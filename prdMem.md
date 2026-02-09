# PRD — Optimisation Mémoire de FibGo

## Product Requirement Document

**Projet** : FibGo — Calculateur Fibonacci Haute Performance
**Module** : `github.com/agbru/fibcalc`
**Version Go** : 1.25+
**Date** : 2026-02-09
**Auteur** : AG Bruneau
**Statut** : Draft

---

## 1. Contexte et Motivation

### 1.1 Situation Actuelle

FibGo est un calculateur Fibonacci académique haute performance implémentant trois algorithmes (Fast Doubling, Matrix Exponentiation, FFT-Based) avec un système de gestion mémoire sophistiqué :

- **10+ pools par classes de taille** pour `[]big.Word` (64 → 16M words)
- **Bump allocator** O(1) pour les temporaires FFT
- **Object pooling** via `sync.Pool` pour `CalculationState` (6 `big.Int`) et `matrixState` (23 `big.Int`)
- **Cache LRU** pour les transformées FFT (256 entrées, 15-30% de speedup)
- **Zero-copy result stealing** pour éviter les copies O(n) du résultat
- **Rotation de pointeurs** dans la boucle de doubling pour éliminer les copies intermédiaires
- **Pré-dimensionnement** des buffers via `preSizeBigInt()` pour les grands calculs
- **Garde MaxPooledBitLen** (100M bits) pour empêcher la saturation des pools

### 1.2 Problème Identifié

Lorsque N croît sans limite (objectif académique de scalabilité), la **taille brute des nombres en RAM** devient le facteur limitant :

| N | Taille de F(N) | RAM par `big.Int` | Temporaires simultanés |
|---|---|---|---|
| 1M | ~209K chiffres | ~87 Ko | ~600 Ko (×6 state) |
| 10M | ~2.1M chiffres | ~870 Ko | ~5.2 Mo (×6 state) |
| 100M | ~21M chiffres | ~8.7 Mo | ~52 Mo (×6 state) |
| 1B | ~209M chiffres | ~87 Mo | ~522 Mo (×6 state) |
| 5B | ~1.04B chiffres | ~435 Mo | ~2.6 Go (×6 state) |

Sur une machine avec 64 Go de RAM, la boucle de Fast Doubling avec ses 6 `big.Int` de travail, les buffers FFT, le cache de transformées et les temporaires des multiplications peut consommer :

- **F(1B)** : ~4-6 Go en pic (gérable)
- **F(5B)** : ~15-20 Go en pic (tendu)
- **F(10B)** : ~30-40 Go en pic (critique)

Le GC de Go ajoute un overhead de ~2× sur la mémoire active, rendant ces situations encore plus critiques.

### 1.3 Objectif

Optimiser la gestion mémoire de FibGo pour **repousser la limite de N calculable** sur du matériel standard (64 Go RAM), tout en préservant la simplicité de présentation des résultats. L'objectif est purement académique : démontrer que l'architecture scale.

### 1.4 Non-Objectifs

- Calcul distribué sur plusieurs machines
- Support GPU/FPGA
- Réécriture en C/Rust pour contourner le GC
- Stockage out-of-core sur disque (hors scope initial, mais mentionné comme extension future)

---

## 2. Utilisateurs et Cas d'Usage

### 2.1 Utilisateur Principal

Chercheur / étudiant académique exécutant des benchmarks de performance sur un laptop personnel (64 Go RAM, CPU multi-core moderne).

### 2.2 Cas d'Usage Principaux

| ID | Cas d'Usage | Priorité |
|---|---|---|
| UC-1 | Calculer F(N) pour N > 1B sans OOM sur 64 Go | P0 |
| UC-2 | Réduire le pic mémoire de 30-50% pour un N donné | P0 |
| UC-3 | Contrôler finement le comportement du GC pendant le calcul | P1 |
| UC-4 | Visualiser l'empreinte mémoire en temps réel (TUI) | P1 |
| UC-5 | Calculer les K premiers/derniers chiffres de F(N) sans stocker F(N) entier | P2 |
| UC-6 | Mode "mémoire contrainte" avec budget RAM configurable | P2 |

---

## 3. Exigences Fonctionnelles

### 3.1 Feature 1 — Multiplications In-Place (P0)

#### 3.1.1 Description

Modifier les opérations de multiplication pour réutiliser les buffers de destination au lieu d'allouer de nouveaux `big.Int`. Actuellement, `math/big.Mul(x, y)` et `bigfft.MulTo(z, x, y)` peuvent allouer de nouveaux backing arrays même quand `z` a une capacité suffisante.

#### 3.1.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F1.1 | `smartMultiply(z, x, y)` doit réutiliser le backing array de `z` quand `cap(z.Bits()) >= len(result.Bits())` | Must |
| F1.2 | `smartSquare(z, x)` doit réutiliser le backing array de `z` selon la même logique | Must |
| F1.3 | `bigfft.MulTo(z, x, y)` doit garantir la réutilisation de `z` quand la capacité est suffisante | Must |
| F1.4 | `bigfft.SqrTo(z, x)` doit garantir la réutilisation de `z` selon la même logique | Must |
| F1.5 | Les opérations in-place ne doivent pas affecter la correction du résultat (vérification par golden tests) | Must |
| F1.6 | Mesure : réduction de ≥30% des allocations dans la boucle de doubling (mesuré via `go test -benchmem`) | Should |

#### 3.1.3 Conception Technique

```
Avant (actuel) :
  z = new(big.Int)           // allocation
  z.Mul(x, y)                // peut réallouer internement
  → 2 allocations potentielles par multiplication

Après :
  if cap(z.Bits()) >= estimatedWords(x, y) {
      z.Mul(x, y)            // réutilise le buffer existant
  } else {
      z.Mul(x, y)            // math/big réalloue (inévitable pour la croissance)
  }
  → 0-1 allocation par multiplication (seulement quand croissance nécessaire)
```

**Impact sur la boucle de doubling** : Les 6 `big.Int` du `CalculationState` (FK, FK1, T1-T4) sont déjà pré-dimensionnés via `preSizeBigInt()`. En garantissant la réutilisation in-place, on élimine les allocations fantômes dans les dernières itérations de la boucle (quand les nombres ne croissent plus significativement).

#### 3.1.4 Fichiers Impactés

- `internal/fibonacci/strategy.go` — `smartMultiply()`, `smartSquare()`
- `internal/bigfft/fft.go` — `MulTo()`, `SqrTo()`
- `internal/fibonacci/doubling_framework.go` — boucle principale
- `internal/fibonacci/matrix_ops.go` — multiplications matricielles

---

### 3.2 Feature 2 — Arena Allocator pour le Calcul (P0)

#### 3.2.1 Description

Introduire un arena allocator dédié au calcul Fibonacci, au-delà du bump allocator existant qui ne couvre que les temporaires FFT. L'arena engloberait **tous** les `big.Int` du cycle de calcul, permettant une libération en bloc à la fin.

#### 3.2.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F2.1 | Implémenter un `CalculationArena` qui pré-alloue un bloc contigu de mémoire pour tous les `big.Int` temporaires d'un calcul | Must |
| F2.2 | L'arena doit supporter l'allocation de `[]big.Word` de taille variable depuis le bloc pré-alloué | Must |
| F2.3 | L'arena doit supporter la croissance (realloc) d'un buffer existant sans copie quand il est le dernier alloué | Should |
| F2.4 | L'arena doit être libérable en un seul appel (`arena.Reset()`) sans passer par le GC | Must |
| F2.5 | L'estimation de la taille de l'arena doit être basée sur N (utilisant la formule `bitLen ≈ N × 0.69424`) | Must |
| F2.6 | L'arena doit pouvoir croître si l'estimation initiale est insuffisante (fallback sur allocation standard) | Must |
| F2.7 | L'arena ne doit pas interférer avec le `sync.Pool` existant — les deux systèmes coexistent | Must |

#### 3.2.3 Conception Technique

```go
// Nouvelle structure dans internal/fibonacci/arena.go
type CalculationArena struct {
    buf    []big.Word   // bloc contigu pré-alloué
    offset int          // pointeur de bump
    cap    int          // capacité totale en words
}

func NewCalculationArena(n uint64) *CalculationArena {
    // Estimation : 6 big.Int × bitLen(F(n)) + marge pour temporaires
    estimatedBits := float64(n) * 0.69424
    wordsPerInt := int(estimatedBits/64) + 1
    totalWords := wordsPerInt * 12  // 6 state + 6 marge temporaires
    return &CalculationArena{
        buf: make([]big.Word, totalWords),
        cap: totalWords,
    }
}

func (a *CalculationArena) AllocBigInt(words int) *big.Int {
    if a.offset+words > a.cap {
        return new(big.Int)  // fallback
    }
    slice := a.buf[a.offset : a.offset+words : a.offset+words]
    a.offset += words
    z := new(big.Int)
    z.SetBits(slice)
    return z
}

func (a *CalculationArena) Reset() {
    a.offset = 0
    // Aucun appel au GC — le bloc reste alloué
}
```

**Intégration** : L'arena est créée au début de `CalculateCore()`, passée en paramètre aux stratégies de multiplication, et libérée (`Reset()`) à la fin du calcul.

#### 3.2.4 Estimation de Taille

| N | Words par `big.Int` | Arena (12 ints) | RAM |
|---|---|---|---|
| 10M | ~108K | ~1.3M words | ~10 Mo |
| 100M | ~1.08M | ~13M words | ~100 Mo |
| 1B | ~10.8M | ~130M words | ~1 Go |
| 5B | ~54M | ~650M words | ~5 Go |

#### 3.2.5 Fichiers Impactés

- `internal/fibonacci/arena.go` — nouveau fichier
- `internal/fibonacci/calculator.go` — intégration dans `FibCalculator`
- `internal/fibonacci/fastdoubling.go` — utilisation dans `CalculateCore()`
- `internal/fibonacci/fft_based.go` — utilisation dans `CalculateCore()`
- `internal/fibonacci/strategy.go` — passage de l'arena aux multiplications

---

### 3.3 Feature 3 — Contrôle Fin du GC (P1)

#### 3.3.1 Description

Contrôler le Garbage Collector de Go pendant les phases critiques du calcul pour réduire les pauses et la pression mémoire. Le GC de Go utilise par défaut `GOGC=100`, ce qui signifie qu'il se déclenche quand la heap double. Pour les calculs avec des Go de données actives, cela cause des scans fréquents et coûteux.

#### 3.3.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F3.1 | Désactiver le GC (`debug.SetGCPercent(-1)`) pendant la boucle de calcul principale | Must |
| F3.2 | Déclencher un GC manuel (`runtime.GC()`) entre les phases de calcul (entre calculateurs en mode comparaison) | Must |
| F3.3 | Restaurer le `GOGC` original à la fin du calcul (même en cas d'erreur, via `defer`) | Must |
| F3.4 | Exposer un flag CLI `--gc-control` (défaut : `auto`) avec les options : `auto`, `aggressive`, `disabled` | Should |
| F3.5 | En mode `auto`, désactiver le GC uniquement pour N > seuil configurable (défaut : 1M) | Should |
| F3.6 | Logger les statistiques GC avant/après le calcul via `runtime.ReadMemStats()` | Should |
| F3.7 | Utiliser `debug.SetMemoryLimit()` (Go 1.19+) pour définir un soft limit mémoire basé sur la RAM disponible | Should |

#### 3.3.3 Conception Technique

```go
// internal/fibonacci/gc_control.go

type GCController struct {
    originalGCPercent int
    memoryLimit       int64
    enabled           bool
}

func NewGCController(mode string, n uint64) *GCController {
    gc := &GCController{}
    switch mode {
    case "aggressive":
        gc.enabled = true
    case "auto":
        gc.enabled = n > 1_000_000
    case "disabled":
        gc.enabled = false
    }
    return gc
}

func (gc *GCController) Begin() {
    if !gc.enabled { return }
    gc.originalGCPercent = debug.SetGCPercent(-1)
    // Soft limit à 90% de la RAM disponible
    var m runtime.MemStats
    runtime.ReadMemStats(&m)
    gc.memoryLimit = int64(float64(m.Sys) * 0.9)
    debug.SetMemoryLimit(gc.memoryLimit)
}

func (gc *GCController) End() {
    if !gc.enabled { return }
    debug.SetGCPercent(gc.originalGCPercent)
    debug.SetMemoryLimit(math.MaxInt64)  // restaurer
    runtime.GC()  // nettoyage final
}
```

#### 3.3.4 Impact Attendu

| Métrique | Sans GC Control | Avec GC Control |
|---|---|---|
| Pauses GC pendant calcul | 10-100ms par cycle | 0ms (GC désactivé) |
| Overhead mémoire GC | ~2× heap active | ~1× heap active |
| Temps total F(100M) | baseline | -10 à -20% estimé |
| Risque OOM | Réduit par GC | Augmenté (pas de collection) |

#### 3.3.5 Fichiers Impactés

- `internal/fibonacci/gc_control.go` — nouveau fichier
- `internal/fibonacci/calculator.go` — intégration dans `FibCalculator.Calculate()`
- `internal/config/config.go` — nouveau flag `--gc-control`
- `internal/app/app.go` — passage du paramètre

---

### 3.4 Feature 4 — Pré-dimensionnement Optimal des Buffers (P0)

#### 3.4.1 Description

Améliorer le pré-dimensionnement existant (`preSizeBigInt()`) pour qu'il soit plus précis et couvre davantage de buffers. Actuellement, seuls les `big.Int` du `CalculationState` sont pré-dimensionnés. Les temporaires des multiplications et les buffers FFT ne le sont pas systématiquement.

#### 3.4.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F4.1 | Pré-dimensionner tous les `big.Int` du `CalculationState` à la taille maximale attendue : `ceil(N × 0.69424 / 64)` words | Must |
| F4.2 | Pré-dimensionner les buffers FFT du bump allocator à la taille estimée via `EstimateBumpCapacity()` amélioré | Must |
| F4.3 | Pré-dimensionner les 23 `big.Int` du `matrixState` pour Matrix Exponentiation | Should |
| F4.4 | Exposer la taille estimée dans les logs (`zerolog`) pour le diagnostic | Should |
| F4.5 | Utiliser `big.Int.SetBits()` pour attacher un buffer pré-alloué sans copie | Must |

#### 3.4.3 Améliorations Spécifiques

**Pré-sizing actuel** (dans `fastdoubling.go`) :
```go
// Seulement pour n > 10_000
estimatedWords := int(float64(n)*0.69424/64) + 1
preSizeBigInt(s.FK, estimatedWords)
// ... pour FK1, T1, T2, T3, T4
```

**Pré-sizing amélioré** :
```go
// Pour tout n > 1000
estimatedBits := uint64(float64(n) * 0.69424)
estimatedWords := int(estimatedBits/64) + 1

// State big.Ints — taille maximale
for _, z := range []*big.Int{s.FK, s.FK1, s.T1, s.T2, s.T3, s.T4} {
    preSizeBigInt(z, estimatedWords)
}

// Bump allocator — taille adaptée
bumpCap := bigfft.EstimateBumpCapacity(estimatedWords)
bigfft.EnsureBumpCapacity(bumpCap)

// Transform cache — pré-chauffer si N > 100K
if n > 100_000 {
    bigfft.PreWarmTransformCache(estimatedWords)
}
```

#### 3.4.4 Fichiers Impactés

- `internal/fibonacci/fastdoubling.go` — pré-sizing amélioré
- `internal/fibonacci/fft_based.go` — pré-sizing amélioré
- `internal/fibonacci/matrix_framework.go` — pré-sizing du `matrixState`
- `internal/bigfft/pool_warming.go` — `EnsureBumpCapacity()`, `PreWarmTransformCache()`
- `internal/bigfft/memory_est.go` — amélioration de `EstimateBumpCapacity()`

---

### 3.5 Feature 5 — Réduction du Nombre de Temporaires Actifs (P0)

#### 3.5.1 Description

Réduire le nombre de `big.Int` temporaires simultanément vivants dans la boucle de calcul. Actuellement, le `CalculationState` contient 6 `big.Int` (FK, FK1, T1, T2, T3, T4), tous de taille ~F(N). En optimisant les formules de doubling, on peut réduire à 4-5 temporaires actifs.

#### 3.5.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F5.1 | Analyser les dépendances de données dans la boucle de doubling pour identifier les temporaires superflus | Must |
| F5.2 | Réduire le `CalculationState` à 5 `big.Int` maximum sans affecter la correction | Should |
| F5.3 | Maintenir la compatibilité avec le parallélisme (les multiplications parallèles nécessitent des destinations distinctes) | Must |
| F5.4 | Valider par golden tests et property-based tests que la correction est préservée | Must |

#### 3.5.3 Analyse des Temporaires

Boucle de doubling actuelle par itération :
```
Étape 1 : T4 = 2*FK1 - FK              (T4 écrit, FK/FK1 lus)
Étape 2 : T3 = FK × T4                 (T3 écrit, FK/T4 lus)
          T2 = FK × FK                  (T2 écrit, FK lu)
          T1 = FK1 × FK1               (T1 écrit, FK1 lu)
Étape 3 : T1 = T1 + T2                 (T1 accumulé)
Étape 4 : rotation FK←T3, FK1←T1       (T2,T4 deviennent libres)
```

**Observation** : Après l'étape 2, T4 n'est plus utilisé. Après l'étape 3, T2 n'est plus utilisé. On pourrait fusionner T4 avec T2 (réutiliser le même buffer), passant de 6 à 5 `big.Int`.

#### 3.5.4 Impact Mémoire

| N | Gain (1 big.Int de moins) | % du total |
|---|---|---|
| 100M | ~8.7 Mo | ~17% du state |
| 1B | ~87 Mo | ~17% du state |
| 5B | ~435 Mo | ~17% du state |

#### 3.5.5 Fichiers Impactés

- `internal/fibonacci/common.go` — `CalculationState` réduit
- `internal/fibonacci/doubling_framework.go` — boucle adaptée
- `internal/fibonacci/strategy.go` — `ExecuteStep()` adapté
- `internal/fibonacci/fastdoubling.go` — `CalculateCore()` adapté

---

### 3.6 Feature 6 — Monitoring Mémoire Temps Réel (P1)

#### 3.6.1 Description

Intégrer un monitoring mémoire détaillé dans le TUI existant et les logs CLI pour visualiser l'empreinte mémoire pendant le calcul, sans complexifier la présentation des résultats.

#### 3.6.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F6.1 | Afficher dans le TUI : heap active, heap totale, nombre d'allocations, pauses GC cumulées | Must |
| F6.2 | Afficher dans le TUI : taille estimée des `big.Int` actifs (FK, FK1) en Mo/Go | Should |
| F6.3 | En mode CLI, afficher un résumé mémoire à la fin du calcul : pic mémoire, allocations totales, temps GC | Must |
| F6.4 | En mode CLI verbose (`-v`), afficher l'évolution mémoire toutes les 5% de progression | Should |
| F6.5 | Ne pas ajouter d'overhead mesurable (< 1%) au calcul pour le monitoring | Must |
| F6.6 | Utiliser `runtime.ReadMemStats()` avec une fréquence maximale de 1 Hz | Must |

#### 3.6.3 Données Affichées

**TUI (panneau metrics existant)** :
```
Memory ──────────────────────────
  Heap Active:   2.4 Go / 64 Go
  Heap Objects:  1,247
  GC Pauses:     0ms (disabled)
  FK size:       827 Mo
  Arena:         1.2 Go (94% used)
```

**CLI (résumé final)** :
```
Memory Stats:
  Peak heap:     4.2 Go
  Total alloc:   12.8 Go
  GC cycles:     0 (disabled)
  GC pause total: 0ms
  Arena used:    1.2 Go / 1.3 Go (92%)
```

#### 3.6.4 Fichiers Impactés

- `internal/tui/metrics.go` — panneau mémoire enrichi
- `internal/cli/presenter.go` — résumé mémoire final
- `internal/metrics/memory.go` — nouveau : collecteur de métriques mémoire
- `internal/fibonacci/observer.go` — nouveau type d'événement `MemoryUpdate`

---

### 3.7 Feature 7 — Mode Calcul Partiel (P2)

#### 3.7.1 Description

Permettre de calculer uniquement les K premiers et/ou K derniers chiffres décimaux de F(N) sans stocker le nombre entier en mémoire. Cela permet de "calculer" F(N) pour des N arbitrairement grands et de vérifier la correction par comparaison avec des résultats connus.

#### 3.7.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F7.1 | Flag CLI `--last-digits K` : calculer F(N) mod 10^K pour obtenir les K derniers chiffres | Must |
| F7.2 | Flag CLI `--first-digits K` : calculer les K premiers chiffres via arithmétique flottante logarithmique | Should |
| F7.3 | En mode `--last-digits`, la mémoire utilisée doit être O(K) et non O(N) | Must |
| F7.4 | En mode `--first-digits`, utiliser la formule de Binet avec précision arbitraire (via `math/big.Float`) | Should |
| F7.5 | Afficher clairement que le résultat est partiel dans la sortie | Must |
| F7.6 | Permettre la combinaison `--last-digits` et `--first-digits` dans un même calcul | Should |

#### 3.7.3 Conception Technique — Derniers Chiffres

Le Fast Doubling fonctionne modulo M = 10^K :
```go
func FastDoublingMod(n uint64, m *big.Int) (*big.Int, error) {
    fk, fk1 := big.NewInt(0), big.NewInt(1)
    // Même boucle de doubling, mais chaque opération est suivie de mod m
    // Mémoire : O(K) au lieu de O(N×log(φ))
}
```

#### 3.7.4 Conception Technique — Premiers Chiffres

Utiliser la relation : `log10(F(N)) ≈ N × log10(φ) - log10(√5)`

```go
func FirstDigits(n uint64, k int) string {
    // Calcul en big.Float avec précision = k × 3.32 bits
    logF := new(big.Float).SetPrec(uint(k*4))
    // logF = n * log10(phi) - 0.5 * log10(5)
    // frac = partie fractionnaire de logF
    // result = 10^frac, tronqué à k chiffres
}
```

#### 3.7.5 Fichiers Impactés

- `internal/fibonacci/modular.go` — nouveau : Fast Doubling modulaire
- `internal/fibonacci/first_digits.go` — nouveau : calcul des premiers chiffres
- `internal/fibonacci/registry.go` — enregistrement des nouveaux modes
- `internal/config/config.go` — flags `--last-digits`, `--first-digits`
- `internal/cli/presenter.go` — affichage des résultats partiels

---

### 3.8 Feature 8 — Budget Mémoire Configurable (P2)

#### 3.8.1 Description

Permettre de définir un budget mémoire maximal pour le calcul. Si le calcul risque de dépasser ce budget, l'application adapte sa stratégie (réduction du cache, désactivation du parallélisme, etc.) ou refuse de démarrer avec un message explicatif.

#### 3.8.2 Exigences

| ID | Exigence | Criticité |
|---|---|---|
| F8.1 | Flag CLI `--memory-limit` (ex: `--memory-limit 8G`) pour définir le budget mémoire | Must |
| F8.2 | Estimation avant calcul : afficher la mémoire estimée et avertir si elle dépasse le budget | Must |
| F8.3 | Si budget dépassé : proposer automatiquement le mode `--last-digits` comme alternative | Should |
| F8.4 | Adaptation dynamique : réduire la taille du cache de transformées si le budget est serré | Should |
| F8.5 | Adaptation dynamique : désactiver le parallélisme des multiplications si le budget est serré | Should |
| F8.6 | Monitoring : avertir (sans arrêter) si le budget est atteint à 90% pendant le calcul | Should |

#### 3.8.3 Estimation de Mémoire

```go
func EstimateMemoryUsage(n uint64, opts Options) MemoryEstimate {
    bitsPerFib := float64(n) * 0.69424
    wordsPerFib := int(bitsPerFib/64) + 1
    bytesPerFib := wordsPerFib * 8

    return MemoryEstimate{
        StateBytes:     bytesPerFib * 6,           // CalculationState
        FFTBufferBytes: bigfft.EstimateBumpCapacity(wordsPerFib) * 8,
        CacheBytes:     estimateCacheMemory(wordsPerFib, opts),
        OverheadBytes:  bytesPerFib * 2,           // GC + runtime overhead
        TotalBytes:     /* somme */,
    }
}
```

#### 3.8.4 Fichiers Impactés

- `internal/fibonacci/memory_budget.go` — nouveau : estimation et contrôle
- `internal/config/config.go` — flag `--memory-limit`
- `internal/app/app.go` — vérification pré-calcul
- `internal/cli/presenter.go` — affichage de l'estimation

---

## 4. Exigences Non-Fonctionnelles

### 4.1 Performance

| ID | Exigence | Criticité |
|---|---|---|
| NF1.1 | Les optimisations mémoire ne doivent pas dégrader le temps de calcul de plus de 5% | Must |
| NF1.2 | L'overhead du monitoring mémoire doit être < 1% du temps total | Must |
| NF1.3 | L'arena allocator doit être au moins aussi rapide que `sync.Pool` pour les allocations | Should |
| NF1.4 | Le pré-dimensionnement ne doit pas ajouter plus de 100ms au démarrage pour N < 1B | Should |

### 4.2 Fiabilité

| ID | Exigence | Criticité |
|---|---|---|
| NF2.1 | Tous les golden tests existants doivent continuer à passer | Must |
| NF2.2 | Les fuzz tests existants (4 targets) doivent continuer à passer | Must |
| NF2.3 | Ajouter des fuzz tests spécifiques pour le calcul modulaire | Must |
| NF2.4 | Couverture de tests ≥ 75% sur les nouveaux fichiers | Must |
| NF2.5 | Aucune data race détectée par `-race` | Must |

### 4.3 Compatibilité

| ID | Exigence | Criticité |
|---|---|---|
| NF3.1 | Aucun breaking change sur l'API CLI existante | Must |
| NF3.2 | Les nouveaux flags sont opt-in (comportement par défaut inchangé) | Must |
| NF3.3 | Compatible Go 1.25+ | Must |
| NF3.4 | Fonctionne sur Linux, Windows, macOS (mêmes plateformes qu'actuellement) | Must |

### 4.4 Maintenabilité

| ID | Exigence | Criticité |
|---|---|---|
| NF4.1 | Respect des conventions de code existantes (imports groupés, `apperrors`, etc.) | Must |
| NF4.2 | Cyclomatic complexity ≤ 15 par fonction (règle golangci-lint existante) | Must |
| NF4.3 | Nouveaux fichiers documentés avec des commentaires GoDoc | Should |
| NF4.4 | Pas de dépendances externes supplémentaires pour les features P0 | Should |

---

## 5. Architecture des Changements

### 5.1 Vue d'Ensemble

```
                    ┌─────────────────┐
                    │   config.go     │  ← nouveaux flags: --gc-control,
                    │                 │    --memory-limit, --last-digits,
                    │                 │    --first-digits
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    app.go       │  ← estimation mémoire pré-calcul
                    │                 │    budget validation
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼──────┐  ┌───▼────────┐
     │ GCController│  │  Arena      │  │ MemBudget  │
     │ gc_control  │  │  arena.go   │  │ memory_    │
     │ .go         │  │             │  │ budget.go  │
     └────────┬───┘  └──────┬──────┘  └───┬────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │  calculator.go  │  ← intégration GC + Arena
                    │  FibCalculator  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼──────┐  ┌───▼────────┐
     │ fastdoub.  │  │ fft_based.  │  │ modular.go │
     │ State: 5×  │  │ State: 5×   │  │ (nouveau)  │
     │ big.Int    │  │ big.Int     │  │ O(K) mem   │
     └────────┬───┘  └──────┬──────┘  └────────────┘
              │              │
              └──────┬───────┘
                     │
            ┌────────▼────────┐
            │  strategy.go    │  ← in-place multiply
            │  smartMultiply  │    arena-aware
            │  smartSquare    │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │  bigfft/fft.go  │  ← MulTo/SqrTo in-place
            │  bump allocator │    amélioré
            └─────────────────┘
```

### 5.2 Nouveaux Fichiers

| Fichier | Responsabilité |
|---|---|
| `internal/fibonacci/arena.go` | Arena allocator pour le calcul |
| `internal/fibonacci/gc_control.go` | Contrôle du GC |
| `internal/fibonacci/memory_budget.go` | Estimation et contrôle du budget mémoire |
| `internal/fibonacci/modular.go` | Fast Doubling modulaire (derniers chiffres) |
| `internal/fibonacci/first_digits.go` | Calcul des premiers chiffres via Binet |
| `internal/metrics/memory.go` | Collecteur de métriques mémoire |

### 5.3 Fichiers Modifiés

| Fichier | Nature de la Modification |
|---|---|
| `internal/fibonacci/common.go` | `CalculationState` réduit à 5 `big.Int` |
| `internal/fibonacci/strategy.go` | Multiplications in-place, arena-aware |
| `internal/fibonacci/doubling_framework.go` | Boucle optimisée, moins de temporaires |
| `internal/fibonacci/fastdoubling.go` | Pré-sizing amélioré, intégration arena |
| `internal/fibonacci/fft_based.go` | Pré-sizing amélioré, intégration arena |
| `internal/fibonacci/matrix_framework.go` | Pré-sizing du `matrixState` |
| `internal/fibonacci/calculator.go` | Intégration GC controller + arena |
| `internal/bigfft/fft.go` | `MulTo`/`SqrTo` in-place garanti |
| `internal/bigfft/memory_est.go` | Estimation améliorée |
| `internal/bigfft/pool_warming.go` | `EnsureBumpCapacity()` |
| `internal/config/config.go` | Nouveaux flags CLI |
| `internal/app/app.go` | Estimation pré-calcul, budget validation |
| `internal/cli/presenter.go` | Résumé mémoire, résultats partiels |
| `internal/tui/metrics.go` | Panneau mémoire enrichi |

---

## 6. Plan de Livraison

### Phase 1 — Fondations Mémoire (P0)

**Objectif** : Réduire l'empreinte mémoire de 30-40% pour un N donné.

| Étape | Feature | Effort Estimé | Dépendances |
|---|---|---|---|
| 1.1 | Multiplications in-place (F1) | Moyen | Aucune |
| 1.2 | Pré-dimensionnement optimal (F4) | Faible | Aucune |
| 1.3 | Réduction des temporaires (F5) | Moyen | F1 |
| 1.4 | Arena allocator (F2) | Élevé | F1, F4 |

**Critères d'acceptation Phase 1** :
- Tous les golden tests passent
- `go test -benchmem` montre ≥30% de réduction des allocations sur F(10M)
- Aucune régression de performance > 5%
- `-race` clean

### Phase 2 — Contrôle et Monitoring (P1)

**Objectif** : Visibilité et contrôle sur le comportement mémoire.

| Étape | Feature | Effort Estimé | Dépendances |
|---|---|---|---|
| 2.1 | Contrôle GC (F3) | Moyen | Phase 1 |
| 2.2 | Monitoring mémoire (F6) | Moyen | Phase 1 |

**Critères d'acceptation Phase 2** :
- Flag `--gc-control` fonctionnel
- TUI affiche les métriques mémoire en temps réel
- CLI affiche le résumé mémoire en fin de calcul
- Overhead monitoring < 1%

### Phase 3 — Modes Avancés (P2)

**Objectif** : Étendre les capacités au-delà des limites de la RAM.

| Étape | Feature | Effort Estimé | Dépendances |
|---|---|---|---|
| 3.1 | Calcul partiel - derniers chiffres (F7) | Moyen | Aucune |
| 3.2 | Calcul partiel - premiers chiffres (F7) | Moyen | Aucune |
| 3.3 | Budget mémoire configurable (F8) | Moyen | Phase 1, F7 |

**Critères d'acceptation Phase 3** :
- `--last-digits 1000` calcule F(10B) en mémoire O(K)
- `--first-digits 100` donne les 100 premiers chiffres corrects (vérifié par OEIS)
- `--memory-limit 8G` adapte la stratégie ou refuse proprement

---

## 7. Métriques de Succès

### 7.1 Métriques Quantitatives

| Métrique | Baseline (actuel) | Cible Phase 1 | Cible Phase 2 | Cible Phase 3 |
|---|---|---|---|---|
| N max calculable (64 Go RAM) | ~2-3B (estimé) | ~5B | ~7B (GC off) | Illimité (mode partiel) |
| Allocations/itération (F(10M)) | À mesurer | -30% | -30% | N/A |
| Pic mémoire F(1B) | ~4-6 Go (estimé) | ~3-4 Go | ~2.5-3.5 Go | O(K) en partiel |
| Temps F(10M) | baseline | ≤ +5% | ≤ baseline | N/A |

### 7.2 Métriques Qualitatives

- La présentation des résultats reste simple et claire
- Les nouveaux flags sont intuitifs et bien documentés
- Le code ajouté respecte les conventions existantes
- La documentation académique peut s'appuyer sur des métriques mémoire précises

---

## 8. Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| La réduction des temporaires introduit des bugs de correction | Moyenne | Élevé | Golden tests + fuzz tests + property-based tests |
| La désactivation du GC cause des OOM | Moyenne | Élevé | `debug.SetMemoryLimit()` comme filet de sécurité |
| L'arena allocator est plus lent que `sync.Pool` pour les petits N | Faible | Moyen | Seuil d'activation (arena seulement pour N > 1M) |
| `big.Int.SetBits()` crée des aliasing bugs | Moyenne | Élevé | Tests de non-aliasing, analyse statique |
| Le monitoring mémoire dégrade la performance | Faible | Faible | Fréquence limitée à 1 Hz, lazy `ReadMemStats()` |
| Les formules de Binet (premiers chiffres) manquent de précision pour très grands N | Faible | Moyen | Validation croisée avec résultats connus (OEIS, Wolfram) |

---

## 9. Extensions Futures (Hors Scope)

Ces idées sont documentées pour référence mais ne font pas partie de ce PRD :

- **Calcul out-of-core** : swap des `big.Int` sur disque SSD via mmap pour des N > 10B
- **Compression des intermédiaires** : compresser les `big.Int` peu utilisés (T3, T4) entre les itérations
- **Multi-machine** : distribuer les multiplications FFT sur un cluster
- **SIMD / AVX-512** : opérations vectorielles sur les `big.Word` arrays (complément aux optimisations amd64 existantes)
- **Memory-mapped big.Int** : représentation de `big.Int` backed par des fichiers mappés en mémoire

---

## 10. Glossaire

| Terme | Définition |
|---|---|
| Arena Allocator | Allocateur qui pré-alloue un bloc contigu et distribue des sous-blocs via un simple incrément de pointeur |
| Bump Allocator | Synonyme d'arena allocator (terminologie utilisée dans le code existant) |
| Fast Doubling | Algorithme O(log n) pour F(N) basé sur les identités F(2k) et F(2k+1) |
| Golden Test | Test de non-régression comparant le résultat à une valeur de référence stockée |
| In-place | Opération qui écrit le résultat dans un buffer existant au lieu d'en allouer un nouveau |
| OOM | Out Of Memory — crash dû à l'épuisement de la mémoire disponible |
| Pool | Cache de buffers réutilisables (`sync.Pool` en Go) |
| PGO | Profile-Guided Optimization — optimisation du compilateur guidée par un profil d'exécution |
| Zero-copy | Technique évitant la copie de données en transférant la propriété d'un pointeur |
