package dev.acbench.collector;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.Registry;
import org.bukkit.World;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.entity.Entity;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.util.Vector;

/**
 * Builds deterministic test arenas floating at y=100 in a flat world. Every arena faces +X (yaw -90), so
 * "forward progress" is always the X delta. Arenas sit 100 blocks apart on the Z axis.
 */
final class Arenas {
	static final String TARGET_TAG = "acbench_target";
	static final int BASE_Y = 100;
	private static final float YAW_EAST = -90f;

	record Arena(String name, double x, double y, double z) {
		Location spawn(World world) {
			return new Location(world, x, y, z, YAW_EAST, 0f);
		}
	}

	/** A spawned target and the position it is pinned to, so knockback cannot move it out of range. */
	record Target(LivingEntity entity, Location anchor, String role) {
	}

	private final World world;
	/** Name of the second bot that stands in as a player target ("player" targets); null if none is used. */
	private final String targetPlayer;
	private final Map<String, Arena> arenas = new LinkedHashMap<>();
	private final List<Target> targets = new ArrayList<>();

	Arenas(World world, String targetPlayer) {
		this.world = world;
		this.targetPlayer = targetPlayer;
	}

	void build() {
		Material floor = Material.STONE;

		// Long straight track: speed, timer, noslow.
		fill(-5, 99, -3, 320, 99, 3, floor);
		register("track", 0.5, BASE_Y, 0.5);

		// Open platform: fly.
		fill(-5, 99, 95, 60, 99, 105, floor);
		register("open", 0.5, BASE_Y, 100.5);

		// Staircase of full blocks, two blocks deep each: step.
		fill(-5, 99, 197, 2, 99, 203, floor);
		for (int i = 0; i < 30; i++) {
			int x = 3 + i * 2;
			fill(x, 99, 197, x + 1, BASE_Y + i, 203, floor);
		}
		register("stairs", 0.5, BASE_Y, 200.5);

		// Narrow ledge 12 blocks above a landing floor: nofall.
		fill(-5, 99, 285, 60, 99, 315, floor);
		fill(-3, 111, 299, 1, 111, 301, floor);
		register("fall", -0.5, 112, 300.5);

		// Long water channel with a start platform: jesus.
		fill(-5, 99, 396, 1, 99, 404, floor);
		fill(2, 95, 396, 160, 99, 404, floor);
		fill(2, 96, 397, 160, 99, 403, Material.WATER);
		register("pool", 0.5, BASE_Y, 400.5);

		// Tall wall right in front of the spawn: spider.
		fill(-5, 99, 495, 5, 99, 505, floor);
		fill(2, BASE_Y, 495, 3, BASE_Y + 60, 505, floor);
		register("wall", 0.5, BASE_Y, 500.5);

		// Flat combat floor; targets are spawned per trial.
		fill(-15, 99, 585, 25, 99, 615, floor);
		register("combat", 0.5, BASE_Y, 600.5);

		// Waiting spot for the target bot while no trial needs it.
		fill(-3, 99, -103, 3, 99, -97, floor);
		register("lobby", 0.5, BASE_Y, -99.5);

		for (Arena arena : arenas.values()) {
			int cx = (int) Math.floor(arena.x()) >> 4;
			int cz = (int) Math.floor(arena.z()) >> 4;
			for (int dx = -2; dx <= 10; dx++) {
				for (int dz = -1; dz <= 1; dz++) world.setChunkForceLoaded(cx + dx, cz + dz, true);
			}
		}
	}

	Arena get(String name) {
		return arenas.get(name);
	}

	List<String> names() {
		return new ArrayList<>(arenas.keySet());
	}

