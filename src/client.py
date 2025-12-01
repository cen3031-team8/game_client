import pygame
import sys
import random

# --- pygame setup ---
import threading
import asyncio
import queue
import json
import time
import traceback
pygame.init()
WINDOW_SIZE = (1280, 720)
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption("Pokémon Game")
clock = pygame.time.Clock()
running = True
dt = 0

# player (small square placeholder for a sprite)
PLAYER_SIZE = 28
player_pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
player_color = pygame.Color(230, 80, 80)  # red-ish
player_border = pygame.Color(40, 40, 40)
player_speed = 320  # pixels per second

# inventory UI state
inventory_open = False
inventory = []

# colors
PAPER = (245, 240, 230)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (90, 150, 200)
BUTTON_TEXT = (255, 255, 255)
# health
HEALTH_MAX = 100
health = HEALTH_MAX

# load background but keep the same image if available
try:
    background = pygame.image.load("background.png").convert()
    background = pygame.transform.scale(background, WINDOW_SIZE)  # scale to window
except Exception as e:
    print(f"Warning: couldn't load background.png ({e}). Using generated grass.")
    background = None

# cached procedurally generated grass surface (used when background is None)
_grass_surface = None
# --- WebSocket client boilerplate ---
# Configure the websocket URL here. Update to your server's ws endpoint.
WS_URL = "ws://127.0.0.1:8508/ws"


