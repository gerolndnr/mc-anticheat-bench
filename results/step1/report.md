# AntiCheat Benchmark – acbench-step1

Run `step1` · Minecraft 26.3 · 3 repetitions · clients: liquidbounce, meteor · anticheats: none, grim

## Summary

Per cheat type the strongest setting counts; every cheat type weighs the same. Detection = any flag; default alert = the anticheat's stock thresholds would have alerted within the ~5 s trial.

| Client | AntiCheat | Score | Detection | Default alert | False positives | Mitigation | Median time to flag | Valid variants |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| liquidbounce | grim | 80 | 75 % | 33 % | 3 % | 56 % | 0.5 s | 25 (+6 without effect) |
| meteor | grim | 92 | 92 % | 42 % | 0 % | 75 % | 0.4 s | 20 (+3 without effect) |

**liquidbounce vs grim** by category: combat: detection 50 %, FP 0 %, mitigation 25 %; movement: detection 88 %, FP 4 %, mitigation 71 %

**meteor vs grim** by category: combat: detection 75 %, FP 0 %, mitigation 25 %; movement: detection 100 %, FP 0 %, mitigation 100 %

## Cheats

Detection = share of cheat trials with at least one flag. Advantage = cheat minus baseline on the scenario metric (sign-normalized). Retained = advantage with the anticheat relative to the advantage without any anticheat.

### liquidbounce

