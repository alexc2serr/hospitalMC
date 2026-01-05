from mcpi.minecraft import Minecraft

mc = Minecraft.create()  # por defecto localhost:4711
mc.postToChat("Hola desde Python!")
print("Mensaje enviado.")