class WebSocketClient:
    """Background-thread WebSocket client with a thread-safe outgoing queue.

    If the `websockets` package is installed the client will attempt to
    connect and send JSON messages. If not available a dummy client will
    consume the queue and print messages (placeholder behavior).
    """

    def __init__(self, url=WS_URL):
        self.url = url
        self._send_q = queue.Queue()
        self._thread = None
        self._running = False
        self._use_real = False

        try:
            import websockets  # type: ignore
            self._use_real = True
            self._websockets = websockets
        except Exception:
            print("[ws] 'websockets' package not available — using dummy logger client")
            self._use_real = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        if self._use_real:
            self._thread = threading.Thread(target=self._run_async, daemon=True)
        else:
            self._thread = threading.Thread(target=self._run_dummy, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        # put a sentinel to unblock queue.get
        try:
            self._send_q.put_nowait(None)
        except Exception:
            pass
        if self._thread:
            self._thread.join(timeout=1.0)

    def send_state(self, state: dict):
        try:
            self._send_q.put_nowait(state)
        except Exception:
            print("[ws] failed to queue state")

    # --- dummy runner (no external deps) ---
    def _run_dummy(self):
        print("[ws] dummy ws client running — messages will be logged")
        while self._running:
            try:
                item = self._send_q.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                break
            try:
                print("[ws] send:", json.dumps(item))
            except Exception:
                print("[ws] send error")

    # --- real async runner using `websockets` package ---
    def _run_async(self):
        # run an asyncio loop in this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_main())
        except Exception:
            print("[ws] async loop terminated:")
            traceback.print_exc()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()

    async def _async_main(self):
        ws_lib = self._websockets
        while self._running:
            try:
                print(f"[ws] connecting to {self.url} ...")
                async with ws_lib.connect(self.url) as ws:
                    print("[ws] connected")
                    # loop while connected
                    while self._running:
                        # try to get a message from send queue in a thread
                        try:
                            item = await asyncio.get_event_loop().run_in_executor(
                                None, lambda: self._send_q.get(timeout=0.25)
                            )
                        except Exception:
                            item = None

                        if item is None:
                            await asyncio.sleep(0)
                            continue

                        try:
                            payload = json.dumps(item)
                            await ws.send(payload)
                        except Exception:
                            print("[ws] send failed, will attempt reconnect")
                            break
            except Exception:
                print("[ws] connection error, retrying in 1s")
                await asyncio.sleep(1.0)


# instantiate and start client; it will be non-blocking
ws_client = WebSocketClient(WS_URL)
ws_client.start()
# periodic send settings
_last_send_time = 0.0
_send_interval = 0.5  # seconds
def generate_grass_surface(size, tile_size=8, seed=None):
    """Create a pixel-art style grass surface of given size.

    tile_size: size of the small blocks (in pixels) used to paint grass.
    seed: optional seed for deterministic generation.
    """
    if seed is not None:
        rnd = random.Random(seed)
    else:
        rnd = random

    w, h = size
    surf = pygame.Surface((w, h))

    # palette of greens for variety
    palette = [
        (74, 148, 74),  # medium
        (86, 170, 86),  # lighter
        (66, 120, 60),  # darker
        (98, 180, 88),  # bright
        (74, 130, 58),  # olive-ish
    ]

    # occasionally place a 'flower' color
    flower_colors = [(240, 200, 80), (220, 140, 200), (240, 120, 120)]

    # loop over tiles
    for y in range(0, h, tile_size):
        for x in range(0, w, tile_size):
            color = rnd.choice(palette)
            rect = pygame.Rect(x, y, tile_size, tile_size)
            surf.fill(color, rect)

            # small chance to add a tiny contrasting block to make texture
            if rnd.random() < 0.06:
                # smaller inset square
                inset = max(1, tile_size // 3)
                ox = x + rnd.randint(0, max(0, tile_size - inset))
                oy = y + rnd.randint(0, max(0, tile_size - inset))
                fcol = rnd.choice(flower_colors)
                surf.fill(fcol, pygame.Rect(ox, oy, inset, inset))

    # optional subtle dithering: draw a few random darker pixels
    for _ in range((w * h) // 800):
        px = rnd.randrange(0, w)
        py = rnd.randrange(0, h)
        surf.set_at((px, py), (40, 80, 40))

    return surf

font = pygame.font.SysFont(None, 20)

def draw_ui():
    # subtle border around the screen (outline so it doesn't cover content)
    border_rect = pygame.Rect(6, 6, screen.get_width() - 12, screen.get_height() - 12)
    pygame.draw.rect(screen, (20, 20, 20), border_rect, width=3, border_radius=6)

    # top-left HUD box drawn on a transparent surface so alpha works
    hud_w, hud_h = 220, 48
    hud_rect = pygame.Rect(16, 16, hud_w, hud_h)
    hud_surf = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
    hud_surf.fill((0, 0, 0, 160))  # semi-transparent background
    pygame.draw.rect(hud_surf, (200, 200, 200), hud_surf.get_rect(), 2)

    # title
    title_surf = font.render("Player", True, (240, 240, 240))
    hud_surf.blit(title_surf, (8, 6))

    # coordinates and instructions
    coords = f"x: {int(player_pos.x)}  y: {int(player_pos.y)}"
    coords_surf = font.render(coords, True, (200, 200, 200))
    instr_surf = font.render("Move: W A S D", True, (180, 180, 180))
    hud_surf.blit(coords_surf, (8, 24))
    hud_surf.blit(instr_surf, (110, 24))

    # blit HUD to main screen
    screen.blit(hud_surf, (hud_rect.x, hud_rect.y))


def draw_inventory_button(mouse_pos=None):
    """Draws a button in the bottom-right that opens the inventory modal.
    Returns the pygame.Rect of the button for click tests.
    """
    btn_w, btn_h = 120, 36
    margin = 16
    x = screen.get_width() - btn_w - margin
    y = screen.get_height() - btn_h - margin
    btn_rect = pygame.Rect(x, y, btn_w, btn_h)

    # hover effect
    is_hover = False
    if mouse_pos:
        is_hover = btn_rect.collidepoint(mouse_pos)

    color = BUTTON_HOVER if is_hover else BUTTON_COLOR
    pygame.draw.rect(screen, color, btn_rect, border_radius=8)
    pygame.draw.rect(screen, (30, 30, 30), btn_rect, 2, border_radius=8)

    label = font.render("Inventory", True, BUTTON_TEXT)
    label_rect = label.get_rect(center=btn_rect.center)
    screen.blit(label, label_rect)
    return btn_rect


def draw_health_bar():
    """Draws the player's health bar in the bottom-left corner."""
    bar_w = 220
    bar_h = 18
    margin = 16
    x = margin
    y = screen.get_height() - bar_h - margin

    # background box
    box_rect = pygame.Rect(x - 6, y - 6, bar_w + 12, bar_h + 12)
    pygame.draw.rect(screen, (10, 10, 10), box_rect, border_radius=6)
    pygame.draw.rect(screen, (120, 120, 120), box_rect, 2, border_radius=6)
    # health fill
    pct = max(0.0, min(1.0, health / HEALTH_MAX)) if HEALTH_MAX > 0 else 0
    fill_w = int(bar_w * pct)
    fill_rect = pygame.Rect(x, y, fill_w, bar_h)

    # use a light red fill color as requested
    fill_color = (240, 120, 120)
    pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(x, y, bar_w, bar_h), border_radius=6)
    if fill_w > 0:
        pygame.draw.rect(screen, fill_color, fill_rect, border_radius=6)

    # text (vertically centered within the bar, slightly lowered)
    txt = f"HP {int(health)}/{HEALTH_MAX}"
    txt_surf = font.render(txt, True, (240, 240, 240))
    txt_rect = txt_surf.get_rect()
    # position text so it's left-aligned with a small inset and vertically centered
    txt_x = x + 8
    txt_y = y + (bar_h - txt_rect.height) // 2 + 1
    screen.blit(txt_surf, (txt_x, txt_y))



def draw_inventory_modal():
    """Draw the inventory modal centered at ~65% of the screen size.
    The modal is 'paper' colored and has a close button.
    """
    w = int(screen.get_width() * 0.65)
    h = int(screen.get_height() * 0.65)
    x = (screen.get_width() - w) // 2
    y = (screen.get_height() - h) // 2
    modal_rect = pygame.Rect(x, y, w, h)

    # dark overlay
    overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))

    # modal (paper)
    pygame.draw.rect(screen, PAPER, modal_rect, border_radius=8)
    pygame.draw.rect(screen, (160, 160, 160), modal_rect, 2, border_radius=8)

    # title
    title = font.render("Inventory", True, (40, 40, 40))
    screen.blit(title, (modal_rect.x + 16, modal_rect.y + 12))

    # close button (top-right of modal)
    cb_w, cb_h = 28, 24
    cb_rect = pygame.Rect(modal_rect.right - cb_w - 12, modal_rect.y + 10, cb_w, cb_h)
    pygame.draw.rect(screen, (200, 60, 60), cb_rect, border_radius=6)
    pygame.draw.rect(screen, (30, 30, 30), cb_rect, 1, border_radius=6)
    x_surf = font.render("X", True, (255, 255, 255))
    x_rect = x_surf.get_rect(center=cb_rect.center)
    screen.blit(x_surf, x_rect)

    return modal_rect, cb_rect


