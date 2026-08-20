import pygame
import pymunk
import math
import random
import time

WIDTH, HEIGHT = 700, 400
ARENA_W, ARENA_H = 400, 300

pygame.init()
pygame.display.set_caption("ILUM Ball")
pygame.mixer.init()
pygame.mixer.music.load("hino.mp3")
pygame.mixer.music.set_volume(0.5)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 18)
big_font = pygame.font.SysFont("Arial", 40)

hit_sound = pygame.mixer.Sound("sword_slice.mp3")
# start_sound = pygame.mixer.Sound("sam.wav")

weapon_img = pygame.image.load("sword.png").convert_alpha()
weapon_img = pygame.transform.scale(weapon_img, (50, 50))

gamora_img = pygame.image.load("gamora.jpg").convert()
gamora_img = pygame.transform.scale(gamora_img, (WIDTH, HEIGHT))

smurf_img = pygame.image.load("smurfete.jpg").convert()
smurf_img = pygame.transform.scale(smurf_img, (WIDTH, HEIGHT))

paused = False

# ============================================================
# EFFECTS
# ============================================================

class Effect:
    def __init__(self, duration):
        self.duration = duration

    def start(self, ball):
        pass

    def update(self, ball, dt):
        self.duration -= dt

    def end(self, ball):
        pass

    def is_finished(self):
        return self.duration <= 0


class SpeedBoost(Effect):
    def __init__(self, duration, multiplier):
        super().__init__(duration)
        self.multiplier = multiplier
        self.original_multiplier = None

    def start(self, ball):
        self.original_multiplier = ball.speed_multiplier
        ball.speed_multiplier *= self.multiplier

    def end(self, ball):
        ball.speed_multiplier /= self.multiplier

class RotationBoost(Effect):
    def __init__(self, duration, multiplier):
        super().__init__(duration)
        self.multiplier = multiplier
        self.original_rotation = None

    def start(self, ball):
        self.original_rotation = ball.omega
        ball.omega *= self.multiplier

    def end(self, ball):
        ball.omega /= self.multiplier


class DamageBoost(Effect):
    def __init__(self, duration, multiplier):
        super().__init__(duration)
        self.multiplier = multiplier
        self.original_multiplier = None

    def start(self, ball):
        self.original_multiplier = ball.damage_multiplier
        ball.damage_multiplier *= self.multiplier

    def end(self, ball):
        ball.damage_multiplier /= self.multiplier


class Shield(Effect):
    def __init__(self, duration):
        super().__init__(duration)

    def start(self, ball):
        ball.invulnerable = True

    def end(self, ball):
        ball.invulnerable = False

# ============================================================
# ABILITIES
# ============================================================

class Ability:
    def activate(self, ball):
        pass


class Heal(Ability):
    def __init__(self, amount=20):
        self.amount = amount

    def activate(self, ball):
        ball.hp = min(ball.max_hp, ball.hp + self.amount)
        # Debug print
        print(f"{ball.nome} curou {self.amount} HP")


class SpeedAbility(Ability):
    def __init__(self, duration=3, multiplier=1.5):
        self.duration = duration
        self.multiplier = multiplier

    def activate(self, ball):
        ball.add_effect(SpeedBoost(self.duration, self.multiplier))
        ball.add_effect(RotationBoost(self.duration, self.multiplier))
        # Debug print
        print(f"{ball.nome} acelerou em {self.multiplier} vezes")


class Berserk(Ability):
    def __init__(self, duration=5, multiplier=2):
        self.duration = duration
        self.multiplier = multiplier

    def activate(self, ball):
        ball.add_effect(DamageBoost(self.duration, self.multiplier))
        # Debug print
        print(f"{ball.nome} aumentou o dano em {self.multiplier} vezes")


class ShieldAbility(Ability):
    def __init__(self, duration=3):
        self.duration = duration

    def activate(self, ball):
        ball.add_effect(Shield(self.duration))
        # Debug print
        print(f"{ball.nome} está invulnerável")

# ============================================================
# WEAPONS
# ============================================================

class Weapon:
    def __init__(self, image, length=40, thickness=3, damage=5, knockback=1, elasticity=1):
        self.image = image
        self.length = length
        self.thickness = thickness
        self.damage = damage
        self.knockback = knockback
        self.elasticity = elasticity

    def create_shape(self, body, radius):
        shape = pymunk.Segment(
            body,
            (radius, 0),
            (radius + self.length, 0),
            self.thickness
        )

        shape.elasticity = self.elasticity
        shape.collision_type = 2
        shape.sensor = True

        return shape

    def get_damage(self, attacker):
        return self.damage * attacker.damage_multiplier

    def get_knockback(self, attacker):
        return self.knockback


