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

class Ball:
    def __init__(self, space, x, y, color, image, mass):
        self.radius = 15
        self.mass = mass

        self.body = pymunk.Body(1, pymunk.moment_for_circle(self.mass, 0, self.radius))
        self.body.position = x, y
        vel_x_inicial = random.uniform(0, 10) * 15
        vel_y_inicial = (150**2 - (vel_x_inicial**2))**0.5
        self.body.velocity = random.choice([-1, 1]) * vel_x_inicial, random.choice([-1, 1]) * vel_y_inicial

        self.shape = pymunk.Circle(self.body, self.radius)
        self.shape.elasticity = 1
        self.shape.friction = 0
        self.shape.collision_type = 1

        self.weapon_length = 40
        self.weapon_shape = pymunk.Segment(
            self.body,
            (self.radius, 0),
            (self.radius + self.weapon_length, 0),
            3
        )
        self.weapon_shape.elasticity = 1
        self.weapon_shape.collision_type = 2
        self.weapon_shape.sensor = True

        space.add(self.body, self.shape, self.weapon_shape)

        self.hp = 100
        self.hits = 0
        self.color = color

        self.angle = 0
        self.omega = random.uniform(3, 5)

        self.original_image = pygame.transform.rotate(image, 180)
        self.image = image

        self.last_hit_time = 0

        # PROVISÓRIO
        self.i_args = False
        self.v_args = False

    def update(self):
        self.angle += self.omega * (1/60)
        self.body.angle = self.angle
        v_min = 50

        def damping(velocidade):
            if velocidade > 250:
                return 1 - ((velocidade-250)**2)/4900000
            else:
                return 1 + ((velocidade-250)**2)/4900000

        d = damping(self.body.velocity.length)
        self.body.velocity = self.body.velocity.length * self.body.velocity.normalized() * d

        if self.body.velocity.length < v_min:
            if self.body.velocity.length > 0:
                self.body.velocity = self.body.velocity.normalized() * v_min
            else:
                self.body.velocity = (v_min, 0)

    def damage(self):
        return 5 + self.hits

    def draw(self, screen):
        x, y = self.body.position

        pygame.draw.circle(screen, self.color, (int(x), int(y)), self.radius)

        pos_x = x + math.cos(self.angle) * (self.radius + self.weapon_length/2)
        pos_y = y + math.sin(self.angle) * (self.radius + self.weapon_length/2)

        image = pygame.transform.rotate(
            self.original_image,
            90 - math.degrees(self.angle)
        )

        rect = image.get_rect(center=(pos_x, pos_y))
        screen.blit(image, rect.topleft)

        # # PROVISÓRIO
        # if self.i_args:
        #     pygame.draw.line(*self.i_args)

        # if self.v_args:
        #     pygame.draw.line(*self.v_args)

        # v_args = [screen, (0, 255, 0), self.body.position, self.body.position+self.body.velocity, 3]
        # pygame.draw.line(*v_args)

        # #PROVISÓRIO
        # a = self.weapon_shape.a.rotated(self.body.angle) + self.body.position
        # b = self.weapon_shape.b.rotated(self.body.angle) + self.body.position
        # pygame.draw.line(screen, (255, 0, 0), a, b)


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

def setup_collision(space, azul, verde):
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

        # Vetor do centro do atacante até o ponto de contato
        r = ponto - atacante.body.position

        # Normal da superfície da espada, apontando para dentro do alvo
        normal = (alvo.body.position - ponto).normalized()

        # Velocidade da espada no ponto de contato
        v_espada = pymunk.Vec2d(
            -r.y,
            r.x
        ) * atacante.omega

        # Velocidade da bola no referencial da espada
        v_rel = alvo.body.velocity - 0.5*v_espada

        # Componente normal da velocidade relativa
        v_normal = v_rel.dot(normal)

        v_rel = v_rel - 2 * v_normal * normal

        # Voltamos para o referencial do mundo
        v_refletida = (v_rel + v_espada)

        inicio = ponto
        fim = (
            ponto.x + v_refletida[0],
            ponto.y + v_refletida[1]
        )

        v_args = [screen, (0, 0, 255), inicio, fim, 3]

        return v_refletida, v_args

    def collide(arbiter, space, data):
        global paused

        s1, s2 = arbiter.shapes
        now = time.time()

        # azul acerta verde
        if (s1 == azul.weapon_shape and s2 == verde.shape) or \
           (s2 == azul.weapon_shape and s1 == verde.shape):

            if now - azul.last_hit_time > 0.1:
                verde.hp -= azul.damage()
                azul.hits += 1
                azul.last_hit_time = now

                # impulso, verde.i_args = calcular_impulso(arbiter, azul, verde, 0.5)
                reflexao, verde.v_args = calcular_reflexao(arbiter, azul, verde)
                verde.body.velocity = reflexao

                azul.omega = -azul.omega
                hit_sound.play()

                # verde.body.apply_impulse_at_local_point(impulso)

                # paused = True

        # verde acerta azul
        elif (s1 == verde.weapon_shape and s2 == azul.shape) or \
             (s2 == verde.weapon_shape and s1 == azul.shape):

            if now - verde.last_hit_time > 0.1:
                azul.hp -= verde.damage()
                verde.hits += 1
                verde.last_hit_time = now

                impulso, azul.i_args = calcular_impulso(arbiter, verde, azul, 1)
                reflexao, azul.v_args = calcular_reflexao(arbiter, verde, azul)
                azul.body.velocity = reflexao

                verde.omega = -verde.omega
                hit_sound.play()

                azul.body.apply_impulse_at_local_point(impulso)

                # paused = True

        # Briga de espadas (🏳️‍🌈?)
        elif (s1 == azul.weapon_shape and s2 == verde.weapon_shape) or \
             (s1 == verde.weapon_shape and s2 == azul.weapon_shape):

            if now - verde.last_hit_time > 0.1:
                azul.omega = -azul.omega
                verde.omega = -verde.omega
                hit_sound.play()

    space.on_collision(2, 1, begin=collide)
    space.on_collision(2, 2, begin=collide)


def random_velocity(body):
    angle = random.uniform(0, 2*math.pi)
    speed = 250
    body.velocity = (math.cos(angle)*speed, math.sin(angle)*speed)

def draw_hud(azul, verde):
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
    screen.blit(font.render(f"Azul HP: {azul.hp}", True, (255,255,255)), (x, 100))
    screen.blit(font.render(f"Verde HP: {verde.hp}", True, (255,255,255)), (x, 150))
    vel_azul = sum(v ** 2 for v in azul.body.velocity)**0.5
    vel_verde = sum(v ** 2 for v in verde.body.velocity)**0.5
    screen.blit(font.render(f"Azul VEL: {vel_azul:.2f}", True, (255,255,255)), (x, 200))
    screen.blit(font.render(f"Verde VEL: {vel_verde:.2f}", True, (255,255,255)), (x, 250))


def new_game():
    space = pymunk.Space()
    space.gravity = (0,0)
    space.damping = 1
    space.iterations = 30

    walls = create_walls(space)

    azul = Ball(space, 120, 150, (0,0,255), weapon_img, 1)
    verde = Ball(space, 280, 150, (0,255,0), weapon_img, 1)

    setup_collision(space, azul, verde)

    game_start_time = time.time()

    return space, walls, azul, verde, game_start_time


space, walls, azul, verde, game_start_time = new_game()

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
        azul.draw(screen)
        verde.draw(screen)
        draw_hud(azul, verde)

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
