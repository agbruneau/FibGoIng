# Plan — Mise à jour de la documentation après l'optimisation mémoire

## Context

Les 8 features d'optimisation mémoire du PRD (`prdMem.md`) ont été entièrement implémentées dans le code (arena allocator, GC controller, réduction 6→5 temporaires, modular fast doubling, budget mémoire, monitoring, etc.). Cependant, la documentation (`Docs/` et `README.md`) n'a **pas été mise à jour** pour refléter ces changements. Ce plan corrige ce décalage.

### Changements implémentés à documenter

1. **CalculationState réduit de 6 à 5 big.Int** — T4 éliminé via reformulation algébrique `F(2k) = 2·FK·FK1 - FK²`
2. **CalculationArena** (`internal/fibonacci/arena.go`) — bump allocator pour allocation contigüe
3. **GCController** (`internal/fibonacci/gc_control.go`) — contrôle du GC (auto/aggressive/disabled)
4. **FastDoublingMod** (`internal/fibonacci/modular.go`) — calcul modulaire O(K) pour `--last-digits`
5. **MemoryEstimate + ParseMemoryLimit** (`internal/fibonacci/memory_budget.go`) — estimation et budget
6. **MemoryCollector** (`internal/metrics/memory.go`) — snapshots mémoire runtime
7. **3 nouveaux flags CLI** : `--gc-control`, `--memory-limit`, `--last-digits`
8. **Monitoring TUI/CLI enrichi** — heap, GC, pauses dans le TUI et résumé CLI

---

## Task 1 — `README.md`

### 1a. Section "Key Features > High-Performance Engineering"

Ajouter après "Zero-Copy Result Return" :
- **Calculation Arena**: Contiguous bump-pointer allocator for all `big.Int` state, reducing GC pressure and memory fragmentation (`internal/fibonacci/arena.go`).
- **GC Controller**: Disables garbage collection during large calculations (N ≥ 1M) with soft memory limit safety net, reducing ~2× GC memory overhead (`internal/fibonacci/gc_control.go`).
- **Memory Budget Estimation**: Pre-calculation memory estimation with `--memory-limit` validation to prevent OOM on constrained hardware.
- **Modular Fast Doubling**: O(K) memory mode for computing the last K digits of F(N) via `--last-digits`, enabling arbitrarily large N.

### 1b. Section "Common Flags" — table de flags CLI

Ajouter 3 lignes au tableau :

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--last-digits` | | `0` | Compute only the last K decimal digits (uses O(K) memory). |
| `--memory-limit` | | | Maximum memory budget (e.g., 8G, 512M). Warns if estimate exceeds limit. |
| `--gc-control` | | `auto` | GC control during calculation (auto, aggressive, disabled). |

### 1c. Section "Configuration" — table des variables d'environnement

Ajouter :

| Variable | Description | Default |
|----------|-------------|---------|
| `FIBCALC_LAST_DIGITS` | Compute last K digits only | `0` |
| `FIBCALC_MEMORY_LIMIT` | Maximum memory budget | |
| `FIBCALC_GC_CONTROL` | GC control mode | `auto` |

### 1d. Section "Mathematical Background"

Mettre à jour section "Fast Doubling Identities" — la formule interne utilise maintenant l'identité équivalente :

```
F(2k)   = 2·F(k)·F(k+1) - F(k)²
F(2k+1) = F(k+1)² + F(k)²
```

> Note : la formule originale `F(2k) = F(k)·(2F(k+1) - F(k))` est mathématiquement identique mais l'implémentation utilise la forme reformulée qui élimine un temporaire.

### 1e. Section "Troubleshooting"

Ajouter un item :

**3. Memory limit exceeded**
For very large N, the estimated memory may exceed available RAM.
**Solution**: Use `--memory-limit 8G` to validate before starting, or `--last-digits 1000` to compute only the last K digits in O(K) memory.

### 1f. Section "Fuzz Testing" — table

Ajouter une ligne :

| `FuzzFastDoublingMod` | Cross-validates modular Fast Doubling output range | n up to 100,000, mod up to 1B |

### 1g. Section "Advanced Examples"

Ajouter :

**6. Last Digits Mode**
Compute the last 100 digits of F(10 billion) using O(K) memory:
```bash
fibcalc -n 10000000000 --last-digits 100
```

**7. Memory Budget Validation**
Check if your machine can handle the calculation before starting:
```bash
fibcalc -n 1000000000 --memory-limit 8G
```

### 1h. Section "Project Structure"

Le `internal/fibonacci/` mentionne déjà les frameworks. Pas de changement structurel nécessaire (les nouveaux fichiers sont dans des packages existants).

---

## Task 2 — `Docs/PERFORMANCE.md`

### 2a. Section "Zero-Allocation Strategy"

Mettre à jour le code example : remplacer `F_k, F_k1, ...` par les 5 champs actuels et mentionner la réduction 6→5 :

```go
var statePool = sync.Pool{
    New: func() interface{} {
        return &CalculationState{
            FK:  new(big.Int),
            FK1: new(big.Int),
            T1:  new(big.Int),
            T2:  new(big.Int),
            T3:  new(big.Int),
        }
    },
}
```

Ajouter un paragraphe sur l'arena :

> **Calculation Arena**: For N > 1,000, a contiguous `CalculationArena` pre-allocates all 5 `big.Int` backing arrays from a single block, reducing GC tracking overhead and memory fragmentation. The arena falls back to heap allocation when exhausted.

### 2b. Nouvelle section "6. GC Control" (après section 5)

```markdown
### 6. GC Controller

