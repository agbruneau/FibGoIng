# Plan d'implementation Schonhage-Strassen - Suivi des taches

## Tableau de suivi

| # | Tache | Phase | Priorite | Statut | Fichiers modifies |
|---|-------|-------|----------|--------|-------------------|
| 1 | `fermat.Sqr()` specialise + `basicSqr()` | Phase 1 | Critique | :white_check_mark: Termine | `internal/bigfft/fermat.go` |
| 2 | Modifier `sqr()` dans fft_poly.go pour utiliser `fermat.Sqr()` | Phase 1 | Critique | :white_check_mark: Termine | `internal/bigfft/fft_poly.go` |
| 3 | Augmenter `MaxEntries` du cache de transformees (128 -> 256) | Phase 1 | Haute | :white_check_mark: Termine | `internal/bigfft/fft_cache.go`, `internal/bigfft/fft_cache_test.go` |
| 4 | Rendre les seuils de parallelisme FFT configurables | Phase 1 | Moyenne | :white_check_mark: Termine | `internal/bigfft/fft_recursion.go` |
| 5 | Tests unitaires pour `fermat.Sqr()` et `basicSqr()` | Phase 1 | Critique | :white_check_mark: Termine | `internal/bigfft/fermat_test.go` |
| 6 | Executer tous les tests et valider | Validation | Critique | :white_check_mark: Termine | - |

## Resultat de validation

```
go test -short -count=1 ./...
ok  github.com/agbru/fibcalc/cmd/fibcalc        2.519s
ok  github.com/agbru/fibcalc/cmd/generate-golden 0.185s
ok  github.com/agbru/fibcalc/internal/app        1.330s
ok  github.com/agbru/fibcalc/internal/bigfft     0.262s
ok  github.com/agbru/fibcalc/internal/calibration 2.252s
ok  github.com/agbru/fibcalc/internal/cli        1.674s
ok  github.com/agbru/fibcalc/internal/config     0.202s
ok  github.com/agbru/fibcalc/internal/errors     0.185s
ok  github.com/agbru/fibcalc/internal/fibonacci  1.993s
ok  github.com/agbru/fibcalc/internal/format     0.160s
ok  github.com/agbru/fibcalc/internal/metrics    0.189s
ok  github.com/agbru/fibcalc/internal/orchestration 1.303s
ok  github.com/agbru/fibcalc/internal/parallel   0.190s
ok  github.com/agbru/fibcalc/internal/sysmon     0.212s
ok  github.com/agbru/fibcalc/internal/testutil   0.186s
ok  github.com/agbru/fibcalc/internal/tui        1.358s
ok  github.com/agbru/fibcalc/internal/ui         0.172s
ok  github.com/agbru/fibcalc/test/e2e            2.425s
```

**18/18 packages : PASS**

## Description des modifications

### Tache 1 - `fermat.Sqr()` specialise (`internal/bigfft/fermat.go`)

Ajout de deux fonctions :

- **`fermat.Sqr(x)`** : Methode de squaring specialisee modulo 2^(n*W)+1.
  - Pour n < smallMulThreshold (30 mots) : utilise `basicSqr` qui exploite la symetrie
  - Pour n >= smallMulThreshold : passe le meme pointeur `&xi` aux deux operandes de `big.Int.Mul`, permettant a Go de detecter le squaring en interne
  - Meme normalisation modulo 2^n+1 que `Mul`

- **`basicSqr(z, x)`** : Multiplication de Schoolbook optimisee pour x*x.
  - Calcule les termes off-diagonaux (x[i]*x[j] pour j>i) une seule fois
  - Double le resultat (shift left 1 bit)
  - Ajoute les termes diagonaux (x[i]*x[i]) via `math/bits.Mul`
  - Economise ~50% des multiplications partielles vs `basicMul(z, x, x)`

### Tache 2 - Integration dans fft_poly.go

Dans `fft_poly.go:sqr()`, remplacement de `buf.Mul(p.Values[i], p.Values[i])` par `buf.Sqr(p.Values[i])`. Cette modification propage le squaring specialise a toute la pile FFT (pointwise squaring dans le domaine frequentiel).

### Tache 3 - Cache de transformees agrandi

Augmentation de `MaxEntries` de 128 a 256 dans `DefaultTransformCacheConfig()`. Ameliore le hit rate pour les calculs iteratifs de Fibonacci avec fast doubling qui reutilisent frequemment les memes transformees FFT.

### Tache 4 - Seuils de parallelisme FFT configurables

- `ParallelFFTRecursionThreshold` et `MaxParallelFFTDepth` : convertis de `const` en `var`
- Ajout de `FFTParallelismConfig` struct
- Ajout de `SetFFTParallelismConfig()` et `GetFFTParallelismConfig()`
- Permet l'ajustement par le systeme de calibration existant

### Tache 5 - Tests

Nouveau fichier `internal/bigfft/fermat_test.go` avec :
- `TestFermatSqrVsMul` : comparaison Sqr vs Mul pour 14 tailles differentes (n=1 a n=50)
- `TestFermatSqrZero` : edge case zero
- `TestFermatSqrOne` : edge case 1
- `TestFermatSqrMaxWord` : edge case mots max + carry
- `TestBasicSqrVsBasicMul` : verification directe de basicSqr pour toutes tailles < 30
- `BenchmarkFermatSqrVsMul` : benchmarks comparatifs

## Equipe AgentsTeam

| Agent | Role | Taches |
|-------|------|--------|
| team-lead | Coordination, fermat.Sqr, tests, validation | 1, 5, 6 |
| poly-modifier | Modification fft_poly.go | 2 |
| cache-modifier | Modification fft_cache.go | 3 |
| threshold-modifier | Modification fft_recursion.go | 4 |

---
*Derniere mise a jour : 2026-02-07 - Phase 1 TERMINEE*
