# AntiCheat Benchmark – acbench-step1

Run `step2` · Minecraft 26.3 · 3 repetitions · clients: liquidbounce, meteor · anticheats: none, grim

## Summary

Per cheat type the strongest setting counts; every cheat type weighs the same. Detection = any flag; default alert = the anticheat's stock thresholds would have alerted within the ~5 s trial.

| Client | AntiCheat | Score | Detection | Default alert | False positives | Mitigation | Median time to flag | Valid variants |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| liquidbounce | grim | 62 | 56 % | 23 % | 46 % | 100 % | 0.0 s | 68 (+3 without effect) |
| meteor | grim | 92 | 94 % | 44 % | 3 % | 75 % | 0.3 s | 17 (+0 without effect) |

**liquidbounce vs grim** by category: combat: detection 53 %, FP 50 %, mitigation 100 %; movement: detection 58 %, FP 44 %, mitigation 100 %

**meteor vs grim** by category: combat: detection 83 %, FP 4 %, mitigation 25 %; movement: detection 100 %, FP 3 %, mitigation 100 %

## Cheats

Detection = share of cheat trials with at least one flag. Advantage = cheat minus baseline on the scenario metric (sign-normalized). Retained = advantage with the anticheat relative to the advantage without any anticheat.

### liquidbounce

