# acbench – AntiCheat-Benchmark für Minecraft

Der Benchmark testet AntiCheat-Plugins mit **echten Hack-Clients**. Abgedeckt sind die Bereiche **Movement** und
**Combat** mit den Clients **Meteor**, **LiquidBounce Nextgen** (inklusive seiner gezielten Grim-Bypass-Modi) und **Wurst**
gegen die AntiCheats **Grim**, **Intave** (freie Basisversion, ohne Cloud-Checks) und **Spartan** (freie Edition,
erkennt bis 5 Spieler online; ein Shard hat 2), **Updated-NoCheatPlus** und **MLSAC** (KI-Combat-AntiCheat mit
Cloud-Bewertung, braucht einen Lizenzschlüssel, siehe unten).
Weitere Clients, AntiCheats und Szenarien kommen per Konfigurationsdatei dazu.

## Architektur

```
            benchmark.toml + config/
                      │
             ./bench run (Python, orchestrator/)
           ┌──────────┴───────────┐
           ▼                      ▼
  Paper-Server 26.3        Minecraft-Client 26.3 (headless, xvfb)
  ├─ AntiCheat (z. B. Grim)  ├─ Hack-Client (z. B. Meteor)
  └─ collector-plugin        └─ driver-mod
     • baut Arenen              • führt Szenario-Inputs aus (Laufen, Zielen, Klicken …)
     • misst pro Trial          • schaltet Cheat-Module über einen Client-Adapter
     • schneidet Flags mit      • meldet Trial-Grenzen per /acbench an den Server
           │                      │
           └──── results/<run>/ ──┘ → analyze → report.md / report.html / trials.csv
```

