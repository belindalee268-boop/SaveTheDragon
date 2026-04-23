from cmu_graphics import *
import random
import math
import yaml

# Logic of Game


def loadYAML(filepath):
    with open(filepath, 'r') as file:
        data = yaml.safe_load(file)
    return data


def goToScreen(app, screenName):
    app.currentScreen = screenName
    setActiveScreen(screenName)


def initializeData(app):
    """Load all YAML files."""
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
                 border='black', labelSize=14, labelBold=True):
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

    def draw(self):
        drawRect(self.x, self.y, self.w, self.h,
                 fill=self.fill, border=self.border)
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
        # Buttons owned by the dialogue system
        self.nextButton = Button(
            'Next', 600, 510, 60, 30, onClick=lambda app: self.advance(), fill='lightGreen')
        self.skipButton = Button(
            'Skip', 680, 510, 60, 30, onClick=lambda app: self.skip(), fill='lightGray')

    def start(self, speaker, lines, onFinish):
        self.speaker = speaker
        self.lines = lines
        self.index = 0
        self.onFinish = onFinish

    def advance(self):
        self.index += 1
        if self.index >= len(self.lines):
            self.finish()

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
        drawRect(40, 420, 720, 140, fill='white',
                 border='black', borderWidth=2)
        if self.speaker is not None:
            drawLabel(self.speaker.name, 60, 440,
                      size=16, bold=True, align='left')
        if 0 <= self.index < len(self.lines):
            line = self.lines[self.index]
            drawLabel(line, 60, 480, size=14,
                      align='left', fill='black')
        self.nextButton.draw()
        self.skipButton.draw()

    def handleClick(self, app, mouseX, mouseY):
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
        app.nextQuestTAs = list(app.chosenTAs)
        app.dropInForNextQuest = None
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
        goToScreen(app, app.screenBeforeTutorial or 'playing')
        app.tutorialCodeLines = []
        app.tutorialSteps = []
        app.tutorialStepIndex = 0

    def advanceTutorialDialogue(self, app):
        nextIdx = app.dialogue.index + 1
        stepIdxAtNext = nextIdx - 2
        if 0 <= stepIdxAtNext < len(app.tutorialSteps):
            step = app.tutorialSteps[stepIdxAtNext]
            if step.get('code'):
                app.tutorialCodeLines.append(
                    (step['code'], step.get('indent', 0)))
        app.dialogue.advance()

# Graphics!


def onAppStart(app):
    app.width = 800
    app.height = 600
    initializeData(app)
    initializeCharacters(app)
    initializeGameState(app)
    app.dialogue = DialogueSystem()
    app.gameFlow = GameFlow()   # see Goal 2 below
    app.currentScreen = 'headmasterSelect'
    # HM select -> TA select -> Level Intro -> Play/Questing (Headmaster Tutorial)
    # -> Quest Transition -> Failure rate check (80% failed on first try)
    # If failed: Level Retry Warning -> Level Intro/Re-teach -> Failure check
    #   If failed again: Game Over womp womp
    #   If not failed: Proceed with looping over failed quests
    # If not failed: Retries until all quests marked as complete
    # Advance to next level, repeat from Level Intro


#  HEADMASTER SELECTION
# Click a headmaster -> preview their greeting. Click the same headmaster
# again -> confirm and move on to TA Select.


def headmasterSelect_onScreenActivate(app):
    app.previewCharacter = None


def headmasterSelect_redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='lightBlue')
    drawLabel('Choose Your Headmaster', app.width / 2, 60,
              size=28, bold=True)
    drawLabel('Click a headmaster to hear their greeting. Click again to confirm.',
              app.width / 2, 100, size=14)
    headmasters = list(app.headmasters.values())
    for i in range(len(headmasters)):
        x = 150 + i * 300
        drawCharacterCard(app, headmasters[i], x, 180,
                          isSelected=(app.previewCharacter is headmasters[i]))
    if app.previewCharacter is not None:
        drawLabel(f'"{app.previewCharacter.greeting}"',
                  app.width / 2, 420, size=14, italic=True)
        drawLabel('Click again to confirm your choice!',
                  app.width / 2, 450, size=14, bold=True, fill='darkGreen')


