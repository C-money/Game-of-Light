
#                                                       ABOUT

# Game of Light
# v0.4
# Cole Hatton

# Simulation of an LED phototransistor feedback grid

# Good Settings found so far:

#       PSR = 1   - always

#       pVRefHigh can be kept at 5 as it has little effect above VP
#           lowering it to VP eliminates negative feedback
#           pVRefHigh has only a slight impact near VP
#           this feature could be left out in future

#       Vg Step Size < 0.5 needed for best results
#           Capacitance needed at gate for best results

#   Hex grid:
#       B_3 looks better than B_6 over a wide range of settings
#       B_3: pSensitivity > 0.08
#       B_6: pSensitivity ~ 0.025, pVRefLow < 0.5

#   Square grid:
#       B_4: pSensitivity ~ 0.06



#                                                       IMPORTS

import sys
import os
import time

import pygame
pygame.init()
from random import random

#os.nice(10);
os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (0,0)


#                                                       CONSTANTS

W = 41              # LED grid width including inactive LEDs for no edge index checking
H = 41              # LED grid height ''

DS = 28             # Dot spacing [px]
DR = 12               # Dot radius [px]

HEX = 0             # Hexagonal grid type
SQUARE = 1          # Square grid type
GRID = HEX       # Grid type set here


# IMPORTANT FINDING -   Simulation produces more interesting patterns when PSR is left
#                       at 1, which is most similar to Conway's Game of Life
PSR = 1         # Phototransistor Sensing Range - Max distance (in nodes) of sensed LEDs
W_ACTIVE = W - PSR     # all active nodes exist from PSR to W_ACTIVE - 1 and PSR to H_ACTIVE - 1
H_ACTIVE = H - PSR

if GRID is HEX:
    WINDOW_WIDTH = int((W + H/2.0) * DS)
    WINDOW_HEIGHT =  int(3.0**(0.5)/2 * (H + 1) * DS)
if GRID is SQUARE:
    WINDOW_WIDTH = int(W * DS + 250)
    WINDOW_HEIGHT =  int(H * DS)

VDD = 5.0             # Vdd potential [V]
VN = 1.5              # A bit less than Vgth for N channel FET [V] 1.2 is minimum for affordable N-FET
VP = VDD - 1.5        # A bit more than Vgth for P channel FET [V] VDD - 1.2 is maximum for affordable P-FET

RQ_ON = 10          # Minimum combined FET on-resistance (Vgs = VDD / 2) [Ohm]
                    #       Will be 10Ohm at most, willing to pay for down to 1.2Ohm
RQI_BASE = 1000 / ((VP - VN)/2)**2 / RQ_ON # pre-calc'd inverse base resistance [1/kOhm] for RQi fn

VG_MIN = -15.0       # Min Voltage for phototrans circuit [v]
VG_MAX = 10.0       # Max Voltage for phototrans cirucit [V]


FLR_MAX = 18        # max flashLightRadius

FLB_MAX = 250       # max flashLightBrightness

STEP_SCALE_BASE = 1.1   # base for gate and LED step scales

P_SENSE_STEP = 0.001    # step size for phototrans sensitivity change


#                                                       VARIABLES

# Step Scales are a cheap way of factoring in effect of capacitances needed
#       at FET gates and drains (phototrans divider tied to gatesm, LED between drains)
# Valid Step Scales between 0 and 1
# Step Scale approaching 1 is equivalent to 0 or tiny capacitance
# Step Scale approaching 0 is equivalent to larger capacitance

vgStepScale = STEP_SCALE_BASE**(-19)   #1.2^-10  # responsiveness of gate voltage to change in light sensed at phototransistor
vdStepScale = STEP_SCALE_BASE**(-53)   #1.2^-28 # responsiveness of drain voltage (voltage between FET drains) to LED / FET circuit