For large calculations (N ≥ 1M), the `GCController` disables Go's garbage collector during computation, eliminating GC pauses and reducing the ~2× memory overhead from GC scanning. A soft memory limit (3× current Sys) acts as an OOM safety net.

| Mode | Activation | Behavior |
|------|-----------|----------|
| `auto` (default) | N ≥ 1,000,000 | Disable GC during calculation |
| `aggressive` | Always | Disable GC regardless of N |
| `disabled` | Never | Standard GC behavior |

Configure via `--gc-control` or `FIBCALC_GC_CONTROL`.
```

### 2c. Nouvelle section "7. Memory Budget Estimation"

```markdown
### 7. Memory Budget Estimation

Pre-calculate estimated memory usage before starting with `--memory-limit`:

| N | Estimated Peak Memory |
|---|---|
| 10M | ~120 Mo |
| 100M | ~1.2 Go |
| 1B | ~12 Go |
| 5B | ~58 Go |

If the estimate exceeds the limit, the tool exits with an error and suggests `--last-digits K` as an alternative.
```

### 2d. Nouvelle section "8. Partial Computation (Last Digits)"

```markdown
### 8. Partial Computation (Last Digits)

The `--last-digits K` mode computes F(N) mod 10^K using modular arithmetic in O(log N) time and O(K) memory, enabling computation for arbitrarily large N:

```bash
fibcalc -n 10000000000 --last-digits 100
```
```

### 2e. Section "Known Limitations"

Mettre à jour item 1 et ajouter :

```
1. **Memory**: F(1 billion) requires ~12 GB of RAM. Use `--memory-limit` to validate before starting.
2. **Workaround**: Use `--last-digits K` for O(K) memory usage with arbitrarily large N.
```

---

## Task 3 — `Docs/algorithms/FAST_DOUBLING.md`

### 3a. Section "Derivation of Doubling Formulae"

Ajouter une note après les formules classiques :

> **Implementation note**: The codebase uses the equivalent reformulation `F(2k) = 2·F(k)·F(k+1) - F(k)²` which eliminates a temporary variable. Both are algebraically identical (expand `F(k)·(2F(k+1) - F(k))` to verify).

### 3b. Section "Zero-Allocation with sync.Pool"

Mettre à jour `CalculationState` de 6 à 5 champs :

```go
type CalculationState struct {
    FK, FK1, T1, T2, T3 *big.Int
}
```

Remplacer "six `*big.Int` temporaries" par "five `*big.Int` temporaries".

### 3c. Nouvelle sous-section "5. Calculation Arena"

Ajouter après la section sync.Pool :

```markdown
### 5. Calculation Arena

For N > 1,000, a `CalculationArena` pre-allocates a single contiguous block for all `big.Int` backing arrays. This reduces GC pressure and improves cache locality:

```go
arena := NewCalculationArena(n)
arena.PreSizeFromArena(s.FK, estimatedWords)
// ... pre-size all 5 state fields
```

If the arena is exhausted, allocation falls back to the standard heap.
```

---

## Task 4 — `Docs/algorithms/COMPARISON.md`

### 4a. Table "Memory"

Corriger "6 big.Int" → "5 big.Int" pour Fast Doubling :

```
| Fast Doubling | 5 big.Int | CalculationState |
```

### 4b. Ajouter "Modular Fast Doubling" à la section algorithms

Ajouter une entrée dans le tableau "Available Algorithms" :

| Modular Fast Doubling | `--last-digits` mode | "Modular Fast Doubling (O(log n), O(K) memory)" |

Ajouter une section :

```markdown
### Modular Fast Doubling (`--last-digits`)

**Recommended for**: Computing the last K digits of F(N) for arbitrarily large N without storing the full result.

