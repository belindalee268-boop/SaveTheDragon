from cmu_graphics import *
import random
import yaml
# Classes and initialization


def loadYAML(filepath):
    with open(filepath, 'r') as file:
        data = yaml.safe_load(file)
    return data


def goToScreen(app, screenName):
    app.currentScreen = screenName
    setActiveScreen(screenName)


def wrapText(text, maxCharsPerLine):
    # Split text into a list of lines, none longer than maxCharsPerLine.
    # Breaks on spaces so words aren't split.
    words = text.split(' ')
    lines = []
    currentLine = ''
    for word in words:
        if len(currentLine) + len(word) + 1 <= maxCharsPerLine:
            if currentLine == '':
                currentLine = word
            else:
                currentLine += ' ' + word
        else:
            if currentLine != '':
                lines.append(currentLine)
            currentLine = word
    if currentLine != '':
        lines.append(currentLine)
    return lines


def initializeData(app):
    # Load all YAML files.
    app.questData = loadYAML('quests.yaml')
    app.characterData = loadYAML('characters.yaml')
    app.teachingData = loadYAML('teaching.yaml')
    app.dialogueData = loadYAML('dialogue.yaml')


def initializeCharacters(app):
    # Build Headmaster
    app.headmasters = {}
    for h in app.characterData['Headmasters']:
        app.headmasters[h['name']] = Headmaster(
            h['name'], h['greeting'], h['picture'])
    # Build TA
    app.TAs = {}
    for t in app.characterData['TAs']:
        app.TAs[t['name']] = TA(
            t['name'], t['personality'], t['greeting'],
            t['hintPreface'], t['picture'])
    app.selectableTAs = list(app.TAs.values())
    app.allTAs = list(app.TAs.values())
    # Chosen during selection screens
    app.chosenHeadmaster = None
    app.chosenTAs = []


def initializeGameState(app):
    # Set up quest, brick, and tutorial state on app launch.
    app.currentLevel = 1
    app.levelManager = None
    app.currentQuest = None
    app.levelTeachCount = 0
    app.activeTAs = []
    app.nextQuestTAs = []
    app.dropInForNextQuest = None
    app.firstHintTA = None
    app.bricks = []
    app.draggedBrick = None
    app.selectedBrick = None
    app.dragOffsetX = 0
    app.dragOffsetY = 0
    app.tutorialSteps = []
    app.tutorialStepIndex = 0
    app.tutorialCodeLines = []
    app.screenBeforeTutorial = None
    app.returningFromTutorial = False
    app.transitionLines = []
    app.transitionIndex = 0
    app.dialogueText = ''   # green status-bar in Playing screen
    # initialize for inserting
    app.brickOriginalX = 0
    app.brickOriginalY = 0


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
        self.totalQuests = len(self.unattempted)
        self.completed = []
        self.failed = []

    def completeQuest(self, quest):
        if quest in self.unattempted:
            self.unattempted.remove(quest)
        self.completed.append(quest)

    def failQuest(self, quest):
        if quest in self.unattempted:
            self.unattempted.remove(quest)
        self.failed.append(quest)

    def getNextQuest(self):
        # Return next unattempted quest only. Returns None when unattempted empty.
        if len(self.unattempted) > 0:
            return self.unattempted.pop(0)
        return None

    def getRetryQuest(self):
        # Return a random failed quest for retry, or None if none left.
        if len(self.failed) > 0:
            random.shuffle(self.failed)
            retryQuest = self.failed.pop(0)
            retryQuest.numTries = 0
            retryQuest.numHints = 0
            retryQuest.failedQuest = False
            return retryQuest
        return None


