port=/dev/ttyUSB0
fqbn=arduino:avr:uno
cc=arduino-cli compile -v --warnings all -b $(fqbn)

upload:
	$(cc) -u -p $(port)
	

dependencies:
	arduino-cli core install arduino:avr
	arduino-cli lib install "Adafruit NeoPixel"
