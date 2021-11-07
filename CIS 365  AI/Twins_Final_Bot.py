
'''
Team Twins first draft bot for CIS 365
Rodney Fulk
Michael Chau
David Fletcher 
'''

import hlt
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square
import logging, os
import random
from collections import defaultdict , OrderedDict
'''if os.path.exists('TeamTwinsBotNew.log'):
    os.remove('TeamTwinsBotNew.log')
logging.basicConfig(filename="TeamTwinsBotNew.log", level=logging.DEBUG)'''

highProductionFactor = .75  #change the factor here only

productionMap = defaultdict(dict)
gotHighProduction = False # Mode flag. Will try to tunnel to high production - Should be set to True once captured
highProduction = None

searchOrder = [ 7, 12, 16, 11, 8, 17, 15, 6,   0, 1, 2, 3, 4, 9, 13, 18, 23, 22, 21, 20, 19, 14, 10, 5] # Search pattern for looking at neighbors from inside out.
directionDefault =[ 3, 3, 0,0,0, 3, 3, 0,0,0, 3,3, 1, 1, 2, 2, 2, 1, 1, 2, 2, 2, 1, 1  ] # direction to move to get into square in list returned by survey. 
myID, game_map = hlt.get_init()
highProduction = 0
hpX = hpY = 0
hpDist  = maxDistance = min(game_map.width, game_map.height) // 2
mySquare = None

#look at all production and setup a highProduction target.
#Also grab initial home square
for x in range(game_map.width):
    for y in range(game_map.height):
        z = game_map.contents[y][x]
        if z.production > highProduction:
            highProduction = z.production
        productionMap[x][y] = z.production
        if z.owner == myID:
            mySquare = z
highProduction = int (highProduction  * highProductionFactor) #Production above this is considered high production.
for x in range(game_map.width): #look for closest 90% of highest production square. 
    for y in range(game_map.height):
        z = game_map.contents[y][x]
        if z.production >= ((highProduction / highProductionFactor) * .9):
            if (game_map.get_distance(z, mySquare) < hpDist):#Distance from high production square to home square
                hpY = z.y
                hpX = z.x

hlt.send_init("TeamTwins")

#Not currently used but could be
def findNearestEnemy(square):
    direction = NORTH
    totalDistance = maxDistance
    for x in (NORTH, EAST, SOUTH, WEST):
        distance = 0
        cur = square
        while ((cur.owner == myID or cur.owner == 0) and (distance < totalDistance)):
            distance += 1
            cur = game_map.get_target(cur, x)
        if (distance < totalDistance):
            direction = x
            totalDistance = distance
    if totalDistance == maxDistance:
        return 4, 0
    return direction, totalDistance

#find nearestHighProduction in a specific direction.
def findNearestHighProduction(square):
    direction = NORTH
    totalDistance = maxDistance
    for x in (NORTH, EAST, SOUTH, WEST):
        distance = 1
        cur = game_map.get_target(square, x)
        while (cur.owner !=myID) and (distance < totalDistance) and (cur.production < highProduction):
            distance += 1
            cur = game_map.get_target(cur, x)
        if (cur.production >= highProduction) and (distance < totalDistance) and (cur.owner != myID):
            totalDistance = distance
            direction = x
    if totalDistance == maxDistance:
        return 4, 0
    return direction, totalDistance

def getDamage(square):
    
    if square.owner == 0 and square.strength > 0:
        return square.production / square.strength
    else:
        # return total potential damage caused by overkill when attacking this square
        return sum(neighbor.strength for neighbor in game_map.neighbors(square) if neighbor.owner not in (0, myID))

def findMaxDamage(square):
    target, direction = max(((neighbor, direction) for direction, neighbor in enumerate(game_map.neighbors(square))
                                if neighbor.owner != myID),
                                default = (None, None),
                                key = lambda t: getDamage(t[0]))
    if target is not None and target.strength < square.strength:
        return direction
    else:
        return STILL

