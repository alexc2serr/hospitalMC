from mcpi.minecraft import Minecraft
import time

mc = Minecraft.create()
mc.postToChat("Python conectado: escuchando golpes de bloques...")
print("Conectado a Minecraft. Esperando golpes de bloques...")

while True:
    hits = mc.events.pollBlockHits()
    if hits:
        print("Golpes detectados:")
        for h in hits:
            print(f" - ({h.pos.x}, {h.pos.y}, {h.pos.z})")
        mc.postToChat("Golpe detectado por Python!")
    time.sleep(0.2)
