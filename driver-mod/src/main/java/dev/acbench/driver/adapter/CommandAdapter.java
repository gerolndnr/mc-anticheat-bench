package dev.acbench.driver.adapter;

import java.util.List;
import java.util.Map;

import net.minecraft.client.Minecraft;

/**
 * Generic adapter for clients that expose a chat command interface (e.g. ".toggle fly on").
 * Command templates come from the client config ({@code adapter_options}); placeholders are
 * {module}, {setting} and {value}. Messages are sent through the normal chat path so the client's
 * command interceptor sees them. Enabled state cannot be read back, so verification is skipped.
 */
public class CommandAdapter implements CheatClientAdapter {
	private final Map<String, String> options;

	public CommandAdapter(Map<String, String> options) {
		this.options = options;
	}

	@Override
	public String id() {
		return "command";
	}

	@Override
	public boolean isPresent() {
		return true;
	}

	@Override
	public void resetSettings(String module) throws AdapterException {
		String template = options.get("reset");
		if (template != null) send(template, module, "", "");
	}

	@Override
	public boolean applySetting(String module, String setting, String value) throws AdapterException {
		send(require("set"), module, setting, value);
		return true;
	}

	@Override
	public void setEnabled(String module, boolean enabled) throws AdapterException {
		send(require(enabled ? "enable" : "disable"), module, "", "");
	}

	@Override
	public Boolean isEnabled(String module) {
		return null;
	}

	@Override
	public List<Map<String, Object>> describeModules() {
		return List.of();
	}

	private String require(String key) throws AdapterException {
		String template = options.get(key);
		if (template == null) throw new AdapterException("command adapter needs adapter_options." + key);
		return template;
	}

	private static void send(String template, String module, String setting, String value) throws AdapterException {
		var connection = Minecraft.getInstance().getConnection();
		if (connection == null) throw new AdapterException("not connected");
		connection.sendChat(template.replace("{module}", module).replace("{setting}", setting).replace("{value}", value));
	}
}
