package dev.acbench.driver.plan;

import java.util.LinkedHashMap;
import java.util.Map;

public class ModuleSpec {
	public String name;
	/** Setting name (optionally "group/setting") to value, in the client's own string syntax. */
	public Map<String, String> settings = new LinkedHashMap<>();
}
