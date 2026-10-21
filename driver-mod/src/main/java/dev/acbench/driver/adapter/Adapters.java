package dev.acbench.driver.adapter;

import java.util.Map;

/** Registry of adapter ids usable in client configs. Add new clients here. */
public final class Adapters {
	private Adapters() {
	}

	public static CheatClientAdapter create(String id, Map<String, String> options) {
		return switch (id) {
			case "meteor" -> new MeteorAdapter();
			case "liquidbounce" -> new LiquidBounceAdapter();
			case "command" -> new CommandAdapter(options);
			case "none" -> new NoneAdapter();
			default -> throw new IllegalArgumentException("Unknown adapter '" + id + "'");
		};
	}
}
