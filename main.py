# visualizer_glut.py
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import re
import math

# --- 1. DATA PARSING ---
# Esta seção não muda, pois é independente da biblioteca gráfica.

def parse_paths_file(filename="Paths_D.txt"):
    """
    Analisa o arquivo Paths_D.txt para extrair o fator de escala e os dados de trajetória.
    """
    print(f"Lendo dados de {filename}...")
    try:
        with open(filename, 'r') as f:
            content = f.readlines()
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{filename}' não encontrado.")
        return None, None, None

    scaling_factor = float(re.search(r'\[(\d+)\]', content[0]).group(1))
    all_paths = []
    max_x, max_y = 0, 0

    for line in content[1:]:
        if not line.strip(): continue
        coords_raw = re.findall(r'\((\d+),(\d+),(\d+)\)', line)
        path = [(int(x), int(y), int(f)) for x, y, f in coords_raw]
        for x, y, _ in path:
            if x > max_x: max_x = x
            if y > max_y: max_y = y
        all_paths.append(path)
        
    print(f"Sucesso ao analisar {len(all_paths)} trajetórias.")
    return scaling_factor, all_paths, (max_x, max_y)

# --- 2. CLASSES DE ENTIDADE E AVATAR ---
# Estas classes também permanecem inalteradas.

class Person:
    """Representa uma entidade controlada pelos dados do arquivo."""
    def __init__(self, path_data, scaling_factor):
        self.path = {f: (x / scaling_factor, y / scaling_factor) for x, y, f in path_data}
        self.x, self.y = 0, 0
        self.color = [0.2, 0.5, 1.0]
        self.size = 0.2
        self.is_active = False
        if self.path:
            self.x, self.y = self.path[min(self.path.keys())]

    def update(self, frame_count):
        if frame_count in self.path:
            self.x, self.y = self.path[frame_count]
            self.is_active = True
        else:
            self.is_active = False
            
    def draw(self):
        if self.is_active:
            glColor3fv(self.color)
            glBegin(GL_QUADS)
            glVertex2f(self.x - self.size / 2, self.y - self.size / 2)
            glVertex2f(self.x + self.size / 2, self.y - self.size / 2)
            glVertex2f(self.x + self.size / 2, self.y + self.size / 2)
            glVertex2f(self.x - self.size / 2, self.y + self.size / 2)
            glEnd()

class Avatar(Person):
    """Representa a entidade controlada pelo usuário."""
    def __init__(self, x_start, y_start):
        global WORLD_WIDTH, WORLD_HEIGHT

        self.path = {}
        self.x, self.y = x_start, y_start
        self.color = [1.0, 0.5, 0.2]
        self.size = 0.25
        self.is_active = True
        self.speed = 0.15  # Velocidade de movimento do avatar

    def update(self): pass
    def move(self, dx, dy):

        global WORLD_WIDTH, WORLD_HEIGHT
        
        # Calcula o fator de correção
        # Queremos que o movimento vertical seja proporcionalmente menor
        # se o WORLD_HEIGHT for menor que o WORLD_WIDTH.
        
        # O fator de escala é a razão entre as dimensões do mundo.
        scale_x = 1.0 
        scale_y = 1.0 
        
        if WORLD_WIDTH > WORLD_HEIGHT:
            # O eixo X é mais "esticado", move Y mais devagar.
            scale_y = WORLD_HEIGHT / WORLD_WIDTH
        elif WORLD_HEIGHT > WORLD_WIDTH:
            # O eixo Y é mais "esticado", move X mais devagar.
            scale_x = WORLD_WIDTH / WORLD_HEIGHT
            
        # Aplica a correção de escala à velocidade
        self.x += dx * self.speed * scale_x
        self.y += dy * self.speed * scale_y

# --- 3. VARIÁVEIS GLOBAIS E ESTADO ---
# Como o GLUT é baseado em callbacks, precisamos de variáveis globais para
# manter o estado da aplicação entre as chamadas de função.

# Dados da aplicação
SCALE, PATHS, MAX_COORDS = 0, [], (0, 0)
WORLD_WIDTH, WORLD_HEIGHT = 0, 0
people, avatar, all_entities = [], None, []
frame_counter, max_frames = 0, 0
animation_direction = 1 # 1 para frente, -1 para trás

# Estado da entrada do teclado
keyboard_state = {"up": False, "down": False, "left": False, "right": False}

# --- 4. FUNÇÕES DE CALLBACK DO GLUT ---