# Phototransistor Sensitivity - Brightness to Steady State Gate Voltage
# has led brightness at phototransistor and phototrans resistor embedded in value
pSensitivity = 0.085
pSensVariation = [[random()*0.2 + 0.9 for i in range(H) ] for j in range(W)]
#Implement pSensVariation as 2D array of rand(0.9, 1.1)

# Phototransistor side of the circuit will be powered between two reference voltages
#       to allow for tuning of system and more fun

pVRefLow = -0.6     # phototransistor circuit low voltage reference
pVRefHigh = 4.95     # phototransistor circuit high voltage reference


idVariation = [[random()*0.2 + 0.9 for i in range(H) ] for j in range(W)]

# Flash Light tool used to initialize and interact with simulation
# Effect of flashlights in real life depends heavily on lightpiping and
#       real sensitvities needed, so don't expect flashlights to work like this in
#       the real life Game of Light

flr = 2             # flash light radius
flashLightRange = range(-flr, flr + 1)      # range of flash light tool

flashLightBrightness = 140

lastTime = 0      # time at the end of the last step
stepTime = 1000      # time to take a step in ms

#                                                       PRE-CALCS


# distance (d = 1/(x^2 + y^2)) lookup table for max PSR distance in x or y from node
if GRID is HEX:
    d = [[(0 if (i is 0 and j is 0) else 1.0/((i + 1 - j/2.0)**2 + (3.0/4)*(j)**2)) for j in range(PSR + 1)] for i in range(PSR + 1)]

if GRID is SQUARE:
    d = [[(0 if (i is 0 and j is 0) else 1.0/(i**2 + j**2)) for j in range(PSR + 1)] for i in range(PSR + 1)]

# initially active nodes
if GRID is HEX:
# active nodes with geometric mean (x, y) less than threshold
    #active_nodes = [[(1 if (i - (W - 1)/ 2.0) * (j - (H - 1)/ 2.0) > -80 else 0) for j in range(H)] for i in range(W)]
# active nodes as hexagon
    active_nodes = [[(1 if (i - j < (W - 1)/ 2.0 and j - i < (W - 1)/ 2.0) else 0) for j in range(H)] for i in range(W)]

if GRID is SQUARE:
# square grid
    active_nodes = [[1 for j in range(H)] for i in range(W)]

#dot positions 
if GRID is HEX:
# hex grid dot positions
    dot_x_pos = [[int((i - j/2.0 + H/2.0)*DS) for j in range(H)] for i in range(W)]
    dot_y_pos = [int((3**0.5)/2*(j+1)*DS) for j in range(H)]

if GRID is SQUARE:
# square grid dot positions
    dot_x_pos = [[int((i)*DS) for j in range(H)] for i in range(W)] # this is only 2D to keep Step function circle drawing generalized for one less conditional at each point
    dot_y_pos = [int((j)*DS) for j in range(H)]


#                                                       ICs

b = [[0 for i in range(H) ] for j in range(W)]
vg = [[0 for i in range(H) ] for j in range(W)]
rqi = [[0 for i in range(H) ] for j in range(W)]
vd = [[0 for i in range(H) ] for j in range(W)]
iD = [[0 for i in range(H) ] for j in range(W)]

b_ext = [[0 for i in range(H) ] for j in range(W)]

x_index = 1
y_index = 1

def PowerCycle():
    global b, vg, rqi, vd, iD, b_ext
    b = [[0 for i in range(H) ] for j in range(W)]
    vg = [[0 for i in range(H) ] for j in range(W)]
    rqi = [[0 for i in range(H) ] for j in range(W)]
    vd = [[0 for i in range(H) ] for j in range(W)]
    iD = [[0 for i in range(H) ] for j in range(W)]

    b_ext = [[0 for i in range(H) ] for j in range(W)]



