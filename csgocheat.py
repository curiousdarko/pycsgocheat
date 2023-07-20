import win32api
import win32con
import win32gui
import pymem
import pymem.process
import pygame
import time
from ctypes import windll
from threading import Thread, Lock


##offsetss
m_dwBoneMatrix = 0x26A8
dwLocalPlayer = 0xDEA98C
m_iTeamNum = 0xF4
m_vecOrigin = 0x138
m_bDormant = 0xED
dwEntityList = 0x4DFFF7C
dwViewMatrix = 0x4DF0DC4


try:
    pm = pymem.Pymem("csgo.exe")
    Client = pymem.process.module_from_name(pm.process_handle, 'client.dll').lpBaseOfDll
except Exception as e:
    print(e)
    exit()

Width = win32api.GetSystemMetrics(0)
Height = win32api.GetSystemMetrics(1)

def W2S(posX, posY, posZ, view):
    clipCoordsX = posX * view[0] + posY * view[1] + posZ * view[2] + view[3]
    clipCoordsY = posX * view[4] + posY * view[5] + posZ * view[6] + view[7]
    clipCoordsW = posX * view[8] + posY * view[9] + posZ * view[10] + view[11]

    if clipCoordsW < 0.1:
         return False, 0, 0

    NDCx = clipCoordsX / clipCoordsW
    NDCy = clipCoordsY / clipCoordsW

    screenX = (Width / 2 * NDCx) + (NDCx + Width / 2)
    screenY = -(Height / 2 * NDCy) + (NDCy + Height / 2)
    return True, screenX, screenY

def get_originpos(EnAddr):
    my_posRx = pm.read_float(EnAddr + m_vecOrigin)
    my_posRy = pm.read_float(EnAddr + m_vecOrigin + 4)
    my_posRz = pm.read_float(EnAddr + m_vecOrigin + 8)

    return my_posRx, my_posRy, my_posRz

def get_bonepos(Entity, n):
    Bonebase = pm.read_int(Entity + m_dwBoneMatrix)

    EnemyBonesx = pm.read_float(Bonebase + 0x30 * n + 0x0C)
    EnemyBonesy = pm.read_float(Bonebase + 0x30 * n + 0x1C)
    EnemyBonesz = pm.read_float(Bonebase + 0x30* n + 0x2C)
    return EnemyBonesx, EnemyBonesy, EnemyBonesz


EntityList = {}
EntityListLock = Lock()

def FindEnt():
    global EntityList
    while True:
        LocalPlayer = pm.read_int(Client + dwLocalPlayer)
        Player_team = pm.read_int(LocalPlayer + m_iTeamNum)
        TempEntityList = {}

        for i in range(20):
            Entity = pm.read_int(Client + dwEntityList + (i * 0x10))
            
            if Entity:
                Enemy_team = pm.read_int(Entity + m_iTeamNum)
                Entity_dormant = pm.read_int(Entity + m_bDormant)
                
            if (Entity and Entity != LocalPlayer and Player_team != Enemy_team) and not Entity_dormant:
                TempEntityList[Entity] = Entity

        with EntityListLock:
            EntityList = TempEntityList
        time.sleep(0.01)

Thread(target=FindEnt).start()

pygame.init()
pygame.mixer.init()
pygame.display.set_caption("Overlay")
SetWindowPos = windll.user32.SetWindowPos
screen = pygame.display.set_mode((Width, Height))
clock = pygame.time.Clock()
alpha = 128
FPS = 60

bg_color = (0, 0, 0)
hwnd = pygame.display.get_wm_info()["window"]
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
    win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*bg_color), 0, win32con.LWA_COLORKEY)
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

color = (160, 32, 240)

while True:
    clock.tick(FPS)
    screen.fill(bg_color)
    screen.set_alpha(128)

    with EntityListLock:
        TempEntityList = EntityList.copy()

    view = []
    for i in range(17):
        view.append(pm.read_float(Client + dwViewMatrix + (i * 4)))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    for Entity in TempEntityList:
        hp = pm.read_int(Entity + 0x100)
        if not hp:
            continue

        my_posRx, my_posRy, my_posRz = get_originpos(Entity)
        state, LegX, LegY = W2S(my_posRx, my_posRy, my_posRz, view)

        my_hedRx, my_hedRy, my_hedRz = get_bonepos(Entity, 8)
        state2, HeadX, HeadY = W2S(my_hedRx, my_hedRy, my_hedRz, view)

        if state and state2:
            
            Diff = HeadY - LegY
            HeadY += Diff // 5
            Diff = HeadY - LegY
            pygame.draw.line(screen, color, (LegX - Diff // 4, HeadY), (LegX - Diff // 4, LegY))
            pygame.draw.line(screen, color, (LegX + Diff // 4, HeadY), (LegX + Diff // 4, LegY))
            pygame.draw.line(screen, color, (LegX - Diff // 4, HeadY), (LegX + Diff // 4, HeadY))
            pygame.draw.line(screen, color, (LegX - Diff // 4, LegY), (LegX + Diff // 4, LegY))  

    pygame.display.flip()
    time.sleep(0.01)
