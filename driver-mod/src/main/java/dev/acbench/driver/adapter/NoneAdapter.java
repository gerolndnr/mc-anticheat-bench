package dev.acbench.driver.adapter;

import java.util.List;
import java.util.Map;

/** Plain vanilla client: no modules exist, so every cheat phase runs without a cheat. */
public class NoneAdapter implements CheatClientAdapter {
	@Override
	public String id() {
		return "none";
	}

	@Override
	public boolean isPresent() {
		return true;
	}

	@Override
	public void resetSettings(String module) {
	}

	@Override
	public boolean applySetting(String module, String setting, String value) {
		return false;
	}

	@Override
	public void setEnabled(String module, boolean enabled) throws AdapterException {
		if (enabled) throw new AdapterException("vanilla client has no module " + module);
	}

	@Override
	public Boolean isEnabled(String module) {
		return false;
	}

	@Override
	public List<Map<String, Object>> describeModules() {
		return List.of();
	}
}