def ResetActiveNodes():
    global active_nodes
    if GRID is HEX:
        #active_nodes = [[(1 if (i - (W - 1)/ 2.0) * (j - (H - 1)/ 2.0) > -80 else 0) for j in range(H)] for i in range(W)]
        active_nodes = [[(1 if (i - j < (W - 1)/ 2.0 and j - i < (W - 1)/ 2.0) else 0) for j in range(H)] for i in range(W)]
    if GRID is SQUARE:
        active_nodes = [[1 for j in range(H)] for i in range(W)]       



#                                                       Circuit functions

# Brightness functions - only one enabled at a time

# Generalized hex brightness summing function for PSR as positive int
def B_hex(x,y):
    light_sensed = 0.0
    for i in range(1, PSR + 1):
        for j in range(PSR + 1):
            light_sensed += d[i][j] * (iD[x + i][y + j] +
                                       iD[x - j][y + i - j] +
                                       iD[x + j - i][y - i])
    b[x][y] = light_sensed + b_ext[x][y]


# Generalized square brightness summing function for PSR as positive int
def B_square(x,y):
    light_sensed = 0.0
    for i in range(1, PSR + 1):
        for j in range(PSR + 1):
            light_sensed += d[i][j] * (iD[x + i][y + j] +
                                       iD[x - j][y + i] +
                                       iD[x - i][y - j] +
                                       iD[x + j][y - i])
    b[x][y] = light_sensed + b_ext[x][y]

# Brightness summing function for PSR = 1, 6 adjacent LEDs summed
def B_6(x,y):
    light_sensed = (iD[x + 1][y] + iD[x + 1][y + 1] +
                    iD[x][y + 1] + iD[x - 1][y] +
                    iD[x - 1][y - 1] + iD[x][y - 1])
    b[x][y] = light_sensed + b_ext[x][y]

# Three LEDs at 120deg summed, originally a bug, but looks good and is implementable in rl
def B_3(x,y): 
    light_sensed = (iD[x + 1][y] + iD[x][y + 1] + iD[x - 1][y - 1])
    b[x][y] = light_sensed + b_ext[x][y]

# Four adjacent LEDs summed - Square grid assumed
def B_4(x,y):
    light_sensed = (iD[x + 1][y] + iD[x][y + 1] + iD[x][y - 1] + iD[x - 1][y])
    b[x][y] = light_sensed + b_ext[x][y]



# Gate voltage (approaches b[x][y] * pSensitivity + pVRefLow)
def VG(x,y):
    global pVRefLow
    vg[x][y] += (b[x][y] * pSensitivity + pVRefLow - vg[x][y]) * vgStepScale #multiply pSensitivity by pSensVariation
    if vg[x][y] > pVRefHigh:
        vg[x][y] = pVRefHigh

def VGwithRand(x,y):
    global pVRefLow
    vg[x][y] += (b[x][y] * pSensitivity * pSensVariation[x][y] + pVRefLow - vg[x][y]) * vgStepScale #multiply pSensitivity by pSensVariation
    if vg[x][y] > pVRefHigh:
        vg[x][y] = pVRefHigh

# Inverse of combined FET resistance
def RQi(x,y):
    #rqi[x][y] = 0 if (vg[x][y] < VN or vg[x][y] > VP) else 1 # / 1000
    rqi[x][y] = (vg[x][y] - VN)*(VP - vg[x][y]) * RQI_BASE
    if rqi[x][y] < 0:
        rqi[x][y] = 0

# Voltage between FET drains (voltage across LED + current limiting resistor)
def VD(x,y):
    vd[x][y] += ((VDD - vd[x][y])*rqi[x][y] - iD[x][y]) * vdStepScale
    if vd[x][y] > VDD:
        vd[x][y] = VDD



QA = 2.604213#pfit[0] #quadratic poly fit
QB = -7.08313#pfit[1]
QC = 2.776874#pfit[2]
SLOPE = 0.17421485#Id_data[1]/Vc_data[1] #slope in linear region
V_Q_TH = 2.3860976#Vc_data[2] #minimum voltage for quadratic region