| Scenario | Variant | AntiCheat | Detection | Time to flag | Advantage (raw) | Retained | Top checks | Notes |
|---|---|---|---:|---:|---:|---:|---|---|
| autoclicker | cooldown | none | 0 % (0/3) | – s | -10.39 (-10.39) | – | – | no measurable effect without anticheat |
| autoclicker | cps10 | none | 0 % (0/3) | – s | -2.31 (-2.31) | – | – | no measurable effect without anticheat |
| autoclicker | cps20 | none | 0 % (0/3) | – s | 8.29 (8.29) | 100 % | – |  |
| autoclicker | cps20 | grim | 67 % (2/3) | 0.0 s | -0.20 (8.29) | -2 % | Simulation ×30 |  |
| criticals | blink | none | 0 % (0/3) | – s | -3.67 (-3.67) | – | – | no measurable effect without anticheat |
| criticals | jump | none | 0 % (0/3) | – s | 1.00 (1.00) | 100 % | – |  |
| criticals | jump | grim | 67 % (2/3) | 0.0 s | 0.00 (1.00) | 0 % | Simulation ×28 |  |
| criticals | noground | none | 0 % (0/3) | – s | -3.67 (-3.67) | – | – | no measurable effect without anticheat |
| criticals | packet | none | 0 % (0/3) | – s | 5.33 (5.33) | 100 % | – |  |
| criticals | packet | grim | 67 % (2/3) | 0.0 s | 0.00 (5.33) | 0 % | Simulation ×29 |  |
| criticals | timer | none | 0 % (0/3) | – s | -3.67 (-3.67) | – | – | no measurable effect without anticheat |
| killaura | closet | none | 0 % (0/3) | – s | 8.00 (8.00) | 100 % | – |  |
| killaura | closet | grim | 33 % (1/3) | 0.0 s | 0.00 (8.00) | 0 % | Simulation ×15 |  |
| killaura | default | none | 0 % (0/3) | – s | 8.00 (8.00) | 100 % | – |  |
| killaura | default | grim | 0 % (0/3) | – s | 0.00 (8.00) | 0 % | – |  |
| reach | plus05 | none | 0 % (0/3) | – s | 11.00 (11.00) | 100 % | – |  |
| reach | plus05 | grim | 67 % (2/3) | 0.0 s | 0.00 (11.00) | 0 % | Simulation ×31 |  |
| reach | plus1 | none | 0 % (0/3) | – s | 10.67 (10.67) | 100 % | – |  |
| reach | plus1 | grim | 33 % (1/3) | 0.0 s | 0.00 (10.67) | 0 % | Simulation ×15 |  |
| velocity | aac4_4_2 | none | 0 % (0/3) | – s | 1.28 (1.28) | 100 % | – |  |
| velocity | aac4_4_2 | grim | 100 % (3/3) | 0.0 s | -0.00 (1.28) | -0 % | Simulation ×328, GroundSpoof ×33, AntiKB ×15 |  |
| velocity | blocksmc | none | 0 % (0/3) | – s | 1.99 (1.99) | 100 % | – |  |
| velocity | blocksmc | grim | 100 % (3/3) | 1.5 s | -0.00 (1.99) | -0 % | AntiKB ×15, Simulation ×15 |  |
| velocity | dexland | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| velocity | grim2344-117 | none | 0 % (0/3) | – s | 1.99 (1.99) | 100 % | – |  |
| velocity | grim2344-117 | grim | 100 % (3/3) | 0.0 s | -0.00 (1.99) | -0 % | Simulation ×113, AimDuplicateLook ×52, Timer ×21, AirLiquidBreak ×15 |  |
| velocity | grim2371 | none | 0 % (0/3) | – s | 1.99 (1.99) | 100 % | – |  |
| velocity | grim2371 | grim | 100 % (3/3) | 1.1 s | -0.00 (1.99) | -0 % | Simulation ×14, AntiKB ×13 |  |
| velocity | half | none | 0 % (0/3) | – s | 1.00 (1.00) | 100 % | – |  |
| velocity | half | grim | 100 % (3/3) | 0.0 s | -0.00 (1.00) | -0 % | Simulation ×456, GroundSpoof ×27, AntiKB ×15 |  |
| velocity | hylex | none | 0 % (0/3) | – s | -0.14 (-0.14) | – | – | no measurable effect without anticheat |
| velocity | hypixel | none | 0 % (0/3) | – s | 1.99 (1.99) | 100 % | – |  |
| velocity | hypixel | grim | 100 % (3/3) | 0.6 s | -0.00 (1.99) | -0 % | Simulation ×105, GroundSpoof ×27, AntiKB ×15 |  |
| velocity | intave | none | 0 % (0/3) | – s | -0.17 (-0.17) | – | – | no measurable effect without anticheat |
| velocity | jumpreset | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| velocity | lag | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| velocity | modify | none | 0 % (0/3) | – s | 1.99 (1.99) | 100 % | – |  |
| velocity | modify | grim | 100 % (3/3) | 1.4 s | -0.00 (1.99) | -0 % | AntiKB ×15, Simulation ×15 |  |
| velocity | reduce | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| velocity | reversal | none | 0 % (0/3) | – s | 1.92 (1.92) | 100 % | – |  |
| velocity | reversal | grim | 100 % (3/3) | 0.0 s | -0.00 (1.92) | -0 % | Simulation ×462, GroundSpoof ×27, AntiKB ×15 |  |
| velocity | strafe | none | 0 % (0/3) | – s | 1.59 (1.59) | 100 % | – |  |
| velocity | strafe | grim | 100 % (3/3) | 0.0 s | -0.00 (1.59) | -0 % | Simulation ×403, GroundSpoof ×27, AntiKB ×15 |  |
| fly | airwalk | none | 0 % (0/3) | – s | -1.25 (-1.25) | – | – | no measurable effect without anticheat |
| fly | creative | none | 0 % (0/3) | – s | 72.21 (72.21) | 100 % | – |  |
| fly | creative | grim | 67 % (2/3) | 0.0 s | 0.00 (72.21) | 0 % | Simulation ×289 |  |
| fly | grim2373jan15 | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | grim2373jan15 | grim | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | grim2859-v | none | 0 % (0/2) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | grim2859-v | grim | 67 % (2/3) | 0.0 s | 0.00 (0.00) | – | Simulation ×223, GroundSpoof ×13 | no measurable effect without anticheat |
| fly | hypixel | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | hypixelflat | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | jetpack | none | 0 % (0/3) | – s | 221.71 (221.71) | 100 % | – |  |
| fly | jetpack | grim | 67 % (2/3) | 0.1 s | 0.00 (221.71) | 0 % | Simulation ×279 |  |
| fly | ncpclip | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | sentinel10thmar | none | 0 % (0/3) | – s | 0.83 (0.83) | 100 % | – |  |
| fly | sentinel10thmar | grim | 67 % (2/3) | 0.0 s | 0.00 (0.83) | 0 % | Simulation ×238, GroundSpoof ×24 |  |
| fly | sentinel20thapr | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | sentinel26thdec | none | 0 % (0/3) | – s | 11.71 (11.71) | 100 % | – |  |
| fly | sentinel26thdec | grim | 100 % (3/3) | 0.0 s | 0.00 (11.71) | 0 % | Simulation ×123, GroundSpoof ×3 |  |
| fly | sentinel27thjan | none | 0 % (0/3) | – s | 20.26 (20.26) | 100 % | – |  |
| fly | sentinel27thjan | grim | 100 % (3/3) | 0.1 s | 0.00 (20.26) | 0 % | Simulation ×413, GroundSpoof ×2 |  |
| fly | spartan524 | none | 0 % (0/3) | – s | -1.25 (-1.25) | – | – | no measurable effect without anticheat |
| fly | vanilla | none | 0 % (0/3) | – s | 40.87 (40.87) | 100 % | – |  |
| fly | vanilla | grim | 67 % (2/3) | 0.1 s | 0.00 (40.87) | 0 % | Simulation ×278, GroundSpoof ×2 |  |
| fly | verusb3896flat | none | 0 % (0/3) | – s | -1.25 (-1.25) | – | – | no measurable effect without anticheat |
| fly | vulcan277 | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| fly | vulcan286-113 | none | 0 % (0/3) | – s | -1.25 (-1.25) | – | – | no measurable effect without anticheat |
| fly | vulcan286-18 | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| fly | vulcan286-18 | grim | 67 % (2/3) | 0.5 s | 0.00 (9.00) | 0 % | Simulation ×224, GroundSpoof ×46 |  |
| fly | vulcan286-teleport-18 | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| jesus | nocheatplus | none | 0 % (0/3) | – s | 2.00 (2.00) | 100 % | – |  |
| jesus | nocheatplus | grim | 100 % (3/3) | 0.0 s | 0.00 (2.00) | 0 % | Simulation ×172, GroundSpoof ×93 |  |
| jesus | vanilla | none | 0 % (0/3) | – s | 2.04 (2.04) | 100 % | – |  |
| jesus | vanilla | grim | 100 % (3/3) | 0.0 s | 0.00 (2.04) | 0 % | Simulation ×82 |  |
| jesus | verusb3901 | none | 0 % (0/3) | – s | 2.00 (2.00) | 100 % | – |  |
| jesus | verusb3901 | grim | 100 % (3/3) | 0.0 s | 0.00 (2.00) | 0 % | Simulation ×77 |  |
| jesus | vulcan291 | none | 0 % (0/3) | – s | 1.55 (1.55) | 100 % | – |  |
| jesus | vulcan291 | grim | 67 % (2/3) | 0.0 s | 0.00 (1.55) | 0 % | Simulation ×55 |  |
| nofall | blink | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | blink | grim | 0 % (0/3) | – s | -0.00 (9.00) | -0 % | – |  |
| nofall | blocksmc | none | 0 % (0/3) | – s | 2.00 (2.00) | 100 % | – |  |
| nofall | blocksmc | grim | 67 % (2/3) | 1.9 s | -0.00 (2.00) | -0 % | Simulation ×7, GroundSpoof ×5 |  |
| nofall | cancel | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| nofall | forcejump | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| nofall | grim2371-1_9 | none | 0 % (0/3) | – s | 2.00 (2.00) | 100 % | – |  |
| nofall | grim2371-1_9 | grim | 33 % (1/3) | 1.7 s | -0.00 (2.00) | -0 % | Simulation ×12, GroundSpoof ×3, NoFall ×1 |  |
| nofall | hypixel | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | hypixel | grim | 33 % (1/3) | 1.6 s | -0.00 (9.00) | -0 % | GroundSpoof ×2, Simulation ×2 |  |
| nofall | hypixelpacket | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | hypixelpacket | grim | 33 % (1/3) | 1.1 s | -0.00 (9.00) | -0 % | TickTimer ×8, NoFall ×4 |  |
| nofall | noground | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | noground | grim | 100 % (3/3) | 0.1 s | -0.00 (9.00) | -0 % | GroundSpoof ×66 |  |
| nofall | packet | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | packet | grim | 0 % (0/3) | – s | -0.00 (9.00) | -0 % | – |  |
| nofall | packetjump | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | packetjump | grim | 33 % (1/3) | 1.7 s | -0.00 (9.00) | -0 % | AimDuplicateLook ×1 |  |
| nofall | spartan524flag | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | spartan524flag | grim | 0 % (0/3) | – s | -0.00 (9.00) | -0 % | – |  |
| nofall | spoofground | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | spoofground | grim | 0 % (0/3) | – s | -0.00 (9.00) | -0 % | – |  |
| nofall | spooflanding | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | spooflanding | grim | 33 % (1/3) | 1.6 s | -0.00 (9.00) | -0 % | Simulation ×2, GroundSpoof ×1 |  |
| nofall | verus | none | 0 % (0/3) | – s | 7.00 (7.00) | 100 % | – |  |
| nofall | verus | grim | 0 % (0/3) | – s | -0.00 (7.00) | -0 % | – |  |
| nofall | vulcan277 | none | 0 % (0/3) | – s | 5.00 (5.00) | 100 % | – |  |
| nofall | vulcan277 | grim | 0 % (0/3) | – s | -0.00 (5.00) | -0 % | – |  |
| nofall | vulcantp288 | none | 0 % (0/3) | – s | 3.00 (3.00) | 100 % | – |  |
| nofall | vulcantp288 | grim | 0 % (0/3) | – s | -0.00 (3.00) | -0 % | – |  |
| noslow | grim2360 | none | 0 % (0/3) | – s | 3.37 (3.37) | 100 % | – |  |
| noslow | grim2360 | grim | 100 % (3/3) | 0.1 s | 0.00 (3.37) | 0 % | NoSlow ×50, Simulation ×22 |  |
| noslow | grim2364-1_8 | none | 0 % (0/3) | – s | 3.34 (3.34) | 100 % | – |  |
| noslow | grim2364-1_8 | grim | 100 % (3/3) | 0.1 s | 0.00 (3.34) | 0 % | NoSlow ×287, Simulation ×19 |  |
| noslow | grim2371 | none | 0 % (0/3) | – s | 1.69 (1.69) | 100 % | – |  |
| noslow | grim2371 | grim | 100 % (3/3) | 0.1 s | 0.00 (1.69) | 0 % | NoSlow ×3 |  |
| noslow | intave14 | none | 0 % (0/3) | – s | 3.35 (3.35) | 100 % | – |  |
| noslow | intave14 | grim | 100 % (3/3) | 0.0 s | 0.00 (3.35) | 0 % | BadPacketsL ×298, Simulation ×65 |  |
| noslow | invalidhand | none | 0 % (0/3) | – s | 3.31 (3.31) | 100 % | – |  |
| noslow | invalidhand | grim | 100 % (3/3) | 0.7 s | 0.00 (3.31) | 0 % | NoSlow ×242, Simulation ×27 |  |
| noslow | jump | none | 0 % (0/3) | – s | 2.90 (2.90) | 100 % | – |  |
| noslow | jump | grim | 100 % (3/3) | 0.0 s | 0.00 (2.90) | 0 % | NoSlow ×282, Simulation ×41 |  |
| noslow | none | none | 0 % (0/3) | – s | 3.31 (3.31) | 100 % | – |  |
| noslow | none | grim | 100 % (3/3) | 0.0 s | 0.00 (3.31) | 0 % | NoSlow ×281, Simulation ×38 |  |
| noslow | release | none | 0 % (0/3) | – s | 3.33 (3.33) | 100 % | – |  |
| noslow | release | grim | 100 % (3/3) | 0.0 s | 0.00 (3.33) | 0 % | BadPacketsL ×297, Simulation ×46 |  |
| speed | blocksmc | none | 0 % (0/3) | – s | -0.37 (-0.37) | – | – | no measurable effect without anticheat |
| speed | custom | none | 0 % (0/3) | – s | 0.02 (0.02) | – | – | no measurable effect without anticheat |
| speed | grimcollide | none | 0 % (0/3) | – s | -1.32 (-1.32) | – | – | no measurable effect without anticheat |
| speed | grimcollide | grim | 67 % (2/3) | 0.0 s | 0.00 (-1.32) | – | Simulation ×51 | no measurable effect without anticheat |
| speed | hylexground | none | 0 % (0/3) | – s | 0.52 (0.52) | 100 % | – |  |
| speed | hylexground | grim | 67 % (2/3) | 0.1 s | 0.00 (0.52) | 0 % | Simulation ×179 |  |
| speed | hylexlowhop | none | 0 % (0/3) | – s | 0.74 (0.74) | 100 % | – |  |
| speed | hylexlowhop | grim | 67 % (2/3) | 0.0 s | 0.00 (0.74) | 0 % | Simulation ×162 |  |
| speed | hypixelbhop | none | 0 % (0/3) | – s | 0.37 (0.37) | 100 % | – |  |
| speed | hypixelbhop | grim | 33 % (1/3) | 0.1 s | 0.00 (0.37) | 0 % | Simulation ×71 |  |
| speed | hypixellowhop | none | 0 % (0/3) | – s | 0.53 (0.53) | 100 % | – |  |
| speed | hypixellowhop | grim | 67 % (2/3) | 0.0 s | 0.00 (0.53) | 0 % | Simulation ×222, GroundSpoof ×26 |  |
| speed | intave14 | none | 0 % (0/3) | – s | 0.06 (0.06) | – | – | no measurable effect without anticheat |
| speed | intave14fast | none | 0 % (0/3) | – s | 0.49 (0.49) | 100 % | – |  |
| speed | intave14fast | grim | 67 % (2/3) | 0.1 s | 0.00 (0.49) | 0 % | Simulation ×224 |  |
| speed | legithop | none | 0 % (0/3) | – s | 0.04 (0.04) | – | – | no measurable effect without anticheat |
| speed | matrix7 | none | 0 % (0/3) | – s | 0.04 (0.04) | – | – | no measurable effect without anticheat |
| speed | ncp | none | 0 % (0/3) | – s | 1.16 (1.16) | 100 % | – |  |
| speed | ncp | grim | 100 % (3/3) | 0.0 s | 0.00 (1.16) | 0 % | Simulation ×316 |  |
| speed | spartan-4_0_4_3 | none | 0 % (0/3) | – s | 4.86 (4.86) | 100 % | – |  |
| speed | spartan-4_0_4_3 | grim | 67 % (2/3) | 1.3 s | 0.00 (4.86) | 0 % | Simulation ×140, GroundSpoof ×24 |  |
| speed | spartan-4_0_4_3-fastfall | none | 0 % (0/3) | – s | 6.41 (6.41) | 100 % | – |  |
| speed | spartan-4_0_4_3-fastfall | grim | 100 % (3/3) | 0.1 s | 0.00 (6.41) | 0 % | Simulation ×239, GroundSpoof ×113, AimDuplicateLook ×62, Timer ×31 |  |
| speed | verusb3882 | none | 0 % (0/3) | – s | 0.62 (0.62) | 100 % | – |  |
| speed | verusb3882 | grim | 100 % (3/3) | 0.0 s | 0.00 (0.62) | 0 % | Simulation ×305 |  |
| speed | vulcan286 | none | 0 % (0/3) | – s | 0.86 (0.86) | 100 % | – |  |
| speed | vulcan286 | grim | 100 % (3/3) | 0.1 s | 0.00 (0.86) | 0 % | Simulation ×342, GroundSpoof ×42 |  |
| speed | vulcan288 | none | 0 % (0/3) | – s | 0.98 (0.98) | 100 % | – |  |
| speed | vulcan288 | grim | 100 % (3/3) | 0.0 s | 0.00 (0.98) | 0 % | Simulation ×253, GroundSpoof ×246 |  |
| speed | vulcanground286 | none | 0 % (0/3) | – s | 1.80 (1.80) | 100 % | – |  |
| speed | vulcanground286 | grim | 67 % (2/3) | 0.0 s | 0.00 (1.80) | 0 % | Simulation ×168, GroundSpoof ×48 |  |
| speed | yport | none | 0 % (0/3) | – s | 1.56 (1.56) | 100 % | – |  |
| speed | yport | grim | 67 % (2/3) | 0.0 s | 0.00 (1.56) | 0 % | Simulation ×216, GroundSpoof ×194 |  |
| spider | polar-29_03_2025 | none | 0 % (0/3) | – s | -1.25 (-1.25) | – | – | no measurable effect without anticheat |
| spider | vanilla | none | 0 % (0/3) | – s | 26.79 (26.79) | 100 % | – |  |
| spider | vanilla | grim | 100 % (3/3) | 0.0 s | 0.00 (26.79) | 0 % | Simulation ×170, GroundSpoof ×2 |  |
| spider | vulcan288 | none | 0 % (0/3) | – s | 74.71 (74.71) | 100 % | – |  |
| spider | vulcan288 | grim | 67 % (2/3) | 0.2 s | 0.00 (74.71) | 0 % | Simulation ×137, GroundSpoof ×1 |  |
| step | blocksmc | none | 0 % (0/3) | – s | -0.25 (-0.25) | – | – | no measurable effect without anticheat |
| step | hypixel | none | 0 % (0/3) | – s | -0.23 (-0.23) | – | – | no measurable effect without anticheat |
| step | instant | none | 0 % (0/3) | – s | 1.75 (1.75) | 100 % | – |  |
| step | instant | grim | 100 % (3/3) | 0.0 s | 0.00 (1.75) | 0 % | Simulation ×132, AimDuplicateLook ×19, Timer ×18, GroundSpoof ×7 |  |
| step | legit | none | 0 % (0/3) | – s | 1.00 (1.00) | 100 % | – |  |
| step | legit | grim | 33 % (1/3) | 0.0 s | 0.00 (1.00) | 0 % | Simulation ×21 |  |
| step | vulcan286 | none | 0 % (0/3) | – s | -1.19 (-1.19) | – | – | no measurable effect without anticheat |
| timer | boost | none | 0 % (0/3) | – s | 0.19 (0.19) | – | – | no measurable effect without anticheat |
| timer | pulse | none | 0 % (0/3) | – s | -1.82 (-1.82) | – | – | no measurable effect without anticheat |
| timer | x1_2 | none | 0 % (0/3) | – s | 1.37 (1.37) | 100 % | – |  |
| timer | x1_2 | grim | 100 % (3/3) | 0.0 s | 0.00 (1.37) | 0 % | Simulation ×166, Timer ×34 |  |
| timer | x2 | none | 0 % (0/3) | – s | 6.69 (6.69) | 100 % | – |  |
| timer | x2 | grim | 100 % (3/3) | 0.6 s | 0.00 (6.69) | 0 % | Timer ×245, Simulation ×97, GroundSpoof ×7, TimerLimit ×1 |  |

