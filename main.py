from cmu_graphics import *
import random
from initAndClasses import *
# ==========================================
# AI STATEMENT PLEASE READ:
# Code was planned and structured with the help of Claude and Gemini
# Claude assisted with minor debugging (finding a missing apostrophe,
#  fixing spelling and capitalization errors, etc)
# Claude provided suggestions for refactoring (organizing screens, deleting useless
#  and/or redundant functions, consolidating similar functions, moving functions
#  in and out of classes)
# No code was copy-and-pasted in from any AI model!
# ==========================================
# All images of Headmaster and TA characters are copied from the 112 website
#     Link: https://www.cs.cmu.edu/~112/staff.html
# Dragon image is also copied from 112 website
#     Link: https://www.cs.cmu.edu/~112/images/112-dragon.png
# All "quest" problem statements are taken from the CS Academy website
# All "quest" solutions are my own homework solutions
#     Link: https://academy.cs.cmu.edu/course
# ==========================================


# Graphics!


def onAppStart(app):
    app.width = 800
    app.height = 600
    initializeData(app)
    initializeCharacters(app)
    initializeGameState(app)
    app.dialogue = DialogueSystem()
    app.gameFlow = GameFlow()
    # Lore -> HM select -> TA select -> Level Intro -> Play/Questing (Headmaster Tutorial)
    # -> Quest Transition -> Failure rate check (80% failed on first try)
    # If failed: Level Retry Warning -> Level Intro/Re-teach -> Failure check
    #   If failed again: Game Over womp womp
    #   If not failed: Proceed with looping over failed quests
    # If not failed: Retries until all quests marked as complete
    # Advance to next level, repeat from Level Intro

# Lore Screen


def storyIntro_onScreenActivate(app):
    # Load lore from YAML
    loreLines = app.dialogueData.get('Lore', ["No lore found."])
    # Start the dialogue system with no speaker (None)
    app.dialogue.start(
        None, loreLines, lambda: goToScreen(app, 'headmasterSelect'))


def storyIntro_onStep(app):
    # This makes the typewriter move!
    app.dialogue.updateTypewriter()


def storyIntro_redrawAll(app):
    # Background - Old Parchment Color
    drawRect(0, 0, 800, 600, fill=rgb(242, 227, 201))
    # Draw scroll border
    drawRect(40, 40, 720, 520, fill=None,
             border=rgb(139, 69, 19), borderWidth=5)
    # Draw 4 Dragons in corners
    path = 'images/smallDragon.png'
    drawImage(path, 20, 20, width=60, height=60)   # Top Left
    drawImage(path, 720, 20, width=60, height=60)  # Top Right
    drawImage(path, 20, 520, width=60, height=60)  # Bottom Left
    drawImage(path, 720, 520, width=60, height=60)  # Bottom Right
    # Draw the typewritten text
    # We use the dialogue's displayedText instead of the full line
    availableWidth = 640  # inner scroll width with side margins
    maxChars = int(availableWidth / (20 * 0.6))  # ~53 chars at size 20
    lineH = 30
    # Use fullLine to compute total height so vertical position stays stable
    totalLines = wrapText(app.dialogue.fullLine, maxChars)
    startY = 300 - (len(totalLines) * lineH) / 2 + lineH / 2
    # Only draw as many chars as the typewriter has revealed
    wrappedDisplayed = wrapText(app.dialogue.displayedText, maxChars)
    for i in range(len(wrappedDisplayed)):
        drawLabel(wrappedDisplayed[i], 400, startY + i * lineH,
                  size=20, italic=True, font='serif', fill=rgb(62, 39, 35))
    # Buttons
    app.dialogue.nextButton.label = "Skip" if app.dialogue.isTyping else "Continue"
    app.dialogue.nextButton.draw()


def storyIntro_onMousePress(app, mouseX, mouseY):
    app.dialogue.handleClick(app, mouseX, mouseY)


def storyIntro_onMouseMove(app, mouseX, mouseY):
    app.dialogue.handleHover(mouseX, mouseY)

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
    borderCol = 'gold' if isSelected else 'black'
    borderW = 4 if isSelected else 2
    drawImage(character.picture, x, y, width=200, height=200)
    drawRect(x, y, 200, 200, border=borderCol, borderWidth=borderW, fill=None)
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
    drawImage(ta.picture, x + 10, y + 10,
              width=w - 20, height=portraitH - 10)
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


def levelIntro_onMouseMove(app, mouseX, mouseY):
    app.dialogue.handleHover(mouseX, mouseY)

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


def tutorial_onMouseMove(app, mouseX, mouseY):
    app.dialogue.handleHover(mouseX, mouseY)

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
        app.bricks.append(codeBrick(scrambled[i], 20, 120 + (i * 40)))


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
        # Back to bank - send it home
        brick.x = 20
        resettleBankBricks(app)


def playing_onMouseMove(app, mouseX, mouseY):
    # Loop through all the buttons on the playing screen and update their hover state
    for button in app.playingButtons:
        button.checkHover(mouseX, mouseY)


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


def questTransition_onMouseMove(app, mouseX, mouseY):
    app.questTransitionButton.checkHover(mouseX, mouseY)


def questTransition_onScreenActivate(app):
    app.questTransitionButton = Button(
        'Next', 340, 540, 120, 40,
        onClick=advanceQuestTransition,
        fill='cornflowerBlue', labelFill='white', labelSize=16, useOpacity=False)


def advanceQuestTransition(app):
    if app.transitionIndex >= len(app.transitionLines) - 1:
        app.gameFlow.startNextQuest(app)
    else:
        app.transitionIndex += 1


def main():
    runAppWithScreens(initialScreen='storyIntro')


main()
