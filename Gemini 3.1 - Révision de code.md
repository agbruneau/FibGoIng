# **Rapport d'Évaluation Académique : agbruneau/FibGo**

**Domaine / Tech Stack :** Calcul mathématique haute performance, CLI et bibliothèque (Go).

**Audience Cible :** Ingénieurs systèmes, développeurs backend, chercheurs en algorithmique.

**Date de l'évaluation :** Février 2026

## **1\. Tableau de Synthèse**

| **Axe d'évaluation** | **Cote** | **Score** |

| 1\. Qualité architecturale | Excellent | 9.5/10 |

| 2\. Qualité du code | Excellent | 9.0/10 |

| 3\. Documentation et onboarding | Excellent | 9.5/10 |

| 4\. Testabilité et couverture | Satisfaisant | 7.5/10 |

| 5\. Opérabilité et production-readiness | Excellent | 9.0/10 |

| 6\. Gouvernance open-source | Satisfaisant | 7.5/10 |

| **Note Globale** | **Excellent** | **8.6/10** |

## **2\. Évaluation Détaillée par Axe**

### **1\. Qualité architecturale**

**Cote :** Excellent

**Justificatif :**

L'architecture respecte strictement les conventions Go (cmd/ pour les points d'entrée, internal/ pour la logique métier encapsulée). La conception est parfaitement alignée avec le problème des performances extrêmes : séparation claire entre les mathématiques pures (bigfft, fibonacci), la gestion de la mémoire (arena.go, gc\_control.go), et l'interface utilisateur (ui, progress). Le couplage semble minimal, favorisant une approche modulaire.

**Recommandations :**

* **P2 :** Extraire les interfaces des stratégies algorithmiques (Fast Doubling, Strassen) dans un package partagé pour faciliter l'injection de nouveaux algorithmes mathématiques par des contributeurs tiers.  
* **P3 :** Isoler davantage le bump allocator de la logique métier de la FFT pour le rendre réutilisable en tant que module de gestion mémoire autonome.

### **2\. Qualité du code**

**Cote :** Excellent

**Justificatif :**

Le code démontre une maîtrise avancée de l'idiomatisme Go et des contraintes d'allocation. L'utilisation d'une stratégie "zéro-allocation" avec sync.Pool et d'un allocateur de mémoire par "bump pointer" réduit drastiquement la pression sur le ramasse-miettes (GC). La présence d'un .golangci.yml configuré avec 26 linters indique une rigueur exceptionnelle sur la dette technique et la maintenabilité.

**Recommandations :**

* **P2 :** Auditer la complexité cyclomatique des fonctions mathématiques denses (notamment dans internal/bigfft/), où l'optimisation extrême nuit souvent à la lisibilité.  
* **P3 :** S'assurer que les optimisations bas niveau (utilisation potentielle du package unsafe pour le zero-copy) sont strictement isolées et documentées pour éviter les corruptions de mémoire silencieuses.

### **3\. Documentation et onboarding**

**Cote :** Excellent

**Justificatif :**

Le dépôt propose une documentation de niveau entreprise. Le README.md expose clairement l'objectif, les algorithmes utilisés et les caractéristiques de performance. Le dossier docs/ est remarquablement riche, contenant des analyses de performance (PERFORMANCE.md), des guides de calibration, et surtout un dossier architecture/ documentant les flux d'exécution et les patterns de conception.

**Recommandations :**

* **P2 :** Intégrer un diagramme C4 (Context/Container) directement dans le README pour donner aux architectes une vision immédiate des interactions internes.  
* **P3 :** Fournir des exemples d'utilisation de FibGo en tant que *bibliothèque* importable dans un autre projet Go, au-delà de son usage en tant qu'outil CLI.

### **4\. Testabilité et couverture**

**Cote :** Satisfaisant

**Justificatif :**

