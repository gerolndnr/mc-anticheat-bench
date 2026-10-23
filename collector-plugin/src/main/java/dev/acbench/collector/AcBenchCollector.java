package dev.acbench.collector;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.bukkit.Bukkit;
import org.bukkit.Difficulty;
import org.bukkit.GameMode;
import org.bukkit.GameRules;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.potion.PotionEffect;
import org.bukkit.util.Vector;

public final class AcBenchCollector extends JavaPlugin {
	private EventLog log;
	private PlanIndex plan;
	private Arenas arenas;
	private TrialRecorder recorder;
	private FlagCapture flags;

	@Override
	public void onEnable() {
		saveDefaultConfig();
		try {
			log = new EventLog(Path.of(getConfig().getString("output_file", "plugins/AcBenchCollector/events.jsonl")));
			plan = new PlanIndex(Path.of(getConfig().getString("plan_file", "plugins/AcBenchCollector/plan.json")));
		} catch (IOException e) {
			getLogger().severe("Cannot open plan or output file: " + e);
			Bukkit.getPluginManager().disablePlugin(this);
			return;
		}

		World world = Bukkit.getWorlds().getFirst();
		prepareWorld(world);
		arenas = new Arenas(world, getConfig().getString("target_player", null));
		arenas.build();
		recorder = new TrialRecorder(log, arenas, this, getConfig().getStringList("target_permissions"));
		Bukkit.getPluginManager().registerEvents(recorder, this);

		flags = new FlagCapture(log, this);
		// Run after every plugin is enabled so event sources can resolve classes of the anticheat.
		Bukkit.getScheduler().runTask(this, () -> {
			flags.configure(getConfig().getMapList("flag_sources"));
			List<Map<String, Object>> plugins = new ArrayList<>();
			for (Plugin p : Bukkit.getPluginManager().getPlugins()) {
				plugins.add(Map.of("name", p.getName(), "version", p.getPluginMeta().getVersion(), "enabled", p.isEnabled()));
			}
			Map<String, Object> data = new LinkedHashMap<>();
			data.put("anticheat", getConfig().getString("anticheat", "none"));
			data.put("run_id", plan.runId);
			data.put("trials", plan.size());
			data.put("server", Bukkit.getVersion());
			data.put("plugins", plugins);
			data.put("arenas", arenas.names());
			log.write("server_ready", data);
		});
	}

	@Override
	public void onDisable() {
		if (flags != null) flags.detach();
		if (arenas != null) arenas.clearTargets();
		if (log != null) {
			log.write("server_stop", Map.of());
			try {
				log.close();
			} catch (IOException ignored) {
			}
		}
	}

	private void prepareWorld(World world) {
		world.setDifficulty(Difficulty.EASY);
		world.setTime(6000);
		world.setStorm(false);
		world.setGameRule(GameRules.ADVANCE_TIME, false);
		world.setGameRule(GameRules.ADVANCE_WEATHER, false);
		world.setGameRule(GameRules.SPAWN_MOBS, false);
		world.setGameRule(GameRules.SPAWN_MONSTERS, false);
		world.setGameRule(GameRules.RANDOM_TICK_SPEED, 0);
		world.setGameRule(GameRules.IMMEDIATE_RESPAWN, true);
		world.setGameRule(GameRules.KEEP_INVENTORY, true);
		world.setGameRule(GameRules.RESPAWN_RADIUS, 0);
		world.setGameRule(GameRules.SPAWN_PHANTOMS, false);
		world.setGameRule(GameRules.SHOW_DEATH_MESSAGES, false);
		world.setGameRule(GameRules.SEND_COMMAND_FEEDBACK, false);
		// Vanilla's own movement checks would act as a hidden extra anticheat; off by default so only the plugin under test counts.
		boolean vanillaChecks = getConfig().getBoolean("vanilla_movement_checks", false);
		world.setGameRule(GameRules.PLAYER_MOVEMENT_CHECK, vanillaChecks);
		world.setGameRule(GameRules.ELYTRA_MOVEMENT_CHECK, vanillaChecks);
		world.setSpawnLocation(new Location(world, 0.5, Arenas.BASE_Y, 0.5));
	}