	void spawnTargets(Arena arena, List<PlanIndex.TargetSpec> specs) {
		clearTargets();
		for (PlanIndex.TargetSpec spec : specs) {
			if ("player".equals(spec.type)) {
				spawnPlayerTarget(arena, spec);
				continue;
			}
			EntityType type = Registry.ENTITY_TYPE.get(NamespacedKey.fromString(spec.type));
			if (type == null || !type.isAlive() || !type.isSpawnable()) {
				throw new IllegalArgumentException("Cannot spawn target type " + spec.type);
			}
			// Facing +X: forward is +X, side is +Z. Targets look back at the spawn.
			Location at = new Location(world, arena.x() + spec.forward, arena.y() + spec.up, arena.z() + spec.side, 90f, 0f);
			Entity entity = world.spawnEntity(at, type);
			LivingEntity living = (LivingEntity) entity;
			living.setAI(false);
			living.setSilent(true);
			living.setPersistent(true);
			living.setRemoveWhenFarAway(false);
			living.addScoreboardTag(TARGET_TAG);
			setAttribute(living, Attribute.MAX_HEALTH, 1000);
			setAttribute(living, Attribute.KNOCKBACK_RESISTANCE, 1);
			living.setHealth(1000);
			targets.add(new Target(living, at, spec.role));
		}
	}

	private void spawnPlayerTarget(Arena arena, PlanIndex.TargetSpec spec) {
		Player player = targetPlayer == null ? null : Bukkit.getPlayerExact(targetPlayer);
		if (player == null) throw new IllegalStateException("target player " + targetPlayer + " is not online");
		Location at = new Location(world, arena.x() + spec.forward, arena.y() + spec.up, arena.z() + spec.side, 90f, 0f);
		player.setGameMode(GameMode.SURVIVAL);
		player.teleport(at);
		player.setVelocity(new Vector());
		player.addScoreboardTag(TARGET_TAG);
		targets.add(new Target(player, at, spec.role));
	}

	/** Keeps targets alive and in place; called every tick. */
	void maintainTargets() {
		for (Target target : targets) {
			LivingEntity entity = target.entity();
			if (!entity.isValid()) continue;
			if (entity instanceof Player player) {
				// Players are only moved back once knockback has displaced them; teleporting every tick fights the client.
				if (player.getLocation().distanceSquared(target.anchor()) > 0.0025) {
					player.teleport(target.anchor());
					player.setVelocity(new Vector());
				}
				player.setFoodLevel(20);
			} else if (entity.getLocation().distanceSquared(target.anchor()) > 0.0001) {
				entity.teleport(target.anchor());
			}
			AttributeInstance max = entity.getAttribute(Attribute.MAX_HEALTH);
			if (max != null) entity.setHealth(max.getValue());
			entity.setFireTicks(0);
		}
	}

	Target firstTarget(String role) {
		for (Target target : targets) {
			if (target.role().equals(role) && target.entity().isValid()) return target;
		}
		return targets.isEmpty() ? null : targets.getFirst();
	}

	void clearTargets() {
		targets.clear();
		for (Entity entity : world.getEntities()) {
			if (!entity.getScoreboardTags().contains(TARGET_TAG)) continue;
			if (entity instanceof Player player) player.removeScoreboardTag(TARGET_TAG);
			else entity.remove();
		}
		parkTargetPlayer();
	}

	/** Moves the target bot out of the way so it cannot influence trials that do not use it. */
	void parkTargetPlayer() {
		Player player = targetPlayer == null ? null : Bukkit.getPlayerExact(targetPlayer);
		if (player == null) return;
		Arena lobby = arenas.get("lobby");
		if (lobby != null && player.getLocation().distanceSquared(lobby.spawn(world)) > 4) player.teleport(lobby.spawn(world));
	}

	boolean isTargetPlayer(Player player) {
		return targetPlayer != null && targetPlayer.equalsIgnoreCase(player.getName());
	}

	private void register(String name, double x, double y, double z) {
		arenas.put(name, new Arena(name, x, y, z));
	}

	private void fill(int x1, int y1, int z1, int x2, int y2, int z2, Material material) {
		for (int x = Math.min(x1, x2); x <= Math.max(x1, x2); x++) {
			for (int y = Math.min(y1, y2); y <= Math.max(y1, y2); y++) {
				for (int z = Math.min(z1, z2); z <= Math.max(z1, z2); z++) {
					world.getBlockAt(x, y, z).setType(material, false);
				}
			}
		}
	}

	private static void setAttribute(LivingEntity entity, Attribute attribute, double value) {
		AttributeInstance instance = entity.getAttribute(attribute);
		if (instance != null) instance.setBaseValue(value);
	}
}