# LED current (proportional to brightness) at Cap voltage
def Id_at_Vd(v, x, y):
    if (v > V_Q_TH):
        ret = QA*v**2 + QB*v + QC
    else:
        ret = SLOPE*v
    return ret #Implement idVariation as 2D array of rand(0.9, 1.1)

def Id_at_Vd_withRand(v, x, y):
    if (v > V_Q_TH):
        ret = QA*v**2 + QB*v + QC
    else:
        ret = SLOPE*v
    return ret * idVariation[x][y] #Implement idVariation as 2D array of rand(0.9, 1.1)




def VRefLowInc(inc):
    global pVRefLow
    pVRefLow += inc
    if pVRefLow > VG_MAX:
        pVRefLow = VG_MAX
    elif pVRefLow < VG_MIN:
        pVRefLow = VG_MIN

def VRefHighInc(inc):
    global pVRefHigh
    pVRefHigh += inc
    if pVRefHigh > VG_MAX:
        pVRefHigh = VG_MAX
    elif pVRefHigh < VG_MIN:
        pVRefHigh = VG_MIN

       
def FlashLightBrightness(inc):
    global flashLightBrightness
    flashLightBrightness += inc
    if flashLightBrightness < 0:
        flashLightBrightness = 0
    elif flashLightBrightness > FLB_MAX:
        flashLightBrightness = FLB_MAX
    

def FlashLightValidPos(x,y):
    return 1 if x >= 0 and x < W and y >= 0 and y < H else 0

def FlashLightClearLast(x,y):
    global x_index, y_index
    if GRID is HEX:
        for i in flashLightRange:
            for j in flashLightRange:
                if FlashLightValidPos(x_index + i, y_index + j) and i - j <= flr and j - i <= flr:
                    b_ext[x_index + i][y_index + j] = 0
    if GRID is SQUARE:
        for i in flashLightRange:
            for j in flashLightRange:
                if FlashLightValidPos(x_index + i, y_index + j):
                    b_ext[x_index + i][y_index + j] = 0

def FlashLightPos(x,y):
    global x_index, y_index
    if GRID is HEX:
        x_index = int((x + y/2.0)/DS - H/2.0 + 0.87)
        y_index = int((2/(3.0**0.5) * y)/DS - 0.5)
        for i in flashLightRange:
            for j in flashLightRange:
                if FlashLightValidPos(x_index + i, y_index + j) and i - j <= flr and j - i <= flr:
                    b_ext[x_index + i][y_index + j] = flashLightBrightness
    if GRID is SQUARE:
        x_index = int(float(x) / DS + 0.5)
        y_index = int(float(y) / DS + 0.5)
        for i in flashLightRange:
            for j in flashLightRange:
                if FlashLightValidPos(x_index + i, y_index + j):
                    b_ext[x_index + i][y_index + j] = flashLightBrightness

def FlashLightSize(inc):
    global flr, flashLightRange
    flr += inc
    if flr > FLR_MAX:
        flr = FLR_MAX
    elif flr < 0:
        flr = 0
    flashLightRange = range(-flr, flr + 1)


if GRID is HEX:
    def ToggleNodes(x,y):
        x_index = int((x + y/2.0)/DS - H/2.0 + 0.87)
        y_index = int((2/(3.0**0.5) * y)/DS - 0.5)
        for i in flashLightRange:
            for j in flashLightRange:
                if FlashLightValidPos(x_index + i, y_index + j) and i - j <= flr and j - i <= flr:
                    active_nodes[x_index + i][y_index + j] ^= 1
if GRID is SQUARE:
    def ToggleNodes(x,y):
        x_index = int(float(x) / DS + 1)
        y_index = int(float(y) / DS + 1)
        for i in flashLightRange:
            for j in flashLightRange:
                if FlashLightValidPos(x_index + i, y_index + j):
                    active_nodes[x_index + i][y_index + j] ^= 1
   





#                                                       Step function