	@Override
	public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
		if (args.length > 0 && args[0].equals("flag")) {
			// Only the server itself (an anticheat's console command) may report flags; a client could fake them.
			if (sender instanceof Player) return true;
			if (!flags.flagFromCommand(args)) log.write("error", Map.of("message", "acbench flag without a command flag source: " + String.join(" ", args)));
			return true;
		}
		if (!(sender instanceof Player player) || args.length == 0) return false;
		switch (args[0]) {
			case "setup" -> setup(player, trial(player, args));
			case "begin" -> {
				PlanIndex.TrialInfo trial = trial(player, args);
				if (trial != null) recorder.begin(trial, player);
			}
			case "end" -> {
				Map<String, String> stats = new LinkedHashMap<>();
				for (int i = 2; i < args.length; i++) {
					int eq = args[i].indexOf('=');
					if (eq > 0) stats.put(args[i].substring(0, eq), args[i].substring(eq + 1));
				}
				if (args.length > 1) recorder.end(player, args[1], stats);
			}
			case "act" -> {
				if (args.length > 2 && args[2].equals("knockback")) recorder.knockback(player);
				log.write("act", Map.of("player", player.getName(), "trial", args.length > 1 ? args[1] : "", "action", args.length > 2 ? args[2] : ""));
			}
			case "done" -> log.write("done", Map.of("player", player.getName()));
			default -> {
				return false;
			}
		}
		return true;
	}

	private PlanIndex.TrialInfo trial(Player player, String[] args) {
		PlanIndex.TrialInfo trial = args.length > 1 ? plan.get(args[1]) : null;
		if (trial == null) log.write("error", Map.of("message", "unknown trial " + (args.length > 1 ? args[1] : "<none>"), "player", player.getName()));
		return trial;
	}

	/** Puts the player into a clean, identical state at the arena spawn and spawns the trial's targets. */
	private void setup(Player player, PlanIndex.TrialInfo trial) {
		if (trial == null) return;
		Arenas.Arena arena = arenas.get(trial.arena);
		if (arena == null) {
			log.write("error", Map.of("message", "unknown arena " + trial.arena, "trial", trial.id));
			return;
		}
		player.setGameMode(GameMode.SURVIVAL);
		player.setAllowFlight(false);
		player.setFlying(false);
		for (PotionEffect effect : player.getActivePotionEffects()) player.removePotionEffect(effect.getType());
		player.setVelocity(new Vector());
		player.setFallDistance(0);
		player.setFireTicks(0);
		player.setNoDamageTicks(0);
		player.setHealth(player.getAttribute(Attribute.MAX_HEALTH).getValue());
		player.setFoodLevel(20);
		player.setSaturation(20);

		player.getInventory().clear();
		int slot = 0;
		for (String entry : trial.loadout) {
			String[] parts = entry.split(":");
			String name = parts.length > 1 && !parts[parts.length - 1].matches("\\d+") ? entry : parts[0];
			int amount = parts.length > 1 && parts[parts.length - 1].matches("\\d+") ? Integer.parseInt(parts[parts.length - 1]) : 1;
			Material material = Material.matchMaterial(name);
			if (material == null) {
				log.write("error", Map.of("message", "unknown loadout item " + entry, "trial", trial.id));
				continue;
			}
			player.getInventory().setItem(slot++, new ItemStack(material, amount));
		}
		player.getInventory().setHeldItemSlot(0);

		try {
			arenas.spawnTargets(arena, trial.targets);
		} catch (IllegalStateException | IllegalArgumentException e) {
			log.write("error", Map.of("message", e.getMessage(), "trial", trial.id));
		}
		player.teleport(arena.spawn(player.getWorld()));
		log.write("setup", Map.of("trial", trial.id, "player", player.getName(), "arena", arena.name()));
	}
}
