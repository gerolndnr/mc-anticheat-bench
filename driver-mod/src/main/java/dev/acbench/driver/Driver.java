package dev.acbench.driver;

import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import dev.acbench.driver.adapter.Adapters;
import dev.acbench.driver.adapter.CheatClientAdapter;
import dev.acbench.driver.mixin.MinecraftAccessor;
import dev.acbench.driver.plan.Action;
import dev.acbench.driver.plan.ModuleSpec;
import dev.acbench.driver.plan.Plan;
import dev.acbench.driver.plan.Trial;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ConnectScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.client.multiplayer.resolver.ServerAddress;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;

/**
 * Tick driven state machine that runs the trials of a plan. Every trial is bracketed by
 * {@code /acbench setup|begin|end} commands so the server side collector can attribute flags and
 * measurements to it on the server's own timeline.
 */
public final class Driver {
	private static final Gson GSON = new GsonBuilder()
		.setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
		.serializeNulls()
		.create();
	private static final int DISCONNECT_GRACE_TICKS = 100;
	/** Title screen and loading run at 20 ticks/s too; give up if the server never lets us in. */
	private static final int JOIN_TIMEOUT_TICKS = 20 * 180;
	private static final int RECONNECT_TIMEOUT_TICKS = 20 * 60;

	private static Driver instance;

	private final Plan plan;
	private final CheatClientAdapter adapter;
	private final Random random;
	private final Set<String> completed;

	private enum State { WAIT_JOIN, INIT, RECONNECT_LEAVE, RECONNECT_JOIN, SETUP, PREPARE, ACTIONS, END, COOLDOWN, FINISH, STOPPING }

	private State state = State.WAIT_JOIN;
	private int stateTicks;
	private boolean everJoined;
	private int disconnectedTicks;
	private int notJoinedTicks;
	/** Trials run on the current connection; with reconnects enabled every trial after the first gets a fresh one. */
	private int trialsThisConnection;
	private ServerData server;
	private int rejoinedTicks;

	private int trialIndex = -1;
	private Trial trial;
	private int actionIndex;
	private int actionTicks;
	private double clickBudget;

	private int attacks;
	private int clicks;
	private int itemUses;
	/** Client ticks and wall time of the action phase; their ratio shows whether the client kept up 20 ticks/s. */
	private int actionTickCount;
	private long actionStartMs;

	private Driver(Plan plan) {
		this.plan = plan;
		this.adapter = Adapters.create(plan.client.adapter, plan.client.adapterOptions);
		this.random = new Random(plan.seed);
		this.completed = loadProgress();
	}

	public static void start(Path planFile) throws IOException {
		Plan plan = GSON.fromJson(Files.readString(planFile), Plan.class);
		instance = new Driver(plan);
		AcBenchDriver.LOG.info("Loaded plan {} with {} trials ({} already completed), adapter {}",
			plan.runId, plan.trials.size(), instance.completed.size(), plan.client.adapter);
	}

	public static Driver instance() {
		return instance;
	}

	public void countAttack() {
		if (state == State.ACTIONS) attacks++;
	}

