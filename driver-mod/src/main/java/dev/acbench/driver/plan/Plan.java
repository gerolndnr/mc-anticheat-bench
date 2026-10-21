package dev.acbench.driver.plan;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Fully resolved run plan written by the orchestrator. The driver only executes it. */
public class Plan {
	public String runId;
	/** "player" runs the trials; "dummy" only joins and stands still as a player target for combat trials. */
	public String role = "player";
	public ClientSpec client = new ClientSpec();
	public long seed = 1;
	public String progressFile;
	public String clientLog;
	public String modulesDump;
	public int startDelayTicks = 100;
	public int setupTicks = 30;
	public int cooldownTicks = 40;
	/** Rejoin before every trial so anticheat state does not carry over between trials. */
	public boolean reconnectBetweenTrials = true;
	public int rejoinSettleTicks = 40;
	/** Fallback "host:port" if the client cannot tell which server it is connected to. */
	public String serverAddress = "127.0.0.1:25565";
	/** Every module any trial touches; all of them are switched off before each trial. */
	public List<String> managedModules = new ArrayList<>();
	public List<Trial> trials = new ArrayList<>();

	public static class ClientSpec {
		public String id = "vanilla";
		public String adapter = "none";
		public Map<String, String> adapterOptions = Map.of();
	}
}
