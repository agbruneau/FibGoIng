# Plan: TUI Dashboard btop-style pour FibGo

## Context

Le projet FibGo est un calculateur de Fibonacci haute performance en Go. L'affichage actuel est un CLI classique (spinner + barre de progression texte). L'objectif est d'ajouter un mode TUI interactif type "dashboard" inspiré de btop, activable via `--tui`, sans modifier le mode CLI existant.

L'architecture actuelle est bien préparée : les interfaces `ProgressReporter` et `ResultPresenter` découplent complètement l'orchestration de la présentation. Le TUI s'insère comme une nouvelle implémentation de ces interfaces.

---

## Stack technique

- `github.com/charmbracelet/bubbletea` v1.3+ - Framework TUI (architecture Elm)
- `github.com/charmbracelet/lipgloss` v1.1+ - Styling et layout
- `github.com/charmbracelet/bubbles` v0.20+ - Composants (viewport pour le scroll)

---

## Architecture Elm (Model, Update, View)

Le pattern Elm est implémenté via bubbletea :
- **Model** : struct Go contenant tout l'état de l'application (progression, résultats, métriques, dimensions terminal)
- **Update** : méthode `Update(msg tea.Msg)` qui reçoit des messages (clavier, progress, résultats, tick) et retourne le modèle mis à jour + commandes optionnelles
- **View** : méthode `View() string` pure qui rend le modèle en string pour affichage

Le pont entre le calcul concurrent (channels) et bubbletea (messages) se fait via `tea.Program.Send()` (thread-safe).

---

## Layout du Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  FibGo Monitor                v0.1.0       Elapsed: 0m 12s     │
├──────────────────────────────────────┬──────────────────────────┤
│  Calculations Log                    │  Metrics                 │
│                                      │   Memory:    42.3 MB     │
│  [12:00:01] Fast Doubling    12.3%   │   Heap:      38.1 MB     │
│  [12:00:02] Matrix Exp        8.7%   │   GC Runs:   12          │
│  [12:00:03] FFT Based        15.1%   │   Speed:     0.15 /s     │
│  [12:00:04] Fast Doubling    34.5%   │   Goroutines: 8          │
│  ...                                 ├──────────────────────────┤
│                                      │  Progress Chart          │
│  [12:00:08] Fast Doubling   100% OK  │                          │
│  [12:00:09] Matrix Exp      100% OK  │  ▁▂▃▄▅▆▇█▇▆▅▇█          │
│  [12:00:10] FFT Based       100% OK  │                          │
│                                      │  avg: 67.8%  ETA: 4s     │
├──────────────────────────────────────┴──────────────────────────┤
│  q: Quit   r: Reset   space: Pause/Resume       Status: Running │
└─────────────────────────────────────────────────────────────────┘
```

- **Header** (3 lignes) : titre "FibGo Monitor", version (`app.Version`), temps écoulé
- **Logs** (60% largeur) : viewport scrollable avec entrées horodatées
- **Metrics** (40% largeur, haut) : mémoire via `runtime.MemStats`, vitesse, goroutines
- **Chart** (40% largeur, bas) : sparkline braille (blocs `▁▂▃▄▅▆▇█`) montrant la progression
- **Footer** (3 lignes) : raccourcis clavier + indicateur d'état

---

## Structure des fichiers

```
internal/tui/
    doc.go          -- Documentation du package
    messages.go     -- Types tea.Msg (ProgressMsg, ResultMsg, TickMsg, MemStatsMsg...)
    styles.go       -- Styles lipgloss (thème sombre btop, bordures arrondies)
    keymap.go       -- Bindings clavier (q, r, space, flèches, pgup/pgdn)
    bridge.go       -- TUIProgressReporter + TUIResultPresenter (implémentent les interfaces orchestration)
    header.go       -- Sous-modèle HeaderModel
    logs.go         -- Sous-modèle LogsModel (avec bubbles/viewport)
    metrics.go      -- Sous-modèle MetricsModel
    chart.go        -- Sous-modèle ChartModel (sparkline braille)
    footer.go       -- Sous-modèle FooterModel
    model.go        -- Modèle racine + Init/Update/View + Run()