	public void tick(Minecraft mc) {
		boolean inWorld = mc.player != null && mc.level != null && mc.getConnection() != null;
		if ("dummy".equals(plan.role)) {
			dummyTick(mc, inWorld);
			return;
		}
		if (state == State.RECONNECT_LEAVE || state == State.RECONNECT_JOIN) {
			reconnectTick(mc, inWorld);
			return;
		}
		if (!inWorld) {
			if (everJoined && state != State.STOPPING && ++disconnectedTicks > DISCONNECT_GRACE_TICKS) {
				log("disconnected", Map.of("trial", trial == null ? "" : trial.id, "state", state.name()));
				// Skip the trial after a restart; otherwise a cheat that always gets kicked would loop forever.
				if (trial != null) markCompleted(trial.id);
				stop(mc);
			} else if (!everJoined && state != State.STOPPING && ++notJoinedTicks > JOIN_TIMEOUT_TICKS) {
				log("join_timeout", Map.of("ticks", notJoinedTicks));
				stop(mc);
			}
			return;
		}
		everJoined = true;
		disconnectedTicks = 0;
		stateTicks++;

		switch (state) {
			case WAIT_JOIN -> {
				if (stateTicks >= plan.startDelayTicks) transition(State.INIT);
			}
			case INIT -> {
				mc.options.pauseOnLostFocus = false;
				init();
				nextTrial(mc);
			}
			case SETUP -> {
				if (stateTicks == 1) command(mc, "setup " + trial.id);
				if (stateTicks >= plan.setupTicks) transition(State.PREPARE);
			}
			case PREPARE -> {
				prepareModules();
				attacks = clicks = itemUses = actionTickCount = 0;
				actionStartMs = System.currentTimeMillis();
				actionIndex = 0;
				actionTicks = 0;
				clickBudget = 0;
				command(mc, "begin " + trial.id);
				transition(State.ACTIONS);
			}
			case ACTIONS -> {
				actionTickCount++;
				runActions(mc);
			}
			case END -> {
				releaseKeys(mc);
				long wallMs = System.currentTimeMillis() - actionStartMs;
				command(mc, "end " + trial.id + " attacks=" + attacks + " clicks=" + clicks + " uses=" + itemUses
					+ " ticks=" + actionTickCount + " wall_ms=" + wallMs);
				disableManagedModules();
				log("trial_end", Map.of("trial", trial.id, "attacks", attacks, "clicks", clicks, "uses", itemUses));
				markCompleted(trial.id);
				transition(State.COOLDOWN);
			}
			case COOLDOWN -> {
				if (stateTicks >= plan.cooldownTicks) nextTrial(mc);
			}
			case FINISH -> {
				if (stateTicks == 1) {
					command(mc, "done");
					log("done", Map.of("trials", plan.trials.size()));
				}
				if (stateTicks >= 40) stop(mc);
			}
			case STOPPING -> {
			}
		}
	}

	/** The target bot stays connected and idle; the collector plugin moves it where a trial needs it. */
	private void dummyTick(Minecraft mc, boolean inWorld) {
		if (inWorld) {
			if (!everJoined) log("dummy_joined", Map.of());
			everJoined = true;
			disconnectedTicks = 0;
			mc.options.pauseOnLostFocus = false;
			releaseKeys(mc);
		} else if (state != State.STOPPING && (everJoined ? ++disconnectedTicks > DISCONNECT_GRACE_TICKS : ++notJoinedTicks > JOIN_TIMEOUT_TICKS)) {
			// Exit so the orchestrator starts a fresh target client.
			log(everJoined ? "disconnected" : "join_timeout", Map.of("role", "dummy"));
			stop(mc);
		}
	}

	private void init() {
		if (!adapter.isPresent()) {
			log("error", Map.of("message", "client for adapter " + adapter.id() + " is not loaded"));
		}
		if (plan.modulesDump != null) {
			try {
				Files.writeString(Path.of(plan.modulesDump), new GsonBuilder().setPrettyPrinting().create().toJson(adapter.describeModules()));
			} catch (IOException | RuntimeException e) {
				AcBenchDriver.LOG.warn("Could not write module dump", e);
			}
		}
		disableManagedModules();
		log("init", Map.of("adapter", adapter.id(), "present", adapter.isPresent()));
	}

	private void nextTrial(Minecraft mc) {
		do {
			trialIndex++;
		} while (trialIndex < plan.trials.size() && completed.contains(plan.trials.get(trialIndex).id));

		if (trialIndex >= plan.trials.size()) {
			trial = null;
			transition(State.FINISH);
			return;
		}
		trial = plan.trials.get(trialIndex);
		releaseKeys(mc);
		transition(plan.reconnectBetweenTrials && trialsThisConnection > 0 ? State.RECONNECT_LEAVE : State.SETUP);
		trialsThisConnection++;
	}

