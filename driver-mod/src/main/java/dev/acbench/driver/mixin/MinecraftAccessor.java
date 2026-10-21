package dev.acbench.driver.mixin;

import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

@Mixin(Minecraft.class)
public interface MinecraftAccessor {
	@Invoker("startAttack")
	boolean acbench$startAttack();

	@Invoker("startUseItem")
	void acbench$startUseItem();
}