def headmasterSelect_onMousePress(app, mouseX, mouseY):
    headmasters = list(app.headmasters.values())
    for i in range(len(headmasters)):
        x = 150 + i * 300
        y = 180
        if x <= mouseX <= x + 200 and y <= mouseY <= y + 200:
            clicked = headmasters[i]
            if app.previewCharacter is clicked:
                app.chosenHeadmaster = clicked
                app.previewCharacter = None
                goToScreen(app, 'taSelect')
            else:
                app.previewCharacter = clicked
            return


def drawCharacterCard(app, character, x, y, isSelected=False):
    # Placeholder rendering. Later you'll swap drawRect for drawImage.
    borderCol = 'gold' if isSelected else 'black'
    borderW = 4 if isSelected else 2
    drawRect(x, y, 200, 200, fill='lightYellow',
             border=borderCol, borderWidth=borderW)
    drawLabel('[portrait]', x + 100, y + 100, size=14, fill='gray')
    drawLabel(character.name, x + 100, y + 220, size=16, bold=True)


#  TA SELECTION
# Player picks 2 TAs from the selectable pool. Same click-to-preview then
# click-again-to-confirm pattern, but we need two confirms.
def taSelect_onScreenActivate(app):
    app.previewCharacter = None
    app.TABrowseIndex = 0


def taSelect_redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='lightYellow')
    drawLabel('Choose Your Two TAs', app.width / 2, 40, size=26, bold=True)
    drawLabel(f'Chosen: {len(app.chosenTAs)} / 2',
              app.width / 2, 75, size=16)
    drawLabel('Press SPACE or arrow keys to browse. Click a TA to greet them, click again to confirm.',
              app.width / 2, 100, size=12)
    TAs = app.selectableTAs
    n = len(TAs)
    if n == 0:
        return
    currentIdx = app.TABrowseIndex
    prevIdx = (currentIdx - 1) % n
    nextIdx = (currentIdx + 1) % n
    drawTACard(app, TAs[prevIdx], 60, 220, 140, 180, isMain=False)
    drawTACard(app, TAs[nextIdx], 600, 220, 140, 180, isMain=False)
    drawTACard(app, TAs[currentIdx], 280, 160, 240, 300, isMain=True)
    drawLabel(f'TA {currentIdx + 1} of {n}',
              app.width / 2, 480, size=14, bold=True)
    current = TAs[currentIdx]
    if app.previewCharacter is current and current not in app.chosenTAs:
        drawLabel(f'"{current.greeting}"',
                  app.width / 2, 510, size=14, italic=True)
        drawLabel('Click again to add them to your team!',
                  app.width / 2, 535, size=14, bold=True, fill='darkGreen')
    else:
        drawLabel('[SPACE / arrows to browse]',
                  app.width / 2, 535, size=12, fill='gray')


def drawTACard(app, ta, x, y, w, h, isMain=False):
    alreadyChosen = ta in app.chosenTAs
    isPreview = (app.previewCharacter is ta) and isMain
    if alreadyChosen:
        fill, border = 'lightGreen', 'darkGreen'
    elif isPreview:
        fill, border = 'lightYellow', 'gold'
    elif isMain:
        fill, border = 'white', 'black'
    else:
        fill, border = 'lightGray', 'gray'
    borderW = 4 if isMain else 2
    drawRect(x, y, w, h, fill=fill, border=border, borderWidth=borderW)
    portraitH = h - 60
    if ta.picture is not None:
        drawImage(ta.picture, x + 10, y + 10,
                  width=w - 20, height=portraitH - 10)
    else:
        drawLabel('[portrait]', x + w / 2, y + portraitH / 2,
                  size=14 if isMain else 12, fill='darkGray')
    drawLabel(ta.name, x + w / 2, y + h - 35,
              size=16 if isMain else 12, bold=True)
    drawLabel(f'({ta.personality})', x + w / 2, y + h - 15,
              size=12 if isMain else 10, italic=True)
    if alreadyChosen:
        drawLabel('CHOSEN', x + w / 2, y + h / 2,
                  size=16 if isMain else 11, bold=True, fill='darkGreen')