| Scenario | Variant | AntiCheat | Detection | Time to flag | Advantage (raw) | Retained | Top checks | Notes |
|---|---|---|---:|---:|---:|---:|---|---|
| autoclicker | cps10 | none | 0 % (0/3) | – s | -5.29 (-5.29) | – | – | no measurable effect without anticheat |
| autoclicker | cps10 | grim | 0 % (0/3) | – s | -5.21 (-5.29) | – | – | no measurable effect without anticheat |
| autoclicker | cps20 | none | 0 % (0/3) | – s | -4.89 (-4.89) | – | – | no measurable effect without anticheat |
| autoclicker | cps20 | grim | 0 % (0/3) | – s | -4.90 (-4.89) | – | – | no measurable effect without anticheat |
| criticals | jump | none | 0 % (0/3) | – s | 4.67 (4.67) | 100 % | – |  |
| criticals | jump | grim | 0 % (0/3) | – s | 4.67 (4.67) | 100 % | – |  |
| criticals | noground | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| criticals | noground | grim | 100 % (3/3) | 1.7 s | 0.00 (0.00) | – | GroundSpoof ×15 | no measurable effect without anticheat |
| criticals | packet | none | 0 % (0/3) | – s | 8.67 (8.67) | 100 % | – |  |
| criticals | packet | grim | 100 % (3/3) | 0.7 s | 0.00 (8.67) | 0 % | Timer ×127, TickTimer ×50, Simulation ×27, GroundSpoof ×19 |  |
| killaura | closet | none | 0 % (0/3) | – s | 8.00 (8.00) | 100 % | – |  |
| killaura | closet | grim | 0 % (0/3) | – s | 8.00 (8.00) | 100 % | – |  |
| killaura | default | none | 0 % (0/3) | – s | 8.00 (8.00) | 100 % | – |  |
| killaura | default | grim | 0 % (0/3) | – s | 8.00 (8.00) | 100 % | – |  |
| reach | plus05 | none | 0 % (0/3) | – s | 10.33 (10.33) | 100 % | – |  |
| reach | plus05 | grim | 100 % (3/3) | 0.3 s | 0.00 (10.33) | 0 % | Reach ×60 |  |
| reach | plus1 | none | 0 % (0/3) | – s | 11.33 (11.33) | 100 % | – |  |
| reach | plus1 | grim | 100 % (3/3) | 0.3 s | 0.00 (11.33) | 0 % | Reach ×58 |  |
| velocity | grim2344 | none | 0 % (0/3) | – s | 1.61 (1.61) | 100 % | – |  |
| velocity | grim2344 | grim | 100 % (3/3) | 0.6 s | 1.46 (1.61) | 91 % | Timer ×75, AimDuplicateLook ×21, AntiKB ×15, AirLiquidBreak ×15 |  |
| velocity | grim2371 | none | 0 % (0/3) | – s | 1.32 (1.32) | 100 % | – |  |
| velocity | grim2371 | grim | 100 % (3/3) | 1.7 s | 1.42 (1.32) | 108 % | AntiKB ×13, RotationPlace ×3, NoFall ×2, TransactionOrder ×2 |  |
| velocity | half | none | 0 % (0/3) | – s | 0.82 (0.82) | 100 % | – |  |
| velocity | half | grim | 100 % (3/3) | 0.6 s | 1.61 (0.82) | 197 % | Simulation ×63, AntiKB ×15 |  |
| velocity | zero | none | 0 % (0/3) | – s | 1.61 (1.61) | 100 % | – |  |
| velocity | zero | grim | 100 % (3/3) | 1.4 s | 1.61 (1.61) | 100 % | Simulation ×26, AntiKB ×15, GroundSpoof ×6 |  |
| fly | grim2373 | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | grim2373 | grim | 0 % (0/3) | – s | -0.09 (0.00) | – | – | no measurable effect without anticheat |
| fly | grim2859v | none | 0 % (0/3) | – s | -0.14 (-0.14) | – | – | no measurable effect without anticheat |
| fly | grim2859v | grim | 0 % (0/3) | – s | -1.25 (-0.14) | – | – | no measurable effect without anticheat |
| fly | vanilla | none | 0 % (0/3) | – s | 40.87 (40.87) | 100 % | – |  |
| fly | vanilla | grim | 100 % (3/3) | 0.6 s | -1.25 (40.87) | -3 % | Simulation ×51, GroundSpoof ×21 |  |
| jesus | ncp | none | 0 % (0/3) | – s | 1.96 (1.96) | 100 % | – |  |
| jesus | ncp | grim | 100 % (3/3) | 0.5 s | -3.03 (1.96) | -155 % | Simulation ×102, GroundSpoof ×8 |  |
| jesus | vanilla | none | 0 % (0/3) | – s | 1.96 (1.96) | 100 % | – |  |
| jesus | vanilla | grim | 100 % (3/3) | 0.5 s | -1.16 (1.96) | -59 % | Simulation ×32, GroundSpoof ×27 |  |
| nofall | grim2371 | none | 0 % (0/3) | – s | 2.00 (2.00) | 100 % | – |  |
| nofall | grim2371 | grim | 33 % (1/3) | 1.8 s | -0.00 (2.00) | -0 % | Simulation ×1 |  |
| nofall | packet | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | packet | grim | 100 % (3/3) | 1.2 s | 3.00 (9.00) | 33 % | Simulation ×18, Timer ×12, GroundSpoof ×7 |  |
| nofall | spoofground | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | spoofground | grim | 100 % (3/3) | 1.2 s | -0.00 (9.00) | -0 % | GroundSpoof ×9 |  |
| noslow | grim2360 | none | 0 % (0/3) | – s | 3.34 (3.34) | 100 % | – |  |
| noslow | grim2360 | grim | 100 % (3/3) | 0.1 s | -0.55 (3.34) | -17 % | NoSlow ×266 |  |
| noslow | grim2371 | none | 0 % (0/3) | – s | 1.69 (1.69) | 100 % | – |  |
| noslow | grim2371 | grim | 100 % (3/3) | 0.1 s | 1.75 (1.69) | 104 % | NoSlow ×3 |  |
| noslow | plain | none | 0 % (0/3) | – s | 3.34 (3.34) | 100 % | – |  |
| noslow | plain | grim | 100 % (3/3) | 0.1 s | -0.57 (3.34) | -17 % | NoSlow ×264 |  |
| speed | grimcollide | none | 0 % (0/3) | – s | -0.04 (-0.04) | – | – | no measurable effect without anticheat |
| speed | grimcollide | grim | 0 % (0/3) | – s | 0.00 (-0.04) | – | – | no measurable effect without anticheat |
| speed | legithop | none | 0 % (0/3) | – s | 1.29 (1.29) | 100 % | – |  |
| speed | legithop | grim | 0 % (0/3) | – s | 1.30 (1.29) | 101 % | – |  |
| speed | ncp | none | 0 % (0/3) | – s | 2.47 (2.47) | 100 % | – |  |
| speed | ncp | grim | 100 % (3/3) | 0.1 s | -5.08 (2.47) | -206 % | Simulation ×169, Timer ×43, TimerLimit ×4 |  |
| spider | vanilla | none | 0 % (0/3) | – s | 28.04 (28.04) | 100 % | – |  |
| spider | vanilla | grim | 100 % (3/3) | 0.4 s | 0.00 (28.04) | 0 % | Simulation ×4 |  |
| step | instant | none | 0 % (0/3) | – s | 10.00 (10.00) | 100 % | – |  |
| step | instant | grim | 100 % (3/3) | 0.6 s | 0.00 (10.00) | 0 % | Timer ×545, Simulation ×249, AimDuplicateLook ×60, TimerLimit ×7 |  |
| timer | x1_2 | none | 0 % (0/3) | – s | 0.85 (0.85) | 100 % | – |  |
| timer | x1_2 | grim | 100 % (3/3) | 0.5 s | -1.45 (0.85) | -170 % | Timer ×101, Simulation ×46, TimerLimit ×6 |  |
| timer | x2 | none | 0 % (0/3) | – s | 4.22 (4.22) | 100 % | – |  |
| timer | x2 | grim | 100 % (3/3) | 0.1 s | -0.85 (4.22) | -20 % | Timer ×311, Simulation ×9, TimerLimit ×7 |  |