- **driver-mod/** (Fabric, Client): Die Mod steuert den echten Client tickgenau. Cheat-Module werden über einen
  `CheatClientAdapter` geschaltet. `MeteorAdapter` nutzt dafür Meteors öffentliche Modul-API per Reflection, sodass
  kein Compile-Dependency nötig ist. Die Mod protokolliert die Ground Truth: welches Modul mit welchen Settings aktiv
  war, ob das Setzen der Settings geklappt hat und wie viele Attack-Pakete gesendet wurden.
- **collector-plugin/** (Paper, Server): Das Plugin baut die Arenen deterministisch auf, setzt Spieler und Ziele pro
  Trial zurück und misst, was der Spieler tatsächlich erreicht hat (Strecke, Höhe, Fallschaden, Treffer, Crits,
  Knockback usw.). Außerdem wandelt es AntiCheat-Alerts in `flag`-Events mit Server-Tick um. Dafür gibt es zwei
  Wege: einen Regex auf die Konsole (funktioniert mit fast jedem AntiCheat) oder ein Bukkit-Event der
  AntiCheat-API per Reflection.
- **orchestrator/** (Python, nur Standardbibliothek): Der Orchestrator erzeugt den Plan, lädt Paper, Clients und
  AntiCheats herunter, startet Server und Client pro AntiCheat neu, startet den Client nach Crashes oder Kicks neu
  (der Fortschritt bleibt erhalten) und wertet am Ende aus.

### Ablauf eines Trials

Neu verbinden (frischer AntiCheat-Zustand) → `setup` (Arena, Zustand, Loadout, Ziele) → Settings zurücksetzen und Variante anwenden, bei `cheat` Modul an →
`begin` → Inputs → `end` (mit Client-Statistik) → Modul aus → Cooldown.

Jedes Szenario läuft pro Wiederholung einmal pro **legaler Spielweise** (Baseline, Cheat aus) und einmal pro
**Variante** (Cheat an). Die Reihenfolge wird pro Wiederholung mit festem Seed gemischt.

**Beste legale Spielweise als Vergleich.** Ein Szenario kann mehrere legale Strategien nennen (`baselines`), z. B.
Sprinten und Sprint-Springen oder Schlagen vom Boden und Sprung-Crits. Die Auswertung wählt im Referenzlauf ohne
AntiCheat die beste davon und vergleicht jeden Cheat damit. So zählt legales Verhalten (Springen, Jump-Reset)
nie als Cheat-Vorteil.

**Kampf gegen einen Spieler.** Kampf-Szenarien nutzen einen zweiten Bot (`target_username`) als Ziel. Er läuft als
eigener, schlanker Client (nur Driver-Mod in der Rolle `dummy`). Das Server-Plugin stellt ihn ans Ziel, hält ihn
dort fest und parkt ihn zwischen den Tests auf einer Wartefläche.

## Kennzahlen

| Kennzahl | Bedeutung |
|---|---|
| Detection | Anteil der Cheat-Trials mit mindestens einem Flag im Fenster `[begin, end + grace_ticks]` |
| Default alert | Anteil der Cheat-Trials, in denen das AntiCheat mit seinen **Standard-Alarmschwellen** schon innerhalb des Trials (~5 s) alarmiert hätte. Berechnet aus allen mitgeschnittenen Verstößen und den Schwellen in `default_alerts` der AntiCheat-Konfiguration |
| Time to flag | Median der Zeit bis zum ersten Flag |
| False positives | Anteil der Baseline-Trials (Cheat aus) mit Flag |
| Advantage | Cheat minus Baseline auf der Szenario-Metrik, mit normalisiertem Vorzeichen |
| Retained | Advantage mit AntiCheat geteilt durch Advantage ohne AntiCheat (Referenzlauf `none`). Gibt an, wie viel vom Cheat trotz Setbacks oder Cancels übrig bleibt |
| Mitigation | 1 − Retained (auf 0..1 begrenzt), gemittelt |
| Score | Gewichtetes Mittel aus Detection, 1 − FP-Rate und Mitigation (`[scoring]` in `benchmark.toml`). **Jede Cheat-Art zählt gleich viel** und wird nach ihrer stärksten Variante bewertet (der Einstellung, mit der ein Cheater am besten durchkommt). So hängt der Score nicht davon ab, wie viele Varianten ein Client hat |

Varianten, die schon **ohne** AntiCheat keinen messbaren Vorteil bringen, werden als „no measurable effect“
markiert und nicht gewertet. Das deckt kaputte Mappings auf, z. B. falsche Setting-Namen nach einem Client-Update.

Ausnahme sind **gezielte Bypässe**: Manche Modi funktionieren nur gegen ein bestimmtes AntiCheat, z. B. LiquidBounces
Fly `Grim2859-V`, der Grims eigene Setbacks ausnutzt. Ohne AntiCheat bringen sie nichts. Bringt eine solche Variante
**mit** dem AntiCheat einen Vorteil, zählt sie als „targeted bypass“. Ihr verbleibender Vorteil wird dann am stärksten
normalen Modus desselben Szenarios gemessen.

Verfügbare Metriken pro Trial: `forward_distance`, `forward_speed`, `max_forward`, `path_horizontal`,
`max_height_gain`, `min_height`, `max_tick_speed`, `air_ticks`, `damage_taken`, `fall_damage`, `hits`,
`hits_per_second`, `cancelled_hits`, `crits`, `avg_hit_distance`, `max_hit_distance`, `swings`,
`swings_per_second`, `teleports`, `velocity_events`, `items_consumed`, `knockback_taken`, `hit_ratio`, `avg_mspt`.

## Voraussetzungen

- Java 25 (Minecraft 26.x), Gradle 9.x
- Python ≥ 3.11
- [`portablemc`](https://pypi.org/project/portablemc/) (`pip install portablemc`) als Launcher
- `xvfb-run` und Mesa für den headless Client (alternativ `headless = false` mit echtem Display).
  Minecraft 26.x findet unter Xvfb oft keinen passenden GLX-Visual und weicht dann auf Vulkan aus. Dafür braucht es
  den Software-Treiber lavapipe: `apt install mesa-vulkan-drivers`.

## Benutzung

```sh
export JAVA_HOME=/pfad/zu/jdk-25               # für den Build (Gradle-Wrapper)
export ACBENCH_JAVA=$JAVA_HOME/bin/java        # Java für den Server
./bench build                                  # baut driver-mod und collector-plugin
./bench fetch                                  # lädt Paper, Clients und AntiCheats nach cache/
./bench plan                                   # zeigt die Trials
./bench run                                    # kompletter Lauf laut benchmark.toml
./bench run --anticheats none,grim --scenarios fly,reach --reps 1   # schneller Teillauf
./bench analyze results/<run-id>               # Auswertung neu rechnen
```

### Parallel laufen lassen

```sh
./bench run --workers 4          # oder [parallel] workers in benchmark.toml ("auto" = 1 pro ~3 Kerne und ~7 GB RAM)
./bench plan --workers 4         # zeigt die ungefähre Laufzeit
```

Jeder Trial ist unabhängig (der Bot verbindet sich vorher neu), deshalb lässt sich ein Client×AntiCheat-Lauf in
**Shards** zerlegen: Teilmengen der Trials, die jeweils ein eigener **Worker** abarbeitet, also eigener Paper-Server,
eigener Bot und eigener Ziel-Bot auf Port `port + Worker-Nummer`, mit eigenen Ordnern unter `work/`.

- Die Trials werden reihum auf die Shards verteilt, damit jeder Shard alle Szenarien mischt. Unter
  `min_trials_per_shard` (Standard 30) wird nicht weiter geteilt.
- Der Scheduler startet zuerst die Referenz-Shards aller Clients. Sobald die Referenz eines Clients komplett ist,
  laufen seine AntiCheat-Shards an, auch wenn ein anderer Client noch seine Referenz misst.
- Vor dem Start werden alle Downloads, der Client-Build und die Spielinstallation einmal erledigt. Server und Clients
  starten nacheinander mit kurzem Abstand, damit sich Paperclip, Xvfb und Start-Spitzen nicht in die Quere kommen.
- Ein abgebrochener Lauf lässt sich mit derselben `--run-id` fortsetzen: Die Shard-Aufteilung bleibt erhalten, jeder
  Shard überspringt seine erledigten Trials.
- Ergebnisse liegen pro Shard unter `results/<run>/<client>/<anticheat>/shards/s<k>/`; Auswertung und Dashboard
  führen sie zusammen.

**Messgüte.** Parallelität darf die Messung nicht verfälschen: Ein überlasteter Rechner verzögert Ticks, und AntiCheats
werten Verzögerungen schnell als Cheat. Deshalb misst jeder Trial, wie viele Ticks pro Sekunde Client und Server
geschafft haben (Soll: 20). Liegt der Median der legalen Trials eines Laufs unter 18,5 Ticks/s oder der Server über
40 ms pro Tick, markieren Report und Dashboard ihn als **überlastet**. Dann mit weniger Workern wiederholen.

### Auf GitHub Actions laufen lassen

Der Workflow [`benchmark.yml`](.github/workflows/benchmark.yml) verteilt einen Run auf viele Runner. Gestartet wird
er unter Actions → Benchmark → „Run workflow“ oder per CLI:

```sh
gh workflow run benchmark.yml                                   # kompletter Lauf laut benchmark.toml
gh workflow run benchmark.yml -f scenarios=fly,reach -f reps=1  # schneller Teillauf
```

Jeder Runner führt genau **einen Shard** aus: einen Teil der Trials eines Client×AntiCheat-Paars, mit eigenem Server,
Bot und Ziel-Bot. Der Ablauf hat fünf Jobs:

1. **prepare**: baut Driver-Mod und Collector, lädt alle Jars, erzeugt fehlende Modul-Dumps (`discover`), installiert
   das Spiel und plant die Referenz-Shards.
2. **reference**: die Shards aller `none`-Paare, alle gleichzeitig.
3. **screen**: liest die Referenz und plant die AntiCheat-Paare nur mit den Varianten, die dort einen Effekt hatten
   (wie lokal, siehe `screen_variants`).
4. **anticheats**: die Shards aller AntiCheat-Paare.
5. **collect**: führt alles zu einem Run zusammen und schreibt den Report in die Job-Zusammenfassung. Der komplette
   Ordner `results/<run>/` liegt als Artefakt `results-gh-<nr>` bereit.

Pro Stufe teilt `./bench ci matrix` die Paare so in Shards auf, dass `ci_slots` Runner (Standard 20, das Limit
gleichzeitiger Jobs im Free-Plan) etwa gleich lange beschäftigt sind. Ein Shard bekommt mindestens
`ci_min_trials_per_shard` Trials (Standard 10), weil jeder Runner ~5 min Start-Up zahlt. Bei mehr Paaren als Runnern
ist jedes Paar ein Job, und GitHub startet die wartenden, sobald ein Runner frei wird. Alle Shards eines Runs messen
dieselben Jars: Sie stehen mit Pfad in `run.json` (`jar_paths`) und werden nicht erneut aufgelöst.

Downloads, der LiquidBounce-Build und die Modul-Dumps liegen im Actions-Cache. Ändert sich die Konfiguration, startet
der Lauf vom letzten Stand: Vorhandene Jars bleiben, nur neue werden geladen. `refresh` lädt alles neu.

**Unveränderte Paare werden nicht neu gemessen.** Jedes Client×AntiCheat-Paar bekommt einen Schlüssel über alles, was
seine Messung bestimmt: den Trial-Plan (Szenarien, Varianten, Wiederholungen, Seed, Timing), die Prüfsummen der Jars
von Paper, Client und AntiCheat, die Flag-Quellen und Config-Dateien des AntiCheats, die Server- und Client-Settings
sowie die Messversion `[measurement] version` aus `benchmark.toml`. Die wird von Hand erhöht, sobald sich ändert,
was ein Trial misst (Driver-Mod, Collector, Server-/Client-Setup); neue Clients oder AntiCheats, Runner-Robustheit und
Auswertung lassen den Cache unberührt. Sauber gemessene Paare (fertig, nicht überlastet,
legales Spiel unbeeinträchtigt) legt `collect` im Pair-Store ab, einem eigenen Eintrag im Actions-Cache. Der nächste
Lauf übernimmt Paare mit gleichem Schlüssel von dort, statt Shards für sie zu planen:

- Neue AntiCheat-Version: nur die Paare dieses AntiCheats laufen, die Referenz kommt aus dem Store, das Screening
  bleibt erhalten.
- Neue Client-Version: die Referenz und alle Paare dieses Clients laufen neu.
- Nur Auswertung geändert (`[scoring]`, `default_alerts`): nichts wird gemessen, alles wird neu ausgewertet.

Der Report nennt übernommene Paare unter „Run health“ („reused from gh-…“). `remeasure` misst alles neu. Der Store
behält pro Paar die zwei neuesten Schlüssel; der Actions-Cache löscht ihn nach 7 Tagen ohne Lauf.

**Lizenzschlüssel (MLSAC).** MLSAC braucht einen Schlüssel von mlsac.net (es gibt einen kostenlosen Tarif). Lege ihn
als Repository-Secret `MLSAC_API_KEY` an (`gh secret set MLSAC_API_KEY`). Strafen stellt MLSAC pro Account auf
mlsac.net ein. Für den Benchmark darf das Preset weder kicken noch bannen, die Suppression-Leiter ist leer (ihre Effekte
reichen sonst minutenlang in spätere Trials hinein), und in den Alert-Einstellungen ist „Also send to console“ an:
MLSAC 2.0.9 meldet Erkennungen nicht über seine API-Events, der Benchmark liest seine Konsolen-Alerts. Ohne Secret
läuft der Benchmark ohne MLSAC.

### Live-Dashboard

```sh
./bench serve                    # http://127.0.0.1:8765
./bench serve --host 0.0.0.0     # auch von anderen Rechnern im Netz erreichbar
```

Die Seite liest direkt aus `results/` und braucht keine weiteren Abhängigkeiten. Sie zeigt:

- **laufende Runs:** Fortschritt und geschätzte Restzeit pro Client×AntiCheat, aktuellen Trial, Live-Feed der Flags und
  der zuletzt beendeten Trials sowie Zwischenergebnisse, die bei jedem neuen Event neu berechnet werden
- **alle vergangenen Runs:** Score, Erkennung, Fehlalarme, Mitigation, die komplette Cheat-Matrix pro Client und einen
  Link auf den statischen Report

Den Live-Zustand schreibt der Runner nach `results/<run>/live.json`. Ist ein Run-Prozess verschwunden, ohne fertig zu
werden, zeigt die Seite ihn als „abgebrochen“.

Ergebnisse landen in `results/<run-id>/`:

- `report.html` und `report.md`
- `results.json` und `trials.csv`
- pro Client und AntiCheat: `plan.json`, `server-events.jsonl`, `client-events.jsonl`, `modules.json`
  (alle Module und Settings des Clients), `server.log` und `client.log`

## Erweitern

### Varianten systematisch erzeugen

Statt jede Variante von Hand einzutragen, kann ein Cheat `auto_modes = "<setting>"` nennen. Jede Option dieses
Settings (aus dem Modul-Dump des Clients) wird dann eine eigene Variante. `exclude_modes` lässt Modi aus, die
Gegenstände oder Schaden brauchen, die das Szenario nicht bietet. Den Dump legt jeder Lauf in
`cache/clients/<id>/modules.json` ab; für einen neuen Client erzeugt `./bench discover --clients <id>` ihn einmalig.

Damit das bezahlbar bleibt, laufen gegen ein AntiCheat nur Varianten, die im Referenzlauf einen Vorteil gezeigt
haben, plus Varianten, deren Name das AntiCheat nennt (gezielte Bypässe). Abschalten mit `screen_variants = false`.

### Neuer Client

1. Lege `config/clients/<id>.toml` an. Darin stehen `adapter` und die Zuordnung `cheats.<cheat-id>` → `module` +
   `variants`. Die Cheat-IDs der Szenarien sind client-neutral: `fly`, `speed`, `step`, `nofall`, `timer`, `noslow`,
   `jesus`, `spider`, `killaura`, `reach`, `velocity`, `criticals`, `autoclicker`. Weitere Optionen:
   - `[download]`: eine `url`, ein lokaler `path` oder ein Build aus Git (`git`, `commit`, `build`, `artifact`).
     Den Git-Build nutzt LiquidBounce, weil es dafür keinen direkten Download-Link gibt; das Ergebnis wird pro
     Commit in `cache/` abgelegt.
   - `[[dependencies]]`: weitere Fabric-Mods von Modrinth (`modrinth`, `version`), z. B. Fabric API.
   - `jvm_args`: zusätzliche JVM-Argumente für den Client.
   - `always_disable`: Module, die vor jedem Trial ausgeschaltet werden, z. B. LiquidBounces `AutoConfig`, das sonst
     Einstellungen aus der Cloud nachlädt.
2. Wähle einen Adapter:
   - Ist der Client per Chat-Befehl steuerbar, reicht `adapter = "command"` mit Templates, zum Beispiel:
     ```toml
     adapter = "command"
     adapter_options = { enable = ".t {module} on", disable = ".t {module} off", set = ".set {module} {setting} {value}" }
     ```
   - Sonst schreibst du eine eigene Klasse in `driver-mod/src/main/java/dev/acbench/driver/adapter/`, die
     `CheatClientAdapter` implementiert (Reflection, damit die Mod ohne den Client baut), und registrierst sie in
     `Adapters.java`. Vorhanden sind `MeteorAdapter`, `LiquidBounceAdapter` und `WurstAdapter`. Benenne die Klasse
     `<Adapter-ID>Adapter.java`.
3. Füge den Client in `benchmark.toml` unter `clients` hinzu. Clients, die keine Fabric-Mods auf derselben
   Minecraft-Version sind, brauchen einen anderen Weg und werden von der Driver-Mod nicht abgedeckt.

### Neuer AntiCheat

Lege `config/anticheats/<id>.toml` an. Darin stehen:

- `plugin`: der Bukkit-Pluginname. Ist das Plugin nach dem Serverstart nicht aktiviert (z. B. weil ein kaputter Build
  geladen wurde), bricht der Orchestrator den Lauf für diesen AntiCheat ab, statt eine Messung mit 0 % Detection
  zu erzeugen.
- Download über `modrinth` (optional mit `version = "…"` zum Pinnen), `url` oder lokale `jars = ["pfad.jar"]`
  (für kostenpflichtige Plugins)
- optional `[[dependencies]]`: weitere Plugins, die der AntiCheat braucht, über `modrinth` oder `url` + `filename`
  (Intave braucht z. B. ProtocolLib)
- mindestens eine `flag_sources`-Quelle, entweder
  - ein Konsolen-Regex mit den benannten Gruppen `player`, `check` und optional `vl`, oder
  - `type = "event"` mit `plugin`, `class` und Getter-Ketten wie `player = "getPlayer.getName"`, oder
  - `type = "callback"` für AntiCheats ohne Violation-Event, aber mit Listener-API (z. B. NoCheatPlus' `NCPHook`):
    `interface`, die statische Registrier-Methode `register` mit `register_args` (`"listener"`, `"enum:Klasse.KONSTANTE"`),
    die Callback-Methode `callback` und für `player`/`check`/`vl` Argument-Index plus Getter-Kette wie `"1.getName"`
- optional `[files]` mit Konfigurationen, die vor dem Serverstart kopiert werden
- `target_bypass_permissions = ["…"]`: die Bypass-Permission(s) des AntiCheats. Der Collector gibt sie beim Join
  ausschließlich dem Ziel-Bot (`target_username`), nie dem Test-Bot. Der Ziel-Bot ist reine Infrastruktur: Ohne
  Ausnahme bewerten AntiCheats die Teleports, mit denen der Collector ihn festhält, und können ihn zurücksetzen oder
  seine Treffer im Velocity-Szenario verwerfen. Die Permission wird bei Join-Priorität `LOWEST` gesetzt, also bevor
  ein AntiCheat sie beim Join liest (Intave liest sie nur dort). Bisher: Grim `grim.exempt`, Intave `intave.bypass`,
  Spartan `spartan.bypass`. Ob sie greift, zeigt „Target bot flags“ im Report (sollte 0 sein).
- optional `categories = ["combat"]`: nur Szenarien dieser Kategorien laufen gegen den AntiCheat (für reine
  Combat- oder Movement-AntiCheats)
- optional `secret_env = ["NAME"]`: Umgebungsvariablen, die `${NAME}` in den `[files]` beim Kopieren ersetzen, z. B. ein
  Lizenzschlüssel aus einem GitHub-Secret. Fehlt eine, wird der AntiCheat übersprungen. Der Schlüssel landet nur im
  Serverordner, nie in den Ergebnissen.
- optional `reuse = false`: für AntiCheats mit Cloud-Bewertung, deren Ergebnisse sich ohne neue Jar ändern können. Ihre
  Paare werden in jedem Lauf gemessen statt aus dem Pair-Store übernommen.
- `type = "command"`: der AntiCheat führt bei jedem Flag den Konsolenbefehl `acbench flag <spieler> [check] [vl]` aus,
  z. B. als Aktion seiner Strafleiter (MLSAC). Spieler können diesen Befehl nicht nutzen.
- optional `[timing]` (z. B. `cooldown_ticks`) und `grace_ticks`: eigene Wartezeit nach jedem Trial und eigenes Fenster,
  in dem Flags noch zum Trial zählen, für AntiCheats, deren Urteile erst nach dem Trial ankommen
- bei `type = "event"` optional `only_if = "isFlagged"`: Getter, der `true` liefern muss, für Events, die auch
  Ergebnisse ohne Erkennung melden
- bei `url`-Downloads optional `sha256`: Prüfsumme der Jar
- optional `known_issues = ["…"]`: nachgewiesene Probleme des AntiCheats selbst (nicht des Benchmarks) auf der
  getesteten Version. Der Report führt sie neben den Zahlen auf; sie ändern nichts an der Messung.
- optional `[[default_alerts]]` (`group`, `checks`, `alert_after`) und `[default_alert_aliases]`: die
  Alarmschwellen der Standard-Konfiguration. Daraus berechnet die Auswertung „Default alert“. Ein Check gehört zu einer
  Gruppe, wenn sein Name einen Gruppeneintrag enthält (wie bei Grim). Standardmäßig zählt jeder Verstoß als 1; mit
  `by = "vl"` gilt stattdessen das gemeldete Violation-Level, für AntiCheats, die Verstöße gewichten (wie Intave)

Wichtig: Für die Detection-Messung sollte der AntiCheat bei **jedem** Verstoß alarmieren und nicht kicken oder
bannen. Beispiele dafür sind `config/anticheats/grim/punishments.yml`, `config/anticheats/intave/config.yml`,
`config/anticheats/spartan/checks.yml` und `config/anticheats/ncp/config.yml`.

### Neues Szenario

Füge in `config/scenarios/<kategorie>.toml` einen `[[scenario]]`-Eintrag hinzu: Arena, Cheat-ID, Metrik,
Vorteilsrichtung und Inputs.

- **Arenen:** `track`, `open`, `stairs`, `fall`, `pool`, `wall`, `combat`. Neue Arenen kommen in
  `collector-plugin/.../Arenas.java` dazu.
- **Neue Kategorie:** neue Datei anlegen und in `benchmark.toml` unter `categories` eintragen.

## Bekannte Grenzen

- **Ein einzelner Bot statt Spielerverhalten.** Die Inputs sind gescriptet. Zielen und Klicken haben zwar Rauschen
  und begrenzte Drehrate, Flags in Baseline-Trials können aber auch das Bot-Verhalten treffen. Die
  Baseline-FP-Rate ist deshalb eine Obergrenze und ersetzt keine FP-Tests mit echten Spielern.
- **Übertrag zwischen Trials (gelöst durch Reconnect).** AntiCheats führen ihren Zustand pro Verbindung. Ohne
  Neuverbinden hat Grim in Wiederholung 1 fast alles geflaggt, in späteren Wiederholungen viele Cheats nur noch per
  Setback blockiert, ohne zu alarmieren. Deshalb verbindet sich der Bot standardmäßig vor jedem Trial neu
  (`reconnect_between_trials`, kostet ~5 s pro Trial). Abschalten ist nur sinnvoll, wenn du das Verhalten über eine
  lange Sitzung messen willst.
- **Das Spieler-Ziel ist ein Bot, der stillsteht.** Gegen einen sich bewegenden, zurückschlagenden Gegner können
  KillAura- und Reach-Checks anders reagieren.
- **Netzwerkbedingungen** (Ping, Jitter, Paketverlust) sind in Schritt 1 noch nicht emuliert.
- **Nur Meteor-Default-Settings und wenige Varianten.** Gezielt getunte Bypass-Konfigurationen (Red-Team) lassen sich
  als zusätzliche Varianten eintragen.
