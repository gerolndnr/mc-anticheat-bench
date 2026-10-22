package dev.acbench.collector;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.destroystokyo.paper.event.server.ServerTickEndEvent;
import io.papermc.paper.event.player.PlayerArmSwingEvent;
import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.PlayerItemConsumeEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerKickEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.event.player.PlayerVelocityEvent;
import org.bukkit.permissions.PermissionAttachment;
import org.bukkit.plugin.Plugin;
import org.bukkit.util.BoundingBox;
import org.bukkit.util.Vector;

/**
 * Measures what a player actually achieved during a trial, independent of any anticheat: distance,
 * height, fall damage, landed hits, knockback taken. Comparing these between cheat and baseline phases,
 * and between "no anticheat" and a given anticheat, gives the advantage a cheat retains.
 */
final class TrialRecorder implements Listener {
	/** Knockback is read twice: right after the hit and once it has settled (or an anticheat has set the player back). */
	private static final int KNOCKBACK_EARLY_TICKS = 10;
	private static final int KNOCKBACK_LATE_TICKS = 40;

	private final EventLog log;
	private final Arenas arenas;
	private final Plugin plugin;
	/** The anticheat's bypass permissions, given to the target bot only. */
	private final List<String> targetPermissions;
	private final Map<UUID, Active> active = new HashMap<>();

	TrialRecorder(EventLog log, Arenas arenas, Plugin plugin, List<String> targetPermissions) {
		this.log = log;
		this.arenas = arenas;
		this.plugin = plugin;
		this.targetPermissions = List.copyOf(targetPermissions);
	}

	private static final class Knockback {
		final int tick;
		final Location from;
		double early = -1;
		double late = -1;

		Knockback(int tick, Location from) {
			this.tick = tick;
			this.from = from;
		}
	}

	private static final class Active {
		final PlanIndex.TrialInfo trial;
		final Player player;
		final int beginTick = Bukkit.getCurrentTick();
		final Location start;
		Location last;
		int ticks;
		double path;
		double maxForward;
		double maxHeight;
		double minHeight;
		double maxTickSpeed;
		int airTicks;
		double damageTaken;
		double fallDamage;
		int hits;
		int cancelledHits;
		int crits;
		double hitDistanceSum;
		double maxHitDistance;
		int swings;
		int teleports;
		int velocityEvents;
		int itemsConsumed;
		int deaths;
		double msptSum;
		final List<Knockback> knockbacks = new ArrayList<>();

		Active(PlanIndex.TrialInfo trial, Player player) {
			this.trial = trial;
			this.player = player;
			this.start = player.getLocation();
			this.last = start;
		}
	}

	void begin(PlanIndex.TrialInfo trial, Player player) {
		active.put(player.getUniqueId(), new Active(trial, player));
		log.write("trial_begin", Map.of("trial", trial.id, "player", player.getName()));
	}

	void end(Player player, String trialId, Map<String, String> clientStats) {
		Active a = active.remove(player.getUniqueId());
		if (a == null || !a.trial.id.equals(trialId)) {
			log.write("error", Map.of("message", "end for unknown trial " + trialId, "player", player.getName()));
			return;
		}
		Location end = player.getLocation();
		double seconds = Math.max(1, a.ticks) / 20.0;
		Map<String, Object> m = new LinkedHashMap<>();
		m.put("ticks", a.ticks);
		m.put("forward_distance", end.getX() - a.start.getX());
		m.put("forward_speed", (end.getX() - a.start.getX()) / seconds);
		m.put("max_forward", a.maxForward);
		m.put("path_horizontal", a.path);
		m.put("max_height_gain", a.maxHeight);
		m.put("min_height", a.minHeight);
		m.put("max_tick_speed", a.maxTickSpeed);
		m.put("air_ticks", a.airTicks);
		m.put("damage_taken", a.damageTaken);
		m.put("fall_damage", a.fallDamage);
		m.put("hits", a.hits);
		m.put("hits_per_second", a.hits / seconds);
		m.put("cancelled_hits", a.cancelledHits);
		m.put("crits", a.crits);
		m.put("avg_hit_distance", a.hits == 0 ? 0 : a.hitDistanceSum / a.hits);
		m.put("max_hit_distance", a.maxHitDistance);
		m.put("swings", a.swings);
		m.put("swings_per_second", a.swings / seconds);
		m.put("teleports", a.teleports);
		m.put("velocity_events", a.velocityEvents);
		m.put("items_consumed", a.itemsConsumed);
		m.put("deaths", a.deaths);
		m.put("avg_mspt", a.ticks == 0 ? 0 : a.msptSum / a.ticks);
		List<Double> early = new ArrayList<>();
		List<Double> late = new ArrayList<>();
		for (Knockback k : a.knockbacks) {
			if (k.early >= 0) early.add(k.early);
			if (k.late >= 0) late.add(k.late);
		}
		m.put("knockbacks", late.size());
		m.put("knockback_early", early.stream().mapToDouble(Double::doubleValue).average().orElse(0));
		m.put("knockback_taken", late.stream().mapToDouble(Double::doubleValue).average().orElse(0));

		Map<String, Object> client = new LinkedHashMap<>();
		clientStats.forEach((k, v) -> {
			try {
				client.put(k, Double.parseDouble(v));
			} catch (NumberFormatException e) {
				client.put(k, v);
			}
		});
		if (client.get("attacks") instanceof Double attacks && attacks > 0) m.put("hit_ratio", a.hits / attacks);

		Map<String, Object> data = new LinkedHashMap<>();
		data.put("trial", trialId);
		data.put("player", player.getName());
		data.put("begin_tick", a.beginTick);
		data.put("metrics", m);
		data.put("client", client);
		log.write("trial_end", data);
	}