### meteor

| Scenario | Variant | AntiCheat | Detection | Time to flag | Advantage (raw) | Retained | Top checks | Notes |
|---|---|---|---:|---:|---:|---:|---|---|
| autoclicker | cps10 | none | 0 % (0/3) | – s | 3.09 (3.09) | 100 % | – |  |
| autoclicker | cps10 | grim | 100 % (3/3) | 0.7 s | 3.11 (3.09) | 101 % | Post ×112 |  |
| autoclicker | cps20 | none | 0 % (0/3) | – s | 12.96 (12.96) | 100 % | – |  |
| autoclicker | cps20 | grim | 100 % (3/3) | 0.7 s | 13.25 (12.96) | 102 % | Post ×151 |  |
| criticals | minijump | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| criticals | minijump | grim | 100 % (3/3) | 0.7 s | 0.00 (0.00) | – | GroundSpoof ×27, Simulation ×27 | no measurable effect without anticheat |
| criticals | packet | none | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received), flagged before kick: 0/3 |
| criticals | packet | grim | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received), flagged before kick: 3/3 [TickTimer ×7, GroundSpoof ×6, Simulation ×3, Timer ×2] |
| criticals | updatedncp | none | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received), flagged before kick: 0/3 |
| criticals | updatedncp | grim | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received), flagged before kick: 3/3 [TickTimer ×8, GroundSpoof ×6, Timer ×1] |
| killaura | closet | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| killaura | closet | grim | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| killaura | default | none | 0 % (0/3) | – s | 8.33 (8.33) | 100 % | – |  |
| killaura | default | grim | 0 % (0/3) | – s | 8.33 (8.33) | 100 % | – |  |
| reach | plus05 | none | 0 % (0/3) | – s | 11.33 (11.33) | 100 % | – |  |
| reach | plus05 | grim | 100 % (3/3) | 0.3 s | 0.00 (11.33) | 0 % | Reach ×59 |  |
| reach | plus1 | none | 0 % (0/3) | – s | 11.67 (11.67) | 100 % | – |  |
| reach | plus1 | grim | 100 % (3/3) | 0.2 s | 0.00 (11.67) | 0 % | Reach ×58 |  |
| velocity | half | none | 0 % (0/3) | – s | 0.85 (0.85) | 100 % | – |  |
| velocity | half | grim | 100 % (3/3) | 0.7 s | 1.65 (0.85) | 193 % | Simulation ×25, AntiKB ×15 |  |
| velocity | zero | none | 0 % (0/3) | – s | 1.69 (1.69) | 100 % | – |  |
| velocity | zero | grim | 100 % (3/3) | 1.6 s | 1.65 (1.69) | 98 % | AntiKB ×15 |  |
| fly | abilities | none | 0 % (0/3) | – s | 72.48 (72.48) | 100 % | – |  |
| fly | abilities | grim | 100 % (3/3) | 0.1 s | -1.25 (72.48) | -2 % | Simulation ×5 |  |
| fly | velocity | none | 0 % (0/3) | – s | 48.67 (48.67) | 100 % | – |  |
| fly | velocity | grim | 100 % (3/3) | 0.1 s | -0.09 (48.67) | -0 % | Simulation ×81 |  |
| jesus | solid | none | 0 % (0/3) | – s | 2.01 (2.01) | 100 % | – |  |
| jesus | solid | grim | 100 % (3/3) | 0.5 s | -0.39 (2.01) | -19 % | Simulation ×45, GroundSpoof ×6 |  |
| nofall | packet | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | packet | grim | 100 % (3/3) | 1.1 s | -0.00 (9.00) | -0 % | GroundSpoof ×33 |  |
| noslow | items | none | 0 % (0/3) | – s | 3.33 (3.33) | 100 % | – |  |
| noslow | items | grim | 100 % (3/3) | 0.1 s | -0.52 (3.33) | -16 % | NoSlow ×205 |  |
| speed | strafe | none | 0 % (0/3) | – s | 1.39 (1.39) | 100 % | – |  |
| speed | strafe | grim | 100 % (3/3) | 0.1 s | -5.45 (1.39) | -392 % | Simulation ×74 |  |
| speed | vanilla | none | 0 % (0/3) | – s | 2.37 (2.37) | 100 % | – |  |
| speed | vanilla | grim | 100 % (3/3) | 0.1 s | -5.45 (2.37) | -230 % | Simulation ×73 |  |
| speed | vanilla_closet | none | 0 % (0/3) | – s | 0.61 (0.61) | 100 % | – |  |
| speed | vanilla_closet | grim | 100 % (3/3) | 0.1 s | -5.45 (0.61) | -890 % | Simulation ×78 |  |
| spider | default | none | 0 % (0/3) | – s | 18.72 (18.72) | 100 % | – |  |
| spider | default | grim | 100 % (3/3) | 0.4 s | 0.00 (18.72) | 0 % | Simulation ×141, GroundSpoof ×2 |  |
| step | default | none | 0 % (0/3) | – s | 10.00 (10.00) | 100 % | – |  |
| step | default | grim | 100 % (3/3) | 0.6 s | 0.00 (10.00) | 0 % | Simulation ×70 |  |
| timer | x1_2 | none | 0 % (0/3) | – s | 0.83 (0.83) | 100 % | – |  |
| timer | x1_2 | grim | 100 % (3/3) | 0.7 s | -1.22 (0.83) | -147 % | Timer ×93, Simulation ×34, TimerLimit ×6 |  |
| timer | x2 | none | 0 % (0/3) | – s | 4.14 (4.14) | 100 % | – |  |
| timer | x2 | grim | 100 % (3/3) | 0.1 s | -1.31 (4.14) | -32 % | Timer ×295, Simulation ×15, TimerLimit ×7 |  |