	/**
	 * Leaves and rejoins the server so the anticheat starts the next trial with fresh per-player state
	 * (violation levels, buffers, setback mode) instead of carrying it over from earlier trials.
	 */
	private void reconnectTick(Minecraft mc, boolean inWorld) {
		stateTicks++;
		if (stateTicks > RECONNECT_TIMEOUT_TICKS) {
			log("reconnect_failed", Map.of("trial", trial.id, "state", state.name()));
			stop(mc);
			return;
		}
		if (state == State.RECONNECT_LEAVE) {
			if (stateTicks == 1) {
				if (mc.getCurrentServer() != null) server = mc.getCurrentServer();
				releaseKeys(mc);
				mc.execute(() -> mc.disconnectFromWorld(ClientLevel.DEFAULT_QUIT_MESSAGE));
			} else if (!inWorld && stateTicks >= 5) {
				ServerData target = server != null ? server : new ServerData("acbench", plan.serverAddress, ServerData.Type.OTHER);
				mc.execute(() -> ConnectScreen.startConnecting(new TitleScreen(), mc, ServerAddress.parseString(target.ip), target, false, null));
				rejoinedTicks = 0;
				transition(State.RECONNECT_JOIN);
			}
			return;
		}
		// RECONNECT_JOIN: wait until the world is loaded and let the anticheat settle before the next setup.
		if (inWorld && ++rejoinedTicks >= plan.rejoinSettleTicks) {
			transition(State.SETUP);
		}
	}

	/** Resets every module of the trial to defaults, applies the variant settings and enables it for cheat phases. */
	private void prepareModules() {
		List<String> failed = new ArrayList<>();
		Map<String, Object> enabled = new LinkedHashMap<>();
		for (ModuleSpec module : trial.modules) {
			try {
				adapter.resetSettings(module.name);
				for (Map.Entry<String, String> setting : module.settings.entrySet()) {
					if (!adapter.applySetting(module.name, setting.getKey(), setting.getValue())) {
						failed.add(module.name + "." + setting.getKey() + "=" + setting.getValue());
					}
				}
				if (trial.cheatActive()) {
					adapter.setEnabled(module.name, true);
					Boolean active = adapter.isEnabled(module.name);
					enabled.put(module.name, active == null ? "unknown" : active);
				}
			} catch (CheatClientAdapter.AdapterException e) {
				failed.add(module.name + ": " + e.getMessage());
			}
		}
		Map<String, Object> data = new LinkedHashMap<>();
		data.put("trial", trial.id);
		data.put("phase", trial.phase);
		data.put("enabled", enabled);
		data.put("failed", failed);
		log("trial_prepared", data);
	}

	private void disableManagedModules() {
		for (String module : plan.managedModules) {
			try {
				adapter.setEnabled(module, false);
			} catch (CheatClientAdapter.AdapterException ignored) {
				// Unknown modules are reported when a trial tries to enable them.
			}
		}
	}

	private void runActions(Minecraft mc) {
		if (actionIndex >= trial.actions.size()) {
			transition(State.END);
			return;
		}
		Action action = trial.actions.get(actionIndex);
		actionTicks++;
		LocalPlayer player = mc.player;

		switch (action.type) {
			case "hold" -> {
				setKeys(mc, action.keys);
				if (action.aim) aim(player, action.maxTurn);
				if (action.cps > 0) click(mc, action);
				if (action.use) {
					if (actionTicks == 1 || !player.isUsingItem()) {
						((MinecraftAccessor) mc).acbench$startUseItem();
						itemUses++;
					}
					mc.options.keyUse.setDown(true);
				}
			}
			case "wait" -> releaseKeys(mc);
			case "look" -> {
				if (action.pitch != null) player.setXRot(action.pitch);
				player.setYRot(player.getYRot() + action.yawDelta);
			}
			case "slot" -> player.getInventory().setSelectedSlot(action.slot);
			case "server" -> command(mc, "act " + trial.id + " " + action.command);
			default -> log("error", Map.of("message", "unknown action type " + action.type));
		}

		if (actionTicks >= Math.max(1, action.ticks)) {
			if ("hold".equals(action.type)) releaseKeys(mc);
			actionIndex++;
			actionTicks = 0;
		}
	}

	private void setKeys(Minecraft mc, List<String> keys) {
		for (Map.Entry<String, KeyMapping> entry : movementKeys(mc).entrySet()) {
			entry.getValue().setDown(keys.contains(entry.getKey()));
		}
	}

	private void releaseKeys(Minecraft mc) {
		setKeys(mc, List.of());
		mc.options.keyUse.setDown(false);
		mc.options.keyAttack.setDown(false);
	}