B_fn = B_3

def Step():
    global lastTime, stepTime
    for x in range(PSR, W_ACTIVE):
        for y in range(PSR, H_ACTIVE):
            if active_nodes[x][y] is 1:
                B_fn(x,y)                  # pick a light summing function
                VG(x,y)
                RQi(x,y)
                VD(x,y)
            else:
                b[x][y] = 0
                vg[x][y] = 0
                rqi[x][y] = 0
                vd[x][y] = 0
    for x in range(PSR, W_ACTIVE):
        for y in range(PSR, H_ACTIVE):
            if active_nodes[x][y] is 1:
                iD[x][y] = Id_at_Vd(vd[x][y], x, y)
            else:
                iD[x][y] = 0
            bp = int(iD[x][y] * 7)
            pygame.draw.circle(window, (b_ext[x][y], bp, bp), (dot_x_pos[x][y], dot_y_pos[y]), DR, 0)
            #pygame.gfxdraw.aacircle(window, dot_x_pos[x][y], dot_y_pos[y], DR, (b_ext[x][y], bp, bp))
    time = pygame.time.get_ticks()
    stepTime = time - lastTime
    lastTime = time;
               

def DispSettings():
    text_vg = font.render("Vg Step Size: " + str(round(vgStepScale, 5)), 1, (100, 30, 10))
    text_vd = font.render("Vd Step Size: " + str(round(vdStepScale, 5)), 1, (100, 30, 10))
    text_vgo = font.render("Low VRef: " + str(pVRefLow), 1, (100, 30, 10))
    text_vgo2 = font.render("High VRef: " + str(pVRefHigh), 1, (100, 30, 10))
    text_psns = font.render("Sensitivity: " + str(pSensitivity), 1, (100, 30, 10))
    text_steprate = font.render("Step Rate: " + str(round(1000.0 / stepTime, 1)), 1, (100, 30, 10))
    background.fill((0, 0, 0))
    background.blit(text_vg, textpos_vg)
    background.blit(text_vd, textpos_vd)
    background.blit(text_vgo, textpos_vgo)
    background.blit(text_vgo2, textpos_vgo2)
    background.blit(text_psns, textpos_psns)
    background.blit(text_steprate, textpos_steprate)

    # Blit everything to the window
    window.blit(background, (0, 0))
    



#create the window
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN|pygame.ASYNCBLIT)#(WINDOW_WIDTH, WINDOW_HEIGHT)) 
pygame.mouse.set_visible(False)

# Fill background
background = pygame.Surface(window.get_size())
background = background.convert()
background.fill((0, 0, 0))

# Display some text
font = pygame.font.SysFont("Arial", 25, bold=False,italic=False)
text_vg = font.render("Vg Step Size: " + str(round(vgStepScale, 5)), 1, (100, 30, 10))
text_vd = font.render("Vd Step Size: " + str(round(vdStepScale, 5)), 1, (100, 30, 10))
text_vgo = font.render("Low VRef: " + str(pVRefLow), 1, (100, 30, 10))
text_vgo2 = font.render("High VRef: " + str(pVRefHigh), 1, (100, 30, 10))
text_psns = font.render("Sensitivity: " + str(pSensitivity), 1, (100, 30, 10))
text_steprate = font.render("Step Rate: " + str(round(1000.0 / stepTime, 1)), 1, (100, 30, 10))

textpos_vg = text_vg.get_rect()
textpos_vg.right = background.get_rect().right - 10
textpos_vg.bottom = background.get_rect().bottom - 10
textpos_vd = text_vd.get_rect()
textpos_vd.right = background.get_rect().right - 10
textpos_vd.bottom = background.get_rect().bottom - 40
textpos_vgo = text_vgo.get_rect()
textpos_vgo.right = background.get_rect().right - 10
textpos_vgo.bottom = background.get_rect().bottom - 70
textpos_vgo2 = text_vgo2.get_rect()
textpos_vgo2.right = background.get_rect().right - 10
textpos_vgo2.bottom = background.get_rect().bottom - 100
textpos_psns = text_psns.get_rect()
textpos_psns.right = background.get_rect().right - 10
textpos_psns.bottom = background.get_rect().bottom - 130
textpos_steprate = text_steprate.get_rect()
textpos_steprate.right = background.get_rect().right - 10
textpos_steprate.bottom = background.get_rect().bottom - 160