class Sword(Weapon):
    def __init__(self, image):
        super().__init__(
            image=image,
            length=40,
            thickness=3,
            damage=5,
            knockback=1,
            elasticity=1
        )


class Hammer(Weapon):
    def __init__(self, image):
        super().__init__(
            image=image,
            length=35,
            thickness=6,
            damage=15,
            knockback=3,
            elasticity=1
        )


class Spear(Weapon):
    def __init__(self, image):
        super().__init__(
            image=image,
            length=65,
            thickness=2,
            damage=8,
            knockback=0.5,
            elasticity=1
        )

# ============================================================
# BALL
# ============================================================

class Ball:
    def __init__(self, nome, space, x, y, color, image, mass, weapon, abilities=None, vel_base = 250):

        # Caracteristicas físicas
        self.radius = 15
        self.mass = mass
        self.color = color
        self.nome = nome

        # Status base
        self.knockback = 1
        self.vel_base = vel_base

        self.max_hp = 100
        self.hp = self.max_hp
        self.hits = 0

        self.speed_multiplier = 1
        self.damage_multiplier = 1
        self.invulnerable = False

        # Armas e Habilidades
        self.weapon = weapon
        self.abilities = abilities if abilities is not None else []
        self.effects = []

        # Física
        self.body = pymunk.Body(self.mass, pymunk.moment_for_circle(self.mass, 0, self.radius))

        self.body.position = x, y

        random_velocity(self.body, 250)

        self.shape = pymunk.Circle(self.body, self.radius)
        self.shape.elasticity = 1
        self.shape.friction = 0
        self.shape.collision_type = 1

        self.weapon_shape = self.weapon.create_shape(
                    self.body,
                    self.radius
                )
        
        # self.weapon_length = 40
        # self.weapon_shape = pymunk.Segment(
        #     self.body,
        #     (self.radius, 0),
        #     (self.radius + self.weapon_length, 0),
        #     3
        # )
        # self.weapon_shape.elasticity = 1
        # self.weapon_shape.collision_type = 2
        # self.weapon_shape.sensor = True

        space.add(self.body, self.shape, self.weapon_shape)

        # Rotação
        self.angle = 0
        self.omega = random.uniform(3, 5)

        weapon_image = pygame.transform.scale(self.weapon.image, [self.weapon.length]*2)
        self.original_image = pygame.transform.rotate(weapon_image, 180)
        self.image = image

        self.last_hit_time = 0

        # Debug Vectors
        self.i_args = False
        self.v_args = False

    # --------------------------------------------------------
    # Stats / combat
    # --------------------------------------------------------

    def damage(self):
        return self.weapon.get_damage(self) + self.hits

    def get_knockback(self):
        return self.weapon.get_knockback(self)

    def take_damage(self, amount):
        if not self.invulnerable:
            self.hp -= amount

    # --------------------------------------------------------
    # Abilities
    # --------------------------------------------------------

    def use_ability(self, index):
        if 0 <= index < len(self.abilities):
            self.abilities[index].activate(self)


    # --------------------------------------------------------
    # Effects
    # --------------------------------------------------------

    def add_effect(self, effect):
        effect.start(self)
        self.effects.append(effect)

    def update_effects(self, dt):
        finished = []

        for effect in self.effects:
            effect.update(self, dt)

            if effect.is_finished():
                effect.end(self)
                finished.append(effect)

        for effect in finished:
            self.effects.remove(effect)

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def update(self):
        self.angle += self.omega * dt
        self.body.angle = self.angle

        self.update_effects(dt)

        v_min = 50

        def damping(velocidade):
            if velocidade > self.vel_base * self.speed_multiplier:
                return 1 - ((velocidade-self.vel_base * self.speed_multiplier)**2)/4900000
            else:
                return 1 + ((velocidade-self.vel_base * self.speed_multiplier)**2)/4900000

        d = damping(self.body.velocity.length)

        if self.body.velocity.length > 0:
            self.body.velocity = (self.body.velocity.normalized() * self.body.velocity.length * d)

        if self.body.velocity.length < v_min:
            if self.body.velocity.length > 0:
                self.body.velocity = (self.body.velocity.normalized() * v_min)
            else:
                self.body.velocity = (v_min, 0)

    # --------------------------------------------------------
    # Drawing
    # --------------------------------------------------------

    def draw(self, screen):
        x, y = self.body.position

        pygame.draw.circle(screen, self.color, (int(x), int(y)), self.radius)

        pos_x = x + math.cos(self.angle) * (self.radius + self.weapon.length/2)
        pos_y = y + math.sin(self.angle) * (self.radius + self.weapon.length/2)

        image = pygame.transform.rotate(self.original_image, 90 - math.degrees(self.angle))

        rect = image.get_rect(center=(pos_x, pos_y))
        screen.blit(image, rect.topleft)

        # Debug Vector
        # if self.i_args:
        #     pygame.draw.line(*self.i_args)

        # if self.v_args:
        #     pygame.draw.line(*self.v_args)

        # v_args = [screen, (0, 255, 0), self.body.position, self.body.position+self.body.velocity, 3]
        # pygame.draw.line(*v_args)

        # Debug Hurtbox
        # a = self.weapon_shape.a.rotated(self.body.angle) + self.body.position
        # b = self.weapon_shape.b.rotated(self.body.angle) + self.body.position
        # pygame.draw.line(screen, (255, 0, 0), a, b)