```

---

## Plan d'implémentation

### Etape 1 : Dépendances et configuration

**Fichiers modifiés :**
- `go.mod` : ajouter bubbletea, lipgloss, bubbles
- `internal/config/config.go:42-79` : ajouter champ `TUI bool` à `AppConfig`
- `internal/config/config.go:149-170` : ajouter flag `--tui` dans `ParseConfig()`
- `internal/config/env.go:155-173` : ajouter override `FIBCALC_TUI` dans `applyBooleanOverrides()`

```bash
go get github.com/charmbracelet/bubbletea github.com/charmbracelet/lipgloss github.com/charmbracelet/bubbles
```

### Etape 2 : Fondations TUI (messages, styles, keymap)

**Fichiers créés :**

- `internal/tui/doc.go` : documentation du package
- `internal/tui/messages.go` : tous les types de messages
  - `ProgressMsg{CalculatorIndex, Value, AverageProgress, ETA}`
  - `ProgressDoneMsg{}`
  - `ComparisonResultsMsg{Results []orchestration.CalculationResult}`
  - `FinalResultMsg{Result, N, Verbose, Details, ShowValue}`
  - `ErrorMsg{Err, Duration}`
  - `TickMsg` (tick 500ms pour sampling métriques)
  - `MemStatsMsg{Alloc, HeapInuse, NumGC, NumGoroutine}`
  - `CalculationCompleteMsg{ExitCode}`
  - `ContextCancelledMsg{Err}`

- `internal/tui/styles.go` : thème sombre btop
  - Palette : fond `#1a1b26`, texte `#a9b1d6`, bordure `#3b4261`, accent `#7aa2f7`, succès `#9ece6a`, warning `#e0af68`, erreur `#f7768e`
  - `panelStyle` avec `lipgloss.RoundedBorder()`
  - Styles par composant (header, logs, metrics, chart, footer)
  - Styles pour progress bar, labels métriques, résultats

- `internal/tui/keymap.go` : bindings avec `bubbles/key`
  - `q`/`ctrl+c` : quitter
  - `r` : reset métriques/chart
  - `space` : pause/resume affichage
  - `up`/`k`, `down`/`j` : scroll logs
  - `pgup`/`pgdn` : scroll rapide

### Etape 3 : Bridge (pont orchestration <-> bubbletea)

**Fichier créé : `internal/tui/bridge.go`**

- `programRef` struct : wrapper partagé pour `*tea.Program` (survit aux copies de modèle par bubbletea)

- `TUIProgressReporter` implémente `orchestration.ProgressReporter`
  - Réutilise `cli.NewProgressWithETA()` pour le calcul d'ETA (pas de réimplémentation)
  - Itère sur `progressChan`, appelle `program.Send(ProgressMsg{...})` pour chaque update
  - Envoie `ProgressDoneMsg{}` quand le channel se ferme

- `TUIResultPresenter` implémente `orchestration.ResultPresenter`
  - `PresentComparisonTable()` -> `program.Send(ComparisonResultsMsg{...})`
  - `PresentResult()` -> `program.Send(FinalResultMsg{...})`
  - `FormatDuration()` -> délègue à `cli.FormatExecutionDuration()`
  - `HandleError()` -> `program.Send(ErrorMsg{...})`

### Etape 4 : Sous-modèles

**Fichiers créés :**

- `internal/tui/header.go` - `HeaderModel`
  - Affiche titre "FibGo Monitor" avec style gradient
  - Version via `app.Version`
  - Temps écoulé formaté via `cli.FormatExecutionDuration()`
  - Layout 3 colonnes avec `lipgloss.JoinHorizontal`