## False positives (baseline trials, cheat off)

| Client | AntiCheat | Scenario | Flagged | Top checks |
|---|---|---|---:|---|
| liquidbounce | grim | autoclicker | 0 % (0/3) | – |
| liquidbounce | grim | criticals | 0 % (0/3) | – |
| liquidbounce | grim | fly | 33 % (1/3) | Timer ×2, Simulation ×2 |
| liquidbounce | grim | jesus | 0 % (0/3) | – |
| liquidbounce | grim | killaura | 0 % (0/3) | – |
| liquidbounce | grim | nofall | 0 % (0/3) | – |
| liquidbounce | grim | noslow | 0 % (0/3) | – |
| liquidbounce | grim | reach | 0 % (0/3) | – |
| liquidbounce | grim | speed | 0 % (0/3) | – |
| liquidbounce | grim | spider | 0 % (0/3) | – |
| liquidbounce | grim | step | 0 % (0/3) | – |
| liquidbounce | grim | timer | 0 % (0/3) | – |
| liquidbounce | grim | velocity | 0 % (0/3) | – |
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

- `liquidbounce/grim`: finished=True, joins=132, unattributed flags=20, errors=0
- `liquidbounce/none`: finished=True, joins=132, unattributed flags=0, errors=0
- `meteor/grim`: finished=True, joins=108, unattributed flags=25, errors=0
- `meteor/none`: finished=True, joins=108, unattributed flags=0, errors=0