class TA:
    def __init__(self, name, personality, greeting, hintPreface, picture):
        self.name = name
        self.personality = personality
        self.greeting = greeting
        self.hintPreface = hintPreface
        self.picture = picture

    def giveGreeting(self):
        return self.greeting

    def giveCodeHint(self, app, quest):
        # based on personality has a preface and then gives the line of code
        if quest.numHints >= 2:
            return f"{self.name}: I've helped as much as I can. Give it a try!"
        missingIndices = []
        for i in range(len(quest.baseLines)):
            expectedText = quest.baseLines[i]
            expectedY = 120 + (i * 40)
            # Check if there is already a brick at the exact right spot with the exact right text
            correctlyPlaced = False
            for brick in app.bricks:
                if brick.text == expectedText and brick.x == 360 and brick.y == expectedY:
                    correctlyPlaced = True
                    break
            # If the slot doesn't have the correct brick
            if not correctlyPlaced:
                missingIndices.append(i)
        if len(missingIndices) == 0:
            app.dialogueText = f"{self.name}: Everything looks perfect! Click 'Check Code'."
            return
        quest.numHints += 1
        hintIndex = random.choice(missingIndices)
        targetText = quest.baseLines[hintIndex]
        targetBrick = None
        for brick in app.bricks:
            if brick.text == targetText:
                if not (brick.x == 360 and brick.y == 120 + (hintIndex * 40)):
                    targetBrick = brick
                    break
        # Snap it into place and update the UI
        if targetBrick != None:
            targetBrick.indentCount = quest.correctIndents[hintIndex]
            insertIntoSolution(app, targetBrick, 120 + hintIndex * 40)
            app.bricks.remove(targetBrick)
            app.bricks.append(targetBrick)
            app.dialogueText = (
                f"{self.name}: {self.hintPreface} I placed line {hintIndex + 1} for you!"
                f"(Hints left: {2 - quest.numHints})")


class Headmaster:
    def __init__(self, name, greeting, picture):
        self.name = name
        self.picture = picture
        self.greeting = greeting

    def giveGreeting(self):
        return self.greeting


class Button:
    def __init__(self, label, x, y, w, h, onClick,
                 fill='lightGray', labelFill='black',
                 border='black', labelSize=14, labelBold=True, useOpacity=True):
        self.label = label
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.onClick = onClick      # function to call when clicked
        self.fill = fill
        self.labelFill = labelFill
        self.border = border
        self.labelSize = labelSize
        self.labelBold = labelBold
        self.isHovered = False
        self.useOpacity = useOpacity

    def draw(self):
        if self.useOpacity:
            currentOpacity = 100 if self.isHovered else 70
        else:
            currentOpacity = 100
        drawRect(self.x, self.y, self.w, self.h,
                 fill=self.fill, border=self.border, opacity=currentOpacity)
        if self.isHovered and not self.useOpacity:
            drawRect(self.x, self.y, self.w, self.h, fill='black', opacity=15)
        # Support multi-line labels — split on '\n'
        lines = self.label.split('\n')
        lineH = self.labelSize + 2
        totalH = len(lines) * lineH
        startY = self.y + self.h / 2 - totalH / 2 + lineH / 2
        for i in range(len(lines)):
            drawLabel(lines[i],
                      self.x + self.w / 2, startY + i * lineH,
                      size=self.labelSize, bold=self.labelBold,
                      fill=self.labelFill)

    def isClicked(self, mouseX, mouseY):
        return (self.x <= mouseX <= self.x + self.w
                and self.y <= mouseY <= self.y + self.h)

    def checkHover(self, mouseX, mouseY):
        if self.isClicked(mouseX, mouseY):
            self.isHovered = True
        else:
            self.isHovered = False

    def handleClick(self, app, mouseX, mouseY):
        # Returns True if the click landed on this button (and calls onClick).
        if self.isClicked(mouseX, mouseY):
            self.onClick(app)
            return True
        return False


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