Le projet affiche un badge de couverture honorable (80 %). La structure inclut un dossier test/e2e/ pour les tests d'intégration complets de la CLI, ainsi qu'un package internal/testutil/. Cependant, pour un outil de précision mathématique calculant des millions de chiffres, 80 % laisse une marge de risque sur les cas limites (edge cases) complexes.

**Recommandations :**

* **P1 :** Implémenter des tests de fuzzing (Go Fuzzing natif) sur les entrées des algorithmes de Fast Doubling et FFT pour débusquer les paniques ou erreurs de précision sur des nombres pseudo-aléatoires massifs.  
* **P2 :** Augmenter la couverture de code à \> 90% pour le code critique situé dans internal/fibonacci/ et internal/bigfft/.

### **5\. Opérabilité et production-readiness**

**Cote :** Excellent

**Justificatif :**

L'opérabilité est l'un des points forts du projet. FibGo intègre des modules dédiés à l'observabilité système (internal/sysmon/), à la remontée de métriques (internal/metrics/), et à la gestion des erreurs parallèles (internal/parallel/). La gestion intelligente du ramasse-miettes (désactivation sous charge avec un filet de sécurité de limite de mémoire) démontre une conception taillée pour les environnements de production sous forte contrainte.

**Recommandations :**

* **P2 :** Si FibGo est appelé à être utilisé comme worker dans une architecture distribuée, exporter les métriques du package metrics/ vers des formats standards (Prometheus/OpenTelemetry).  
* **P3 :** Ajouter un mode d'exportation de logs structurés (JSON) via slog pour faciliter l'ingestion par un système SIEM ou un stack ELK/Loki.

### **6\. Gouvernance open-source**

**Cote :** Satisfaisant

**Justificatif :**

Les bases sont saines : présence d'une licence Apache 2.0 (idéale pour l'entreprise), d'un CONTRIBUTING.md, et d'un CHANGELOG.md. Le cycle de développement semble structuré avec l'utilisation de balises sémantiques. Cependant, le projet souffre d'un manque de signaux sociaux (0 fork, 0 star), indiquant que l'outil, bien qu'excellent techniquement, n'a pas encore été éprouvé par une communauté diversifiée. Il manque également des Issue/Pull Request templates.

**Recommandations :**

* **P1 :** Créer des templates GitHub .github/ISSUE\_TEMPLATE (rapport de bug, demande de feature) et un pull\_request\_template.md.  
* **P3 :** Ajouter un Code of Conduct (ex: Contributor Covenant) pour standardiser l'accueil de la communauté.

## **3\. Verdict Global**

**Verdict : Prototype mature (High-End)**

FibGo n'est pas un simple "Proof of Concept". C'est un outil d'ingénierie logicielle d'une maturité exceptionnelle sur les plans de l'architecture bas niveau, de l'optimisation des ressources et de l'idiomatisme du code. Il est virtuellement "Prêt pour la production" dans un contexte de calcul pur en CLI. Pour atteindre le statut d'adoption "Enterprise" généralisée (intégration dans des pipelines tiers ou des serveurs de calcul), il doit consolider ses tests par fuzzing et standardiser son observabilité (OpenTelemetry).

## **4\. Top 5 des Actions Prioritaires (Enterprise Readiness)**

