package dev.acbench.driver;

import java.nio.file.Path;

import net.fabricmc.api.ClientModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AcBenchDriver implements ClientModInitializer {
	public static final Logger LOG = LoggerFactory.getLogger("acbench-driver");

	@Override
	public void onInitializeClient() {
		String planPath = System.getProperty("acbench.plan", System.getenv("ACBENCH_PLAN"));
		if (planPath == null || planPath.isBlank()) {
			LOG.info("No benchmark plan given (-Dacbench.plan), driver stays inactive");
			return;
		}
		try {
			Driver.start(Path.of(planPath));
		} catch (Exception e) {
			LOG.error("Failed to load benchmark plan {}", planPath, e);
		}
	}
}