def taSelect_onMousePress(app, mouseX, mouseY):
    TAs = app.selectableTAs
    if len(TAs) == 0:
        return
    mainX, mainY, mainW, mainH = 280, 160, 240, 300
    if not (mainX <= mouseX <= mainX + mainW
            and mainY <= mouseY <= mainY + mainH):
        return
    clicked = TAs[app.TABrowseIndex]
    if clicked in app.chosenTAs:
        return
    if app.previewCharacter is clicked:
        app.chosenTAs.append(clicked)
        app.previewCharacter = None
        if len(app.chosenTAs) == 2:
            app.gameFlow.enterLevelIntro(app)
    else:
        app.previewCharacter = clicked


def taSelect_onKeyPress(app, key):
    n = len(app.selectableTAs)
    if n == 0:
        return
    if key == 'space' or key == 'right':
        app.TABrowseIndex = (app.TABrowseIndex + 1) % n
        app.previewCharacter = None
    elif key == 'left':
        app.TABrowseIndex = (app.TABrowseIndex - 1) % n
        app.previewCharacter = None

# Level Intro Screen


def levelIntro_onScreenActivate(app):
    introLines = app.teachingData['levels'][app.currentLevel]['introDialogue']
    app.dialogue.start(app.chosenHeadmaster, introLines,
                       onFinish=lambda: app.gameFlow.startNextQuest(app))


def levelIntro_redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='lightBlue')
    drawLabel(f'Level {app.currentLevel}: {app.levelManager.topic}',
              app.width / 2, 50, size=26, bold=True)
    drawCharacterCard(app, app.chosenHeadmaster, 300, 120)
    app.dialogue.draw()


def levelIntro_onMousePress(app, mouseX, mouseY):
    app.dialogue.handleClick(app, mouseX, mouseY)

# Level Retry Warning Screen


def levelRetryWarning_redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='lightCoral')
    drawLabel('Level Failed', app.width / 2, 100,
              size=32, bold=True, fill='darkRed')
    drawLabel(f"{app.chosenHeadmaster.name} wants to try again...",
              app.width / 2, 160, size=18)
    drawCharacterCard(app, app.chosenHeadmaster, 300, 190)
    app.dialogue.draw()


def levelRetryWarning_onMousePress(app, mouseX, mouseY):
    app.dialogue.handleClick(app, mouseX, mouseY)


# Gameover screen
def gameOver_redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='black')
    drawLabel('GAME OVER', app.width / 2, 100,
              size=48, bold=True, fill='red')
    drawLabel('The Dragon will never learn to code.',
              app.width / 2, 170, size=20, fill='white')
    app.dialogue.draw()


def gameOver_onMousePress(app, mouseX, mouseY):
    app.dialogue.handleClick(app, mouseX, mouseY)

# Game complete screen


def gameComplete_redrawAll(app):
    drawRect(0, 0, 800, 600, fill='gold')
    drawLabel('The Dragon can code again!', 400, 260, size=32, bold=True)
    drawLabel('Thank you for saving the Dragon!', 400, 320, size=20)


# Tutorial Screen


def tutorial_redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='lavender')
    drawLabel('Headmaster Tutorial', app.width / 2, 40, size=24, bold=True)
    tutorial = app.teachingData['levels'][app.currentLevel]['tutorial']
    drawLabel(tutorial['problem'], app.width / 2, 75, size=14, italic=True)
    drawCharacterCard(app, app.chosenHeadmaster, 60, 120)
    panelX, panelY, panelW, panelH = 350, 120, 380, 280
    drawRect(panelX, panelY, panelW, panelH,
             fill='lightSlateGray', border='steelBlue', borderWidth=2)
    drawLabel('Code So Far', panelX + panelW / 2, panelY - 15,
              size=14, bold=True)
    for i in range(len(app.tutorialCodeLines)):
        text, indent = app.tutorialCodeLines[i]
        lineY = panelY + 20 + i * 30
        indentPx = indent * 20
        availableWidth = panelW - 20 - indent   # 10px margin each side
        fontSize = pickFontSize(text, availableWidth)
        drawRect(panelX + 10, lineY - 12, panelW - 20, 28,
                 fill='crimson', border='darkSlateGray')
        drawLabel(text, panelX + 20 + indentPx, lineY + 2,
                  align='left', size=fontSize)
    app.dialogue.draw()