# ============================================================
# ARENA
# ============================================================


def create_walls(space):
    static = space.static_body
    walls = [
        pymunk.Segment(static, (0,0), (ARENA_W,0), 8),
        pymunk.Segment(static, (0,ARENA_H), (ARENA_W,ARENA_H), 8),
        pymunk.Segment(static, (0,0), (0,ARENA_H), 8),
        pymunk.Segment(static, (ARENA_W,0), (ARENA_W,ARENA_H), 8),
    ]
    for w in walls:
        w.elasticity = 1
        w.friction = 0
    space.add(*walls)
    return walls

def draw_walls(screen, walls):
    for w in walls:
        pygame.draw.line(screen, (255,255,255), w.a, w.b, int(w.radius*2))

# ============================================================
# COMBAT
# ============================================================

def calcular_impulso(arbiter, atacante, alvo, knockback):
    c1 = alvo.body.position
    c2 = atacante.body.position

    r_module = alvo.radius

    contato = next(iter(arbiter.contact_point_set.points))
    ponto = contato.point_b

    r_vector = (c1[0]-ponto.x, c1[1]-ponto.y)
    d_vector = (ponto.x-c2[0], ponto.y-c2[1])

    r_norm = (r_vector[0]/r_module, r_vector[1]/r_module)
    d_module = (d_vector[0]**2 + d_vector[1]**2)**0.5

    omega = atacante.omega

    i_vector = (abs(d_module*knockback*omega)*r_norm[0], 
                abs(d_module*knockback*omega)*r_norm[1])

    inicio = ponto
    fim = (ponto.x + i_vector[0], ponto.y + i_vector[1])

    i_args = [screen, (255, 0, 0), inicio, fim, 3]

    return i_vector, i_args

def calcular_reflexao(arbiter, atacante, alvo):
    contato = next(iter(arbiter.contact_point_set.points))
    ponto = contato.point_b

    r = ponto - atacante.body.position

    normal = (alvo.body.position - ponto).normalized()

    v_espada = pymunk.Vec2d(
        -r.y,
        r.x
    ) * atacante.omega

    v_rel = alvo.body.velocity - 0.5*v_espada

    v_normal = v_rel.dot(normal)

    v_rel = v_rel - 2 * v_normal * normal

    v_refletida = (v_rel + v_espada)

    inicio = ponto
    fim = (ponto.x + v_refletida[0], ponto.y + v_refletida[1]    )

    v_args = [screen, (0, 0, 255), inicio, fim, 3]

    return v_refletida, v_args

def setup_collision(space, azul, verde):

    def collide(arbiter, space, data):
        global paused

        s1, s2 = arbiter.shapes
        now = time.time()

        attacker = None
        target = None
        weapon1 = None
        weapon2 = None

        # Define quem atacou e quem apanhou
        for ball in balls:
            if s1 == ball.weapon_shape:
                attacker = ball
                weapon1 = ball
            if s2 == ball.weapon_shape:
                attacker = ball
                weapon2 = ball

            if s1 == ball.shape:
                target = ball
            elif s2 == ball.shape:
                target = ball

        # Espada ataca bola
        if attacker is not None and target is not None:
            if attacker is target:
                return True

            if now - attacker.last_hit_time <= 0.1:
                return True

            attacker.last_hit_time = now

            # Damage
            target.take_damage(attacker.damage())
            attacker.hits += 1

            # Impulse
            impulse, target.i_args = calcular_impulso(arbiter, attacker, target, attacker.get_knockback())

            # Reflection
            reflection, target.v_args = calcular_reflexao(arbiter, attacker, target)

            target.body.velocity = reflection

            # Weapon reaction
            attacker.omega = -attacker.omega

            hit_sound.play()

            target.body.apply_impulse_at_local_point(impulse)

            # Debug pause
            # paused = True

            return True

        # Briga de espadas (🏳️‍🌈?)
        if weapon1 is not None and weapon2 is not None:
            if now - weapon1.last_hit_time <= 0.1:
                return True

            if now - weapon2.last_hit_time <= 0.1:
                return True

            weapon1.last_hit_time = now
            weapon2.last_hit_time = now

            weapon1.omega = -weapon1.omega
            weapon2.omega = -weapon2.omega

            hit_sound.play()

            return True

        return True


    space.on_collision(2, 1, begin=collide)
    space.on_collision(2, 2, begin=collide)