#Finds nearest edge to move center pieces to when over strength size
def findNearestEdge(square):
    totalDistance = maxDistance
    direction = NORTH
    for x in (NORTH, EAST, SOUTH, WEST):
        distance = 0
        cur = square
        while cur.owner == myID and distance < totalDistance:
            distance += 1
            cur = game_map.get_target(cur, direction)
        if (distance < totalDistance):
            direction = x
            totalDistance = distance
    if distance >= maxDistance: #If no edge in direction, return 0
        return 4, 0
    return direction, totalDistance

'''
pieces dictionaries Key is X, Y, values are flag for moved, and priority to fill
'''
def sortPieces():
    edgePieces = defaultdict(dict)
    centerPieces = defaultdict(dict)
    for square in game_map:
        if square.owner == myID:
            edgePiece = any(neighbor.owner != myID for neighbor in game_map.neighbors(square))
            if edgePiece:
                edgePieces[square.y][square.x] = [False, 0]
            else:
                centerPieces[square.y][square.x]= [False, 0]
    return edgePieces, centerPieces

#will make move to square if possible. May also include surrounding pieces too
#site is the location trying to move to

def makeEdgeMove(square, moves, edgePieces, neighbor, site, priority):
    success = False
    move = None
    direction = directionDefault[site]
    if square.strength > neighbor[site].strength:
        move = Move(square, direction)
        success = True
    else:
        move = Move(square, STILL)
        success = True
    if move != None:
        moves.append(move)
        edgePieces[square.y][square.x][0] = True
        edgePieces[square.y][square.x][1] = priority
    return moves, edgePieces, success

#used by lambda to get production of square
def getProduction(square):
    return square.production