def tutorial_onMousePress(app, mouseX, mouseY):
    if app.dialogue.nextButton.isClicked(mouseX, mouseY):
        app.gameFlow.advanceTutorialDialogue(app)
    elif app.dialogue.skipButton.isClicked(mouseX, mouseY):
        app.dialogue.skip()

# Playing Screen


def playing_onScreenActivate(app):
    setupBricks(app)
    app.selectedBrick = None
    app.draggedBrick = None
    app.dialogueText = 'Drag blocks into the main area to solve the problem!'
    app.playingButtons = [
        Button('Check Code', 650, 90, 130, 40,
               onClick=evaluateSolution,
               fill='mediumSpringGreen', labelFill='royalBlue'),
        Button('Ask for TA Hint', 650, 150, 130, 40,
               onClick=giveHintFromActiveTA,
               fill='deepSkyBlue', labelFill='white'),
        Button('Ask Headmaster\nfor Help', 650, 210, 130, 40,
               onClick=lambda a: a.gameFlow.triggerHeadmasterTutorial(a),
               fill='white', labelFill='black', labelSize=12),
    ]


def setupBricks(app):
    app.bricks = []
    scrambled = app.currentQuest.baseLines[:]
    random.shuffle(scrambled)
    for i in range(len(scrambled)):
        app.bricks.append(codeBrick(scrambled[i], 20, 140 + (i * 40)))


def playing_redrawAll(app):
    drawRect(0, 0, 800, 600, fill='darkSlateGray')
    drawRect(350, 120, 280, 400, fill='lightSlateGray', border='steelBlue')
    # Draw line numbers
    numLines = len(app.currentQuest.baseLines)
    for i in range(numLines):
        drawLabel(str(i + 1), 340, 120 + i * 40 + 15,
                  size=12, bold=True, fill='white', align='right')
    drawLabel('Solution Area', 490, 105, size=16, bold=True)
    drawLabel('Block Bank', 160, 105, size=16, bold=True)
    # Draw problem statement
    problemLines = wrapText(f'Quest: {app.currentQuest.problemStatement}', 110)
    for i in range(len(problemLines)):
        drawLabel(problemLines[i], 20, 20 + i * 18,
                  size=13, bold=True, fill='white', align='left')
    drawRect(50, 520, 700, 60, fill='lawnGreen', border='steelBlue')
    drawLabel(app.dialogueText, 400, 550, size=14)
    # Draw all buttons
    for button in app.playingButtons:
        button.draw()
    # TA labels
    for i in range(len(app.activeTAs)):
        drawLabel(f'TA: {app.activeTAs[i].name}',
                  700, 270 + i * 20, size=12, fill='white')
    # Draw code bricks
    for brick in app.bricks:
        color = 'crimson' if brick.x > 350 else 'lightCoral'
        borderCol = 'yellow' if brick is app.selectedBrick else 'darkSlateGray'
        borderW = 3 if brick is app.selectedBrick else 1
        drawRect(brick.x, brick.y, brick.width, brick.height,
                 fill=color, border=borderCol, borderWidth=borderW)
        indent = brick.indentCount * 15
        availableWidth = brick.width - 20 - indent   # 10px margin each side
        fontSize = pickFontSize(brick.text, availableWidth)
        drawLabel(brick.text, brick.x + 10 + indent,
                  brick.y + 15, align='left', size=fontSize)


def pickFontSize(text, availableWidth, maxSize=14, minSize=8):
    # Guess a font size so text fits in availableWidth pixels.
    # Approximates character width as ~0.6 * fontSize.
    for size in range(maxSize, minSize - 1, -1):
        estimatedWidth = len(text) * size * 0.6
        if estimatedWidth <= availableWidth:
            return size
    return minSize


def playing_onMousePress(app, mouseX, mouseY):
    # Check all buttons first
    for button in app.playingButtons:
        if button.handleClick(app, mouseX, mouseY):
            return
    # Otherwise, try to grab a brick
    for brick in reversed(app.bricks):
        if (brick.x <= mouseX <= brick.x + brick.width
                and brick.y <= mouseY <= brick.y + brick.height):
            app.draggedBrick = brick
            app.selectedBrick = brick
            app.dragOffsetX = mouseX - brick.x
            app.dragOffsetY = mouseY - brick.y
            app.brickOriginalX = brick.x
            app.brickOriginalY = brick.y
            return