def reshape(width, height):
    """Callback para quando a janela é redimensionada."""
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # Inverte o eixo Y para corresponder às coordenadas do arquivo
    glOrtho(0, WORLD_WIDTH, WORLD_HEIGHT, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def display():
    """Callback de renderização. Chamada para desenhar a cena."""
    glClear(GL_COLOR_BUFFER_BIT)
    
    for entity in all_entities:
        entity.draw()
        
    glutSwapBuffers()

def update(value):
    """
    Callback do temporizador para animação e atualização de estado.
    Esta função é o coração da lógica da aplicação.
    """
    global frame_counter, animation_direction # Adicione animation_direction

    # 1. Atualiza o estado da animação (NOVA LÓGICA)
    
    # Avança ou retrocede o contador
    frame_counter += animation_direction
    
    # Verifica os limites e inverte a direção
    if frame_counter > max_frames:
        frame_counter = max_frames - 1 # Volta um frame para evitar pular
        animation_direction = -1       # Inverte para trás
    elif frame_counter < 0:
        frame_counter = 1              # Volta um frame para evitar pular
        animation_direction = 1        # Inverte para frente
        
    for person in people:
        person.update(frame_counter)
        
    # 2. Atualiza a posição do avatar com base no estado do teclado
    dx, dy = 0, 0
    if keyboard_state["left"]: dx = -1
    if keyboard_state["right"]: dx = 1
    if keyboard_state["up"]: dy = -1
    if keyboard_state["down"]: dy = 1
    avatar.move(dx, dy)
    
    # 3. Processamento de Dados: Verificação de proximidade
    PROXIMITY_THRESHOLD = 0.5
    for entity in all_entities:
        entity.color = [1.0, 0.5, 0.2] if isinstance(entity, Avatar) else [0.2, 0.5, 1.0]

    for i in range(len(all_entities)):
        for j in range(i + 1, len(all_entities)):
            e1, e2 = all_entities[i], all_entities[j]
            if e1.is_active and e2.is_active:
                dist = math.hypot(e1.x - e2.x, e1.y - e2.y)
                if dist < PROXIMITY_THRESHOLD:
                    e1.color = e2.color = [1.0, 0.0, 0.0]

    # 4. Solicita que o GLUT redesenhe a tela
    glutPostRedisplay()
    
    # 5. Agenda a próxima chamada de update para criar um loop de animação
    fps = 60
    glutTimerFunc(1000 // fps, update, 0)

def special_key_down(key, x, y):
    """Callback para quando uma tecla especial (setas) é pressionada."""
    if key == GLUT_KEY_UP:    keyboard_state["up"] = True
    if key == GLUT_KEY_DOWN:  keyboard_state["down"] = True
    if key == GLUT_KEY_LEFT:  keyboard_state["left"] = True
    if key == GLUT_KEY_RIGHT: keyboard_state["right"] = True

def special_key_up(key, x, y):
    """Callback para quando uma tecla especial (setas) é solta."""
    if key == GLUT_KEY_UP:    keyboard_state["up"] = False
    if key == GLUT_KEY_DOWN:  keyboard_state["down"] = False
    if key == GLUT_KEY_LEFT:  keyboard_state["left"] = False
    if key == GLUT_KEY_RIGHT: keyboard_state["right"] = False

# --- 5. FUNÇÃO PRINCIPAL ---

def main():
    """Função principal que inicializa o GLUT e inicia o loop de eventos."""
    global SCALE, PATHS, MAX_COORDS, WORLD_WIDTH, WORLD_HEIGHT
    global people, avatar, all_entities, max_frames
    AMPLITUDE_FACTOR = 0.5
    
    # Carrega e analisa os dados do arquivo
    SCALE, PATHS, MAX_COORDS = parse_paths_file()
    if not PATHS: return

    SCALE_VISUAL = SCALE * AMPLITUDE_FACTOR
    
    WORLD_WIDTH = MAX_COORDS[0] / SCALE
    WORLD_HEIGHT = MAX_COORDS[1] / SCALE
    
    # Cria as entidades
    people = [Person(path, SCALE) for path in PATHS]
    avatar = Avatar(WORLD_WIDTH / 2, WORLD_HEIGHT / 2)
    all_entities = people + [avatar]
    max_frames = max(max(p.path.keys() if p.path else [0] for p in people))
    
    # Inicializa o GLUT
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    
    # Configura e cria a janela
    glutInitWindowSize(1200, 800)
    glutInitWindowPosition(100, 100)
    glutCreateWindow("T1 - Visualizador de Trajetorias (GLUT) - CG 2025/2".encode('utf-8'))
    
    # Registra as funções de callback
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutSpecialFunc(special_key_down)    # Tecla especial pressionada
    glutSpecialUpFunc(special_key_up)      # Tecla especial solta
    
    # Configura a cor de fundo
    glClearColor(0.1, 0.1, 0.1, 1.0)
    
    print("\n--- Controles ---")
    print("Use as SETAS do teclado para mover o avatar laranja.")
    print("Feche a janela para sair.")
    print("------------------\n")

    # Inicia o primeiro ciclo de animação
    glutTimerFunc(0, update, 0)
    
    # Inicia o loop de eventos do GLUT. Este é o último comando.
    glutMainLoop()

if __name__ == '__main__':
    main()