	/** Applies a vanilla hit from the trial's attacker so the knockback reaches the client as a velocity packet. */
	void knockback(Player player) {
		Active a = active.get(player.getUniqueId());
		Arenas.Target attacker = arenas.firstTarget("attacker");
		if (a == null || attacker == null) {
			log.write("error", Map.of("message", "knockback without active trial or attacker", "player", player.getName()));
			return;
		}
		player.setNoDamageTicks(0);
		a.knockbacks.add(new Knockback(Bukkit.getCurrentTick(), player.getLocation()));
		player.damage(1.0, attacker.entity());
	}

	@EventHandler
	public void onTickEnd(ServerTickEndEvent event) {
		arenas.maintainTargets();
		int tick = Bukkit.getCurrentTick();
		for (Active a : active.values()) {
			Player p = a.player;
			if (!p.isOnline()) continue;
			Location loc = p.getLocation();
			a.ticks++;
			a.msptSum += event.getTickDuration();
			double dx = loc.getX() - a.last.getX();
			double dz = loc.getZ() - a.last.getZ();
			double step = Math.sqrt(dx * dx + dz * dz);
			a.path += step;
			a.maxTickSpeed = Math.max(a.maxTickSpeed, step * 20);
			a.maxForward = Math.max(a.maxForward, loc.getX() - a.start.getX());
			a.maxHeight = Math.max(a.maxHeight, loc.getY() - a.start.getY());
			a.minHeight = Math.min(a.minHeight, loc.getY() - a.start.getY());
			if (isAirborne(p, loc)) a.airTicks++;
			for (Knockback k : a.knockbacks) {
				double kx = loc.getX() - k.from.getX();
				double kz = loc.getZ() - k.from.getZ();
				if (k.early < 0 && tick - k.tick >= KNOCKBACK_EARLY_TICKS) k.early = Math.sqrt(kx * kx + kz * kz);
				if (k.late < 0 && tick - k.tick >= KNOCKBACK_LATE_TICKS) k.late = Math.sqrt(kx * kx + kz * kz);
			}
			a.last = loc;
		}
	}

	/** Position based, so a spoofed on-ground flag does not hide flying. */
	private static boolean isAirborne(Player p, Location loc) {
		if (p.isInWater() || p.isClimbing() || p.isGliding() || p.isInsideVehicle()) return false;
		BoundingBox box = p.getBoundingBox();
		double y = box.getMinY() - 0.06;
		double[][] corners = {{box.getMinX(), box.getMinZ()}, {box.getMinX(), box.getMaxZ()}, {box.getMaxX(), box.getMinZ()}, {box.getMaxX(), box.getMaxZ()}};
		for (double[] c : corners) {
			if (!loc.getWorld().getBlockAt((int) Math.floor(c[0]), (int) Math.floor(y), (int) Math.floor(c[1])).isPassable()) return false;
		}
		return true;
	}