- **Complexity**: O(log N) time, O(K) memory where K is the number of digits
- **Use case**: N > 1 billion where full computation exceeds available RAM
```

### 4c. Détail opération count

Mettre à jour "Detailed Operation Count" pour Fast Doubling : ajouter une note que les 3 mults sont maintenant `FK×FK1`, `FK²`, `FK1²` (au lieu de `FK×T4`, `FK²`, `FK1²`).

---

## Task 5 — `Docs/architecture/patterns/design-patterns.md`

### 5a. Pattern 7 (Object Pooling) — CalculationState

Mettre à jour les 6 big.Int → 5 big.Int. Changer :

```go
type CalculationState struct {
    FK, FK1, T1, T2, T3, T4 *big.Int  // REMOVE T4
}
```
→
```go
type CalculationState struct {
    FK, FK1, T1, T2, T3 *big.Int
}
```

### 5b. Nouveau Pattern 13 : Calculation Arena

Ajouter après Pattern 12 :

```markdown
## 13. Calculation Arena

**Location**: `internal/fibonacci/arena.go`

The Calculation Arena is a bump-pointer allocator that pre-allocates a single contiguous block for all `big.Int` backing arrays in a Fibonacci calculation. This complements the existing bump allocator (Pattern 8) which covers FFT temporaries — the arena covers the calculation state itself.

### Structure

```go
type CalculationArena struct {
    buf    []big.Word
    offset int
}
```

| Property | Value |
|----------|-------|
| Allocation cost | O(1) pointer bump |
| Sizing | 10 × estimated words per F(n) |
| Fallback | Heap allocation when exhausted |
| Release | O(1) via Reset() |

### Integration

Created at the start of `CalculateCore()`, used to pre-size all 5 `CalculationState` fields. Coexists with `sync.Pool` (arena for initial sizing, pool for recycling state objects).
```

### 5c. Nouveau Pattern 14 : GC Controller

```markdown
## 14. GC Controller

**Location**: `internal/fibonacci/gc_control.go`

The GC Controller disables Go's garbage collector during intensive calculations to eliminate GC pauses and reduce the ~2× memory overhead from heap scanning.

### Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| `auto` | N ≥ 1,000,000 | Disable GC + set soft memory limit |
| `aggressive` | Always | Disable GC regardless of N |
| `disabled` | Never | Standard GC behavior |

### Safety Net

`debug.SetMemoryLimit(3 × Sys)` prevents uncontrolled memory growth. Restored via `defer gc.End()` even on error.
```

### 5d. Section "Pattern Interactions"

Mettre à jour l'arbre d'appels pour inclure arena et GC :

```
+-- CalculateWithObservers()                  [Decorator]
     |
     +-- GCController.Begin()                 [GC Controller]    ← NEW
     +-- defer GCController.End()             [GC Controller]    ← NEW
     |
     +-- core.CalculateCore()                 [Decorator -> coreCalculator]
          |
          +-- NewCalculationArena(n)          [Calculation Arena] ← NEW
          +-- arena.PreSizeFromArena(...)      [Calculation Arena] ← NEW
```

### 5e. Table "Quick Reference"

Ajouter lignes 13 et 14 :

| 13 | Calculation Arena | `internal/fibonacci/arena.go` | `CalculationArena`, `PreSizeFromArena` | Contiguous pre-allocation for state big.Int |
| 14 | GC Controller | `internal/fibonacci/gc_control.go` | `GCController`, `GCMode`, `GCStats` | Disable GC during large calculations |

### 5f. Table of Contents

Ajouter entrées 13, 14 et mettre à jour les numéros (Pattern Interactions → 15, Quick Reference → 16).

---

## Task 6 — `Docs/architecture/README.md`

### 6a. Table `internal/fibonacci`

Ajouter les fichiers :

| `arena.go` | `CalculationArena` — contiguous bump allocator for state big.Int |
| `gc_control.go` | `GCController` — GC control during calculation (auto/aggressive/disabled) |
| `memory_budget.go` | `EstimateMemoryUsage`, `ParseMemoryLimit` — pre-calculation memory validation |
| `modular.go` | `FastDoublingMod` — modular fast doubling for `--last-digits` mode |

Mettre à jour la ligne `fastdoubling.go` : mentionner "5 big.Int" au lieu de 6 implicite.

### 6b. Table `internal/metrics`

Ajouter :

| `memory.go` | `MemoryCollector`, `MemorySnapshot` — runtime memory statistics |

### 6c. Codebase stats

Mettre à jour "17 Go packages | 98 source files" si nécessaire (4 nouveaux fichiers .go ajoutés).

### 6d. ADR-005 : Calculation Arena

```markdown
### ADR-005: Calculation Arena for Contiguous Allocation

**Context**: For very large N, per-buffer GC tracking adds significant memory overhead.

**Decision**: Pre-allocate a single contiguous block via `CalculationArena` for all 5 state `big.Int` backing arrays, falling back to heap when exhausted.

**Consequences**:
- Reduced GC pressure for large calculations
- O(1) bulk release via `Reset()`
- Coexists with existing `sync.Pool` (pool recycles state objects, arena pre-sizes their backing arrays)
```

### 6e. ADR-006 : GC Controller

```markdown
### ADR-006: GC Control During Large Calculations

