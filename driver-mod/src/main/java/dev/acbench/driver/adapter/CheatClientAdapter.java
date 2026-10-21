package dev.acbench.driver.adapter;

import java.util.List;
import java.util.Map;

/**
 * Bridge between the benchmark driver and one cheat client. To support a new client, implement this
 * interface and register it in {@link Adapters}, or use the generic {@link CommandAdapter} when the
 * client can be fully controlled through chat commands.
 */
public interface CheatClientAdapter {
	String id();

	/** Whether the client is loaded in this game instance. */
	boolean isPresent();

	/** Resets all settings of the module to the client's defaults. */
	void resetSettings(String module) throws AdapterException;

	/** Applies one setting; returns false if the client rejected the value. */
	boolean applySetting(String module, String setting, String value) throws AdapterException;

	void setEnabled(String module, boolean enabled) throws AdapterException;

	/** Returns null if the adapter cannot tell. */
	Boolean isEnabled(String module) throws AdapterException;

	/** Describes all modules and settings, written to disk so scenario mappings can be maintained. */
	List<Map<String, Object>> describeModules();

	class AdapterException extends Exception {
		public AdapterException(String message) {
			super(message);
		}

		public AdapterException(String message, Throwable cause) {
			super(message, cause);
		}
	}
}
