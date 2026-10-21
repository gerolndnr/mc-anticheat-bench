package dev.acbench.driver.mixin;

import dev.acbench.driver.Driver;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Minecraft.class)
public abstract class MinecraftMixin {
	@Inject(method = "tick", at = @At("HEAD"))
	private void acbench$onTick(CallbackInfo ci) {
		Driver driver = Driver.instance();
		if (driver != null) driver.tick((Minecraft) (Object) this);
	}
}
