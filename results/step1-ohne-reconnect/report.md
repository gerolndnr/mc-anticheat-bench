# AntiCheat Benchmark – acbench-step1

Run `step1` · Minecraft 26.3 · 3 repetitions · clients: meteor · anticheats: none, grim

## Summary

| Client | AntiCheat | Score | Detection | False positives | Mitigation | Median time to flag | Valid variants |
|---|---|---:|---:|---:|---:|---:|---:|
| meteor | grim | 77 | 63 % | 0 % | 70 % | 0.9 s | 20 (+3 without effect) |

**meteor vs grim** by category: combat: detection 50 %, FP 0 %, mitigation 25 %; movement: detection 72 %, FP 0 %, mitigation 100 %

## Cheats

Detection = share of cheat trials with at least one flag. Advantage = cheat minus baseline on the scenario metric (sign-normalized). Retained = advantage with the anticheat relative to the advantage without any anticheat.

### meteor

| Scenario | Variant | AntiCheat | Detection | Time to flag | Advantage (raw) | Retained | Top checks | Notes |
|---|---|---|---:|---:|---:|---:|---|---|
| autoclicker | cps10 | none | 0 % (0/3) | – s | 3.16 (3.16) | 100 % | – |  |
| autoclicker | cps10 | grim | 67 % (2/3) | 0.9 s | 3.30 (3.16) | 104 % | Post ×72 |  |
| autoclicker | cps20 | none | 0 % (0/3) | – s | 13.23 (13.23) | 100 % | – |  |
| autoclicker | cps20 | grim | 67 % (2/3) | 2.2 s | 13.33 (13.23) | 101 % | Post ×68 |  |
| criticals | minijump | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| criticals | minijump | grim | 67 % (2/3) | 0.7 s | 0.00 (0.00) | – | Simulation ×21, GroundSpoof ×18 | no measurable effect without anticheat |
| criticals | packet | none | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received) |
| criticals | packet | grim | 100 % (3/3) | 4.0 s | 0.00 (–) | – | TickTimer ×37, Timer ×28, Post ×8, GroundSpoof ×7 | no measurable effect without anticheat |
| criticals | updatedncp | none | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received) |
| criticals | updatedncp | grim | 67 % (2/3) | 3.1 s | 0.00 (–) | – | TickTimer ×24, Timer ×20, Post ×9, GroundSpoof ×5 | no measurable effect without anticheat |
| killaura | closet | none | 0 % (0/3) | – s | 8.67 (8.67) | 100 % | – |  |
| killaura | closet | grim | 0 % (0/3) | – s | 9.00 (8.67) | 104 % | – |  |
| killaura | default | none | 0 % (0/3) | – s | 7.67 (7.67) | 100 % | – |  |
| killaura | default | grim | 0 % (0/3) | – s | 8.67 (7.67) | 113 % | – |  |
| reach | plus05 | none | 0 % (0/3) | – s | 10.00 (10.00) | 100 % | – |  |
| reach | plus05 | grim | 33 % (1/3) | 0.3 s | 0.00 (10.00) | 0 % | Reach ×19 |  |
| reach | plus1 | none | 0 % (0/3) | – s | 11.00 (11.00) | 100 % | – |  |
| reach | plus1 | grim | 67 % (2/3) | 0.4 s | 0.00 (11.00) | 0 % | Reach ×39 |  |
| velocity | half | none | 0 % (0/3) | – s | 0.83 (0.83) | 100 % | – |  |
| velocity | half | grim | 67 % (2/3) | 0.7 s | 1.65 (0.83) | 197 % | Simulation ×28, AntiKB ×5 |  |
| velocity | zero | none | 0 % (0/3) | – s | 1.68 (1.68) | 100 % | – |  |
| velocity | zero | grim | 100 % (3/3) | 0.8 s | 1.65 (1.68) | 98 % | Simulation ×32, AntiKB ×15, GroundSpoof ×7 |  |
| fly | abilities | none | 0 % (0/3) | – s | 72.39 (72.39) | 100 % | – |  |
| fly | abilities | grim | 67 % (2/3) | 0.1 s | -1.25 (72.39) | -2 % | Simulation ×3 |  |
| fly | velocity | none | 0 % (0/3) | – s | 48.67 (48.67) | 100 % | – |  |
| fly | velocity | grim | 33 % (1/3) | 0.1 s | -0.33 (48.67) | -1 % | Simulation ×18 |  |
| jesus | solid | none | 0 % (0/3) | – s | 2.01 (2.01) | 100 % | – |  |
| jesus | solid | grim | 100 % (3/3) | 0.5 s | -1.16 (2.01) | -58 % | Simulation ×67, GroundSpoof ×4 |  |
| nofall | packet | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | packet | grim | 67 % (2/3) | 1.1 s | -0.00 (9.00) | -0 % | GroundSpoof ×18, Simulation ×7 |  |
| noslow | items | none | 0 % (0/3) | – s | 3.34 (3.34) | 100 % | – |  |
| noslow | items | grim | 67 % (2/3) | 0.1 s | -0.71 (3.34) | -21 % | NoSlow ×135 |  |
| speed | strafe | none | 0 % (0/3) | – s | 1.41 (1.41) | 100 % | – |  |
| speed | strafe | grim | 100 % (3/3) | 1.2 s | -5.43 (1.41) | -386 % | Simulation ×116, GroundSpoof ×37 |  |
| speed | vanilla | none | 0 % (0/3) | – s | 2.34 (2.34) | 100 % | – |  |
| speed | vanilla | grim | 100 % (3/3) | 3.9 s | -5.43 (2.34) | -232 % | Simulation ×47 |  |
| speed | vanilla_closet | none | 0 % (0/3) | – s | 0.59 (0.59) | 100 % | – |  |
| speed | vanilla_closet | grim | 67 % (2/3) | 0.8 s | -5.43 (0.59) | -920 % | Simulation ×88 |  |
| spider | default | none | 0 % (0/3) | – s | 18.72 (18.72) | 100 % | – |  |
| spider | default | grim | 67 % (2/3) | 1.8 s | 0.00 (18.72) | 0 % | Simulation ×65, GroundSpoof ×2 |  |
| step | default | none | 0 % (0/3) | – s | 10.00 (10.00) | 100 % | – |  |
| step | default | grim | 33 % (1/3) | 0.9 s | 0.00 (10.00) | 0 % | Simulation ×27 |  |
| timer | x1_2 | none | 0 % (0/3) | – s | 0.84 (0.84) | 100 % | – |  |
| timer | x1_2 | grim | 67 % (2/3) | 2.1 s | -1.71 (0.84) | -205 % | Timer ×38, Simulation ×16, TimerLimit ×3 |  |
| timer | x2 | none | 0 % (0/3) | – s | 4.12 (4.12) | 100 % | – |  |
| timer | x2 | grim | 100 % (3/3) | 1.3 s | -1.61 (4.12) | -39 % | Timer ×158, Simulation ×8, TimerLimit ×5 |  |

## False positives (baseline trials, cheat off)

| Client | AntiCheat | Scenario | Flagged | Top checks |
|---|---|---|---:|---|
| meteor | grim | autoclicker | 0 % (0/3) | – |
| meteor | grim | criticals | 0 % (0/3) | – |
| meteor | grim | fly | 0 % (0/3) | – |
| meteor | grim | jesus | 0 % (0/3) | – |
| meteor | grim | killaura | 0 % (0/3) | – |
| meteor | grim | nofall | 0 % (0/3) | – |
| meteor | grim | noslow | 0 % (0/3) | – |
| meteor | grim | reach | 0 % (0/3) | – |
| meteor | grim | speed | 0 % (0/3) | – |
| meteor | grim | spider | 0 % (0/3) | – |
| meteor | grim | step | 0 % (0/3) | – |
| meteor | grim | timer | 0 % (0/3) | – |
| meteor | grim | velocity | 0 % (0/3) | – |

## Run health

- `meteor/grim`: finished=True, unattributed flags=2, errors=0
- `meteor/none`: finished=True, unattributed flags=0, errors=0