- `internal/tui/logs.go` - `LogsModel`
  - Utilise `bubbles/viewport` pour le scroll
  - `AddProgressEntry(msg)` : ajoute ligne `[HH:MM:SS] AlgoName  XX.X%`
  - `AddResults(results)` : ajoute tableau de comparaison
  - `AddFinalResult(msg)` : ajoute résultat final
  - `AddError(msg)` : ajoute erreur formatée
  - Auto-scroll vers le bas (sauf si l'utilisateur scrolle manuellement)

- `internal/tui/metrics.go` - `MetricsModel`
  - Affiche : Memory (Alloc), Heap (HeapInuse), GC Runs, Goroutines
  - Calcule la vitesse de progression (delta progress / delta temps)
  - Formatage humain des tailles mémoire (KB/MB/GB)
  - `UpdateMemStats(msg)` : met à jour depuis `runtime.ReadMemStats()`
  - `UpdateProgress(msg)` : met à jour vitesse de calcul

- `internal/tui/chart.go` - `ChartModel`
  - Sparkline avec caractères braille/blocs (`▁▂▃▄▅▆▇█`)
  - Buffer circulaire de `dataPoints` (limité par la largeur du panel)
  - `AddDataPoint(progress)` : ajoute point
  - `Reset()` : vide le buffer
  - Affiche progression moyenne et ETA sous le graphique

- `internal/tui/footer.go` - `FooterModel`
  - Raccourcis clavier formatés : `q: Quit  r: Reset  space: Pause/Resume`
  - Indicateur d'état aligné à droite : Running / Paused / Done / Error
  - `SetPaused(bool)`, `SetDone(bool)` pour changer l'état

### Etape 5 : Modèle racine et point d'entrée

**Fichier créé : `internal/tui/model.go`**

- `Model` struct principal :
  - Sous-modèles : `header`, `logs`, `metrics`, `chart`, `footer`
  - Etat : `ctx`, `cancel`, `config`, `calculators`, `progressPer []float64`
  - Résultats : `results`, `startTime`, `paused`, `done`, `exitCode`
  - Terminal : `width`, `height`
  - Bridge : `ref *programRef`

- `NewModel(ctx, cancel, calculators, cfg)` : constructeur

- `Init()` : retourne batch de commandes
  - `tickCmd()` : timer 500ms pour sampling métriques
  - `startCalculationCmd()` : lance les calculs en goroutine via `orchestration.ExecuteCalculations()`
  - `watchContextCmd()` : surveille l'annulation du contexte

- `Update(msg)` : dispatch des messages
  - `tea.KeyMsg` : quit (q/ctrl+c), pause (space), reset (r)
  - `tea.WindowSizeMsg` : propage dimensions à tous les sous-modèles
  - `ProgressMsg` : met à jour logs, chart, metrics
  - `ComparisonResultsMsg` / `FinalResultMsg` : met à jour logs
  - `ErrorMsg` : met à jour logs, marque done
  - `TickMsg` : lance `sampleMemStatsCmd()` + relance `tickCmd()`
  - `MemStatsMsg` : met à jour metrics
  - `CalculationCompleteMsg` : marque done, stocke exitCode
  - `ContextCancelledMsg` : quitte proprement

- `View()` : compose le bento grid
  - Calcule dimensions des panneaux selon taille terminal
  - Logs = 60% largeur, Metrics+Chart = 40%
  - Metrics = 40% hauteur droite, Chart = 60%
  - `lipgloss.JoinHorizontal` / `JoinVertical` pour la composition

- `Run(ctx, calculators, cfg) int` : point d'entrée public
  - Crée le modèle, crée `tea.NewProgram` avec `tea.WithAltScreen()`
  - Injecte le `*tea.Program` dans `programRef` avant `p.Run()`
  - Retourne l'exitCode du modèle final

- `startCalculationCmd(ref)` : `tea.Cmd` qui lance l'orchestration
  - Crée `TUIProgressReporter` et `TUIResultPresenter` avec le `programRef`
  - Appelle `orchestration.ExecuteCalculations()` (bloquant)
  - Puis `orchestration.AnalyzeComparisonResults()`
  - Retourne `CalculationCompleteMsg{ExitCode}`

- `tickCmd()` : retourne `tea.Tick(500ms, func(t) TickMsg(t))`
- `sampleMemStatsCmd()` : lit `runtime.ReadMemStats()` + `runtime.NumGoroutine()`
- `watchContextCmd(ctx)` : attend `<-ctx.Done()`, retourne `ContextCancelledMsg`

### Etape 6 : Intégration dans le cycle de vie

**Fichier modifié : `internal/app/app.go`**

- Ajouter import `"github.com/agbru/fibcalc/internal/tui"`
- Ajouter dans `Run()` (ligne ~141, avant `return a.runCalculate(ctx, out)`) :
  ```go
  if a.Config.TUI {
      return a.runTUI(ctx, out)
  }
  ```
- Nouvelle méthode `runTUI(ctx, out) int` :
  - Setup context avec timeout + signaux (même pattern que `runCalculate`)
  - Récupère les calculateurs via `cli.GetCalculatorsToRun()`
  - Appelle `tui.Run(ctx, calculatorsToRun, a.Config)`

### Etape 7 : Tests

**Fichiers créés :**
- `internal/tui/model_test.go` : tests unitaires pour Update() avec divers messages, View() basique
- `internal/tui/bridge_test.go` : tests pour TUIProgressReporter (drainage channel, envoi messages)
- `internal/tui/chart_test.go` : tests pour le rendu sparkline avec différentes données

**Fichier modifié :**
- `internal/config/config_test.go` : ajouter test case pour le flag `--tui`

---

## Fonctionnalités clavier

| Touche | Action |
|--------|--------|
| `q` / `Ctrl+C` | Quitter (annule le contexte, arrête les calculs) |
| `Space` | Pause/Resume l'affichage (les calculs continuent) |
| `r` | Reset les métriques et le graphique |
| `Up` / `k` | Scroll logs vers le haut |
| `Down` / `j` | Scroll logs vers le bas |
| `PgUp` / `PgDn` | Scroll rapide |

---

## Points de conception critiques

1. **Partage du `*tea.Program`** : Un wrapper `programRef` (pointeur partagé) survit aux copies de modèle par bubbletea. Initialisé entre `tea.NewProgram()` et `p.Run()`.

2. **Thread-safety** : `tea.Program.Send()` est thread-safe. `ProgressWithETA` n'est accédé que dans la goroutine unique du `TUIProgressReporter`. `Update()` de bubbletea est single-threaded par design.

3. **Pause** : Ne pause pas le calcul (impossible sans contrôle de goroutine), seulement l'affichage (ignore les `TickMsg`, fige les logs). Même comportement que btop.

4. **`runtime.ReadMemStats()`** : Opération stop-the-world, échantillonnée seulement toutes les 500ms pour minimiser l'impact sur les calculs.

5. **Annulation contexte** : Le `watchContextCmd` traduit les timeouts/signaux en messages bubbletea pour un arrêt propre.

---

## Fichiers existants réutilisés (pas de réimplémentation)

| Composant | Fichier source | Utilisation dans le TUI |
|-----------|---------------|------------------------|
| `ProgressWithETA` | `internal/cli/progress_eta.go` | Bridge calcule l'ETA |
| `FormatETA()` | `internal/cli/progress_eta.go` | Affichage ETA dans chart/logs |
| `FormatExecutionDuration()` | `internal/cli/ui.go:28` | Header elapsed, résultats |
| `formatNumberString()` | `internal/cli/ui.go:363` | Formatage des nombres dans les résultats |
| `GetCalculatorsToRun()` | `internal/cli/calculate.go` | Sélection des calculateurs |
| `app.Version` | `internal/app/version.go` | Affichage version dans le header |

---

## Vérification

1. `go build ./cmd/fibcalc` -- compilation sans erreur
2. `go test -v -race -cover ./...` -- tous les tests passent
3. `./fibcalc --tui -n 1000000` -- lance le dashboard TUI, vérifie :
   - Layout btop avec bordures arrondies et thème sombre
   - Progression en temps réel dans les logs
   - Métriques mémoire mises à jour
   - Sparkline qui se remplit progressivement
   - `q` quitte proprement
   - `space` fige l'affichage
   - `r` reset le graphique
4. `./fibcalc -n 1000000` -- mode CLI classique inchangé
5. `FIBCALC_TUI=true ./fibcalc -n 1000000` -- variable d'env fonctionne