class DialogueSystem:
    def __init__(self):
        self.speaker = None
        self.lines = []
        self.index = 0
        self.onFinish = None
        self.boxX = 40
        self.boxY = 420
        self.boxW = 720
        self.boxH = 140
        self.fontSize = 14
        # Buttons owned by the dialogue system
        self.nextButton = Button(
            'Next', 600, 510, 60, 30, onClick=lambda app: self.advance(),
            fill='lightGreen', useOpacity=False)
        self.skipButton = Button(
            'Skip', 680, 510, 60, 30, onClick=lambda app: self.skip(),
            fill='lightGray', useOpacity=False)
        # Set up typewriting for lore
        self.fullLine = ""
        self.displayedText = ""
        self.charIndex = 0
        self.isTyping = False
        self.typingSpeed = 1
        self.setupLine()

    def setupLine(self):
        if 0 <= self.index < len(self.lines):
            self.fullLine = self.lines[self.index]
            if self.useTypewriter:
                self.displayedText = ""
                self.charIndex = 0
                self.isTyping = True
            else:
                self.displayedText = self.fullLine
                self.charIndex = len(self.fullLine)
                self.isTyping = False

    def updateTypewriter(self):
        if self.isTyping:
            if self.charIndex < len(self.fullLine):
                self.displayedText += self.fullLine[self.charIndex]
                self.charIndex += 1
            else:
                self.isTyping = False

    def start(self, speaker, lines, onFinish, useTypewriter=False):
        self.speaker = speaker
        self.lines = lines
        self.index = 0
        self.onFinish = onFinish
        self.useTypewriter = useTypewriter
        self.setupLine()

    def advance(self):
        if self.isTyping:
            # SKIP FEATURE: If clicked while typing, show the whole line instantly
            self.displayedText = self.fullLine
            self.isTyping = False
        else:
            # Normal advance to next line
            self.index += 1
            if self.index >= len(self.lines):
                self.finish()
            else:
                self.setupLine()

    def skip(self):
        self.finish()

    def finish(self):
        callback = self.onFinish
        self.speaker = None
        self.lines = []
        self.index = 0
        self.onFinish = None
        if callback is not None:
            callback()

    def draw(self):
        drawRect(self.boxX, self.boxY, self.boxW, self.boxH, fill='white',
                 border='black', borderWidth=2)
        if self.speaker is not None:
            drawLabel(self.speaker.name, 60, 440,
                      size=16, bold=True, align='left')
        if 0 <= self.index < len(self.lines):
            line = self.lines[self.index]
            textX = self.boxX + 20
            availableWidth = self.boxW - 80  # leave margin for buttons on the right
            maxChars = int(availableWidth / (self.fontSize * 0.6))
            wrappedLines = wrapText(line, maxChars)
            lineH = 16
            textStartY = 465
            for i in range(len(wrappedLines)):
                drawLabel(wrappedLines[i], 60, textStartY + i * lineH,
                          size=14, align='left', fill='black')
        self.nextButton.draw()
        self.skipButton.draw()

    def handleHover(self, mouseX, mouseY):
        # Update hover state for both standard dialogue buttons
        if self.nextButton:
            self.nextButton.checkHover(mouseX, mouseY)
        if self.skipButton:
            self.skipButton.checkHover(mouseX, mouseY)

    def checkClick(self, app, mouseX, mouseY):
        # Returns True if click was on Next or Skip.
        if self.nextButton.handleClick(app, mouseX, mouseY):
            return True
        if self.skipButton.handleClick(app, mouseX, mouseY):
            return True
        return False


