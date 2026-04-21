from cmu_graphics import *
import random
import math
import yaml

# Logic of Game


def loadYAML(filepath):
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
        for line in self.realSolution:
            strippedLine = line.lstrip()
            self.baseLines.append(strippedLine)
            numSpaces = len(line) - len(strippedLine)
            self.correctIndents.append(numSpaces // 2)

    def checkIfFailed(self):
        if self.numTries >= 3 or self.numHints >= 2:
            self.failedQuest = True
        return self.failedQuest

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
        if quest in self.unattempted:
            self.completed.append(quest)
        self.unattempted.remove(quest)

    def failQuest(self, quest):
        if quest in self.unattempted:
            self.unattempted.remove(quest)
        self.failed.append(quest)

    def completeFailedQuest(self, quest):
        self.failed.remove(quest)
        self.completed.append(quest)

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

    def giveCodeHint(self, app, quest):
        # based on personality has a preface and then gives the line of code
        if quest.numHints >= 2:
            return "I've helped as much as I can. Give it a try!"
        quest.numHints += 1
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
        self.indentCount = 0

    def shiftBrick(self, direction):
        if direction == 'left' and self.indentCount > 0:
            self.indentCount -= 1
        elif direction == 'right':
            self.indentCount += 1

# Graphics!


def onAppStart(app):
    app.width = 800
    app.height = 600
    # grab quests from yaml file
    app.questData = loadYAML('quests.yaml')
    app.characterData = loadYAML('characters.yaml')
    app.teachingData = loadYAML('teaching.yaml')
    app.dialogueData = loadYAML('dialogue.yaml')
    # Characters
    app.headmasters = {}
    for h in app.characterData['headmasters']:
        app.headmasters[h['name']] = Headmaster(h['name'], h['greeting'])
    app.tas = {}
    for t in app.characterData['tas']:
        app.tas[t['name']] = TA(
            t['name'], t['personality'], t['greeting'],
            t['hintPreface'], t['selectable'])
    app.selectableTAs = [ta for ta in app.tas.values() if ta.selectable]
    app.allTAs = list(app.tas.values())
    # Chosen characters (set during selection screens)
    app.chosenHeadmaster = None
    app.chosenTAs = []               # will hold 2 TAs
    app.previewCharacter = None
    app.currentLevel = 1
    app.levelManager = LevelManager(
        app.currentLevel, app.gameData['levels'][app.currentLevel])
    app.currentQuest = None
    app.bricks = []
    app.currentQuestFailed = False
    app.draggedBrick = None
    app.dragOffsetX = 0
    app.dragOffsetY = 0
    app.selectedBrick = None
    app.activeTAs = []  # TAs for a quest
    # dialogue system setup
    app.dialogueSpeaker = None
    app.dialogueLines = []
    app.dialogueIndex = 0
    app.dialogueOnFinish = None
    app.dialogueText = ''
    app.state = 'Headmaster Select'

#  DIALOGUE SYSTEM EXECUTION
# When the user clicks Next, we advance one line. When we run out of lines (or user
# click Skip), we call app.dialogueOnFinish() to transition states.


def startDialogue(app, speaker, lines, onFinish):
    app.dialogueSpeaker = speaker
    app.dialogueLines = lines
    app.dialogueIndex = 0
    app.dialogueOnFinish = onFinish


def advanceDialogue(app):
    app.dialogueIndex += 1
    if app.dialogueIndex >= len(app.dialogueLines):
        finishDialogue(app)


def skipDialogue(app):
    finishDialogue(app)


def finishDialogue(app):
    callback = app.dialogueOnFinish
    app.dialogueSpeaker = None
    app.dialogueLines = []
    app.dialogueIndex = 0
    app.dialogueOnFinish = None
    if callback is not None:
        callback()


def drawDialogueBox(app):
    # Bottom-of-screen dialogue box
    drawRect(40, 420, 720, 140, fill='white', border='black', borderWidth=2)
    if app.dialogueSpeaker is not None:
        drawLabel(app.dialogueSpeaker.name, 60, 440,
                  size=16, bold=True, align='left')
    if 0 <= app.dialogueIndex < len(app.dialogueLines):
        currentLine = app.dialogueLines[app.dialogueIndex]
        drawLabel(currentLine, 60, 480, size=14,
                  align='left', fill='black')
    # Next button
    drawRect(600, 510, 60, 30, fill='lightGreen', border='black')
    drawLabel('Next', 630, 525, size=14, bold=True)
    # Skip button
    drawRect(680, 510, 60, 30, fill='lightGray', border='black')
    drawLabel('Skip', 710, 525, size=14, bold=True)


def clickedNextButton(mx, my):
    return 600 <= mx <= 660 and 510 <= my <= 540


def clickedSkipButton(mx, my):
    return 680 <= mx <= 740 and 510 <= my <= 540

#  HEADMASTER SELECTION
# Click a headmaster -> preview their greeting. Click the same headmaster
# again -> confirm and move on to TA Select.


def drawHeadmasterSelect(app):
    drawRect(0, 0, app.width, app.height, fill='lightBlue')
    drawLabel('Choose Your Headmaster', app.width / 2, 60,
              size=28, bold=True)
    drawLabel('Click a headmaster to hear their greeting. Click again to confirm.',
              app.width / 2, 100, size=14)
    headmasters = list(app.headmasters.values())
    for i in range(len(headmasters)):
        x = 150 + i * 300
        y = 180
        drawCharacterCard(app, headmasters[i], x, y,
                          isSelected=(app.previewCharacter is headmasters[i]))
    if app.previewCharacter is not None:
        drawLabel(f'"{app.previewCharacter.greeting}"',
                  app.width / 2, 420, size=14, italic=True)
        drawLabel('Click again to confirm your choice!',
                  app.width / 2, 450, size=14, bold=True, fill='darkGreen')


def drawCharacterCard(app, character, x, y, isSelected=False):
    # Placeholder rendering. Later you'll swap drawRect for drawImage.
    borderCol = 'gold' if isSelected else 'black'
    borderW = 4 if isSelected else 2
    drawRect(x, y, 200, 200, fill='lightYellow',
             border=borderCol, borderWidth=borderW)
    drawLabel('[portrait]', x + 100, y + 100, size=14, fill='gray')
    drawLabel(character.name, x + 100, y + 220, size=16, bold=True)


def handleHeadmasterSelectClick(app, mx, my):
    headmasters = list(app.headmasters.values())
    for i in range(len(headmasters)):
        x = 150 + i * 300
        y = 180
        if x <= mx <= x + 200 and y <= my <= y + 200:
            clicked = headmasters[i]
            if app.previewCharacter is clicked:
                # Second click = confirm
                app.chosenHeadmaster = clicked
                app.previewCharacter = None
                app.state = 'TA Select'
            else:
                # First click = preview greeting
                app.previewCharacter = clicked
            return

#  TA SELECTION
# Player picks 2 TAs from the selectable pool. Same click-to-preview then
# click-again-to-confirm pattern, but we need two confirms.


def pickActiveTAs(app):
    # Normally it's the 2 chosen TAs. 5% chance per quest: replace one of
    # them with a randomly picked TA from all TAs.
    app.activeTAs = list(app.chosenTAs)
    if random.random() < 0.05:
        replaceIdx = random.randint(0, 1)
        candidates = [t for t in app.allTAs if t not in app.activeTAs]
        if len(candidates) > 0:
            app.activeTAs[replaceIdx] = random.choice(candidates)


def drawTASelect(app):
    drawRect(0, 0, app.width, app.height, fill='lightYellow')
    drawLabel('Choose Your Two TAs', app.width / 2, 40, size=28, bold=True)
    drawLabel(f'Chosen: {len(app.chosenTAs)} / 2',
              app.width / 2, 80, size=16)
    drawLabel('Click a TA to hear them. Click again to confirm.',
              app.width / 2, 105, size=13)

    TAs = app.selectableTAs
    for i in range(len(TAs)):
        x = 80 + i * 220
        y = 150
        alreadyChosen = TAs[i] in app.chosenTAs
        isPreview = (app.previewCharacter is TAs[i])
        drawTACard(app, TAs[i], x, y, alreadyChosen, isPreview)

    if app.previewCharacter is not None and app.previewCharacter not in app.chosenTAs:
        drawLabel(f'"{app.previewCharacter.greeting}"',
                  app.width / 2, 400, size=14, italic=True)
        drawLabel('Click again to add them to your team!',
                  app.width / 2, 430, size=14, bold=True, fill='darkGreen')


def drawTACard(app, TA, x, y, alreadyChosen, isPreview):
    if alreadyChosen:
        fillCol = 'lightGreen'
        borderCol = 'darkGreen'
    elif isPreview:
        fillCol = 'lightYellow'
        borderCol = 'gold'
    else:
        fillCol = 'white'
        borderCol = 'black'
    drawRect(x, y, 180, 200, fill=fillCol, border=borderCol, borderWidth=3)
    drawLabel('[portrait]', x + 90, y + 100, size=14, fill='gray')
    drawLabel(TA.name, x + 90, y + 220, size=16, bold=True)
    drawLabel(f'({TA.personality})', x + 90, y + 240, size=12, italic=True)
    if alreadyChosen:
        drawLabel('CHOSEN', x + 90, y + 175, size=14, bold=True,
                  fill='darkGreen')


def handleTASelectClick(app, mx, my):
    tas = app.selectableTAs
    for i in range(len(tas)):
        x = 80 + i * 220
        y = 150
        if x <= mx <= x + 180 and y <= my <= y + 200:
            clicked = tas[i]
            if clicked in app.chosenTAs:
                return          # already chosen, ignore
            if app.previewCharacter is clicked:
                # Confirm this TA
                app.chosenTAs.append(clicked)
                app.previewCharacter = None
                if len(app.chosenTAs) == 2:
                    enterLevelIntro(app)
            else:
                app.previewCharacter = clicked
            return

#  LEVEL INTRO


def enterLevelIntro(app):
    # Called when we need to start (or restart) a level's teaching.
    app.levelManager = LevelManager(
        app.currentLevel, app.questData['levels'][app.currentLevel])
    app.state = 'Level Intro'
    introLines = app.teachingData['levels'][app.currentLevel]['introDialogue']
    startDialogue(app, app.chosenHeadmaster, introLines,
                  onFinish=lambda: startNextQuest(app))


def drawLevelIntro(app):
    drawRect(0, 0, app.width, app.height, fill='lightBlue')
    drawLabel(f'Level {app.currentLevel}: {app.levelManager.topic}',
              app.width / 2, 50, size=26, bold=True)
    drawCharacterCard(app, app.chosenHeadmaster, 300, 120)
    drawDialogueBox(app)

# INPUT HANDLERS


def onMousePress(app, mouseX, mouseY):
    if app.state == 'Headmaster Select':
        handleHeadmasterSelectClick(app, mouseX, mouseY)
    elif app.state == 'TA Select':
        handleTASelectClick(app, mouseX, mouseY)
    elif app.state == 'Level Intro':
        if clickedNextButton(mouseX, mouseY):
            advanceDialogue(app)
        elif clickedSkipButton(mouseX, mouseY):
            skipDialogue(app)
    elif app.state == 'Playing':
        executePlayingClick(app, mouseX, mouseY)
    elif app.state == 'Quest Transition':
        if 300 <= mouseX <= 500 and 450 <= mouseY <= 500:
            startNextQuest(app)


def executePlayingClick(app, mouseX, mouseY):
    # Check Code button
    if 650 <= mouseX <= 780 and 50 <= mouseY <= 90:
        evaluateSolution(app)
        return
    # TA Hint button
    elif 650 <= mouseX <= 780 and 110 <= mouseY <= 150:
        giveHintFromActiveTA(app)
        return
    # Headmaster Tutorial button
    elif 650 <= mouseX <= 780 and 170 <= mouseY <= 210:
        app.dialogueText = (
            f"{app.chosenHeadmaster.name}: "
            f"{app.teachingData['levels'][app.currentLevel]['helpText']}")
        Headmaster.giveHelp()
    for brick in reversed(app.bricks):
        if brick.x <= mouseX <= brick.x + brick.width and brick.y <= mouseY <= brick.y + brick.height:
            app.draggedBrick = brick
            app.selectedBrick = brick
            app.dragOffsetX = mouseX - brick.x
            app.dragOffsetY = mouseY - brick.y
            return


def giveHintFromActiveTA(app):
    # First hint: random active TA. Second hint: the other one.
    q = app.currentQuest
    if q.numHints == 0:
        hinter = random.choice(app.activeTAs)
    elif q.numHints == 1:
        # Pick the one who hasn't spoken yet — but we didn't store that.
        # Simplest: pick randomly again (close enough for v1) — or track.
        hinter = random.choice(app.activeTAs)
    else:
        app.dialogueText = "No more hints available!"
        return
    hinter.giveCodeHint(app, q)


def startNextQuest(app):
    app.currentQuest = app.levelManager.getNextQuest()
    if app.currentQuest is None:
        # Level finished — advance to next level
        app.currentLevel += 1
        if app.currentLevel in app.gameData['levels']:
            app.levelManager = LevelManager(
                app.currentLevel, app.gameData['levels'][app.currentLevel])
            app.state = 'Level Intro'
        else:
            app.state = 'Game Complete'
    pickActiveTAs(app)
    resetQuestUI(app)
    app.state = 'Playing'


def resetQuestUI(app):
    setupBricks(app)
    app.selectedBrick = None
    app.draggedBrick = None
    app.dialogueText = 'Drag blocks into the main area to solve the problem!'


def setupBricks(app):
    app.bricks = []
    scrambled = app.currentQuest.baseLines[:]
    random.shuffle(scrambled)
    for i in range(len(scrambled)):
        app.bricks.append(codeBrick(scrambled[i], 20, 100 + (i * 40)))


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
            gridSlot = rounded((app.draggedBrick.y - 80) / 40)
            # Prevent the block from snapping completely off the top of the screen
            gridSlot = max(0, gridSlot)
            app.draggedBrick.y = 80 + (gridSlot * 40)
        else:
            # If they drop it on the left side, snap it back to a neat column in the Block Bank
            app.draggedBrick.x = 20
        app.draggedBrick = None


def onKeyPress(app, key):
    if app.state != 'Playing' or app.selectedBrick is None:
        return
    if key == 'right':
        app.selectedBrick.shiftBrick('right')
    elif key == 'left':
        app.selectedBrick.shiftBrick('left')

# SOLUTION CHECKS


def evaluateSolution(app):
    # convert bricks into list, use checkErrors function
    solutionBricks = [b for b in app.bricks if b.x > 300]
    solutionBricks.sort(key=lambda b: b.y)
    if len(solutionBricks) < len(app.currentQuest.realSolution):
        app.dialogueText = 'You must use all blocks to finish the quest!'
        return
    playerLines = [b.text for b in solutionBricks]
    playerIndents = [b.indentCount for b in solutionBricks]
    masterLines = app.currentQuest.baseLines
    masterIndents = app.currentQuest.correctIndents
    lineMistakes = 0
    indentMistakes = 0
    maxDistance = 0
    for i in range(len(masterLines)):
        if i >= len(playerLines) or playerLines[i] != masterLines[i]:
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
        app.currentQuest.numTries += 1
        app.dialogueText = "Minor Error: A line is slightly out of place or needs an indent shift."
        checkIfDead(app)
    # Major Error: Everything else
    else:
        app.currentQuest.numTries += 1
        app.dialogueText = "Major Error: The code is way off. Please re-evaluate your logic."
        checkIfDead(app)


def checkIfDead(app):
    if app.currentQuest.checkIfFailed():
        app.levelManager.failQuest(app.currentQuest)
        app.dialogueText = "Quest failed! We'll try this one again later."
        app.state = 'Quest Transition'
    else:
        app.dialogueText += f"Tries Left: {3 - app.currentQuest.numTries}/3"

# DRAWING STUFF


def redrawAll(app):
    # case on states
    if app.state == 'Headmaster Select':
        drawHeadmasterSelect(app)
    elif app.state == 'TA Select':
        drawTASelect(app)
    elif app.state == 'Level Intro':
        drawLevelIntro(app)
    elif app.state == 'Playing':
        drawPlayingScreen(app)
    elif app.state == 'Quest Transition':
        drawRect(0, 0, 800, 600, fill='lightYellow')
        drawLabel(app.dialogueText, 400, 300, size=24)
        drawRect(300, 450, 200, 50, fill='blue')
        drawLabel('Continue', 400, 475, size=20, fill='white')
    elif app.state == 'Game Complete':
        drawRect(0, 0, 800, 600, fill='gold')
        drawLabel('The Dragon can code again!', 400, 260, size=32, bold=True)
        drawLabel('Thank you for saving CS Academy.',
                  400, 320, size=20)


def drawCharacter(person, x, y):
    drawImage(person.picture, x, y, width=20, height=20)
    drawLabel(person.name, x, y + 20, bold=True, fill='white')


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

    # Show active TAs (top-right corner)
    for i in range(len(app.activeTAs)):
        drawLabel(f'TA: {app.activeTAs[i].name}',
                  700, 230 + i * 20, size=12, fill='white')

    # Bricks
    for brick in app.bricks:
        color = 'crimson' if brick.x > 350 else 'lightCoral'
        borderCol = 'yellow' if brick is app.selectedBrick else 'darkSlateGray'
        borderW = 3 if brick is app.selectedBrick else 1
        drawRect(brick.x, brick.y, brick.width, brick.height,
                 fill=color, border=borderCol, borderWidth=borderW)
        indent = brick.indentCount * 20
        drawLabel(brick.text, brick.x + 10 + indent,
                  brick.y + 15, align='left', size=14)


def main():
    runApp()


main()