	@EventHandler(priority = EventPriority.MONITOR)
	public void onHit(EntityDamageByEntityEvent event) {
		if (!(event.getDamager() instanceof Player player)) return;
		Active a = active.get(player.getUniqueId());
		Entity target = event.getEntity();
		if (a == null || !target.getScoreboardTags().contains(Arenas.TARGET_TAG)) return;
		if (event.isCancelled()) {
			a.cancelledHits++;
			return;
		}
		a.hits++;
		if (event.isCritical()) a.crits++;
		double distance = distanceToBox(player.getEyeLocation().toVector(), target.getBoundingBox());
		a.hitDistanceSum += distance;
		a.maxHitDistance = Math.max(a.maxHitDistance, distance);
	}

	private static double distanceToBox(Vector point, BoundingBox box) {
		double x = Math.max(box.getMinX(), Math.min(point.getX(), box.getMaxX()));
		double y = Math.max(box.getMinY(), Math.min(point.getY(), box.getMaxY()));
		double z = Math.max(box.getMinZ(), Math.min(point.getZ(), box.getMaxZ()));
		return point.distance(new Vector(x, y, z));
	}

	@EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
	public void onDamage(EntityDamageEvent event) {
		if (!(event.getEntity() instanceof Player player)) return;
		Active a = active.get(player.getUniqueId());
		if (a == null) return;
		a.damageTaken += event.getFinalDamage();
		if (event.getCause() == EntityDamageEvent.DamageCause.FALL) a.fallDamage += event.getFinalDamage();
	}

	@EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
	public void onSwing(PlayerArmSwingEvent event) {
		Active a = active.get(event.getPlayer().getUniqueId());
		if (a != null) a.swings++;
	}

	@EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
	public void onTeleport(PlayerTeleportEvent event) {
		Active a = active.get(event.getPlayer().getUniqueId());
		if (a != null) a.teleports++;
	}

	@EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
	public void onVelocity(PlayerVelocityEvent event) {
		Active a = active.get(event.getPlayer().getUniqueId());
		if (a != null) a.velocityEvents++;
	}

	@EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
	public void onConsume(PlayerItemConsumeEvent event) {
		Active a = active.get(event.getPlayer().getUniqueId());
		if (a != null) a.itemsConsumed++;
	}

	@EventHandler(priority = EventPriority.MONITOR)
	public void onDeath(PlayerDeathEvent event) {
		Active a = active.get(event.getPlayer().getUniqueId());
		if (a != null) a.deaths++;
		log.write("death", Map.of("player", event.getPlayer().getName(), "trial", a == null ? "" : a.trial.id));
	}

	/**
	 * Exempts the target bot from the anticheat: it is benchmark infrastructure, and the collector's teleports that pin
	 * it in place would otherwise draw flags, setbacks and cancelled actions. Runs first on join because Intave resolves
	 * its bypass once on join; Grim and Spartan read theirs later. Only the target bot is ever exempted.
	 */
	@EventHandler(priority = EventPriority.LOWEST)
	public void onTargetJoin(PlayerJoinEvent event) {
		Player player = event.getPlayer();
		if (targetPermissions.isEmpty() || !arenas.isTargetPlayer(player)) return;
		PermissionAttachment attachment = player.addAttachment(plugin);
		for (String permission : targetPermissions) attachment.setPermission(permission, true);
		log.write("target_exempt", Map.of("player", player.getName(), "permissions", targetPermissions));
	}

	@EventHandler(priority = EventPriority.MONITOR)
	public void onJoin(PlayerJoinEvent event) {
		log.write("join", Map.of("player", event.getPlayer().getName()));
		if (arenas.isTargetPlayer(event.getPlayer())) arenas.parkTargetPlayer();
	}

	@EventHandler(priority = EventPriority.MONITOR)
	public void onQuit(PlayerQuitEvent event) {
		Active a = active.remove(event.getPlayer().getUniqueId());
		log.write("quit", Map.of("player", event.getPlayer().getName(), "trial", a == null ? "" : a.trial.id));
	}

	@EventHandler(priority = EventPriority.MONITOR)
	public void onKick(PlayerKickEvent event) {
		Active a = active.remove(event.getPlayer().getUniqueId());
		Map<String, Object> data = new LinkedHashMap<>();
		data.put("player", event.getPlayer().getName());
		data.put("trial", a == null ? "" : a.trial.id);
		data.put("reason", net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer.plainText().serialize(event.reason()));
		data.put("cancelled", event.isCancelled());
		log.write("kick", data);
	}
}
