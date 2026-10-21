package dev.acbench.driver.plan;

import java.util.ArrayList;
import java.util.List;

public class Trial {
	public String id;
	public String scenario;
	public String category;
	public String variant;
	/** "baseline" (cheat off) or "cheat". */
	public String phase;
	public int rep;
	public String arena;
	public List<String> targetTypes = new ArrayList<>();
	public List<ModuleSpec> modules = new ArrayList<>();
	public List<Action> actions = new ArrayList<>();

	public boolean cheatActive() {
		return "cheat".equals(phase);
	}
}
