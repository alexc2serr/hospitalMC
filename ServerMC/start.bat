@echo off
REM Script para iniciar un servidor de Minecraft en Windows

REM Ajusta la cantidad de memoria según tu PC (Xms = mínimo, Xmx = máximo)
java -Xms1G -Xmx2G -jar server.jar nogui

REM Pausa para que la ventana no se cierre automáticamente al terminar
pause
