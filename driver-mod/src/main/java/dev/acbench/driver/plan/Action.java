package dev.acbench.driver.plan;

import java.util.ArrayList;
import java.util.List;

/**
 * One step of a scenario. Supported types:
 * <ul>
 *   <li>{@code hold}: hold {@link #keys} for {@link #ticks}; optionally aim at a target, click with {@link #cps} or use the held item</li>
 *   <li>{@code wait}: release everything for {@link #ticks}</li>
 *   <li>{@code look}: set pitch and/or turn the yaw by {@link #yawDelta}</li>
 *   <li>{@code slot}: select hotbar {@link #slot}</li>
 *   <li>{@code server}: ask the collector plugin to perform {@link #command} (e.g. knockback)</li>
 * </ul>
 */
public class Action {
	public String type;
	public int ticks;
	public List<String> keys = new ArrayList<>();
	public boolean aim;
	public float maxTurn = 18f;
	public double cps;
	public double jitter = 0.25;
	public boolean use;
	public Float pitch;
	public float yawDelta;
	public int slot;
	public String command;
}
