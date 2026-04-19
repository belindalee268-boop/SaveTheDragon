from cmu_graphics import *
import random
import math
import yaml

# Logic of Game


def loadGameData(filepath):
    with open(filepath, 'r') as file:
        data = yaml.safe_load(file)
    return data


class Quest:
    def __init__(self, questID, problemStatement, realSolution):
        self.questID = questID
        self.problemStatement = problemStatement
        self.realSolution = realSolution
        self.numTries = 0
        self.failedQuest = False
        self.numHints = 0
        self.questCompleted = False
        self.baseLines = []
        self.correctIndents = []
        for line in realSolution:
            strippedLine = line.lstrip()
            self.baseLines.append(strippedLine)
            numSpaces = len(line) - len(strippedLine)
            self.correctIndents.append(numSpaces // 4)

    def checkIfFailed(self):
        if self.numTries >= 3 or self.numHints >= 2:
            self.failedQuest = True
        return self.failedQuest

    def updateNumTries(self, didSucceed):
        if not didSucceed:
            self.numTries += 1

    def updateNumHints(self, gotHint):
        if gotHint:
            self.numHints += 1

    def __repr__(self):
        return self.problemStatement

    def __eq__(self, other):
        return isinstance(other, Quest) and self.problemStatement == other.problemStatement and self.realSolution == other.realSolution

    def __hash__(self):
        return hash(str(self))


class LevelManager:
    def __init__(self, levelNum, questsList):
        self.levelNum = levelNum
        self.topic = questsList['topic']
        self.unattempted = []
        for quest in questsList['quests']:
            self.unattempted.append(
                Quest(quest['id'], quest['statement'], quest['solution']))
        self.completed = []
        self.failed = []

    def completeQuest(self, quest):
        self.completed.append(quest)
        self.unattempted.remove(quest)

    def failQuest(self, quest):
        self.failed.append(quest)
        self.unattempted.remove(quest)

    def completeFailedQuest(self, quest):
        self.failed.remove(quest)
        self.completed.append(quest)

    def getLevelManager(self, level):
        if level == self.levelNum:
            return self
        else:
            return None

    def getNextQuest(self):
        if len(self.unattempted) > 0:
            return self.unattempted.pop(0)
        elif len(self.failed) > 0:
            random.shuffle(self.failed)
            retryQuest = self.failed.pop(0)
            retryQuest.numTries = 0
            retryQuest.numHints = 0
            retryQuest.failedQuest = False
            return retryQuest
        else:
            return None


class TA:
    def __init__(self, name, personality, picture):
        self.name = name
        self.personality = personality
        self.picture = picture

    def giveGreeting(self):
        # return greetings[self.personality]
        pass

    def giveCodeHint(self, quest, codeLine):
        # based on personality has a preface and then gives the line of code
        if quest.numHints >= 2:
            return "I've helped as much as I can. Give it a try!"
        quest.numHints += 1


class Headmaster:
    def __init__(self, name, picture):
        self.name = name
        self.picture = picture

    def giveGreeting(self):
        if self.name == 'Lauren Sands':
            return "I'm Lauren! Let's get ready to save the Dragon!"
        elif self.name == 'David Kosbie':
            return 'I am Headmaster Kosbie. I will guide you through everything you will encounter.'

    def giveHelp(self):
        pass


# Graphics!
def onAppStart(app):
    app.width = 800
    app.height = 600
    # grab quests from yaml file
    app.gameData = loadGameData('quests.yaml')
    app.currentLevel = 1
    app.levelManager = LevelManager(
        app.currentLevel, app.gameData['levels'][app.currentLevel])
    app.state = 'Level Intro'
    app.currentQuest = app.levelManager.getNextQuest()
    app.bricks = []
    setupBricks(app)
    app.currentQuestFailed = False
    app.draggedBrick = None
    app.dialogueText = 'Drag blocks into the main area to solve the problem!'
    app.dragOffsetX = 0
    app.dragOffsetY = 0


class Button:
    def __init__(self, buttonName, buttonColor, left, top, width, height):
        self.buttonName = buttonName
        self.buttonColor = buttonColor
        self.left = left
        self.top = top
        self.width = width
        self.height = height


class codeBrick:
    def __init__(self, text, x, y):
        self.text = text
        self.x = x
        self.y = y
        self.width = 280
        self.height = 30
        self.isDragging = False

    def shiftBrick(self, direction):
        if direction == 'left' and self.indentCount > 0:
            self.indentCount -= 1
        elif direction == 'right':
            self.indentCount += 1
        self.text = ('    ' * self.indentCount) + self.baseText


def onMousePress(app, mouseX, mouseY):
    if app.state == 'Level Intro':
        if 300 <= mouseX <= 500 and 450 <= mouseY <= 500:
            app.currentQuest = app.levelManager.getNextQuest()
            setupBricks(app)
            app.state = 'Playing'
    elif app.state == 'Playing':
        executePlayingClick(app, mouseX, mouseY)
    elif app.state == 'Quest Transition':
        if 300 <= mouseX <= 500 and 450 <= mouseY <= 500:
            app.currentQuest = app.levelManager.getNextQuest()
            if app.currentQuest == None:
                app.currentLevel += 1
                app.levelManager = LevelManager(
                    app.currentLevel, app.gameData['levels'][app.currentLevel])
                app.state = 'Level Intro'
            else:
                setupBricks(app)
                app.state = 'Playing'


def setupBricks(app):
    app.bricks = []
    scrambled = app.currentQuest.realSolution[:]
    random.shuffle(scrambled)
    for i in range(len(scrambled)):
        app.bricks.append(codeBrick(scrambled[i], 20, 100 + (i * 40)))


def executePlayingClick(app, mouseX, mouseY):
    if 650 <= mouseX <= 780 and 50 <= mouseY <= 90:
        evaluateSolution(app)
    elif 650 <= mouseX <= 780 and 110 <= mouseY <= 150:
        giveTAHint(app)
    elif 650 <= mouseX <= 780 and 170 <= mouseY <= 210:
        app.dialogueText = "Headmaster: Let's try an easier problem together."
        Headmaster.giveHelp()
    for brick in reversed(app.bricks):
        if brick.x <= mouseX <= brick.x + brick.width and brick.y <= mouseY <= brick.y + brick.height:
            app.draggedBrick = brick
            app.dragOffsetX = mouseX - brick.x
            app.dragOffsetY = mouseY - brick.y
            app.bricks.remove(brick)


def giveTAHint(app, quest):
    missingIndices = []
    for i in range(len(quest.realSolution)):
        expectedText = quest.realSolution[i]
        expectedY = 80 + (i * 40)
        # Check if there is already a brick at the exact right spot with the exact right text
        brickIsCorrectlyPlaced = False
        for brick in app.bricks:
            if brick.text == expectedText and brick.x == 360 and brick.y == expectedY:
                brickIsCorrectlyPlaced = True
                break
        # If the slot doesn't have the correct brick
        if not brickIsCorrectlyPlaced:
            missingIndices.append(i)
    if len(missingIndices) == 0:
        app.dialogueText = "TA: Everything looks perfect! Click 'Check Code'."
    hintIndex = random.choice(missingIndices)
    targetText = quest.realSolution[hintIndex]
    targetBrick = None
    for brick in app.bricks:
        if brick.text == targetText:
            if not (brick.x == 360 and brick.y == 80 + (hintIndex * 40)):
                targetBrick = brick
                break
    # Snap it into place and update the UI
    if targetBrick != None:
        targetBrick.x = 360
        targetBrick.y = 80 + (hintIndex * 40)
        app.bricks.remove(targetBrick)
        app.bricks.append(targetBrick)
        app.dialogueText = f"TA: I placed line {hintIndex + 1} for you! (Hints left: {2 - quest.numHints})"


def onMouseDrag(app, mouseX, mouseY):
    # drag codeBricks from their holding cell into position
    if app.draggedBrick != None:
        app.draggedBrick.x = mouseX - app.dragOffsetX
        app.draggedBrick.y = mouseY - app.dragOffsetY


def onMouseRelease(app, mouseX, mouseY):
    if app.draggedBrick != None:
        # If the player drags the block past x=300, snap it into the Solution Area
        if app.draggedBrick.x > 300:
            app.draggedBrick.x = 360
            gridSlot = round((app.draggedBrick.y - 80) / 40)
            # Prevent the block from snapping completely off the top of the screen
            gridSlot = max(0, gridSlot)
            app.draggedBrick.y = 80 + (gridSlot * 40)
        else:
            # If they drop it on the left side, snap it back to a neat column in the Block Bank
            app.draggedBrick.x = 20
        app.draggedBrick = None


def drawCharacter(person, x, y):
    drawImage(person.picture, x, y, width=20, height=20)
    drawLabel(person.name, x, y + 20, bold=True, fill='white')


def evaluateSolution(app):
    # convert bricks into list, use checkErrors function
    solutionBricks = [b for b in app.bricks if b.x > 300]
    solutionBricks.sort(key=lambda b: b.y)
    if len(solutionBricks) < len(app.currentQuest.realSolution):
        app.dialogueText = 'You must use all blocks to finish the quest!'
    playerLines = [b.text for b in solutionBricks]
    playerIndents = [b.indent for b in solutionBricks]
    masterLines = app.currentQuest.baseLines
    masterIndents = app.currentQuest.correctIndents
    lineMistakes = 0
    indentMistakes = 0
    maxDistance = 0
    for i in range(len(playerLines)):
        if playerLines[i] != masterLines[i]:
            lineMistakes += 1
            if playerLines[i] in masterLines:
                correctIdx = masterLines.index(playerLines[i])
                distance = abs(correctIdx - i)
                maxDistance = max(maxDistance, distance)
        if playerIndents[i] != masterIndents[i]:
            indentMistakes += 1
    if lineMistakes == 0 and indentMistakes == 0:
        app.currentQuest.questCompleted = True
        app.dialogueText = "Perfect! You have found the solution."
        app.state = 'Quest Transition'
    # Minor Error: Small swap (2 lines) OR 2 indent mistakes
    elif (lineMistakes <= 2 and maxDistance <= 1) or (lineMistakes == 0 and indentMistakes == 2):
        app.currentQuest.updateNumTries(False)
        app.dialogueText = "Minor Error: A line is slightly out of place or needs an indent shift."
        checkIfDead(app)
    # Major Error: Everything else
    else:
        app.currentQuest.updateNumTries(False)
        app.dialogueText = "Major Error: The code is way off. Please re-evaluate your logic."
        checkIfDead(app)


def checkIfDead(app):
    if app.currentQuest.checkIfFailed():
        app.levelManager.failQuest(app.currentQuest)
        app.dialogueText = "Quest failed! We'll try this one again later."
        app.state = 'Quest Transition'
    else:
        app.dialogueText = f"Tries Left: {3 - app.currentQuest.numTries}/3"


def redrawAll(app):
    # case on states
    if app.state == 'Level Intro':
        drawRect(0, 0, 800, 600, fill='lightblue')
        drawLabel(app.levelManager.topic, 400, 200, size=30, bold=True)
        # drawLabel(app.levelManager.introText, 400,
        # 300, size=16)  # Headmaster teaching
        drawRect(300, 450, 200, 50, fill='green')
        drawLabel("Start Level", 400, 475, size=20, fill='white')
    elif app.state == 'Playing':
        drawPlayingScreen(app)
    elif app.state == 'Quest Transition':
        drawRect(0, 0, 800, 600, fill='lightyellow')
        # "Good job!" or "We'll retry later!"
        drawLabel(app.dialogueText, 400, 300, size=24)
        drawRect(300, 450, 200, 50, fill='blue')
        drawLabel("Continue", 400, 475, size=20, fill='white')


def drawPlayingScreen(app):
    drawRect(0, 0, 800, 600, fill='darkSlateGray')
    drawRect(350, 80, 280, 400, fill='lightSlateGray', border='steelBlue')
    drawLabel('Solution Area', 490, 65, size=16, bold=True)
    drawLabel('Block Bank', 160, 65, size=16, bold=True)

    # Problem
    drawLabel(f'Quest: {app.currentQuest.problemStatement}',
              400, 20, size=18, bold=True)
    drawRect(50, 500, 700, 80, fill='lawnGreen', border='steelBlue')
    drawLabel(app.dialogueText, 400, 540, size=16)

    # Buttons
    drawRect(650, 50, 130, 40, fill='mediumSpringGreen', border='steelBlue')
    drawLabel('Check Code', 715, 70, size=14, bold=True, fill='royalBlue')
    drawRect(650, 110, 130, 40, fill='deepSkyBlue', border='steelBlue')
    drawLabel('Ask for TA Hint', 715, 130, size=14, bold=True, fill='white')
    drawRect(650, 170, 130, 40, fill='white', border='steelBlue')
    drawLabel('Ask Headmaster for Help', 715, 190, size=14, bold=True)

    # Bricks
    for brick in app.bricks:
        color = 'crimson' if brick.x > 350 else 'lightCoral'
        drawRect(brick.x, brick.y, brick.width, brick.height,
                 fill=color, border='darkSlateGray')
        drawLabel(brick.text, brick.x + 10,
                  brick.y + 15, align='left', size=14)


def main():
    runApp()


main()