def playing_onMouseDrag(app, mouseX, mouseY):
    if app.draggedBrick is not None:
        app.draggedBrick.x = mouseX - app.dragOffsetX
        app.draggedBrick.y = mouseY - app.dragOffsetY


def playing_onMouseRelease(app, mouseX, mouseY):
    if app.draggedBrick is None:
        return
    brick = app.draggedBrick
    app.draggedBrick = None
    movedDistance = ((brick.x - app.brickOriginalX) ** 2
                     + (brick.y - app.brickOriginalY) ** 2) ** 0.5
    if movedDistance < 10:
        # Just a click, snap back to original position, do nothing
        brick.x = app.brickOriginalX
        brick.y = app.brickOriginalY
        return
    if brick.x > 300:
        # Snapping to solution area
        insertIntoSolution(app, brick, mouseY)
    else:
        # Back to bank — send it home
        brick.x = 20
        resettleBankBricks(app)


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


def resettleBankBricks(app):
    # After a brick leaves the solution area, shift remaining solution
    # bricks up to close gaps. Bank bricks are left where they are."""
    solutionBricks = [b for b in app.bricks if b.x > 300]
    solutionBricks.sort(key=lambda b: b.y)
    for i in range(len(solutionBricks)):
        solutionBricks[i].x = 360
        solutionBricks[i].y = 120 + i * 40


def playing_onKeyPress(app, key):
    if app.selectedBrick is None:
        return
    if key == 'right':
        app.selectedBrick.shiftBrick('right')
    elif key == 'left':
        app.selectedBrick.shiftBrick('left')


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


def giveHintFromActiveTA(app):
    # First hint: random active TA. Second hint: the OTHER one.
    q = app.currentQuest
    if q.numHints >= 2:
        app.dialogueText = "No more hints available!"
        return
    if q.numHints == 0:
        hinter = random.choice(app.activeTAs)
        app.firstHintTA = hinter
    else:
        if len(app.activeTAs) >= 2 and app.firstHintTA is app.activeTAs[0]:
            hinter = app.activeTAs[1]
        elif len(app.activeTAs) >= 2:
            hinter = app.activeTAs[0]
        else:
            hinter = app.activeTAs[0]
    hinter.giveCodeHint(app, q)


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
        app.levelManager.completeQuest(app.currentQuest)
        app.gameFlow.triggerQuestTransition(app, succeeded=True)
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
        app.gameFlow.triggerQuestTransition(app, succeeded=False)
    app.dialogueText += f"Tries Left: {3 - app.currentQuest.numTries}/3"

# Quest Transition Screen


def questTransition_redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='lightYellow')
    for i in range(len(app.activeTAs)):
        x = 180 + i * 280
        drawCharacterCard(app, app.activeTAs[i], x, 80)
    if 0 <= app.transitionIndex < len(app.transitionLines):
        speaker, line = app.transitionLines[app.transitionIndex]
        drawRect(60, 360, 680, 140, fill='white',
                 border='black', borderWidth=2)
        drawLabel(speaker.name, 80, 380, size=16, bold=True, align='left')
        drawLabel(line, 80, 420, size=14, align='left', fill='black')
        drawLabel(f'{app.transitionIndex + 1} / {len(app.transitionLines)}',
                  400, 510, size=12, fill='gray')
        # Update button label based on position
        isLast = (app.transitionIndex == len(app.transitionLines) - 1)
        app.questTransitionButton.label = 'Continue' if isLast else 'Next'
        app.questTransitionButton.draw()


def questTransition_onMousePress(app, mouseX, mouseY):
    app.questTransitionButton.handleClick(app, mouseX, mouseY)


def questTransition_onScreenActivate(app):
    app.questTransitionButton = Button(
        'Next', 340, 540, 120, 40,
        onClick=advanceQuestTransition,
        fill='cornflowerBlue', labelFill='white', labelSize=16)


def advanceQuestTransition(app):
    if app.transitionIndex >= len(app.transitionLines) - 1:
        app.gameFlow.startNextQuest(app)
    else:
        app.transitionIndex += 1


def main():
    runAppWithScreens(initialScreen='headmasterSelect')


main()


###########
# Pictures
# UI: text fitting correctly, inserting code
# UI: Size stuff
# Dialogue: Teaching each level + tutorials per level

# Insert more quests later
