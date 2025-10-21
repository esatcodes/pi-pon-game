import pygame
import math
import random
import sys

# Pygame başlatma
pygame.init()

# Ekran boyutları
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tower Defense (TETech Studios)")

# Renkler
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)
RED = (220, 20, 60)
BLUE = (30, 144, 255)
YELLOW = (255, 215, 0)
GRAY = (128, 128, 128)
DARK_GREEN = (0, 100, 0)
PURPLE = (147, 112, 219)
ORANGE = (255, 140, 0)
PATH_COLOR = (139, 69, 19)

# FPS
clock = pygame.time.Clock()
FPS = 60

# Oyun durumları
MENU = 0
PLAYING = 1
WAVE_BREAK = 2
GAME_OVER = 3

# Oyun değişkenleri
game_state = MENU
money = 500
lives = 20
wave = 1
enemies_in_wave = 7  # başlangıçta biraz daha fazla düşman (önerilen değişiklik)
victory = False
countdown_timer = 0
selected_tower = None

# Zorluk (difficulty_screen ile belirlenecek)
difficulty = None  # "easy", "normal", "hard"

# Yol noktaları
path = [
    (50, 100), (200, 100), (200, 300), (400, 300),
    (400, 150), (600, 150), (600, 400), (800, 400),
    (800, 200), (950, 200)
]