**Context**: Go's GC adds ~2× memory overhead for heap scanning during large calculations.

**Decision**: Disable GC during computation for N ≥ 1M (auto mode), with `debug.SetMemoryLimit` as OOM safety net.

**Consequences**:
- Eliminates GC pauses during computation
- Reduces peak memory by ~50% (no GC overhead)
- Small OOM risk mitigated by soft memory limit
- Configurable via `--gc-control` flag
```

### 6f. Data Flow

Mettre à jour étape 7 pour mentionner GC control et arena :

```
7. ... Each Calculator.Calculate() creates ProgressSubject + ChannelObserver
   - GCController.Begin() disables GC for large N
   - FibCalculator.CalculateWithObservers(): small-N fast path, FFT cache, pool warming
   - CalculateCore creates CalculationArena and pre-sizes state from arena
   - Core algorithm executes the computation loop
   - GCController.End() restores GC and runs collection
```

### 6g. Section "Design Patterns"

Mettre à jour le décompte de "12 documented design patterns" → "14 documented design patterns" et ajouter "Calculation Arena, GC Controller" à la liste.

---

## Task 7 — `Docs/TESTING.md`

### 7a. Table "Fuzz Testing"

Ajouter :

| `FuzzFastDoublingMod` | Validates modular Fast Doubling output range | n up to 100,000, mod up to 1B |

Mettre à jour "Four fuzz tests" → "Five fuzz tests" dans l'intro et "4 fuzz targets" → "5 fuzz targets".

### 7b. Table "Test Organization" — `internal/fibonacci`

Ajouter aux test files : `arena_test.go`, `gc_control_test.go`, `memory_budget_test.go`, `modular_test.go`

Mettre à jour testing approach : ajouter "arena allocation, GC control, modular arithmetic"

### 7c. Table "Test Organization" — `internal/metrics`

Ajouter :

| `internal/metrics` | `memory_test.go` | Unit (memory snapshot collection) |

---

## Task 8 — `Docs/TUI_GUIDE.md`

### 8a. Section "Sub-Models > Metrics"

Mettre à jour pour mentionner la vue enrichie : "Heap: X / Y | GC: N (Xms)" et les champs `heapSys`, `heapObjects`, `pauseTotalNs`.

---

## Task 9 — `Docs/algorithms/BIGFFT.md`

### 9a. Section mémoire

Ajouter une note mentionnant que le `CalculationArena` (`internal/fibonacci/arena.go`) complète le bump allocator existant. Le bump allocator couvre les temporaires FFT, l'arena couvre les `big.Int` de l'état de calcul. Les deux systèmes coexistent sans interférence.

---

## Task 10 — `CLAUDE.md`

### 10a. Table des fichiers `internal/fibonacci`

Ajouter les 4 nouveaux fichiers :

| `arena.go` | `CalculationArena` bump allocator for calculation state |
| `gc_control.go` | `GCController` for GC management during computation |
| `memory_budget.go` | Memory estimation and budget validation |
| `modular.go` | `FastDoublingMod` for modular arithmetic (`--last-digits`) |

### 10b. Table `internal/metrics`

Ajouter :

| `memory.go` | `MemoryCollector`, `MemorySnapshot` — runtime memory statistics |

### 10c. Section "Key Patterns"

Ajouter :
- **Calculation Arena**: Contiguous bump-pointer pre-allocation for state `big.Int` backing arrays in `internal/fibonacci/arena.go`
- **GC Controller**: Disables GC during large calculations with soft memory limit safety net in `internal/fibonacci/gc_control.go`

### 10d. Table "Options"

Mentionner `GCMode` dans la description d'Options.

### 10e. Fuzz tests

Mettre à jour "4 fuzz targets" → "5 fuzz targets", ajouter `FuzzFastDoublingMod`.

---

## Ordre d'exécution

1. `CLAUDE.md` (source de vérité pour le code)
2. `README.md` (vitrine publique)
3. `Docs/PERFORMANCE.md`
4. `Docs/algorithms/FAST_DOUBLING.md`
5. `Docs/algorithms/COMPARISON.md`
6. `Docs/algorithms/BIGFFT.md`
7. `Docs/architecture/patterns/design-patterns.md`
8. `Docs/architecture/README.md`
9. `Docs/TESTING.md`
10. `Docs/TUI_GUIDE.md`

## Vérification

- Relecture de chaque fichier modifié pour cohérence interne
- Vérification que tous les liens cross-références sont valides
- `go build ./...` pour confirmer que le code compile (pas de modifications code)
- Grep pour s'assurer qu'aucune référence à "6 big.Int" ou "T4" ne subsiste dans la documentation
- Vérification que les numéros de patterns (12→14) sont cohérents partout