background.blit(text_vg, textpos_vg)
background.blit(text_vd, textpos_vd)
background.blit(text_vgo, textpos_vgo)
background.blit(text_vgo2, textpos_vgo2)
background.blit(text_psns, textpos_psns)
background.blit(text_steprate, textpos_steprate)

# Blit everything to the window
window.blit(background, (0, 0))
pygame.display.flip()


#draw a line - see http://www.pygame.org/docs/ref/draw.html for more 
#pygame.draw.line(window, (255, 255, 255), (0, 0), (30, 50))

#draw it to the window
pygame.display.flip()

mouse_x = 0
mouse_y = 0


#input handling (somewhat boilerplate code):
while True:
    #time.sleep(0.005)
    DispSettings()
    Step()
    pygame.display.update()

    
    for event in pygame.event.get(): 
        if event.type is pygame.QUIT:
            pygame.quit()
            sys.exit(0)
        else:
            #print event
            
            if event.type is 3:                     #keystroke
                keycode = event.dict.values()[1]
                if keycode is 48:
                    pygame.quit()
                    sys.exit(0)
                elif keycode is 114:      #'r'
                    PowerCycle()
                elif keycode is 116:      #'t'
                    ResetActiveNodes()
                elif keycode is 102:      #'f'
                    FlashLightClearLast(mouse_x, mouse_y)
                    FlashLightSize(1)
                    FlashLightPos(mouse_x, mouse_y)
                elif keycode is 100:      #'d'
                    FlashLightClearLast(mouse_x, mouse_y)
                    FlashLightSize(-1)
                    FlashLightPos(mouse_x, mouse_y)
                elif keycode is 119:      #'w'
                    VRefLowInc(0.1)
                elif keycode is 115:      #'s'
                    VRefLowInc(-0.1)
                elif keycode is 113:      #'q'
                    VRefHighInc(0.05)
                elif keycode is 97:       #'a'
                    VRefHighInc(-0.05)                   
                elif keycode is 118:      #'v'
                    FlashLightBrightness(10)
                    FlashLightClearLast(mouse_x, mouse_y)
                    FlashLightPos(mouse_x, mouse_y)
                elif keycode is 99:       #'c'
                    FlashLightBrightness(-10)
                    FlashLightClearLast(mouse_x, mouse_y)
                    FlashLightPos(mouse_x, mouse_y)
                elif keycode is 105:      #'i'
                    vgStepScale *= STEP_SCALE_BASE
                    vdStepScale *= STEP_SCALE_BASE
                elif keycode is 107:      #'k'
                    vgStepScale /= STEP_SCALE_BASE
                    vdStepScale /= STEP_SCALE_BASE
                elif keycode is 111:      #'o'
                    vdStepScale *= STEP_SCALE_BASE
                elif keycode is 108:      #'l'
                    vdStepScale /= STEP_SCALE_BASE
                elif keycode is 117:      #'u'
                    pSensitivity += P_SENSE_STEP
                elif keycode is 106:      #'j'
                    pSensitivity -= P_SENSE_STEP
                #DispSettings()
                                   
            if event.type is 4:                     #mouse move
                mouse_x = event.dict.values()[1][0]
                mouse_y = event.dict.values()[1][1]
                FlashLightClearLast(mouse_x, mouse_y)
                FlashLightPos(mouse_x, mouse_y)

            if event.type is 6:                     #mouse button up
                ToggleNodes(mouse_x, mouse_y)