### meteor

| Scenario | Variant | AntiCheat | Detection | Time to flag | Advantage (raw) | Retained | Top checks | Notes |
|---|---|---|---:|---:|---:|---:|---|---|
| autoclicker | cps10 | none | 0 % (0/3) | – s | -1.80 (-1.80) | – | – | no measurable effect without anticheat |
| autoclicker | cps20 | none | 0 % (0/3) | – s | 8.24 (8.24) | 100 % | – |  |
| autoclicker | cps20 | grim | 100 % (3/3) | 0.2 s | 8.68 (8.24) | 105 % | Post ×153, Timer ×2 |  |
| criticals | jump | none | 0 % (0/3) | – s | -3.33 (-3.33) | – | – | no measurable effect without anticheat |
| criticals | minijump | none | 0 % (0/3) | – s | -3.33 (-3.33) | – | – | no measurable effect without anticheat |
| criticals | oldncp | none | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received), flagged before kick: 0/3 |
| criticals | packet | none | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received), flagged before kick: 0/3 |
| criticals | updatedncp | none | – (0/0) | – s | – (–) | – | – | no measurable effect without anticheat, 3 kicked (Invalid move player packet received), flagged before kick: 0/3 |
| killaura | closet | none | 0 % (0/3) | – s | 8.67 (8.67) | 100 % | – |  |
| killaura | closet | grim | 0 % (0/3) | – s | 8.00 (8.67) | 92 % | – |  |
| killaura | default | none | 0 % (0/3) | – s | 7.67 (7.67) | 100 % | – |  |
| killaura | default | grim | 33 % (1/3) | 1.1 s | 8.33 (7.67) | 109 % | Reach ×6 |  |
| reach | plus05 | none | 0 % (0/3) | – s | 9.33 (9.33) | 100 % | – |  |
| reach | plus05 | grim | 100 % (3/3) | 0.3 s | 0.00 (9.33) | 0 % | Reach ×58 |  |
| reach | plus1 | none | 0 % (0/3) | – s | 10.33 (10.33) | 100 % | – |  |
| reach | plus1 | grim | 100 % (3/3) | 0.3 s | 0.00 (10.33) | 0 % | Reach ×58 |  |
| velocity | half | none | 0 % (0/3) | – s | 1.00 (1.00) | 100 % | – |  |
| velocity | half | grim | 100 % (3/3) | 0.6 s | 0.06 (1.00) | 6 % | Simulation ×50, AntiKB ×15 |  |
| velocity | zero | none | 0 % (0/3) | – s | 1.99 (1.99) | 100 % | – |  |
| velocity | zero | grim | 100 % (3/3) | 1.4 s | 1.99 (1.99) | 100 % | AntiKB ×15 |  |
| fly | abilities | none | 0 % (0/3) | – s | 72.48 (72.48) | 100 % | – |  |
| fly | abilities | grim | 67 % (2/3) | 0.1 s | -1.25 (72.48) | -2 % | Simulation ×2 |  |
| fly | velocity | none | 0 % (0/3) | – s | 48.67 (48.67) | 100 % | – |  |
| fly | velocity | grim | 100 % (3/3) | 0.1 s | -0.58 (48.67) | -1 % | Simulation ×175, GroundSpoof ×2 |  |
| jesus | ignore | none | 0 % (0/3) | – s | 0.00 (0.00) | – | – | no measurable effect without anticheat |
| jesus | solid | none | 0 % (0/3) | – s | 1.99 (1.99) | 100 % | – |  |
| jesus | solid | grim | 100 % (3/3) | 0.4 s | -0.76 (1.99) | -38 % | Simulation ×61, GroundSpoof ×8, Timer ×4, TimerLimit ×3 |  |
| nofall | airplace | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| nofall | packet | none | 0 % (0/3) | – s | 9.00 (9.00) | 100 % | – |  |
| nofall | packet | grim | 100 % (3/3) | 1.1 s | -0.00 (9.00) | -0 % | GroundSpoof ×35, Simulation ×3 |  |
| nofall | place | none | 0 % (0/3) | – s | -0.00 (-0.00) | – | – | no measurable effect without anticheat |
| noslow | items | none | 0 % (0/3) | – s | 3.32 (3.32) | 100 % | – |  |
| noslow | items | grim | 100 % (3/3) | 0.1 s | -0.58 (3.32) | -18 % | NoSlow ×265 |  |
| speed | strafe | none | 0 % (0/3) | – s | 0.09 (0.09) | – | – | no measurable effect without anticheat |
| speed | vanilla | none | 0 % (0/3) | – s | -1.33 (-1.33) | – | – | no measurable effect without anticheat |
| speed | vanilla8 | none | 0 % (0/3) | – s | 1.02 (1.02) | 100 % | – |  |
| speed | vanilla8 | grim | 100 % (3/3) | 0.0 s | -6.75 (1.02) | -661 % | Simulation ×215 |  |
| speed | vanilla_closet | none | 0 % (0/3) | – s | -0.75 (-0.75) | – | – | no measurable effect without anticheat |
| spider | default | none | 0 % (0/3) | – s | 17.43 (17.43) | 100 % | – |  |
| spider | default | grim | 100 % (3/3) | 0.4 s | -1.25 (17.43) | -7 % | Simulation ×141, GroundSpoof ×2 |  |
| step | default | none | 0 % (0/3) | – s | 1.75 (1.75) | 100 % | – |  |
| step | default | grim | 100 % (3/3) | 0.6 s | -8.25 (1.75) | -472 % | Simulation ×143 |  |
| timer | x1_2 | none | 0 % (0/3) | – s | 1.32 (1.32) | 100 % | – |  |
| timer | x1_2 | grim | 100 % (3/3) | 0.4 s | -2.70 (1.32) | -205 % | Timer ×100, Simulation ×48, GroundSpoof ×7, TimerLimit ×3 |  |
| timer | x2 | none | 0 % (0/3) | – s | 6.84 (6.84) | 100 % | – |  |
| timer | x2 | grim | 100 % (3/3) | 0.1 s | -3.22 (6.84) | -47 % | Timer ×308, Simulation ×29, TimerLimit ×12 |  |