	private static Map<String, KeyMapping> movementKeys(Minecraft mc) {
		Map<String, KeyMapping> keys = new LinkedHashMap<>();
		keys.put("forward", mc.options.keyUp);
		keys.put("back", mc.options.keyDown);
		keys.put("left", mc.options.keyLeft);
		keys.put("right", mc.options.keyRight);
		keys.put("jump", mc.options.keyJump);
		keys.put("sneak", mc.options.keyShift);
		keys.put("sprint", mc.options.keySprint);
		return keys;
	}

	/** Clicks at roughly the requested CPS, with per-tick jitter so the pattern is not perfectly regular. */
	private void click(Minecraft mc, Action action) {
		clickBudget += action.cps / 20.0 * (1.0 + action.jitter * (random.nextDouble() * 2 - 1));
		while (clickBudget >= 1.0) {
			clickBudget -= 1.0;
			((MinecraftAccessor) mc).acbench$startAttack();
			clicks++;
		}
	}

	/** Turns towards the nearest benchmark target with a capped turn rate and small noise, like a human would. */
	private void aim(LocalPlayer player, float maxTurn) {
		Entity target = nearestTarget(player);
		if (target == null) return;
		Vec3 eye = player.getEyePosition();
		Vec3 center = target.getBoundingBox().getCenter();
		double dx = center.x - eye.x;
		double dy = center.y - eye.y;
		double dz = center.z - eye.z;
		float yaw = (float) (Mth.atan2(dz, dx) * Mth.RAD_TO_DEG) - 90f;
		float pitch = (float) -(Mth.atan2(dy, Math.sqrt(dx * dx + dz * dz)) * Mth.RAD_TO_DEG);
		float dYaw = Mth.clamp(Mth.wrapDegrees(yaw - player.getYRot()), -maxTurn, maxTurn);
		float dPitch = Mth.clamp(pitch - player.getXRot(), -maxTurn, maxTurn);
		player.setYRot(player.getYRot() + dYaw + (float) random.nextGaussian() * 0.35f);
		player.setXRot(Mth.clamp(player.getXRot() + dPitch + (float) random.nextGaussian() * 0.2f, -90f, 90f));
	}

	private Entity nearestTarget(LocalPlayer player) {
		Entity best = null;
		double bestDist = 64;
		for (Entity entity : Minecraft.getInstance().level.entitiesForRendering()) {
			if (entity == player || !(entity instanceof LivingEntity) || !entity.isAlive()) continue;
			if (!trial.targetTypes.isEmpty() && !trial.targetTypes.contains(EntityType.getKey(entity.getType()).toString())) continue;
			double dist = entity.distanceToSqr(player);
			if (dist < bestDist) {
				best = entity;
				bestDist = dist;
			}
		}
		return best;
	}

	private static void command(Minecraft mc, String command) {
		mc.getConnection().sendCommand("acbench " + command);
	}

	private void transition(State next) {
		state = next;
		stateTicks = 0;
	}

	private void stop(Minecraft mc) {
		transition(State.STOPPING);
		mc.stop();
	}

	private Set<String> loadProgress() {
		if (plan.progressFile == null) return new HashSet<>();
		try {
			Path path = Path.of(plan.progressFile);
			if (!Files.exists(path)) return new HashSet<>();
			return GSON.fromJson(Files.readString(path), new TypeToken<HashSet<String>>() {}.getType());
		} catch (IOException e) {
			return new HashSet<>();
		}
	}

	private void markCompleted(String trialId) {
		completed.add(trialId);
		if (plan.progressFile == null) return;
		try {
			Files.writeString(Path.of(plan.progressFile), GSON.toJson(completed));
		} catch (IOException e) {
			AcBenchDriver.LOG.warn("Could not write progress", e);
		}
	}

	private void log(String type, Map<String, ?> data) {
		Map<String, Object> event = new LinkedHashMap<>();
		event.put("type", type);
		event.put("time_ms", System.currentTimeMillis());
		event.putAll(data);
		String line = GSON.toJson(event);
		AcBenchDriver.LOG.info(line);
		if (plan.clientLog == null) return;
		try (Writer w = Files.newBufferedWriter(Path.of(plan.clientLog), StandardCharsets.UTF_8,
			StandardOpenOption.CREATE, StandardOpenOption.APPEND)) {
			w.write(line);
			w.write('\n');
		} catch (IOException e) {
			AcBenchDriver.LOG.warn("Could not write client log", e);
		}
	}
}