# ============================================================
# GAME
# ============================================================

def random_velocity(body, base_speed = 250):
    angle = random.uniform(0, 2*math.pi)
    body.velocity = (math.cos(angle)*base_speed, math.sin(angle)*base_speed)

def draw_hud(balls):
    x = ARENA_W + 10

    elapsed_time = time.time() - game_start_time

    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)

    timer_text = font.render(
        f"{minutes:02d}:{seconds:02d}",
        True,
        (255, 255, 255)
    )

    screen.blit(timer_text, (x, 50))

    for i, ball in enumerate(balls):
        y = 100 + i * 100

        screen.blit(font.render(f"Bola {ball.nome} HP: {ball.hp:.0f}", True, (255, 255, 255)), (x, y))

        velocity = ball.body.velocity.length

        screen.blit(font.render(f"Bola {ball.nome} VEL: {velocity:.2f}", True, (255, 255, 255)), (x, y + 40))



def new_game():
    global game_start_time

    space = pymunk.Space()
    space.gravity = (0,0)
    space.damping = 1
    space.iterations = 30

    walls = create_walls(space)

    # --------------------------------------------------------
    # Weapons
    # --------------------------------------------------------

    sword = Sword(weapon_img)
    sword2 = Sword(weapon_img)

    # Example:
    # hammer = Hammer(weapon_img)
    # spear = Spear(weapon_img)

    # --------------------------------------------------------
    # Abilities
    # --------------------------------------------------------

    azul_abilities = [
        Heal(20),
        SpeedAbility(3, 1.5)
    ]

    verde_abilities = [
        Berserk(5, 2),
        ShieldAbility(3)
    ]

    # --------------------------------------------------------
    # Balls
    # --------------------------------------------------------

    azul = Ball("Azul", space, 120, 150, (0, 0, 255), weapon_img, 1, sword, azul_abilities)

    verde = Ball("Verde", space, 280, 150, (0, 255, 0), weapon_img, 1, sword2, verde_abilities)

    balls = [
        azul,
        verde
    ]

    # def damage(self):
    #     return 15 - self.hits

    # verde.damage = damage.__get__(verde)

    setup_collision(space, azul, verde)

    game_start_time = time.time()

    return space, walls, balls, game_start_time


space, walls, balls, game_start_time = new_game()

azul = balls[0]
verde = balls[1]

state = "menu"
start_button = pygame.Rect(450, 150, 180, 60)

paused = False

running = True
while running:
    dt = 1/60

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if state == "menu" and start_button.collidepoint(event.pos):
                state = "intro"
                # start_sound.play()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = False
            if event.key == pygame.K_p:
                paused = True

            # Test abilities
            if event.key == pygame.K_1:
                azul.use_ability(0)

            if event.key == pygame.K_2:
                azul.use_ability(1)

            if event.key == pygame.K_3:
                verde.use_ability(0)

            if event.key == pygame.K_4:
                verde.use_ability(1)

    screen.fill((30,30,30))

    if state == "menu":
        screen.blit(big_font.render("ILUM Ball", True, (255,255,255)), (420, 80))
        pygame.draw.rect(screen, (160, 32, 240), start_button)
        screen.blit(font.render("START", True, (0,0,0)), (500, 165))

    elif state == "intro":
        text = big_font.render("SWORD VS SWORD", True, (255,255,255))
        screen.blit(text, (200, 150))

        if not pygame.mixer.get_busy():
            pygame.mixer.music.play(-1)
            state = "game"

    elif state == "game":
        if not paused:
            azul.update()
            verde.update()

            space.step(dt)

        draw_walls(screen, walls)

        for ball in balls:
            ball.draw(screen)

        draw_hud(balls)

        if paused:
            pause_text = font.render("PAUSADO - ESPAÇO PARA CONTINUAR", True, (255,255,255))
            screen.blit(pause_text, (ARENA_W + 10, 300))

        if azul.hp <= 0 or verde.hp <= 0:
            state = "game_over"

    elif state == "game_over":

        if verde.hp <= 0:
            screen.blit(smurf_img, (0, 0))
        else:
            screen.blit(gamora_img, (0, 0))

        text = big_font.render("VENCEU", True, (255,255,255))
        screen.blit(text, (250, 30))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()