## False positives (baseline trials, cheat off)

| Client | AntiCheat | Scenario | Flagged | Top checks |
|---|---|---|---:|---|
| liquidbounce | grim | autoclicker | 17 % (1/6) | Simulation ×16 |
| liquidbounce | grim | criticals | 50 % (3/6) | Simulation ×47 |
| liquidbounce | grim | fly | 100 % (3/3) | Simulation ×66 |
| liquidbounce | grim | jesus | 50 % (3/6) | Simulation ×76 |
| liquidbounce | grim | killaura | 67 % (2/3) | Simulation ×29 |
| liquidbounce | grim | nofall | 0 % (0/3) | – |
| liquidbounce | grim | noslow | 50 % (3/6) | NoSlow ×74, Simulation ×58 |
| liquidbounce | grim | reach | 0 % (0/3) | – |
| liquidbounce | grim | speed | 33 % (2/6) | Simulation ×50 |
| liquidbounce | grim | spider | 67 % (4/6) | Simulation ×81 |
| liquidbounce | grim | step | 33 % (2/6) | Simulation ×44 |
| liquidbounce | grim | timer | 0 % (0/3) | – |
| liquidbounce | grim | velocity | 100 % (6/6) | Simulation ×869, AntiKB ×28, GroundSpoof ×24 |
| meteor | grim | autoclicker | 17 % (1/6) | Timer ×4, TimerLimit ×3 |
| meteor | grim | criticals | 0 % (0/6) | – |
| meteor | grim | fly | 0 % (0/3) | – |
| meteor | grim | jesus | 17 % (1/6) | Timer ×2, Simulation ×2 |
| meteor | grim | killaura | 0 % (0/3) | – |
| meteor | grim | nofall | 0 % (0/3) | – |
| meteor | grim | noslow | 0 % (0/6) | – |
| meteor | grim | reach | 0 % (0/3) | – |
| meteor | grim | speed | 0 % (0/6) | – |
| meteor | grim | spider | 0 % (0/6) | – |
| meteor | grim | step | 0 % (0/6) | – |
| meteor | grim | timer | 0 % (0/3) | – |
| meteor | grim | velocity | 0 % (0/6) | – |

## Run health

- `liquidbounce/grim`: finished=True, shards=1, joins=277, unattributed flags=3459, errors=0, client – ticks/s, server 20.0 ticks/s **INVALID: legal play impaired in 33/48 baseline trials (bot held back or frozen), results of this pair do not measure the cheats**
- `liquidbounce/none`: finished=True, shards=1, joins=381, unattributed flags=0, errors=0, client – ticks/s, server 20.0 ticks/s
- `meteor/grim`: finished=True, shards=1, joins=115, unattributed flags=27, errors=0, client – ticks/s, server 20.0 ticks/s
- `meteor/none`: finished=True, shards=1, joins=152, unattributed flags=0, errors=0, client – ticks/s, server 20.0 ticks/s