while running:
    
    # events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # if inventory open, check close button and outside clicks
            if inventory_open:
                modal_rect, cb_rect = draw_inventory_modal()
                # if clicked on close button, close
                if cb_rect.collidepoint((mx, my)):
                    inventory_open = False
                # if clicked outside modal, close
                elif not modal_rect.collidepoint((mx, my)):
                    inventory_open = False
            else:
                # check inventory button click
                btn = draw_inventory_button((mx, my))
                if btn.collidepoint((mx, my)):
                    inventory_open = True

    # input (continuous key state)
    keys = pygame.key.get_pressed()
    move = pygame.Vector2(0, 0)
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        move.y = -1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        move.y = 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        move.x = -1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        move.x = 1

    # normalize to prevent faster diagonal movement
    if move.length_squared() > 0:
        move = move.normalize()
        player_pos += move * player_speed * dt

    # clamp to screen bounds
    half = PLAYER_SIZE / 2
    player_pos.x = max(half + 8, min(screen.get_width() - half - 8, player_pos.x))
    player_pos.y = max(half + 8, min(screen.get_height() - half - 8, player_pos.y))

    # send periodic game state over websocket (non-blocking)
    now = time.time()
    if now - _last_send_time >= _send_interval:
        state = {
            "x": int(player_pos.x),
            "y": int(player_pos.y),
            "health": int(health),
            "inventory": inventory,
            "timestamp": now,
        }
        try:
            ws_client.send_state(state)
        except Exception:
            # send failures are non-fatal here
            pass
        _last_send_time = now

    # draw
    if background:
        screen.blit(background, (0, 0))
    else:
        # generate a cached pixel-art grass surface sized to the window
        if _grass_surface is None or _grass_surface.get_size() != screen.get_size():
            # choose a random seed per run so appearance varies each launch
            _grass_surface = generate_grass_surface(screen.get_size(), tile_size=8)
        screen.blit(_grass_surface, (0, 0))

    # draw UI overlays first (HUD/background elements)
    draw_ui()

    # draw player as a square centered at player_pos
    rect = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
    rect.center = (int(player_pos.x), int(player_pos.y))
    # border
    pygame.draw.rect(screen, player_border, rect.inflate(4, 4), border_radius=6)
    # main
    pygame.draw.rect(screen, player_color, rect, border_radius=6)

    # draw inventory button above world so it's always clickable
    mouse_pos = pygame.mouse.get_pos()
    btn_rect = draw_inventory_button(mouse_pos)

    # draw health bar bottom-left
    draw_health_bar()

    # if inventory is open, draw modal on top
    if inventory_open:
        modal_rect, cb_rect = draw_inventory_modal()
    pygame.display.flip()

    # frame timing
    dt = clock.tick(60) / 1000.0

# stop websocket client cleanly
try:
    ws_client.stop()
except Exception:
    pass

pygame.quit()
