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


def checkErrors(quest, userSolution):
    wrongCount = 0
    maxDistance = 0
    for i in range(len(userSolution)):
        if userSolution[i] != quest.realSolution[i]:
            wrongCount += 1
            distance = abs(userSolution[i] - quest.realSolution[i])
            maxDistance = max(distance, maxDistance)
    if wrongCount > 0:
        if wrongCount <= 2 and maxDistance == 1:
            quest.numTries += 1
            return 'Minor Error: A line is slightly out of place or needs an indent shift.'
        else:
            quest.numTries += 1
            return 'Major Error: The code is way off. Please re-evaluate your logic'
    else:
        return 'Perfect! You have found the solution.'


def giveHint(quest, userSolution):
    emptyLines = []
    for i in range(len(quest.realSolution)):
        if not userSolution[i]:
            emptyLines.append(i)
    hintLine = random.choice(emptyLines)
    return (hintLine, quest.realSolution[hintLine])


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
        return greetings[self.personality]

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
        return easierProblem


# Graphics!
def onAppStart(app):
    app.width = 800
    app.height = 600
    # grab quests from yaml file
    app.gameData = loadGameData('quests.yaml')
    app.currentLevel = 1
    app.currentQuestIndex = 0
    app.levelManager = LevelManager(1, app.gameData['levels'][1])
    app.state = 'Level Intro'
    app.currentQuest = None
    loadQuest(app)
    app.currentQuestFailed = False
    app.draggedBrick = None
    app.dialogueText = 'Drag blocks into the main area to solve the problem!'
    app.dragOffsetX = 0
    app.dragOffsetY = 0
    app.userSolution = []

# Written by Gemini!


def loadQuest(app):
    levelQuests = app.gameData['levels'][app.currentLevel]['quests']
    questData = levelQuests[app.currentQuestIndex]
    statement = questData['statement']
    solution = questData['solution']
    questID = questData['id']
    app.currentQuest = Quest(questID, statement, solution)
    app.bricks = []
    scrambled = solution[:]
    random.shuffle(scrambled)
    for i in range(len(scrambled)):
        app.bricks.append(codeBrick(scrambled[i], 20, 100 + (i + 40)))
    app.dialogueText = f'Level {app.currentLevel} - Quest {questID}'

# Written by Gemini!


def advanceToNextQuest(app):
    levelQuests = app.gameData['levels'][app.currentLevel]['quests']
    app.currentQuestIndex += 1
    if app.currentQuestIndex >= len(levelQuests):
        app.currentLevel += 1
        app.currentQuestIndex = 0
        if app.currentLevel not in app.gameData['levels']:
            app.dialogueText = 'You have successfully saved the Dragon! Yippee!'
            app.bricks = []
            return
    loadQuest(app)


class Button:
    def __init__(self, buttonName, buttonColor, left, top, width, height):
        self.buttonName = buttonName
        self.buttonColor = buttonColor
        self.left = left
        self.top = top
        self.width = width
        self.height = height


class codeBrick:
    def __init__(self, linePosition, text, x, y):
        self.linePosition = linePosition
        self.text = text
        self.x = x
        self.y = y
        self.width = 280
        self.height = 30
        self.isDragging = False

    def shiftBrick(self, direction):
        if direction == 'left':
            if self.text[0].isspace():
                self.text = self.text[1:]
        elif direction == 'right':
            self.text = '\t' + self.text


def onMousePress(app, mouseX, mouseY):
    # if clicked on button, figure out which button and execute it
    # if clicked on a codeBrick, highlight it
    checkButtonClick(app, mouseX, mouseY)


def checkButtonClick(app, mouseX, mouseY):
    # figure out which button, if any, were clicked, and execute it
    pass


def onMouseDrag(app, mouseX, mouseY):
    # drag codeBricks from their holding cell into position
    if app.draggedBrick != None:
        app.draggedBrick.x = mouseX - app.dragOffsetX
        app.draggedBrick.y = mouseY - app.dragOffsetY


def onMouseRelease(app, mouseX, mouseY):
    if app.draggedBrick != None:
        # snap the brick to a line
        app.draggedBrick = None


def drawCharacter(person, x, y):
    drawImage(person.picture, x, y, width=20, height=20)
    drawLabel(person.name, x, y + 20, bold=True, fill='white')


def evaluateSolution(bricks, quest):
    # convert bricks into list, use checkErrors function
    solutionBricks = [b for b in app.bricks if b.x > 350]
    solutionBricks.sort(key=lambda b: b.y)
    userSolution = [b.text for b in solutionBricks]
    print(checkErrors(quest, userSolution))
    if userSolution == app.currentQuest.realSolution:
        app.currentQuest.questCompleted = True
    else:
        app.currentQuest.numTries += 1
        if app.currentQuest.checkIfFailed():
            app.dialogueText = "Quest failed! You've run out of tries or hints."
        else:
            app.dialogueText = f"Tries Left: {3 - app.currentQuest.numTries}/3"


def redrawAll(app):
    # case on states
    if app.state == 'Level Intro':
        drawRect(0, 0, 800, 600, fill='lightblue')
        drawLabel(app.levelManager.topic, 400, 200, size=30, bold=True)
        drawLabel(app.levelManager.introText, 400,
                  300, size=16)  # Headmaster teaching
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
