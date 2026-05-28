port=/dev/ttyUSB0
fqbn=arduino:avr:uno
cc=arduino-cli compile -v --warnings all -b $(fqbn)

upload:
	$(cc) -u -p $(port)
	