class GameFlow:
    # Quest/level progression and screen transitions.

    def enterLevelIntro(self, app):
        if app.levelManager is None or app.levelManager.levelNum != app.currentLevel:
            app.levelManager = LevelManager(
                app.currentLevel, app.questData['levels'][app.currentLevel])
            app.levelTeachCount = 0
        app.levelTeachCount += 1
        goToScreen(app, 'levelIntro')

    def startNextQuest(self, app):
        app.currentQuest = app.levelManager.getNextQuest()
        if app.currentQuest is None:
            self.handleEndOfFirstPass(app)
            return
        if len(app.nextQuestTAs) > 0:
            app.activeTAs = app.nextQuestTAs
        else:
            app.activeTAs = list(app.chosenTAs)
        app.nextQuestTAs = []
        app.dropInForNextQuest = None
        app.firstHintTA = None
        goToScreen(app, 'playing')

    def handleEndOfFirstPass(self, app):
        lm = app.levelManager
        failRate = len(lm.failed) / lm.totalQuests if lm.totalQuests > 0 else 0
        if failRate > 0.8:
            if app.levelTeachCount >= 2:
                self.triggerGameOver(app)
            else:
                self.triggerLevelRetryWarning(app)
            return
        if len(lm.failed) == 0:
            self.advanceToNextLevel(app)
        else:
            self.startRetryQuest(app)

    def advanceToNextLevel(self, app):
        app.currentLevel += 1
        if app.currentLevel in app.questData['levels']:
            app.levelManager = None
            self.enterLevelIntro(app)
        else:
            goToScreen(app, 'gameComplete')

    def triggerLevelRetryWarning(self, app):
        lines = app.dialogueData['levelRetryWarning']
        app.dialogue.start(app.chosenHeadmaster, lines,
                           onFinish=lambda: self.reteachLevel(app))
        goToScreen(app, 'levelRetryWarning')

    def reteachLevel(self, app):
        lm = app.levelManager
        lm.unattempted = lm.failed + lm.unattempted
        lm.failed = []
        self.enterLevelIntro(app)

    def triggerGameOver(self, app):
        lines = app.dialogueData['gameOver']
        app.dialogue.start(app.chosenHeadmaster, lines, onFinish=lambda: None)
        goToScreen(app, 'gameOver')

    def startRetryQuest(self, app):
        retry = app.levelManager.getRetryQuest()
        if retry is None:
            self.advanceToNextLevel(app)
            return
        app.currentQuest = retry
        app.activeTAs = list(app.chosenTAs)
        goToScreen(app, 'playing')

    def prepareNextQuestTAs(self, app):
        # If a drop-in was already forced (e.g. via debug shortcut), respect it
        if app.dropInForNextQuest is not None:
            return
        app.nextQuestTAs = list(app.chosenTAs)
        isFirstQuestOfLevel = (len(app.levelManager.completed) == 0
                               and len(app.levelManager.failed) == 0)
        if isFirstQuestOfLevel:
            return
        if random.random() < 0.05:
            candidates = [t for t in app.allTAs if t not in app.chosenTAs]
            if len(candidates) > 0:
                replaceIdx = random.randint(0, 1)
                dropIn = random.choice(candidates)
                app.nextQuestTAs[replaceIdx] = dropIn
                app.dropInForNextQuest = dropIn

    def triggerQuestTransition(self, app, succeeded):
        self.prepareNextQuestTAs(app)
        talkers = list(app.activeTAs)
        random.shuffle(talkers)
        taGeneric, taPunchline = talkers[0], talkers[1]
        if succeeded:
            genericLine = random.choice(app.dialogueData['transitionSuccess'])
        else:
            genericLine = random.choice(app.dialogueData['transitionFail'])
        punchLine = app.dialogueData['punchline']
        app.transitionLines = [
            (taGeneric, genericLine),
            (taPunchline, punchLine),
        ]
        if app.dropInForNextQuest is not None:
            template = random.choice(app.dialogueData['dropInIntro'])
            dropInLine = template.format(name=app.dropInForNextQuest.name)
            app.transitionLines.append((app.dropInForNextQuest, dropInLine))
        app.transitionIndex = 0
        goToScreen(app, 'questTransition')

    def triggerHeadmasterTutorial(self, app):
        tutorial = app.teachingData['levels'][app.currentLevel]['tutorial']
        app.screenBeforeTutorial = app.currentScreen
        app.tutorialSteps = tutorial['steps']
        app.tutorialStepIndex = 0
        app.tutorialCodeLines = []
        lines = [tutorial['problem'], tutorial['intro']]
        for step in tutorial['steps']:
            lines.append(step['narration'])
        lines.append("Let's return to your quest. You've got this!")
        app.dialogue.start(app.chosenHeadmaster, lines,
                           onFinish=lambda: self.returnFromTutorial(app))
        goToScreen(app, 'tutorial')

    def returnFromTutorial(self, app):
        app.returningFromTutorial = True  # signal to not re-setup bricks
        goToScreen(app, app.screenBeforeTutorial or 'playing')
        app.tutorialCodeLines = []
        app.tutorialSteps = []
        app.tutorialStepIndex = 0

    def advanceTutorialDialogue(self, app):
        if not app.dialogue.isTyping:
            nextIdx = app.dialogue.index + 1
            stepIdxAtNext = nextIdx - 2
            if 0 <= stepIdxAtNext < len(app.tutorialSteps):
                step = app.tutorialSteps[stepIdxAtNext]
                if step.get('code'):
                    app.tutorialCodeLines.append(
                        (step['code'], step.get('indent', 0)))
        app.dialogue.advance()


def insertIntoSolution(app, brick, mouseY):
    # Place brick at the target slot. If that slot is occupied, push
    # the occupant (and any contiguous chain below) down by one slot.
    targetSlot = rounded((mouseY - 120) / 40)
    targetSlot = max(0, targetSlot)
    # Build a map: slot -> brick currently there (excluding the one being placed)
    slotOccupant = {}
    for b in app.bricks:
        if b is brick or b.x <= 300:
            continue
        slot = rounded((b.y - 120) / 40)
        slotOccupant[slot] = b
    # If target slot is empty, just place
    if targetSlot not in slotOccupant:
        brick.x = 360
        brick.y = 120 + targetSlot * 40
        return
    # Target slot is occupied: find the contiguous chain of occupied
    # slots starting at targetSlot, and push them all down by one
    chainSlot = targetSlot
    while chainSlot in slotOccupant:
        chainSlot += 1
    # Now chainSlot is the first EMPTY slot below the chain.
    # Shift every brick in the chain down by one, starting from the bottom.
    for slot in range(chainSlot - 1, targetSlot - 1, -1):
        b = slotOccupant[slot]
        b.x = 360
        b.y = 120 + (slot + 1) * 40
    # Place the dragged brick
    brick.x = 360
    brick.y = 120 + targetSlot * 40