1. ![][image1]Implémenter des pipelines de Fuzz Testing natifs à Go pour valider l'intégrité arithmétique des algorithmes FFT et Strassen sous des charges erratiques.  
2. ![][image2]Déployer les templates de base GitHub (Issues, PRs, Code of Conduct) pour institutionnaliser la collaboration technique.  
3. ![][image3]Extraire les interfaces des stratégies algorithmiques (Fast Doubling, Strassen) dans un package partagé pour faciliter l'injection de nouveaux algorithmes.  
4. ![][image4]Ajouter des exemples clairs d'utilisation de FibCalc en tant que bibliothèque (API publique) dans le README.  
5. ![][image5]Assurer que les métriques système (sysmon) et de performance puissent être formatées de manière compatible avec les standards de l'industrie (Prometheus/JSON structuré).

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA1CAYAAAD8i7czAAAE3klEQVR4Xu3cP4hcRRgA8A1GUBQ1ajjN7d3bHIcgCBIOJWAECxEEBQsLwSB2/gEFFQlYCWIvEhREEAuNgmiVRq6wsBDTaCEpJJBIQiCQHAROiNHE79ubt5mbrDFqEoT8fjC8mW/mvdm31cfM7A4GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADA/0fXdXfWpe2/GuX3MBqNnojqxravtrS0dO3s7Oxwfn7+ybbvn4j5Xm9jAAATc3Nz90XCcLaORXslyodZj2Tk4eyP8keUb+pxl0o8d/dwOFys2qejvJ31TIqivu/c6H8u7r87ysk2/lfinRdi/Jk2PjMzc0N+F5s3b76xj8XYj7LU42LMgYi938SOb9269d46VuIrMfaZNg4AMJHJRiQNh+tYtI9GOVTHRqPRx5cxYfu2am7MpCiTpqp/nLz9W9OSqgvJ+aLsbePTxLjVePZSG29syHfKax2M7/SOKKM6BgBwnkgkTkZ5owqNk4vII56vYpctYctVq3rlKZKfHSW5GYt5r4v++/t2sSFijywsLNzcxMeraXHPQ03s5Nzc3D11LM3Ozt6W49t4xI7mymLOkfP38Yg9Vo8bTEnE4jPdlc+txgzy/WLcSh1LuXqYW695bfsAACYy4chzWFV7fyQmn9Vj0uVK2Foxxxdds+JXi7598VleyXpcn21W4lYy+RkOh9dH/UCJ5dm8s3mtE6lor+YKV9lyzf5Xq75sf5L1GPN91LfFPDtzJS3qP/XjSnu1uu+tMncmvONEr8z/ZZRPs16Nzfm3l/pXg785LwcAXKXKyk8mJx/0ZdBs2/WuYMJ2plu/4jeR58Kib3/fjvpyJkhZj3eZifapMu6B+LwvVOPWnV/L94iyu2pPktZMAPMz9H3lvZfj+nVc99T3tVutWc9Vv3xeH0vRXq1XEfMdmvlP9HUAgHUywYhk4Xgbn+ZiErauSvymlPfa8a1clcpkp17xq2VflGNRfoixzw3WJ5fj7cm+VNuMG+qkalDOyG3ZsuX2bPRz9p1dc34t6ge7stqW4+pt2G7K+bWI7Y6ypwq126bj+aMcjrIc9z9ejQUAWC8TjijvtvFpLiZh+6/myy9S23gv+2LMpjaeRmt/w5EyQcpfXr6UjUyo+qRqOBze2pUt0v6+MufBvK9sj+bq26N9f47tz7/lc/NafiU6ScRi7lvq8bna12+/5tz5PWc9n5/3XugdAQBq/YrUeYfup7kSCVs8f2934fNrp/qVsZTJVnyu7SUpmqxiRf27fiUs+nZlPP82JOLb2oQpk7BubVXt6WhuzNW4KDvKvTsjvlzqm3JMJG8PZjKWW5zR/jW3ZOMzPFXG5Hbq6axH7PMS29WdW6H7sVzXJWwx9s1pP6AAAK5ikTAcyqShKpMD960+GarL/CXexuvW/uNt3RzdlJW/8j9oZ2L+X+J6anFx8aa+L9pHSvz3KNv6eDlTdiTKi30sxr0c7RNRfo7EKy7j+fP8XspE9rcoxyKReqe/J5V7XqvaeV+9pZz35hm8yZm5Mn+Oy9g4ocxfkmasfN4jEbqmHw8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABr/gRBcEGJep6UpQAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA1CAYAAAD8i7czAAAFHElEQVR4Xu3bTYhWVRgA4BENjIp+RXK+mTszVmKbhCEoCNr0uyhChX5s30YIalGrCKJVmyhpEYZECwmCamFEBUVBWEKrrBYtSqwIQSmyRTHa+37fOePxOjpFTuX0PHC457zn555Zzcu55xsbAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/jEruq67spbp6em1/QH/khVTU1MPxZ4+mpycfDgDs7Oz561fv36iNw4AYPmLpGhzlONtLJKlO9pY1A9HmeuPO9vivZvyHYPB4LI2HrGnlvrdAAD/WZEIfZAnWW1scnLypkyQ1qxZc2EzLk/hlixpmp6e7nL9mZmZi/t95d37+nEAgP+FTJKibG5jkbC9HbG5NrbUCVusfSzK7n48lXdv68djn1unpqZWN6EVEburaZ8ixt9e62vXrr0g1+71r851o7qyxiKZvK22y/oral9p176t+em29jXy0/Od+WyD4+Pjl0d8Y9ZzXnnvKeqe+mtnO/ru6ccBgGWkJCzHN2zYcFGNRWJwa8b6ScBSJmyx7o259rp1667o9y0kk5woR0r9+SiPjo2Sop2ZQMVzTxm6qt1z1N+N/tl47i/t/VG+Ld05f24wGFxd+j7LZyREz8ZjZa6T60d5oM6JvjdjvUu7UbK5t8w73iaR0d4e5ZUy/sPsz3q85/yY+2C090XZE/Vry/jX69zSPjQxMXH9WNlfPFeV+NFY74ZmzjAOACwz8Y/+zkwgorxYygun++FBt4QJWyQeL//ZtfMzbRk7TFBKAnYs1nhobJTU7I2yvfTlp90fSv2WMve1KDvKcjl++Dk4nkfqvNI+Wp7vj4+PD+r+Yp1deapV6+X986eROa5+Ss4fSbR/V9Qfqe9r9ns0k+RmzAdN/csY92TWZ2Zmron2oRrvTvwN2T5c6wDAMpPJQVdOmxbTLZKw5d2z7kTit2Dpn9pV3SiJGiZIVUlQct7xKHORuDzejJ3fc9S3Rfm9ac8nc2Xsc7Wv9uepWNbzJCznl1OyjB+I8kYmd+2caD/WnTi1O0kmbdG3M+uZ7Jb3D3Xl9Kxp75+YmLi7tsdGCdv8+Jwfe7ov63VP7T3CYnhqGOVglPcmF/kEDACc4/IffznpWVS3SML2d+QeTrd2f4/R/jYTqKadp1D52TITnuui/XPT92uUjXlXLNvtSVnpz3txmQCd8W+Lvm/6SVzVjU7IZkt9Rze6h5d32vIz6tFudHetjh0mYHU/5XRuPlHN+fFYlf2l75Q9NSeMAMByV//x/4V7Y2dMav6uXDvKljY2GAyuyng9ESvjdteEbXr0y9L2c2R+4h3eL8s7YnW/kdC9U/rz7tt8ghTxV0v1pLtuqRvdO6sndSfdS2uVecMfE2Q93jvelc+V3SjRq8nclvqOeD5dnnnnbldZan6t/AxaTiwX3FM/Xse3MQDgHJdJS/7Tb8r8KdBCemOznPTLyrMkT6R+yvUzkYrnL/G8PxKaJ/oDo+/rbvRJ8KUF+g7FnAPxfCaen2S7TWai/XGU76N80c6Ld90csd/K3M/HShIW8Uu63i9mq+ibir4fazvqb0X5IcKbsl2SxvxBwuF6B60bnQDWBO/7SDo39OZ/Vduxzr25pygHo/5pnVfWmit7/W6s+UUrAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/xd/AEPRXHnmBPSEAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA1CAYAAAD8i7czAAAFUUlEQVR4Xu3cT4geRRYA8AmJ4KLi6hqDyWR6vmQ1iIJIEFQUPKgoqCwqrCh72JMinrx4FYIHb0HEgygiIoIIHkSSQ5Cggrq7Fw8qeNGViKBsAkICG0nG977v1VhpxsHR8Q/J7wdFV72urq6eyzyqq7+5OQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4De3YRiGS1qZTCZbxh1+Z5tiXv8dB9eqnu3W+fn5C8fnAAD+8CKZuTvKUh9bXFy8rcV27959VtTfqr4vRznR9/015RzGc/uZMvH70XHi3KNRjoxiH0W5vY+tVVx/eZRvx3EAgDWJhOJglHf62MLCwg2Z4GzevPncqD/WJzuVRD3Q9/81xD32xL3vXS3R+qnqef43jq+mPf84vhZx3xeyjOMAAGtSCdjdfSySjP1DraRNJpOron6sncv+mcT90Hv9zc/P/2lxcXFv3fuUhG3Lli3nxGFj1mMed8ZhQ38+rjs7E71cGWyxGOO1KE9t27btL/lqtO+f40X/3X0sXw1H/5N9rNm5c+fF4zFSjj2eT4zx7fbt26/suuWc7+jbvZxHPV8+x039M6RsR/xv4zgAcBrL5CATol27dp3XYpE03JKxlZKCSmSWMmkZn1tPcY8P65h76/qVrtxztydjUZ6Lcv/Q7XGL+jeRIF1T/TLh3FTx76Icj+rGSAa3Rf3/GY/6X6N+fZSD8dw3V99LIil6Mo7vZD2vyXgkZPM5Zvu7RP2rPFZ9KffH7dix4/ys53xjHluznmNkMlf9DmRSFseP+mvjsCn/7tmvrvk4xru0zrV+R2Ne11b99bymnQMATmPxj//2ShCerfLMah8exPkjUe4Zx9dTJC5XRLJzY9Yz8an5ZeI0nW+LVd8XcsWpzn0S9cezHonTZdH+poac7l9riVZLOuuad+u41D93tD/Pe7X2XI3R+lRi9kbWY653Rf26rMf9/xn1fVmvxGx5/1omhDX3V6I8XbEdUf8u63H8z9ws0cy5bYhz/2j94vhJq1f7cKsDAKe5YbZ/bXm1ZzXR70CtXq2okpiW+K1YxtesJPqdGGZJ2nIZv7KM2Jt9O85fkP1W2nO2MNq/tjDbk3ewtfOV5VArbs14rGg/UPP4Io7PR2K22J2bJlxjmUxmGcdrnAuq/kT/LJXkjffaTZPFKIeG2QpdvnYFAM4UmQhE7vHgOD6Wq1OTyWSoZq4CPXpKh3USc3movT5sKsFZTlLylWauVvV9KtFZ8eOEofavde2j2b8lZNF+P8ojufctmhvqlWkbK1+Hbqwk799tjN4q953eJ+vt50T61b3qcyifJe7952xngtfPNfUrigDAGaYlAlu3br1ofG4sk4/hh5WyfS0RWU/5oUGMu38czzlmwtTaWa/kalnbO9bHov3S3Gx16liUyzPWJz9xfK+O0z1kQ/10SSaHQ301G/d5u/pcN4xWIqP9WR1PWZ2Laz6t+PTVZu2Tuzpjk9lHFEer6/T1Z+4jjGv+Vdfk33k6116bcxP9H89n7mMAwGmmEoOlrvzo741FcvDiqO+Krx5/iWG2N246dtzvvox1G/BbmW7yj4Tqg1Ovnonr/h59jkc5VAnQ9GvNvLbvV32OtD1tmWBF+3BLgOp3505GOTb60vSpKF9niWv2tnh9uHG4zj3f9d8X5csoD7dYxXM/Wr7efLXK1231chjNtak9eScWZq9kv5yrDyEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4E30Pd6hhmkgDuxoAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA1CAYAAAD8i7czAAAFZElEQVR4Xu3cSYgdRRgA4AkqKCquISaZeT2ZqMEFXOJy0IMICiKKqKCinqOQkwe96sGDghCCJxWCingREURBCeJyET1HQQSjuIASBckEoiTx/9+rGmsqMy5xxCXfB0V3/VVdXe+dfqqre2oKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD4583Ozh4/DMPaWqJ+at/nnxBzOS/KztFo9Erf9kfFbzlrbm7u3D7+Z6xfv/6MmZmZC2OsK/u23oYNG9ZEuX56enp93/ZHrVmz5sT4zVf1cQDgKBeJ0XtZutihjRs3zpTzb+KwKkuc/5CJVNt3JcXY30VydEcX+zpi97Wx3xNJ1s05Vh8/EjHOz5lALhHfGfN6swnl/3MojzWQSVyJHVtjcc2WTMxqvYp+l0T5aaq5HgBgLBOKKLf2sdFodNMwWXnL9g0Zj9hcaTut7b8SIpH5JMbd0cfjfndHOdjHf0v0f6KPHaFjS8L1u2Lum6PvfB/vRZ/dfSzF79/WxwAAxo/gMiHZtGnTyW08Y9PT0ydMTRKWg3Nzc6dkPBO1ksCtbfv/VTHerSUxOmx1qSSONWlalY8dy/kxkeTcUvu18jHmsHhV7Ji6qhXXXLN58+bjmraUq2M35LENxr2vjvieXCmLMS+r8Vx9rCuQTd8dXcK5Kufe1MeWSwDj/z6nvQcAwFgmKX0CEQnNs1EubmNV9N3a918JMeb+KB/28RTxF+o9Y14flARubxyvK+0LiV6Z33ic3H8W54+W697NflE+ysSo/Q3lmufbfk3bS1nP5DXK2XH+cdz3njg/Pc7n161bd2bTdz5X2Uo1E8Bnylxfy0CZz6VlHgsJb5zfGP2+yGsykcx71jYAgEwWdkb5LspTWSJheWSJ1aexkkwcqqttKynHjXtv6eNpmOwh25XJUVnx2t4mNXE+PzMzc/kw2QPWJlu3ZVKXq2PlceU4sYvze+P8yeyTq2TdNQ8MzX6+cu/xSt3q1atPKvPMfWv1UWldkVu0f638loy9H2Vr6ZOrcA8NzR7ASOKm2+tirlfM/sn9egDA/1xJQJZMlHqZvJTHpEsqycc48Vum3N1fk2Ynb6rmvri6OrVItuXqVlPfkwla2x6JzkVx/DDKT7laFcfHc9zap17X1kssrxmvgJX6rnxhoVQX7V9rkr7sl6ty73dt/f61msQtvHAQ9d3N+FnPFbwDZc7b/45kGAD4D6srRu1jveVEv8+myipQJku5atV1+UtyHkP34kOKROaCUfciQkmC6iPQ/PxHTaI+H5ZJCqcmydP2Phix+WGyd63WD+X/Uh5f5gsXPzZtmVx9XM73l899jD+DknPM0iaJcX5n6b+qxuv4WUr97aE8tgUAOEz59MXCCtJyhslj06eHX1fK8jMfKyoSmm1D9xmOsk9s0fyGJkFLcd0nUb+ttL3YrhaWFyqey/OyArbUpzl215W9HKeOHcdHS0Jbf+t4tSwfC4/Kixel31vl+GN5LPt66Z+xb6Lv1VHuyetqgpxtEXsjjzHfh4cmkSzjv1PrAMBRLBOHtiz1XbBUHwP2pe+3EobJ3rQDwyQp/CrKy8v0eXWYvKSwP+Z3ftf+aXm8mO3X1ngkRo+0/ap8xBv9Dkb5Pj+yO0z28+WqWt2L9ljUv42yr93bN0zmua/pd3+OMTSrhDGPB8t4C7FS/7bWU1z7QcS+jLI3zu9q2wAA/nMiqdmTq1Z9HACAf4fDNvEDAPAvMhqNbq+lbwMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA4Kj2C4OmXopCT7SAAAAAAElFTkSuQmCC>