#choose priority for edge pieces
#return priority, strength and direction of highest priority
def moveEdge(square, moves, edgePieces):
    neighbors = {}
    enemy = True
    production = 0
    neighbor = edgeSurvey(square)
    lookUp = [7, 12, 16, 11]
    if (square.strength) > (square.production * 5) and  not (edgePieces[square.y][square.x][0]):
        #check which space we can do most damage aka overkill
        direction = findMaxDamage(square)
        if direction !=4:
            moves, edgePieces, success = makeEdgeMove(square, moves, edgePieces, neighbor, lookUp[direction], 90)
            if success:
                return moves, edgePieces
        #First check for high production nearby - move if can
        for site in searchOrder:
            if neighbor[site].production >= highProduction and neighbor[site].owner != myID:
                moves, edgePieces, success = makeEdgeMove(square, moves, edgePieces, neighbor, site, 50)
                if success:
                    return moves, edgePieces
        #If no enemy or highproduction right by then look up to half board away for high production
        direction, distance = findNearestHighProduction(square)
        if (direction!=4) and (distance < (maxDistance//2)) and (distance > 0):
            moves, edgePieces, success = makeEdgeMove(square, moves, edgePieces, neighbor, lookUp[direction], 30)
            if success:
                return moves, edgePieces
        #Try highest production square
        target, direction = max(((neighbor, direction) for direction, neighbor in enumerate(game_map.neighbors(square))
                                if neighbor.owner == 0),
                                default = (None, None),
                                key = lambda t: getProduction(t[0]))
        moves, edgePieces, success = makeEdgeMove(square, moves, edgePieces, neighbor, lookUp[direction], 60)
        if success:
            return moves, edgePieces
        #staying since can't do anything else
        moves.append(Move(square, STILL))
        edgePieces[square.y][square.x][0]=True
        edgePieces[square.y][square.x][1]=80
    else: #If production is not high enough don't move - exceptions can go here
        moves.append(Move(square, STILL))
    return moves, edgePieces

def edgeSurvey(square):
    combos = ((-2, -2),(-1, -2), (0, -2), (1, -2 ), (2, -2), # 0   1   2   3  4
              (-2, -1),(-1, -1), (0, -1), (1, -1 ), (2, -1), # 5   6   7   8  9   North = 7
              (-2, 0),(-1, 0),           (1,0),    (2, 0),  # 10  11      12 13  West = 11, East = 12
              (-2, 1),(-1, 1),  (0, 1),  (1,1),    (2, 1),  # 14  15  16  17 18  South = 16
              (-2, 2),(-1, 2),  (0, 2),  (1,2),    (2, 2))  # 19  20  21  22 23
    nList = list(game_map.contents[(square.y + dy) % game_map.height][(square.x + dx) % game_map.width] for dx, dy in combos if dx or dy)
    return nList

#Go through edge pieces from top to bottom left to right
#return priority and direction
def doEdge(edgePieces):
    moves = list()
    for y, dv in edgePieces.items():
        for x, value in dv.items():
            if not value[0]: #check if already moved
                square = game_map.contents[y][x]
                moves, edgePieces = moveEdge(square, moves, edgePieces)
    return moves, edgePieces
    


#Routine returns lists reordered to allow movements to be from opposite ends
#so a list of [1, 2, 3, 4] is returned as [1, 4, 2, 3] 
def reorderList(dList, start, end):
    listCount = end - start+1
    listHalf = listCount // 2
    listEven = True
    dIndex = []
    if (listCount % 2 == 1):
        listEven = False
    for temp in range(listHalf):
        dIndex.append(dList[temp+start])
        dIndex.append(dList[end-temp])
    if listCount%2 ==1:
        dIndex.append(dList[end - listHalf])
    return dIndex

#Takes a dictionary, grabs the keys out and puts them in order in a list.
#This then calls reorderList to work its magic to allow it to work from outside in.
def orderDictIndex(dictionary):
    dList = []
    dIndex = []
    oDict = OrderedDict(sorted(dictionary.items()))
    for read, temp in oDict.items():
        dList.append(read)
    start = end = 0
    count = len(dList)
    ptr = dList[0]
    for read in range(count):
        if (dList[read] == ptr):
            if read !=0:
                end +=1
            ptr +=1
            if read == (count-1):
                dIndex += reorderList(dList, start, end)
        else:
            dIndex += reorderList(dList, start, end)
            if read == (count-1):
                dIndex.append(dList[read])
            else:
                end +=1
                start = end
                ptr = dList[read] +1
    return dIndex


#does all moves for non-edge pieces
def doCenter(moves, centerPieces, edgePieces):
    move = None
    yList = orderDictIndex(centerPieces)
    for cnt in range(len(yList)):
        y = yList[cnt]
        xList = orderDictIndex(centerPieces[y])
        for cnt2 in range(len(xList)):
            x = xList[cnt2]
            if not centerPieces[y][x][0]: #check if already moved
                square = game_map.contents[y][x]
                if (square.strength > (square.production * 3)):
                    #next four lines are default move
                    direction, totalDistance = findNearestEnemy(square)
                    move = Move(square, direction)
                    centerPieces[y][x][1] = 100
                    centerPieces[y][x][0] = True
                    if square.strength > 100: #If strength is over 100 lets move regardless
                        direction, distance = findNearestEnemy(square)
                        if (direction!=4) and (distance > 0):
                            move = Move(square, direction)
                        else: # if no high production squares then just randomly move
                            move = Move(square, NORTH if random.random() > 0.3 else WEST)
                else:
                    move = Move(square, STILL)
                    centerPieces[y][x][1] = 50
                    centerPieces[y][x][0] = True
                moves.append(move)
    return moves, centerPieces

logging.info('myID = %s' , myID)
turn = 0
while True:
    logging.info('\nTurn = %s\n' , turn)
    turn +=1
    game_map.get_frame()
    edgePieces, centerPieces =  sortPieces() #sort pieces between edge pieces and center pieces
    moves, edgePieces = doEdge(edgePieces)
    if len(centerPieces) > 0:
        moves, centerPieces = doCenter(moves, centerPieces, edgePieces)
    hlt.send_frame(moves)