# ==================== ZORLUK SEÇİMİ ====================
def difficulty_screen():
    global difficulty
    selecting = True
    font = pygame.font.Font(None, 64)
    small_font = pygame.font.Font(None, 32)

    while selecting:
        clock.tick(FPS)
        screen.fill((25, 25, 25))

        title = font.render("Select Difficulty", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        easy_text = small_font.render("1 - Easy", True, (0, 255, 0))
        normal_text = small_font.render("2 - Normal", True, (255, 255, 0))
        hard_text = small_font.render("3 - Hard", True, (255, 0, 0))

        screen.blit(easy_text, (WIDTH // 2 - easy_text.get_width() // 2, 250))
        screen.blit(normal_text, (WIDTH // 2 - normal_text.get_width() // 2, 300))
        screen.blit(hard_text, (WIDTH // 2 - hard_text.get_width() // 2, 350))

        hint = small_font.render("Press 1 / 2 / 3 to choose. Esc to quit.", True, WHITE)
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 420))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    difficulty = "easy"
                    selecting = False
                elif event.key == pygame.K_2:
                    difficulty = "normal"
                    selecting = False
                elif event.key == pygame.K_3:
                    difficulty = "hard"
                    selecting = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

# ================== PATLAMA ANİMASYONU (Sprite) ==================
class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames = []
        max_r = 36
        # Basit patlama efekti: 6 karelik büyüyen ve saydamlaşan daireler
        for i in range(6):
            size = max_r - i * 5
            surf = pygame.Surface((max_r*2, max_r*2), pygame.SRCALPHA)
            alpha = max(30, 200 - i * 30)
            color = (255, 180 - i*20, 40, alpha)
            pygame.draw.circle(surf, color, (max_r, max_r), size)
            self.frames.append(surf)
        self.index = 0
        self.image = self.frames[self.index]
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.frame_delay = 5
        self.frame_timer = 0

    def update(self):
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.index += 1
            if self.index < len(self.frames):
                self.image = self.frames[self.index]
                self.rect = self.image.get_rect(center=self.rect.center)
            else:
                self.kill()

# Explosion group
explosion_group = pygame.sprite.Group()

# Ses: patlama sesi yükleme (yoksa sessiz devam)
try:
    pygame.mixer.init()
    try:
        explosion_sound = pygame.mixer.Sound("explosion.wav")
        explosion_sound.set_volume(0.45)
    except:
        explosion_sound = None
        # dosya yoksa sessiz devam
except:
    explosion_sound = None

# -------------------- Kule sınıfı --------------------
class Tower:
    def __init__(self, x, y, tower_type):
        self.x = x
        self.y = y
        self.tower_type = tower_type
        self.level = 1
        self.upgrade_cost = 0

        self.update_stats()
        self.fire_cooldown = 0
        self.target = None

    def update_stats(self):
        base_stats = {
            "basic": {
                "range": 120,
                "damage": 10,
                "fire_rate": 30,
                "cost": 100,
                "color": BLUE,
                "upgrade_cost": 80
            },
            "sniper": {
                "range": 200,
                "damage": 50,
                "fire_rate": 90,
                "cost": 250,
                "color": RED,
                "upgrade_cost": 200
            },
            "rapid": {
                "range": 100,
                "damage": 5,
                "fire_rate": 10,
                "cost": 150,
                "color": YELLOW,
                "upgrade_cost": 120
            }
        }

        stats = base_stats[self.tower_type]
        self.range = stats["range"] + (self.level - 1) * 20
        self.damage = stats["damage"] + (self.level - 1) * 5
        self.fire_rate = max(5, stats["fire_rate"] - (self.level - 1) * 3)
        self.cost = stats["cost"]
        self.color = stats["color"]
        self.upgrade_cost = int(stats["upgrade_cost"] * (1.5 ** (self.level - 1)))

    def upgrade(self):
        if self.level < 5:
            self.level += 1
            self.update_stats()
            return True
        return False

    def draw(self, screen):
        size = 15 + (self.level - 1) * 3
        pygame.draw.rect(screen, self.color, (self.x - size, self.y - size, size * 2, size * 2))
        pygame.draw.rect(screen, BLACK, (self.x - size, self.y - size, size * 2, size * 2), 2)

        font = pygame.font.Font(None, 20)
        level_text = font.render(str(self.level), True, WHITE)
        text_rect = level_text.get_rect(center=(self.x, self.y))
        screen.blit(level_text, text_rect)

        if self == selected_tower:
            pygame.draw.circle(screen, self.color, (self.x, self.y), self.range, 2)
            if self.level < 5:
                info_y = self.y - self.range - 30
                upgrade_text = font.render(f"Upgrade: ${self.upgrade_cost}", True, YELLOW)
                screen.blit(upgrade_text, (self.x - 50, info_y))
                stat_text = font.render(f"Lv{self.level+1}: DMG+5 RNG+20", True, WHITE)
                screen.blit(stat_text, (self.x - 60, info_y + 20))

    def is_clicked(self, pos):
        size = 15 + (self.level - 1) * 3
        return (self.x - size <= pos[0] <= self.x + size and 
                self.y - size <= pos[1] <= self.y + size)

    def find_target(self, enemies):
        self.target = None
        min_dist = self.range
        for enemy in enemies:
            dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
            if dist <= self.range:
                if self.target is None or dist < min_dist:
                    self.target = enemy
                    min_dist = dist

    def shoot(self):
        if self.target and self.fire_cooldown <= 0:
            # Doğrudan damage uygulayan basit yaklaşım
            self.target.health -= self.damage
            self.fire_cooldown = self.fire_rate
            return Projectile(self.x, self.y, self.target, self.color)
        return None

    def update(self, enemies):
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        self.find_target(enemies)
        return self.shoot()

# -------------------- Mermi sınıfı --------------------
class Projectile:
    def __init__(self, x, y, target, color):
        self.x = x
        self.y = y
        self.target = target
        self.speed = 10
        self.color = color
        self.active = True

    def update(self):
        if not self.target or self.target.health <= 0:
            self.active = False
            return
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.speed or dist == 0:
            self.active = False
            return
        self.x += (dx / dist) * self.speed
        self.y += (dy / dist) * self.speed

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), 4)

# -------------------- Düşman sınıfı --------------------
class Enemy:
    def __init__(self, wave, enemy_type="normal"):
        self.path = path.copy()
        self.path_index = 0
        self.x = path[0][0]
        self.y = path[0][1]
        self.enemy_type = enemy_type
        self.reached_end = False

        # Temel istatistikler (dalga etkisi)
        if enemy_type == "normal":
            self.speed = 1.2 + (wave * 0.1)
            self.max_health = 70 + (wave * 20)
            self.reward = 15 + (wave * 3)
            self.color = RED
            self.size = 12
        elif enemy_type == "fast":
            self.speed = 2.4 + (wave * 0.14)
            self.max_health = 35 + (wave * 10)
            self.reward = 25 + (wave * 4)
            self.color = YELLOW
            self.size = 10
        elif enemy_type == "tank":
            self.speed = 0.6 + (wave * 0.06)
            self.max_health = 180 + (wave * 45)
            self.reward = 40 + (wave * 8)
            self.color = PURPLE
            self.size = 16
        elif enemy_type == "boss":
            self.speed = 0.9 + (wave * 0.08)
            self.max_health = 700 + (wave * 120)
            self.reward = 150 + (wave * 20)
            self.color = ORANGE
            self.size = 22

        # Zorluk etkisi
        global difficulty
        if difficulty == "easy":
            self.speed *= 0.85
            self.max_health = int(self.max_health * 0.9)
        elif difficulty == "normal":
            self.speed *= 1.0
            self.max_health = int(self.max_health * 1.0)
        elif difficulty == "hard":
            self.speed *= 1.2
            self.max_health = int(self.max_health * 1.35)

        self.health = self.max_health

    def move(self):
        if self.path_index >= len(self.path) - 1:
            self.reached_end = True
            return

        target = self.path[self.path_index + 1]
        dx = target[0] - self.x
        dy = target[1] - self.y
        dist = math.hypot(dx, dy)

        if dist < self.speed:
            self.path_index += 1
            if self.path_index >= len(self.path) - 1:
                self.reached_end = True
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
        # Ek görsel efektler
        if self.enemy_type == "boss":
            pygame.draw.polygon(screen, YELLOW, [
                (self.x - 10, self.y - self.size),
                (self.x - 5, self.y - self.size - 8),
                (self.x, self.y - self.size),
                (self.x + 5, self.y - self.size - 8),
                (self.x + 10, self.y - self.size)
            ])
        if self.enemy_type == "tank":
            pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.size, 2)
            pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.size - 4, 1)
        if self.enemy_type == "fast":
            pygame.draw.line(screen, WHITE, (self.x - 15, self.y), (self.x - 8, self.y), 2)
            pygame.draw.line(screen, WHITE, (self.x - 15, self.y - 5), (self.x - 10, self.y - 5), 2)
            pygame.draw.line(screen, WHITE, (self.x - 15, self.y + 5), (self.x - 10, self.y + 5), 2)

        # Sağlık çubuğu
        bar_width = max(30, self.size * 2)
        bar_height = 5
        health_width = int((self.health / self.max_health) * bar_width)
        pygame.draw.rect(screen, RED, (self.x - bar_width//2, self.y - self.size - 10, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, (self.x - bar_width//2, self.y - self.size - 10, health_width, bar_height))

# -------------------- Buton sınıfı --------------------
class Button:
    def __init__(self, x, y, width, height, text, color, text_color=BLACK):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def draw(self, screen):
        color = tuple(min(c + 30, 255) for c in self.color) if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        font = pygame.font.Font(None, 24)
        text_surf = font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered

# Oyun nesneleri
towers = []
enemies = []
projectiles = []

# Butonlar
tower_buttons = [
    Button(820, 50, 150, 50, "Basic ($100)", BLUE, WHITE),
    Button(820, 120, 150, 50, "Sniper ($250)", RED, WHITE),
    Button(820, 190, 150, 50, "Rapid ($150)", YELLOW, BLACK)
]
wave_button = Button(820, 280, 150, 50, "Next Wave", GREEN, WHITE)
upgrade_button = Button(820, 350, 150, 50, "Upgrade", ORANGE, WHITE)
sell_button = Button(820, 420, 150, 50, "Sell (50%)", RED, WHITE)

selected_tower_type = None
spawn_timer = 0
spawn_delay = 60
enemies_spawned = 0

def draw_path():
    for i in range(len(path) - 1):
        pygame.draw.line(screen, PATH_COLOR, path[i], path[i + 1], 20)
    for point in path:
        pygame.draw.circle(screen, DARK_GREEN, point, 10)

def draw_signature():
    font = pygame.font.Font(None, 24)
    text = font.render("Designed by TETech Studios", True, (0, 200, 255))
    screen.blit(text, (10, HEIGHT - 28))

def draw_ui():
    pygame.draw.rect(screen, GRAY, (800, 0, 200, HEIGHT))
    font = pygame.font.Font(None, 32)
    money_text = font.render(f"Para: ${money}", True, YELLOW)
    lives_text = font.render(f"Can: {lives}", True, RED)
    wave_text = font.render(f"Dalga: {wave}", True, WHITE)
    screen.blit(money_text, (820, 10))
    screen.blit(lives_text, (820, 500))
    screen.blit(wave_text, (820, 540))
    font_small = pygame.font.Font(None, 20)
    preview_text = font_small.render("Sonraki Dalga:", True, WHITE)
    screen.blit(preview_text, (820, 575))

    if wave < 15:
        next_wave = get_enemy_composition(wave + 1)
        enemy_counts = {"normal": 0, "fast": 0, "tank": 0, "boss": 0}
        for e_type in next_wave:
            enemy_counts[e_type] += 1
        y_offset = 595
        if enemy_counts["normal"] > 0:
            pygame.draw.circle(screen, RED, (830, y_offset), 6)
            text = font_small.render(f"x{enemy_counts['normal']}", True, WHITE)
            screen.blit(text, (845, y_offset - 8))
            y_offset += 20
        if enemy_counts["fast"] > 0:
            pygame.draw.circle(screen, YELLOW, (830, y_offset), 5)
            text = font_small.render(f"x{enemy_counts['fast']} Hızlı", True, WHITE)
            screen.blit(text, (845, y_offset - 8))
            y_offset += 20
        if enemy_counts["tank"] > 0:
            pygame.draw.circle(screen, PURPLE, (830, y_offset), 8)
            text = font_small.render(f"x{enemy_counts['tank']} Tank", True, WHITE)
            screen.blit(text, (845, y_offset - 8))
            y_offset += 20
        if enemy_counts["boss"] > 0:
            pygame.draw.circle(screen, ORANGE, (830, y_offset), 10)
            text = font_small.render(f"BOSS!", True, ORANGE)
            screen.blit(text, (845, y_offset - 8))

    for button in tower_buttons:
        button.draw(screen)
    wave_button.draw(screen)

    if selected_tower:
        upgrade_button.draw(screen)
        sell_button.draw(screen)
        font_small = pygame.font.Font(None, 20)
        info_text = font_small.render(f"Level: {selected_tower.level}/5", True, WHITE)
        screen.blit(info_text, (820, 480))
        info_text2 = font_small.render(f"DMG: {selected_tower.damage}", True, WHITE)
        screen.blit(info_text2, (900, 480))

    if selected_tower_type:
        font_small = pygame.font.Font(None, 24)
        text = font_small.render("Kule yerleştir", True, WHITE)
        screen.blit(text, (820, 260))

def draw_menu():
    screen.fill(DARK_GREEN)
    font_big = pygame.font.Font(None, 80)
    title = font_big.render("TOWER DEFENSE", True, YELLOW)
    title_rect = title.get_rect(center=(WIDTH // 2, 150))
    screen.blit(title, title_rect)
    font_med = pygame.font.Font(None, 40)
    subtitle = font_med.render("Kale Savunması", True, WHITE)
    subtitle_rect = subtitle.get_rect(center=(WIDTH // 2, 220))
    screen.blit(subtitle, subtitle_rect)
    start_button = Button(WIDTH // 2 - 100, 300, 200, 60, "BAŞLAT", GREEN, WHITE)
    start_button.draw(screen)
    font_small = pygame.font.Font(None, 26)
    instructions = [
        "Kuleleri yerleştir ve düşmanları durdur!",
        "",
        "• 3 farklı kule tipi (Basic, Sniper, Rapid)",
        "• Kuleleri upgrade et (Level 5'e kadar)",
        "• 4 farklı düşman tipi:",
        "  Normal (Kırmızı) - Dengeli",
        "  Hızlı (Sarı) - Çevik ama zayıf",
        "  Tank (Mor) - Yavaş ama güçlü",
        "  BOSS (Turuncu) - Her 5 dalgada!",
        "• 15 dalgayı tamamla ve kazan!",
    ]
    y = 390
    for instruction in instructions:
        text = font_small.render(instruction, True, WHITE)
        text_rect = text.get_rect(center=(WIDTH // 2, y))
        screen.blit(text, text_rect)
        y += 28
    return start_button

def draw_wave_break(time_left):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(150)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))
    font = pygame.font.Font(None, 72)
    text = font.render(f"Dalga {wave}", True, YELLOW)
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(text, text_rect)
    font_med = pygame.font.Font(None, 48)
    countdown = font_med.render(f"{time_left} saniye...", True, WHITE)
    countdown_rect = countdown.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
    screen.blit(countdown, countdown_rect)
    font_small = pygame.font.Font(None, 36)
    tip = font_small.render("Kulelerini hazırla!", True, GREEN)
    tip_rect = tip.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80))
    screen.blit(tip, tip_rect)

def draw_game_over():
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(200)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))
    font = pygame.font.Font(None, 72)
    if victory:
        text = font.render("KAZANDIN!", True, GREEN)
    else:
        text = font.render("OYUN BİTTİ!", True, RED)
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(text, text_rect)
    font_small = pygame.font.Font(None, 36)
    score_text = font_small.render(f"Dalga: {wave}  Para: ${money}", True, WHITE)
    score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
    screen.blit(score_text, score_rect)
    restart_text = font_small.render("R - Yeniden Başlat", True, YELLOW)
    restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 70))
    screen.blit(restart_text, restart_rect)

def spawn_wave():
    global enemies_spawned, spawn_timer
    enemies_spawned = 0
    spawn_timer = 0

def get_enemy_composition(wave):
    enemies_list = []
    if wave % 5 == 0:
        enemies_list.append("boss")
    if wave >= 3:
        fast_count = min(wave - 2, 5)
        enemies_list.extend(["fast"] * fast_count)
    if wave >= 5:
        tank_count = min((wave - 4) // 2, 4)
        enemies_list.extend(["tank"] * tank_count)
    normal_count = enemies_in_wave - len(enemies_list)
    enemies_list.extend(["normal"] * max(0, normal_count))
    random.shuffle(enemies_list)
    return enemies_list

current_wave_enemies = []

def reset_game():
    global money, lives, wave, enemies_in_wave, victory, game_state
    global towers, enemies, projectiles, enemies_spawned, selected_tower_type, selected_tower, countdown_timer
    money = 500
    lives = 20
    wave = 1
    enemies_in_wave = 7
    victory = False
    game_state = MENU
    towers = []
    enemies = []
    projectiles = []
    enemies_spawned = 0
    selected_tower_type = None
    selected_tower = None
    countdown_timer = 0

# Ana oyun döngüsü
running = True
start_button = None

# İlk olarak zorluk seçimini göster
difficulty_screen()

while running:
    clock.tick(FPS)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == MENU:
                if start_button and start_button.is_clicked(mouse_pos):
                    game_state = WAVE_BREAK
                    countdown_timer = 3 * FPS  # 3 saniye
            elif game_state == PLAYING:
                if selected_tower:
                    if upgrade_button.is_clicked(mouse_pos):
                        if selected_tower.level < 5 and money >= selected_tower.upgrade_cost:
                            money -= selected_tower.upgrade_cost
                            selected_tower.upgrade()
                        continue
                    if sell_button.is_clicked(mouse_pos):
                        sell_value = selected_tower.cost // 2
                        money += sell_value
                        towers.remove(selected_tower)
                        selected_tower = None
                        continue
                clicked_tower_button = False
                for i, button in enumerate(tower_buttons):
                    if button.is_clicked(mouse_pos):
                        tower_types = ["basic", "sniper", "rapid"]
                        costs = [100, 250, 150]
                        if money >= costs[i]:
                            selected_tower_type = tower_types[i]
                            selected_tower = None
                        clicked_tower_button = True
                        break
                if clicked_tower_button:
                    continue
                clicked_tower = None
                for tower in towers:
                    if tower.is_clicked(mouse_pos):
                        clicked_tower = tower
                        break
                if clicked_tower:
                    selected_tower = clicked_tower
                    selected_tower_type = None
                else:
                    if selected_tower_type and mouse_pos[0] < 780:
                        tower_costs = {"basic": 100, "sniper": 250, "rapid": 150}
                        cost = tower_costs[selected_tower_type]
                        if money >= cost:
                            can_place = True
                            for point in path:
                                if math.hypot(mouse_pos[0] - point[0], mouse_pos[1] - point[1]) < 40:
                                    can_place = False
                            for tower in towers:
                                if math.hypot(mouse_pos[0] - tower.x, mouse_pos[1] - tower.y) < 40:
                                    can_place = False
                            if can_place:
                                towers.append(Tower(mouse_pos[0], mouse_pos[1], selected_tower_type))
                                money -= cost
                                selected_tower_type = None
                    else:
                        if mouse_pos[0] < 780:
                            selected_tower = None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and game_state == GAME_OVER:
                reset_game()

    # Oyun mantığı
    if game_state == WAVE_BREAK:
        countdown_timer -= 1
        if countdown_timer <= 0:
            game_state = PLAYING
            current_wave_enemies = get_enemy_composition(wave)
            spawn_wave()

    elif game_state == PLAYING:
        # Düşman spawn
        if enemies_spawned < enemies_in_wave and spawn_timer <= 0:
            if enemies_spawned < len(current_wave_enemies):
                enemy_type = current_wave_enemies[enemies_spawned]
                enemies.append(Enemy(wave, enemy_type))
            else:
                enemies.append(Enemy(wave, "normal"))
            enemies_spawned += 1
            spawn_timer = spawn_delay
        spawn_timer -= 1

        # Düşmanları güncelle
        for enemy in enemies[:]:
            enemy.move()
            if enemy.health <= 0:
                # Patlama animasyonu oluştur
                explosion = Explosion(enemy.x, enemy.y)
                explosion_group.add(explosion)
                try:
                    if explosion_sound:
                        explosion_sound.play()
                except:
                    pass
                try:
                    enemies.remove(enemy)
                except ValueError:
                    pass
                money += enemy.reward
            elif enemy.reached_end:
                try:
                    enemies.remove(enemy)
                except ValueError:
                    pass
                lives -= 1
                if lives <= 0:
                    game_state = GAME_OVER

        # Kuleleri güncelle
        for tower in towers:
            projectile = tower.update(enemies)
            if projectile:
                projectiles.append(projectile)

        # Mermileri güncelle
        for proj in projectiles[:]:
            proj.update()
            if not proj.active:
                projectiles.remove(proj)

        # Dalga tamamlandı mı?
        if len(enemies) == 0 and enemies_spawned >= enemies_in_wave:
            if wave >= 15:
                game_state = GAME_OVER
                victory = True
            else:
                wave += 1
                enemies_in_wave += 3
                game_state = WAVE_BREAK
                countdown_timer = 3 * FPS

    # Çizim
    if game_state == MENU:
        start_button = draw_menu()
    else:
        screen.fill(GREEN)
        draw_path()
        for tower in towers:
            tower.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)
        for proj in projectiles:
            proj.draw(screen)

        # animasyonları güncelle ve çiz
        explosion_group.update()
        explosion_group.draw(screen)

        draw_ui()

        if selected_tower_type and mouse_pos[0] < 780:
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, 15, 2)

        for button in tower_buttons + [wave_button]:
            button.is_clicked(mouse_pos)

        if selected_tower:
            upgrade_button.is_clicked(mouse_pos)
            sell_button.is_clicked(mouse_pos)

        if game_state == WAVE_BREAK:
            draw_wave_break(countdown_timer // FPS + 1)
        elif game_state == GAME_OVER:
            draw_game_over()

        # Signature her kare çizilir
        draw_signature()

    pygame.display.flip()

pygame.quit()
