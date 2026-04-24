import re

from src.generation.core.game_state import GameState
from src.generation.picture_generate import picture_generate

str = """
import arcade
import random
import math
import time
from PIL import Image, ImageDraw
from menu import *
from camera import *
from asset_manager import *

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Ball Bounce Challenge"
GRID_SIZE = 32
GRID_WIDTH = SCREEN_WIDTH // GRID_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // GRID_SIZE
BALL_RADIUS = 16
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 15
WALL_THICKNESS = 20
MAX_BALLS = 5
BALL_SPEED = 5
PADDLE_SPEED = 8
FRICTION = 0.99

# --- Game States ---
START = 0
PLAYING = 1
GAME_OVER = 2

# --- UI Colors ---
UI_BG_COLOR = arcade.color.DARK_BLUE_GRAY
UI_TEXT_COLOR = arcade.color.WHITE

# --- Helper Functions ---
def create_texture(name, size, color, shape="rect"):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if shape == "rect":
        draw.rectangle((0, 0, size, size), fill=color)
    elif shape == "circle":
        draw.ellipse((0, 0, size, size), fill=color)
    return arcade.Texture(f"{name}_{random.randint(0, 10000)}", img)

def screen_to_grid(x, y):
    grid_x = int(x // GRID_SIZE)
    grid_y = int(y // GRID_SIZE)
    return grid_x, grid_y

def grid_to_screen(grid_x, grid_y):
    x = grid_x * GRID_SIZE
    y = grid_y * GRID_SIZE
    return x, y

# --- Particle System ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.uniform(2, 5)
        self.lifetime = random.uniform(0.5, 1.5)
        self.age = 0
        self.dx = random.uniform(-1, 1)
        self.dy = random.uniform(-1, 1)

    def update(self, delta_time):
        self.age += delta_time
        self.x += self.dx
        self.y += self.dy
        self.size *= 0.95

    def draw(self):
        if self.age < self.lifetime:
            arcade.draw_rectangle_filled(
                self.x, self.y,
                self.size, self.size,
                self.color
            )

class ParticleManager:
    def __init__(self):
        self.particles = []

    def add_particles(self, x, y, color, count=10):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def update(self, delta_time):
        for particle in self.particles[:]:
            particle.update(delta_time)
            if particle.age >= particle.lifetime:
                self.particles.remove(particle)

    def draw(self):
        for particle in self.particles:
            particle.draw()

# --- Game Objects ---
class Ball(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.texture = AssetManager.get_texture('ball', fallback_color=arcade.color.RED, width=BALL_RADIUS*2, height=BALL_RADIUS*2)
        # DESCRIPTION: a bright red circular ball with a white highlight
        self.center_x = x
        self.center_y = y
        self.radius = BALL_RADIUS
        self.change_x = random.uniform(-BALL_SPEED, BALL_SPEED)
        self.change_y = random.uniform(-BALL_SPEED, BALL_SPEED)
        self.color = arcade.color.RED

    def update(self):
        # Movement with friction
        self.center_x += self.change_x
        self.center_y += self.change_y
        self.change_x *= FRICTION
        self.change_y *= FRICTION

        # Wall bouncing
        if self.center_x < self.radius + WALL_THICKNESS:
            self.center_x = self.radius + WALL_THICKNESS
            self.change_x *= -1
        elif self.center_x > SCREEN_WIDTH - self.radius - WALL_THICKNESS:
            self.center_x = SCREEN_WIDTH - self.radius - WALL_THICKNESS
            self.change_x *= -1

        if self.center_y < self.radius + WALL_THICKNESS:
            self.center_y = self.radius + WALL_THICKNESS
            self.change_y *= -1
        elif self.center_y > SCREEN_HEIGHT - self.radius - WALL_THICKNESS:
            self.center_y = SCREEN_HEIGHT - self.radius - WALL_THICKNESS
            self.change_y *= -1

class Paddle(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture = AssetManager.get_texture('paddle', fallback_color=arcade.color.BLUE, width=PADDLE_WIDTH, height=PADDLE_HEIGHT)
        # DESCRIPTION: a blue rectangular paddle with rounded edges
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = GRID_SIZE * 2
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.speed = PADDLE_SPEED
        self.change_x = 0

    def update(self):
        self.center_x += self.change_x
        if self.center_x < self.w
"""
constants = dict(re.findall(r"([A-Z_][A-Z0-9_]*)\s*=\s*(.+)", str))
safe_env = {}
for name, expr in constants.items():
    try:
        safe_env[name] = eval(expr, {"__builtins__": None}, safe_env)
    except:
        pass

pattern = r"get_texture\(\s*'([^']+)'.*?width\s*=\s*([^,\s)]+).*?height\s*=\s*([^\s,)]+)\s*\)[\s\S]*?#\s*DESCRIPTION:\s*([^\n]+)"
matches = re.findall(pattern, str, re.DOTALL)
print(matches)
print(1)
for match in matches:
    if len(match) != 4: continue
    name, width, height, description = match
    try:
        width = eval(width, {"__builtins__": None}, safe_env)
    except:
        width = int(width)

    try:
        height = eval(height, {"__builtins__": None}, safe_env)
    except:
        height = int(height)
    size = [int(width), int(height)]
    picture_generate(name, description, size)    
        
