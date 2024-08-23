from SquareGamePlugin import Plugin

game = Plugin()
game.name = "Example plugin"

game.connect("127.0.0.1", 5555)
game.send_chat("Example", "Hello World!")
