Refactoring Types: ['Move Attribute']
ellij/diff/actions/DocumentFragmentContent.java
/*
 * Copyright 2000-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.diff.actions;

import com.intellij.diff.contents.DocumentContent;
import com.intellij.openapi.diff.FragmentContent;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.EditorFactory;
import com.intellij.openapi.editor.RangeMarker;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.TextRange;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.util.LineSeparator;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.nio.charset.Charset;

/**
 * Represents sub text of other content. Original content should provide not null document.
 */
public class DocumentFragmentContent implements DocumentContent {
  // TODO: reuse DocumentWindow ?

  public static final Key<Document> ORIGINAL_DOCUMENT = FragmentContent.ORIGINAL_DOCUMENT; // TODO: replace with own one ?

  @NotNull private final DocumentContent myOriginal;

  @NotNull private final MyDocumentsSynchronizer mySynchonizer;

  private int myAssignments = 0;

  public DocumentFragmentContent(@NotNull Project project, @NotNull DocumentContent original, @NotNull TextRange range) {
    myOriginal = original;

    RangeMarker rangeMarker = myOriginal.getDocument().createRangeMarker(range.getStartOffset(), range.getEndOffset(), true);
    rangeMarker.setGreedyToLeft(true);
    rangeMarker.setGreedyToRight(true);

    mySynchonizer = new MyDocumentsSynchronizer(project, rangeMarker);
  }

  @NotNull
  @Override
  public Document getDocument() {
    return mySynchonizer.getDocument2();
  }

  @Nullable
  @Override
  public VirtualFile getHighlightFile() {
    return myOriginal.getHighlightFile();
  }

  @Nullable
  @Override
  public OpenFileDescriptor getOpenFileDescriptor(int offset) {
    return myOriginal.getOpenFileDescriptor(offset + mySynchonizer.getStartOffset());
  }

  @Nullable
  @Override
  public LineSeparator getLineSeparator() {
    return null;
  }

  @Nullable
  @Override
  public Charset getCharset() {
    return null;
  }

  @Nullable
  @Override
  public FileType getContentType() {
    return myOriginal.getContentType();
  }

  @Nullable
  @Override
  public OpenFileDescriptor getOpenFileDescriptor() {
    return getOpenFileDescriptor(0);
  }

  @Override
  public void onAssigned(boolean isAssigned) {
    if (isAssigned) {
      if (myAssignments == 0) mySynchonizer.startListen();
      myAssignments++;
    }
    else {
      myAssignments--;
      if (myAssignments == 0) mySynchonizer.stopListen();
    }
    assert myAssignments >= 0;
  }

  private static class MyDocumentsSynchronizer extends DocumentsSynchronizer {
    @NotNull private final RangeMarker myRangeMarker;

    public MyDocumentsSynchronizer(@NotNull Project project, @NotNull RangeMarker originalRange) {
      super(project, getOriginal(originalRange), getCopy(originalRange));
      myRangeMarker = originalRange;
    }

    public int getStartOffset() {
      return myRangeMarker.getStartOffset();
    }

    public int getEndOffset() {
      return myRangeMarker.getEndOffset();
    }

    @Override
    protected void onDocumentChanged1(@NotNull DocumentEvent event) {
      if (!myRangeMarker.isValid()) {
        myDocument2.setReadOnly(false);
        replaceString(myDocument2, 0, myDocument2.getTextLength(), "Invalid selection range");
        myDocument2.setReadOnly(true);
        return;
      }
      CharSequence newText = myDocument1.getCharsSequence().subSequence(myRangeMarker.getStartOffset(), myRangeMarker.getEndOffset());
      replaceString(myDocument2, 0, myDocument2.getTextLength(), newText);
    }

    @Override
    protected void onDocumentChanged2(@NotNull DocumentEvent event) {
      if (!myRangeMarker.isValid()) {
        return;
      }
      if (!myDocument1.isWritable()) return;

      CharSequence newText = event.getNewFragment();
      int originalOffset = event.getOffset() + myRangeMarker.getStartOffset();
      int originalEnd = originalOffset + event.getOldLength();
      replaceString(myDocument1, originalOffset, originalEnd, newText);
    }

    @Override
    public void startListen() {
      if (myRangeMarker.isValid()) {
        myDocument2.setReadOnly(false);
        CharSequence nexText = myDocument1.getCharsSequence().subSequence(myRangeMarker.getStartOffset(), myRangeMarker.getEndOffset());
        replaceString(myDocument2, 0, myDocument2.getTextLength(), nexText);
        myDocument2.setReadOnly(!myDocument1.isWritable());
      }
      else {
        myDocument2.setReadOnly(false);
        replaceString(myDocument2, 0, myDocument2.getTextLength(), "Invalid selection range");
        myDocument2.setReadOnly(true);
      }
      super.startListen();
    }
  }

  @NotNull
  protected static Document getOriginal(@NotNull RangeMarker rangeMarker) {
    return rangeMarker.getDocument();
  }

  @NotNull
  protected static Document getCopy(@NotNull RangeMarker rangeMarker) {
    final Document originalDocument = rangeMarker.getDocument();

    Document result = EditorFactory.getInstance().createDocument("");
    result.putUserData(ORIGINAL_DOCUMENT, originalDocument);
    return result;
  }
}


File: platform/diff-impl/src/com/intellij/diff/tools/fragmented/UnifiedDiffViewer.java
/*
 * Copyright 2000-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.diff.tools.fragmented;

import com.intellij.diff.DiffContext;
import com.intellij.diff.actions.BufferedLineIterator;
import com.intellij.diff.actions.DocumentFragmentContent;
import com.intellij.diff.actions.NavigationContextChecker;
import com.intellij.diff.actions.impl.OpenInEditorWithMouseAction;
import com.intellij.diff.actions.impl.SetEditorSettingsAction;
import com.intellij.diff.comparison.DiffTooBigException;
import com.intellij.diff.contents.DocumentContent;
import com.intellij.diff.fragments.LineFragment;
import com.intellij.diff.requests.ContentDiffRequest;
import com.intellij.diff.requests.DiffRequest;
import com.intellij.diff.tools.util.*;
import com.intellij.diff.tools.util.base.*;
import com.intellij.diff.tools.util.side.TwosideTextDiffViewer;
import com.intellij.diff.util.*;
import com.intellij.diff.util.DiffUserDataKeysEx.ScrollToPolicy;
import com.intellij.diff.util.DiffUtil.DocumentData;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.actionSystem.Separator;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.diff.LineTokenizer;
import com.intellij.openapi.editor.*;
import com.intellij.openapi.editor.actionSystem.EditorActionManager;
import com.intellij.openapi.editor.actionSystem.ReadonlyFragmentModificationHandler;
import com.intellij.openapi.editor.colors.EditorColors;
import com.intellij.openapi.editor.event.DocumentAdapter;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.editor.ex.EditorEx;
import com.intellij.openapi.editor.highlighter.EditorHighlighter;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Computable;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.UserDataHolder;
import com.intellij.util.Function;
import com.intellij.util.containers.ContainerUtil;
import gnu.trove.TIntFunction;
import org.jetbrains.annotations.*;

import javax.swing.*;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;

import static com.intellij.diff.util.DiffUtil.getLineCount;

public class UnifiedDiffViewer extends ListenerDiffViewerBase {
  public static final Logger LOG = Logger.getInstance(UnifiedDiffViewer.class);

  @NotNull protected final EditorEx myEditor;
  @NotNull protected final Document myDocument;
  @NotNull private final UnifiedDiffPanel myPanel;

  @NotNull private final SetEditorSettingsAction myEditorSettingsAction;
  @NotNull private final PrevNextDifferenceIterable myPrevNextDifferenceIterable;
  @NotNull private final MyStatusPanel myStatusPanel;

  @NotNull private final MyInitialScrollHelper myInitialScrollHelper = new MyInitialScrollHelper();
  @NotNull private final MyFoldingModel myFoldingModel;

  @NotNull protected Side myMasterSide = Side.RIGHT;

  @Nullable private ChangedBlockData myChangedBlockData;

  private final boolean[] myForceReadOnlyFlags;
  private boolean myReadOnlyLockSet = false;

  private boolean myDuringOnesideDocumentModification;
  private boolean myDuringTwosideDocumentModification;

  private boolean myStateIsOutOfDate; // whether something was changed since last rediff
  private boolean mySuppressEditorTyping; // our state is inconsistent. No typing can be handled correctly

  public UnifiedDiffViewer(@NotNull DiffContext context, @NotNull DiffRequest request) {
    super(context, (ContentDiffRequest)request);

    myPrevNextDifferenceIterable = new MyPrevNextDifferenceIterable();
    myStatusPanel = new MyStatusPanel();

    myForceReadOnlyFlags = TextDiffViewerUtil.checkForceReadOnly(myContext, myRequest);

    boolean leftEditable = isEditable(Side.LEFT, false);
    boolean rightEditable = isEditable(Side.RIGHT, false);
    if (leftEditable && !rightEditable) myMasterSide = Side.LEFT;
    if (!leftEditable && rightEditable) myMasterSide = Side.RIGHT;


    myDocument = EditorFactory.getInstance().createDocument("");
    myEditor = DiffUtil.createEditor(myDocument, myProject, true, true);

    List<JComponent> titles = DiffUtil.createTextTitles(myRequest, ContainerUtil.list(myEditor, myEditor));
    UnifiedContentPanel contentPanel = new UnifiedContentPanel(titles, myEditor);

    myPanel = new UnifiedDiffPanel(myProject, contentPanel, this, myContext);

    myFoldingModel = new MyFoldingModel(myEditor, this);

    myEditorSettingsAction = new SetEditorSettingsAction(getTextSettings(), getEditors());
    myEditorSettingsAction.applyDefaults();

    new MyOpenInEditorWithMouseAction().register(getEditors());

    TextDiffViewerUtil.checkDifferentDocuments(myRequest);
  }

  @Override
  @CalledInAwt
  protected void onInit() {
    super.onInit();
    installEditorListeners();
    installTypingSupport();
    myPanel.setLoadingContent(); // We need loading panel only for initial rediff()
  }

  @Override
  @CalledInAwt
  protected void onDispose() {
    super.onDispose();
    EditorFactory.getInstance().releaseEditor(myEditor);
  }

  @Override
  @CalledInAwt
  protected void processContextHints() {
    super.processContextHints();
    Side side = DiffUtil.getUserData(myRequest, myContext, DiffUserDataKeys.MASTER_SIDE);
    if (side != null) myMasterSide = side;

    myInitialScrollHelper.processContext(myRequest);
  }

  @Override
  @CalledInAwt
  protected void updateContextHints() {
    super.updateContextHints();
    myInitialScrollHelper.updateContext(myRequest);
    myFoldingModel.updateContext(myRequest, getFoldingModelSettings());
  }

  @CalledInAwt
  protected void updateEditorCanBeTyped() {
    myEditor.setViewer(mySuppressEditorTyping || !isEditable(myMasterSide, true));
  }

  private void installTypingSupport() {
    if (!isEditable(myMasterSide, false)) return;

    updateEditorCanBeTyped();
    myEditor.getColorsScheme().setColor(EditorColors.READONLY_FRAGMENT_BACKGROUND_COLOR, null); // guarded blocks
    EditorActionManager.getInstance().setReadonlyFragmentModificationHandler(myDocument, new MyReadonlyFragmentModificationHandler());
    myDocument.putUserData(DocumentFragmentContent.ORIGINAL_DOCUMENT, getDocument(myMasterSide)); // use undo of master document

    myDocument.addDocumentListener(new MyOnesideDocumentListener());
  }

  @CalledInAwt
  @NotNull
  public List<AnAction> createToolbarActions() {
    List<AnAction> group = new ArrayList<AnAction>();

    // TODO: allow to choose myMasterSide
    group.add(new MyIgnorePolicySettingAction());
    group.add(new MyHighlightPolicySettingAction());
    group.add(new MyToggleExpandByDefaultAction());
    group.add(new MyReadOnlyLockAction());
    group.add(myEditorSettingsAction);

    return group;
  }

  @CalledInAwt
  @NotNull
  public List<AnAction> createPopupActions() {
    List<AnAction> group = new ArrayList<AnAction>();

    group.add(Separator.getInstance());
    group.add(new MyIgnorePolicySettingAction().getPopupGroup());
    group.add(Separator.getInstance());
    group.add(new MyHighlightPolicySettingAction().getPopupGroup());
    group.add(Separator.getInstance());
    group.add(new MyToggleExpandByDefaultAction());

    return group;
  }

  @NotNull
  protected List<AnAction> createEditorPopupActions() {
    return TextDiffViewerUtil.createEditorPopupActions();
  }

  @CalledInAwt
  protected void installEditorListeners() {
    new TextDiffViewerUtil.EditorActionsPopup(createEditorPopupActions()).install(getEditors());
  }

  //
  // Diff
  //

  @Override
  @CalledInAwt
  protected void onSlowRediff() {
    super.onSlowRediff();
    myStatusPanel.setBusy(true);
  }

  @Override
  @NotNull
  protected Runnable performRediff(@NotNull final ProgressIndicator indicator) {
    try {
      indicator.checkCanceled();

      final Document document1 = getContent1().getDocument();
      final Document document2 = getContent2().getDocument();

      final DocumentData documentData = ApplicationManager.getApplication().runReadAction(new Computable<DocumentData>() {
        @Override
        public DocumentData compute() {
          return new DocumentData(document1.getImmutableCharSequence(), document2.getImmutableCharSequence(),
                                  document1.getModificationStamp(), document2.getModificationStamp());
        }
      });

      final boolean innerFragments = getDiffConfig().innerFragments;
      final List<LineFragment> fragments = DiffUtil.compareWithCache(myRequest, documentData, getDiffConfig(), indicator);

      final DocumentContent content1 = getContent1();
      final DocumentContent content2 = getContent2();

      indicator.checkCanceled();
      TwosideDocumentData data = ApplicationManager.getApplication().runReadAction(new Computable<TwosideDocumentData>() {
        @Override
        public TwosideDocumentData compute() {
          indicator.checkCanceled();
          UnifiedFragmentBuilder builder = new UnifiedFragmentBuilder(fragments, document1, document2, myMasterSide);
          builder.exec();

          indicator.checkCanceled();

          EditorHighlighter highlighter = buildHighlighter(myProject, content1, content2,
                                                           documentData.getText1(), documentData.getText2(), builder.getRanges(),
                                                           builder.getText().length());

          UnifiedEditorRangeHighlighter rangeHighlighter = new UnifiedEditorRangeHighlighter(myProject, document1, document2,
                                                                                             builder.getRanges());

          return new TwosideDocumentData(builder, highlighter, rangeHighlighter);
        }
      });
      UnifiedFragmentBuilder builder = data.getBuilder();

      FileType fileType = content2.getContentType() == null ? content1.getContentType() : content2.getContentType();

      LineNumberConvertor convertor = builder.getConvertor();
      List<LineRange> changedLines = builder.getChangedLines();
      boolean isEqual = builder.isEqual();

      CombinedEditorData editorData = new CombinedEditorData(builder.getText(), data.getHighlighter(), data.getRangeHighlighter(), fileType,
                                                             convertor.createConvertor1(), convertor.createConvertor2());

      return apply(editorData, builder.getBlocks(), convertor, changedLines, isEqual, innerFragments);
    }
    catch (DiffTooBigException e) {
      return new Runnable() {
        @Override
        public void run() {
          clearDiffPresentation();
          myPanel.setTooBigContent();
        }
      };
    }
    catch (ProcessCanceledException e) {
      throw e;
    }
    catch (Throwable e) {
      LOG.error(e);
      return new Runnable() {
        @Override
        public void run() {
          clearDiffPresentation();
          myPanel.setErrorContent();
        }
      };
    }
  }

  private void clearDiffPresentation() {
    myPanel.resetNotifications();
    myStatusPanel.setBusy(false);
    destroyChangedBlockData();

    myStateIsOutOfDate = false;
    mySuppressEditorTyping = false;
    updateEditorCanBeTyped();
  }

  @CalledInAwt
  protected void markSuppressEditorTyping() {
    mySuppressEditorTyping = true;
    updateEditorCanBeTyped();
  }

  @CalledInAwt
  protected void markStateIsOutOfDate() {
    myStateIsOutOfDate = true;
    if (myChangedBlockData != null) {
      for (UnifiedDiffChange diffChange : myChangedBlockData.getDiffChanges()) {
        diffChange.updateGutterActions();
      }
    }
  }

  @Nullable
  private EditorHighlighter buildHighlighter(@Nullable Project project,
                                             @NotNull DocumentContent content1,
                                             @NotNull DocumentContent content2,
                                             @NotNull CharSequence text1,
                                             @NotNull CharSequence text2,
                                             @NotNull List<HighlightRange> ranges,
                                             int textLength) {
    EditorHighlighter highlighter1 = DiffUtil.initEditorHighlighter(project, content1, text1);
    EditorHighlighter highlighter2 = DiffUtil.initEditorHighlighter(project, content2, text2);

    if (highlighter1 == null && highlighter2 == null) return null;
    if (highlighter1 == null) highlighter1 = DiffUtil.initEmptyEditorHighlighter(text1);
    if (highlighter2 == null) highlighter2 = DiffUtil.initEmptyEditorHighlighter(text2);

    return new UnifiedEditorHighlighter(myDocument, highlighter1, highlighter2, ranges, textLength);
  }

  @NotNull
  private Runnable apply(@NotNull final CombinedEditorData data,
                         @NotNull final List<ChangedBlock> blocks,
                         @NotNull final LineNumberConvertor convertor,
                         @NotNull final List<LineRange> changedLines,
                         final boolean isEqual, final boolean innerFragments) {
    return new Runnable() {
      @Override
      public void run() {
        myFoldingModel.updateContext(myRequest, getFoldingModelSettings());

        clearDiffPresentation();
        if (isEqual) myPanel.addNotification(DiffNotifications.EQUAL_CONTENTS);

        TIntFunction separatorLines = myFoldingModel.getLineNumberConvertor();
        myEditor.getGutterComponentEx().setLineNumberConvertor(mergeConverters(data.getLineConvertor1(), separatorLines),
                                                               mergeConverters(data.getLineConvertor2(), separatorLines));

        ApplicationManager.getApplication().runWriteAction(new Runnable() {
          @Override
          public void run() {
            myDuringOnesideDocumentModification = true;
            try {
              myDocument.setText(data.getText());
            }
            finally {
              myDuringOnesideDocumentModification = false;
            }
          }
        });

        if (data.getHighlighter() != null) myEditor.setHighlighter(data.getHighlighter());
        DiffUtil.setEditorCodeStyle(myProject, myEditor, data.getFileType());

        if (data.getRangeHighlighter() != null) data.getRangeHighlighter().apply(myProject, myDocument);


        ArrayList<UnifiedDiffChange> diffChanges = new ArrayList<UnifiedDiffChange>(blocks.size());
        for (ChangedBlock block : blocks) {
          diffChanges.add(new UnifiedDiffChange(UnifiedDiffViewer.this, block, innerFragments));
        }

        List<RangeMarker> guarderRangeBlocks = new ArrayList<RangeMarker>();
        if (!myEditor.isViewer()) {
          for (ChangedBlock block : blocks) {
            int start = myMasterSide.select(block.getStartOffset2(), block.getStartOffset1());
            int end = myMasterSide.select(block.getEndOffset2() - 1, block.getEndOffset1() - 1);
            if (start >= end) continue;
            guarderRangeBlocks.add(createGuardedBlock(start, end));
          }
          int textLength = myDocument.getTextLength(); // there are 'fake' newline at the very end
          guarderRangeBlocks.add(createGuardedBlock(textLength, textLength));
        }

        myChangedBlockData = new ChangedBlockData(diffChanges, guarderRangeBlocks, convertor);

        myFoldingModel.install(changedLines, myRequest, getFoldingModelSettings());

        myInitialScrollHelper.onRediff();

        myStatusPanel.update();
        myPanel.setGoodContent();
      }
    };
  }

  @NotNull
  private RangeMarker createGuardedBlock(int start, int end) {
    RangeMarker block = myDocument.createGuardedBlock(start, end);
    block.setGreedyToLeft(true);
    block.setGreedyToRight(true);
    return block;
  }

  @Contract("!null, _ -> !null")
  private static TIntFunction mergeConverters(@NotNull final TIntFunction convertor, @NotNull final TIntFunction separatorLines) {
    return new TIntFunction() {
      @Override
      public int execute(int value) {
        return convertor.execute(separatorLines.execute(value));
      }
    };
  }

  /*
   * This convertor returns -1 if exact matching is impossible
   */
  @CalledInAwt
  protected int transferLineToOnesideStrict(@NotNull Side side, int line) {
    if (myChangedBlockData == null) return -1;

    LineNumberConvertor lineConvertor = myChangedBlockData.getLineNumberConvertor();
    return side.isLeft() ? lineConvertor.convertInv1(line) : lineConvertor.convertInv2(line);
  }

  /*
   * This convertor returns -1 if exact matching is impossible
   */
  @CalledInAwt
  protected int transferLineFromOnesideStrict(@NotNull Side side, int line) {
    if (myChangedBlockData == null) return -1;

    LineNumberConvertor lineConvertor = myChangedBlockData.getLineNumberConvertor();
    return side.isLeft() ? lineConvertor.convert1(line) : lineConvertor.convert2(line);
  }

  /*
   * This convertor returns 'good enough' position, even if exact matching is impossible
   */
  @CalledInAwt
  protected int transferLineToOneside(@NotNull Side side, int line) {
    if (myChangedBlockData == null) return line;

    LineNumberConvertor lineConvertor = myChangedBlockData.getLineNumberConvertor();
    return side.isLeft() ? lineConvertor.convertApproximateInv1(line) : lineConvertor.convertApproximateInv2(line);
  }

  /*
   * This convertor returns 'good enough' position, even if exact matching is impossible
   */
  @CalledInAwt
  @NotNull
  protected Pair<int[], Side> transferLineFromOneside(int line) {
    int[] lines = new int[2];

    if (myChangedBlockData == null) {
      lines[0] = line;
      lines[1] = line;
      return Pair.create(lines, myMasterSide);
    }

    LineNumberConvertor lineConvertor = myChangedBlockData.getLineNumberConvertor();

    Side side = myMasterSide;
    lines[0] = lineConvertor.convert1(line);
    lines[1] = lineConvertor.convert2(line);

    if (lines[0] == -1 && lines[1] == -1) {
      lines[0] = lineConvertor.convertApproximate1(line);
      lines[1] = lineConvertor.convertApproximate2(line);
    }
    else if (lines[0] == -1) {
      lines[0] = lineConvertor.convertApproximate1(line);
      side = Side.RIGHT;
    }
    else if (lines[1] == -1) {
      lines[1] = lineConvertor.convertApproximate2(line);
      side = Side.LEFT;
    }

    return Pair.create(lines, side);
  }

  @CalledInAwt
  private void destroyChangedBlockData() {
    if (myChangedBlockData == null) return;

    for (UnifiedDiffChange change : myChangedBlockData.getDiffChanges()) {
      change.destroyHighlighter();
    }
    for (RangeMarker block : myChangedBlockData.getGuardedRangeBlocks()) {
      myDocument.removeGuardedBlock(block);
    }
    myChangedBlockData = null;

    UnifiedEditorRangeHighlighter.erase(myProject, myDocument);

    myFoldingModel.destroy();

    myStatusPanel.update();
  }

  //
  // Typing
  //

  private class MyOnesideDocumentListener extends DocumentAdapter {
    @Override
    public void beforeDocumentChange(DocumentEvent e) {
      if (myDuringOnesideDocumentModification) return;
      if (myChangedBlockData == null) {
        LOG.warn("oneside beforeDocumentChange - myChangedBlockData == null");
        return;
      }
      // TODO: modify Document guard range logic - we can handle case, when whole read-only block is modified (ex: my replacing selection).

      try {
        myDuringTwosideDocumentModification = true;

        Document twosideDocument = getDocument(myMasterSide);

        LineCol onesideStartPosition = LineCol.fromOffset(myDocument, e.getOffset());
        LineCol onesideEndPosition = LineCol.fromOffset(myDocument, e.getOffset() + e.getOldLength());

        int line1 = onesideStartPosition.line;
        int line2 = onesideEndPosition.line + 1;
        int shift = DiffUtil.countLinesShift(e);

        int twosideStartLine = transferLineFromOnesideStrict(myMasterSide, onesideStartPosition.line);
        int twosideEndLine = transferLineFromOnesideStrict(myMasterSide, onesideEndPosition.line);
        if (twosideStartLine == -1 || twosideEndLine == -1) {
          // this should never happen
          logDebugInfo(e, onesideStartPosition, onesideEndPosition, twosideStartLine, twosideEndLine);
          markSuppressEditorTyping();
          return;
        }

        int twosideStartOffset = twosideDocument.getLineStartOffset(twosideStartLine) + onesideStartPosition.column;
        int twosideEndOffset = twosideDocument.getLineStartOffset(twosideEndLine) + onesideEndPosition.column;
        twosideDocument.replaceString(twosideStartOffset, twosideEndOffset, e.getNewFragment());

        for (UnifiedDiffChange change : myChangedBlockData.getDiffChanges()) {
          change.processChange(line1, line2, shift);
        }

        LineNumberConvertor lineNumberConvertor = myChangedBlockData.getLineNumberConvertor();
        lineNumberConvertor.handleOnesideChange(line1, line2, shift, myMasterSide);
      }
      finally {
        // TODO: we can avoid marking state out-of-date in some simple cases (like in SimpleDiffViewer)
        // but this will greatly increase complexity, so let's wait if it's actually required by users
        markStateIsOutOfDate();

        myFoldingModel.onDocumentChanged(e);
        scheduleRediff();

        myDuringTwosideDocumentModification = false;
      }
    }

    private void logDebugInfo(DocumentEvent e,
                              LineCol onesideStartPosition, LineCol onesideEndPosition,
                              int twosideStartLine, int twosideEndLine) {
      StringBuilder info = new StringBuilder();
      Document document1 = getDocument(Side.LEFT);
      Document document2 = getDocument(Side.RIGHT);
      info.append("==== OnesideDiffViewer Debug Info ====");
      info.append("myMasterSide - ").append(myMasterSide).append('\n');
      info.append("myLeftDocument.length() - ").append(document1.getTextLength()).append('\n');
      info.append("myRightDocument.length() - ").append(document2.getTextLength()).append('\n');
      info.append("myDocument.length() - ").append(myDocument.getTextLength()).append('\n');
      info.append("e.getOffset() - ").append(e.getOffset()).append('\n');
      info.append("e.getNewLength() - ").append(e.getNewLength()).append('\n');
      info.append("e.getOldLength() - ").append(e.getOldLength()).append('\n');
      info.append("onesideStartPosition - ").append(onesideStartPosition).append('\n');
      info.append("onesideEndPosition - ").append(onesideEndPosition).append('\n');
      info.append("twosideStartLine - ").append(twosideStartLine).append('\n');
      info.append("twosideEndLine - ").append(twosideEndLine).append('\n');
      Pair<int[], Side> pair1 = transferLineFromOneside(onesideStartPosition.line);
      Pair<int[], Side> pair2 = transferLineFromOneside(onesideEndPosition.line);
      info.append("non-strict transferStartLine - ").append(pair1.first[0]).append("-").append(pair1.first[1])
        .append(":").append(pair1.second).append('\n');
      info.append("non-strict transferEndLine - ").append(pair2.first[0]).append("-").append(pair2.first[1])
        .append(":").append(pair2.second).append('\n');
      info.append("---- OnesideDiffViewer Debug Info ----");

      LOG.warn(info.toString());
    }
  }

  @Override
  protected void onDocumentChange(@NotNull DocumentEvent e) {
    if (myDuringTwosideDocumentModification) return;

    markStateIsOutOfDate();
    markSuppressEditorTyping();

    myFoldingModel.onDocumentChanged(e);
    scheduleRediff();
  }

  @CalledWithWriteLock
  public void applyChange(@NotNull UnifiedDiffChange change, @NotNull Side sourceSide) {
    if (myStateIsOutOfDate || myChangedBlockData == null) return;

    Side affectedSide = sourceSide.other();
    if (!isEditable(affectedSide, true)) return;

    Document document1 = getDocument(Side.LEFT);
    Document document2 = getDocument(Side.RIGHT);

    LineFragment lineFragment = change.getLineFragment();

    DiffUtil.applyModification(affectedSide.select(document1, document2),
                               affectedSide.getStartLine(lineFragment), affectedSide.getEndLine(lineFragment),
                               sourceSide.select(document1, document2),
                               sourceSide.getStartLine(lineFragment), sourceSide.getEndLine(lineFragment));

    // no need to mark myStateIsOutOfDate - it will be made by DocumentListener
    // TODO: we can apply change manually, without marking state out-of-date. But we'll have to schedule rediff anyway.
    scheduleRediff();
  }

  //
  // Impl
  //


  @NotNull
  public TextDiffSettingsHolder.TextDiffSettings getTextSettings() {
    return TextDiffViewerUtil.getTextSettings(myContext);
  }

  @NotNull
  public FoldingModelSupport.Settings getFoldingModelSettings() {
    return TextDiffViewerUtil.getFoldingModelSettings(myContext);
  }

  @NotNull
  private DiffUtil.DiffConfig getDiffConfig() {
    return new DiffUtil.DiffConfig(getIgnorePolicy(), getHighlightPolicy());
  }

  @NotNull
  private HighlightPolicy getHighlightPolicy() {
    HighlightPolicy policy = getTextSettings().getHighlightPolicy();
    if (policy == HighlightPolicy.DO_NOT_HIGHLIGHT) return HighlightPolicy.BY_LINE;
    return policy;
  }

  @NotNull
  private IgnorePolicy getIgnorePolicy() {
    IgnorePolicy policy = getTextSettings().getIgnorePolicy();
    if (policy == IgnorePolicy.IGNORE_WHITESPACES_CHUNKS) return IgnorePolicy.IGNORE_WHITESPACES;
    return policy;
  }

  //
  // Getters
  //

  @NotNull
  public EditorEx getEditor() {
    return myEditor;
  }

  @NotNull
  protected List<? extends EditorEx> getEditors() {
    return Collections.singletonList(myEditor);
  }

  @NotNull
  protected List<? extends DocumentContent> getContents() {
    //noinspection unchecked
    return (List<? extends DocumentContent>)(List)myRequest.getContents();
  }

  @NotNull
  protected DocumentContent getContent(@NotNull Side side) {
    return side.select(getContents());
  }

  @NotNull
  protected DocumentContent getContent1() {
    return getContent(Side.LEFT);
  }

  @NotNull
  protected DocumentContent getContent2() {
    return getContent(Side.RIGHT);
  }

  @CalledInAwt
  @Nullable
  protected List<UnifiedDiffChange> getDiffChanges() {
    return myChangedBlockData == null ? null : myChangedBlockData.getDiffChanges();
  }

  @NotNull
  @Override
  public JComponent getComponent() {
    return myPanel;
  }

  @Nullable
  @Override
  public JComponent getPreferredFocusedComponent() {
    if (!myPanel.isGoodContent()) return null;
    return myEditor.getContentComponent();
  }

  @NotNull
  @Override
  protected JComponent getStatusPanel() {
    return myStatusPanel;
  }

  @CalledInAwt
  public boolean isEditable(@NotNull Side side, boolean respectReadOnlyLock) {
    if (myReadOnlyLockSet && respectReadOnlyLock) return false;
    if (side.select(myForceReadOnlyFlags)) return false;
    return DiffUtil.canMakeWritable(getDocument(side));
  }

  @NotNull
  public Document getDocument(@NotNull Side side) {
    return getContent(side).getDocument();
  }

  protected boolean isStateIsOutOfDate() {
    return myStateIsOutOfDate;
  }

  //
  // Misc
  //

  @Nullable
  @Override
  protected OpenFileDescriptor getOpenFileDescriptor() {
    return getOpenFileDescriptor(myEditor.getCaretModel().getOffset());
  }

  @CalledInAwt
  @Nullable
  protected UnifiedDiffChange getCurrentChange() {
    if (myChangedBlockData == null) return null;
    int caretLine = myEditor.getCaretModel().getLogicalPosition().line;

    for (UnifiedDiffChange change : myChangedBlockData.getDiffChanges()) {
      if (DiffUtil.isSelectedByLine(caretLine, change.getLine1(), change.getLine2())) return change;
    }
    return null;
  }

  @CalledInAwt
  @Nullable
  protected OpenFileDescriptor getOpenFileDescriptor(int offset) {
    LogicalPosition position = myEditor.offsetToLogicalPosition(offset);
    Pair<int[], Side> pair = transferLineFromOneside(position.line);
    int offset1 = DiffUtil.getOffset(getContent1().getDocument(), pair.first[0], position.column);
    int offset2 = DiffUtil.getOffset(getContent2().getDocument(), pair.first[1], position.column);

    // TODO: issue: non-optimal GoToSource position with caret on deleted block for "Compare with local"
    //       we should transfer using calculated diff, not jump to "somehow related" position from old content's descriptor

    OpenFileDescriptor descriptor1 = getContent1().getOpenFileDescriptor(offset1);
    OpenFileDescriptor descriptor2 = getContent2().getOpenFileDescriptor(offset2);
    if (descriptor1 == null) return descriptor2;
    if (descriptor2 == null) return descriptor1;
    return pair.second.select(descriptor1, descriptor2);
  }

  public static boolean canShowRequest(@NotNull DiffContext context, @NotNull DiffRequest request) {
    return TwosideTextDiffViewer.canShowRequest(context, request);
  }

  //
  // Actions
  //

  private class MyPrevNextDifferenceIterable extends PrevNextDifferenceIterableBase<UnifiedDiffChange> {
    @NotNull
    @Override
    protected List<UnifiedDiffChange> getChanges() {
      return ContainerUtil.notNullize(getDiffChanges());
    }

    @NotNull
    @Override
    protected EditorEx getEditor() {
      return myEditor;
    }

    @Override
    protected int getStartLine(@NotNull UnifiedDiffChange change) {
      return change.getLine1();
    }

    @Override
    protected int getEndLine(@NotNull UnifiedDiffChange change) {
      return change.getLine2();
    }

    @Override
    protected void scrollToChange(@NotNull UnifiedDiffChange change) {
      DiffUtil.scrollEditor(myEditor, change.getLine1(), true);
    }
  }

  private class MyOpenInEditorWithMouseAction extends OpenInEditorWithMouseAction {
    @Override
    protected OpenFileDescriptor getDescriptor(@NotNull Editor editor, int line) {
      if (editor != myEditor) return null;

      return getOpenFileDescriptor(myEditor.logicalPositionToOffset(new LogicalPosition(line, 0)));
    }
  }

  private class MyToggleExpandByDefaultAction extends TextDiffViewerUtil.ToggleExpandByDefaultAction {
    public MyToggleExpandByDefaultAction() {
      super(getTextSettings());
    }

    @Override
    protected void expandAll(boolean expand) {
      myFoldingModel.expandAll(expand);
    }
  }

  private class MyHighlightPolicySettingAction extends TextDiffViewerUtil.HighlightPolicySettingAction {
    public MyHighlightPolicySettingAction() {
      super(getTextSettings());
    }

    @NotNull
    @Override
    protected HighlightPolicy getCurrentSetting() {
      return getHighlightPolicy();
    }

    @NotNull
    @Override
    protected List<HighlightPolicy> getAvailableSettings() {
      ArrayList<HighlightPolicy> settings = ContainerUtil.newArrayList(HighlightPolicy.values());
      settings.remove(HighlightPolicy.DO_NOT_HIGHLIGHT);
      return settings;
    }

    @Override
    protected void onSettingsChanged() {
      rediff();
    }
  }

  private class MyIgnorePolicySettingAction extends TextDiffViewerUtil.IgnorePolicySettingAction {
    public MyIgnorePolicySettingAction() {
      super(getTextSettings());
    }

    @NotNull
    @Override
    protected IgnorePolicy getCurrentSetting() {
      return getIgnorePolicy();
    }

    @NotNull
    @Override
    protected List<IgnorePolicy> getAvailableSettings() {
      ArrayList<IgnorePolicy> settings = ContainerUtil.newArrayList(IgnorePolicy.values());
      settings.remove(IgnorePolicy.IGNORE_WHITESPACES_CHUNKS);
      return settings;
    }

    @Override
    protected void onSettingsChanged() {
      rediff();
    }
  }

  private class MyReadOnlyLockAction extends TextDiffViewerUtil.ReadOnlyLockAction {
    public MyReadOnlyLockAction() {
      super(getContext());
      init();
    }

    @Override
    protected void doApply(boolean readOnly) {
      myReadOnlyLockSet = readOnly;
      if (myChangedBlockData != null) {
        for (UnifiedDiffChange unifiedDiffChange : myChangedBlockData.getDiffChanges()) {
          unifiedDiffChange.updateGutterActions();
        }
      }
      updateEditorCanBeTyped();
    }

    @Override
    protected boolean canEdit() {
      return !myForceReadOnlyFlags[0] && DiffUtil.canMakeWritable(getContent1().getDocument()) ||
             !myForceReadOnlyFlags[1] && DiffUtil.canMakeWritable(getContent2().getDocument());
    }
  }

  //
  // Scroll from annotate
  //

  private class AllLinesIterator implements Iterator<Pair<Integer, CharSequence>> {
    @NotNull private final Side mySide;
    @NotNull private final Document myDocument;
    private int myLine = 0;

    private AllLinesIterator(@NotNull Side side) {
      mySide = side;

      myDocument = getContent(mySide).getDocument();
    }

    @Override
    public boolean hasNext() {
      return myLine < getLineCount(myDocument);
    }

    @Override
    public Pair<Integer, CharSequence> next() {
      int offset1 = myDocument.getLineStartOffset(myLine);
      int offset2 = myDocument.getLineEndOffset(myLine);

      CharSequence text = myDocument.getImmutableCharSequence().subSequence(offset1, offset2);

      Pair<Integer, CharSequence> pair = new Pair<Integer, CharSequence>(myLine, text);
      myLine++;

      return pair;
    }

    @Override
    public void remove() {
      throw new UnsupportedOperationException();
    }
  }

  private class ChangedLinesIterator extends BufferedLineIterator {
    @NotNull private final Side mySide;
    @NotNull private final List<UnifiedDiffChange> myChanges;

    private int myIndex = 0;

    private ChangedLinesIterator(@NotNull Side side, @NotNull List<UnifiedDiffChange> changes) {
      mySide = side;
      myChanges = changes;
      init();
    }

    @Override
    public boolean hasNextBlock() {
      return myIndex < myChanges.size();
    }

    @Override
    public void loadNextBlock() {
      LOG.assertTrue(!myStateIsOutOfDate);

      UnifiedDiffChange change = myChanges.get(myIndex);
      myIndex++;

      LineFragment lineFragment = change.getLineFragment();

      int insertedStart = lineFragment.getStartOffset2();
      int insertedEnd = lineFragment.getEndOffset2();
      CharSequence insertedText = getContent(mySide).getDocument().getCharsSequence().subSequence(insertedStart, insertedEnd);

      int lineNumber = lineFragment.getStartLine2();

      LineTokenizer tokenizer = new LineTokenizer(insertedText.toString());
      for (String line : tokenizer.execute()) {
        addLine(lineNumber, line);
        lineNumber++;
      }
    }
  }

  //
  // Helpers
  //

  @Nullable
  @Override
  public Object getData(@NonNls String dataId) {
    if (DiffDataKeys.PREV_NEXT_DIFFERENCE_ITERABLE.is(dataId)) {
      return myPrevNextDifferenceIterable;
    }
    else if (CommonDataKeys.VIRTUAL_FILE.is(dataId)) {
      return DiffUtil.getVirtualFile(myRequest, myMasterSide);
    }
    else if (DiffDataKeys.CURRENT_EDITOR.is(dataId)) {
      return myEditor;
    }
    else if (DiffDataKeys.CURRENT_CHANGE_RANGE.is(dataId)) {
      UnifiedDiffChange change = getCurrentChange();
      if (change != null) {
        return new LineRange(change.getLine1(), change.getLine2());
      }
    }
    return super.getData(dataId);
  }

  private class MyStatusPanel extends StatusPanel {
    @Override
    protected int getChangesCount() {
      return myChangedBlockData == null ? 0 : myChangedBlockData.getDiffChanges().size();
    }
  }

  private static class TwosideDocumentData {
    @NotNull private final UnifiedFragmentBuilder myBuilder;
    @Nullable private final EditorHighlighter myHighlighter;
    @Nullable private final UnifiedEditorRangeHighlighter myRangeHighlighter;

    public TwosideDocumentData(@NotNull UnifiedFragmentBuilder builder,
                               @Nullable EditorHighlighter highlighter,
                               @Nullable UnifiedEditorRangeHighlighter rangeHighlighter) {
      myBuilder = builder;
      myHighlighter = highlighter;
      myRangeHighlighter = rangeHighlighter;
    }

    @NotNull
    public UnifiedFragmentBuilder getBuilder() {
      return myBuilder;
    }

    @Nullable
    public EditorHighlighter getHighlighter() {
      return myHighlighter;
    }

    @Nullable
    public UnifiedEditorRangeHighlighter getRangeHighlighter() {
      return myRangeHighlighter;
    }
  }

  private static class ChangedBlockData {
    @NotNull private final List<UnifiedDiffChange> myDiffChanges;
    @NotNull private final List<RangeMarker> myGuardedRangeBlocks;
    @NotNull private final LineNumberConvertor myLineNumberConvertor;

    public ChangedBlockData(@NotNull List<UnifiedDiffChange> diffChanges,
                            @NotNull List<RangeMarker> guarderRangeBlocks,
                            @NotNull LineNumberConvertor lineNumberConvertor) {
      myDiffChanges = diffChanges;
      myGuardedRangeBlocks = guarderRangeBlocks;
      myLineNumberConvertor = lineNumberConvertor;
    }

    @NotNull
    public List<UnifiedDiffChange> getDiffChanges() {
      return myDiffChanges;
    }

    @NotNull
    public List<RangeMarker> getGuardedRangeBlocks() {
      return myGuardedRangeBlocks;
    }

    @NotNull
    public LineNumberConvertor getLineNumberConvertor() {
      return myLineNumberConvertor;
    }
  }

  private static class CombinedEditorData {
    @NotNull private final CharSequence myText;
    @Nullable private final EditorHighlighter myHighlighter;
    @Nullable private final UnifiedEditorRangeHighlighter myRangeHighlighter;
    @Nullable private final FileType myFileType;
    @NotNull private final TIntFunction myLineConvertor1;
    @NotNull private final TIntFunction myLineConvertor2;

    public CombinedEditorData(@NotNull CharSequence text,
                              @Nullable EditorHighlighter highlighter,
                              @Nullable UnifiedEditorRangeHighlighter rangeHighlighter,
                              @Nullable FileType fileType,
                              @NotNull TIntFunction convertor1,
                              @NotNull TIntFunction convertor2) {
      myText = text;
      myHighlighter = highlighter;
      myRangeHighlighter = rangeHighlighter;
      myFileType = fileType;
      myLineConvertor1 = convertor1;
      myLineConvertor2 = convertor2;
    }

    @NotNull
    public CharSequence getText() {
      return myText;
    }

    @Nullable
    public EditorHighlighter getHighlighter() {
      return myHighlighter;
    }

    @Nullable
    public UnifiedEditorRangeHighlighter getRangeHighlighter() {
      return myRangeHighlighter;
    }

    @Nullable
    public FileType getFileType() {
      return myFileType;
    }

    @NotNull
    public TIntFunction getLineConvertor1() {
      return myLineConvertor1;
    }

    @NotNull
    public TIntFunction getLineConvertor2() {
      return myLineConvertor2;
    }
  }

  private class MyInitialScrollHelper extends InitialScrollPositionSupport.TwosideInitialScrollHelper {
    @NotNull
    @Override
    protected List<? extends Editor> getEditors() {
      return UnifiedDiffViewer.this.getEditors();
    }

    @Override
    protected void disableSyncScroll(boolean value) {
    }

    @Override
    public void onSlowRediff() {
      // Will not happen for initial rediff
    }

    @Nullable
    @Override
    protected LogicalPosition[] getCaretPositions() {
      LogicalPosition position = myEditor.getCaretModel().getLogicalPosition();
      Pair<int[], Side> pair = transferLineFromOneside(position.line);
      LogicalPosition[] carets = new LogicalPosition[2];
      carets[0] = getPosition(pair.first[0], position.column);
      carets[1] = getPosition(pair.first[1], position.column);
      return carets;
    }

    @Override
    protected boolean doScrollToPosition() {
      if (myCaretPosition == null) return false;

      LogicalPosition twosidePosition = myMasterSide.selectNotNull(myCaretPosition);
      int onesideLine = transferLineToOneside(myMasterSide, twosidePosition.line);
      LogicalPosition position = new LogicalPosition(onesideLine, twosidePosition.column);

      myEditor.getCaretModel().moveToLogicalPosition(position);

      if (myEditorsPosition != null && myEditorsPosition.isSame(position)) {
        DiffUtil.scrollToPoint(myEditor, myEditorsPosition.myPoints[0], false);
      }
      else {
        DiffUtil.scrollToCaret(myEditor, false);
      }
      return true;
    }

    @NotNull
    private LogicalPosition getPosition(int line, int column) {
      if (line == -1) return new LogicalPosition(0, 0);
      return new LogicalPosition(line, column);
    }

    private void doScrollToLine(@NotNull Side side, @NotNull LogicalPosition position) {
      int onesideLine = transferLineToOneside(side, position.line);
      DiffUtil.scrollEditor(myEditor, onesideLine, position.column, false);
    }

    @Override
    protected boolean doScrollToLine() {
      if (myScrollToLine == null) return false;
      doScrollToLine(myScrollToLine.first, new LogicalPosition(myScrollToLine.second, 0));
      return true;
    }

    private boolean doScrollToChange(@NotNull ScrollToPolicy scrollToChangePolicy) {
      if (myChangedBlockData == null) return false;
      List<UnifiedDiffChange> changes = myChangedBlockData.getDiffChanges();

      UnifiedDiffChange targetChange = scrollToChangePolicy.select(changes);
      if (targetChange == null) return false;

      DiffUtil.scrollEditor(myEditor, targetChange.getLine1(), false);
      return true;
    }

    @Override
    protected boolean doScrollToChange() {
      if (myScrollToChange == null) return false;
      return doScrollToChange(myScrollToChange);
    }

    @Override
    protected boolean doScrollToFirstChange() {
      return doScrollToChange(ScrollToPolicy.FIRST_CHANGE);
    }

    @Override
    protected boolean doScrollToContext() {
      if (myNavigationContext == null) return false;
      if (myChangedBlockData == null) return false;

      ChangedLinesIterator changedLinesIterator = new ChangedLinesIterator(Side.RIGHT, myChangedBlockData.getDiffChanges());
      NavigationContextChecker checker = new NavigationContextChecker(changedLinesIterator, myNavigationContext);
      int line = checker.contextMatchCheck();
      if (line == -1) {
        // this will work for the case, when spaces changes are ignored, and corresponding fragments are not reported as changed
        // just try to find target line  -> +-
        AllLinesIterator allLinesIterator = new AllLinesIterator(Side.RIGHT);
        NavigationContextChecker checker2 = new NavigationContextChecker(allLinesIterator, myNavigationContext);
        line = checker2.contextMatchCheck();
      }
      if (line == -1) return false;

      doScrollToLine(Side.RIGHT, new LogicalPosition(line, 0));
      return true;
    }
  }

  private static class MyFoldingModel extends FoldingModelSupport {
    public MyFoldingModel(@NotNull EditorEx editor, @NotNull Disposable disposable) {
      super(new EditorEx[]{editor}, disposable);
    }

    public void install(@Nullable List<LineRange> changedLines,
                        @NotNull UserDataHolder context,
                        @NotNull FoldingModelSupport.Settings settings) {
      Iterator<int[]> it = map(changedLines, new Function<LineRange, int[]>() {
        @Override
        public int[] fun(LineRange line) {
          return new int[]{
            line.start,
            line.end};
        }
      });
      install(it, context, settings);
    }

    @NotNull
    public TIntFunction getLineNumberConvertor() {
      return getLineConvertor(0);
    }
  }

  private static class MyReadonlyFragmentModificationHandler implements ReadonlyFragmentModificationHandler {
    @Override
    public void handle(ReadOnlyFragmentModificationException e) {
      // do nothing
    }
  }
}


File: platform/platform-api/src/com/intellij/openapi/command/undo/UndoManager.java
/*
 * Copyright 2000-2009 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.openapi.command.undo;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.fileEditor.FileEditor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Pair;
import org.jetbrains.annotations.Nullable;

public abstract class UndoManager {

  public static UndoManager getInstance(Project project) {
    return project.getComponent(UndoManager.class);
  }

  public static UndoManager getGlobalInstance() {
    return ApplicationManager.getApplication().getComponent(UndoManager.class);
  }

  public abstract void undoableActionPerformed(UndoableAction action);
  public abstract void nonundoableActionPerformed(DocumentReference ref, boolean isGlobal);

  public abstract boolean isUndoInProgress();
  public abstract boolean isRedoInProgress();

  public abstract void undo(@Nullable FileEditor editor);
  public abstract void redo(@Nullable FileEditor editor);
  public abstract boolean isUndoAvailable(@Nullable FileEditor editor);
  public abstract boolean isRedoAvailable(@Nullable FileEditor editor);

  public abstract Pair<String, String> getUndoActionNameAndDescription(FileEditor editor);
  public abstract Pair<String, String> getRedoActionNameAndDescription(FileEditor editor);
}

File: platform/platform-api/src/com/intellij/openapi/diff/FragmentContent.java
/*
 * Copyright 2000-2013 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.openapi.diff;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.EditorFactory;
import com.intellij.openapi.editor.RangeMarker;
import com.intellij.openapi.editor.event.DocumentEvent;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Key;
import com.intellij.openapi.util.TextRange;
import com.intellij.openapi.vfs.VirtualFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;

/**
 * Represents sub text of other content. Original content should provide not null document.
 */
public class FragmentContent extends DiffContent {
  private static final Logger LOG = Logger.getInstance("#com.intellij.openapi.diff.FragmentContent");
  private final DiffContent myOriginal;
  private final FileType myType;
  private final MyDocumentsSynchronizer mySynchonizer;
  public static final Key<Document> ORIGINAL_DOCUMENT = new Key<Document>("ORIGINAL_DOCUMENT");
  private final boolean myForceReadOnly;

  public FragmentContent(@NotNull DiffContent original, @NotNull TextRange range, Project project, VirtualFile file) {
    this(original, range, project, file, false);
  }

  public FragmentContent(@NotNull DiffContent original, @NotNull TextRange range, Project project, VirtualFile file, boolean forceReadOnly) {
    this(original, range, project, file != null ? DiffContentUtil.getContentType(file) : null, forceReadOnly);
  }

  public FragmentContent(@NotNull DiffContent original, @NotNull TextRange range, Project project, FileType fileType) {
    this(original, range, project, fileType, false);
  }

  public FragmentContent(@NotNull DiffContent original, @NotNull TextRange range, Project project, FileType fileType, boolean forceReadOnly) {
    RangeMarker rangeMarker = original.getDocument().createRangeMarker(range.getStartOffset(), range.getEndOffset(), true);
    rangeMarker.setGreedyToLeft(true);
    rangeMarker.setGreedyToRight(true);
    mySynchonizer = new MyDocumentsSynchronizer(project, rangeMarker);
    myOriginal = original;
    myType = fileType;
    myForceReadOnly = forceReadOnly;
  }

  public FragmentContent(DiffContent original, TextRange range, Project project) {
    this(original, range, project, (FileType)null);
  }

  private static String subText(Document document, int startOffset, int length) {
    return document.getCharsSequence().subSequence(startOffset, startOffset + length).toString();
  }


  @Override
  public void onAssigned(boolean isAssigned) {
    myOriginal.onAssigned(isAssigned);
    mySynchonizer.listenDocuments(isAssigned);
    super.onAssigned(isAssigned);
  }

  @Override
  @NotNull
  public Document getDocument() {
    return mySynchonizer.getCopy();
  }

  @Override
  public OpenFileDescriptor getOpenFileDescriptor(int offset) {
    return myOriginal.getOpenFileDescriptor(offset + mySynchonizer.getStartOffset());
  }

  @Override
  public VirtualFile getFile() {
    return null;
  }

  @Override
  @Nullable
  public FileType getContentType() {
    return myType != null ? myType : myOriginal.getContentType();
  }

  @Override
  public byte[] getBytes() throws IOException {
    return getDocument().getText().getBytes();
  }

  public static FragmentContent fromRangeMarker(RangeMarker rangeMarker, Project project) {
    Document document = rangeMarker.getDocument();
    VirtualFile file = FileDocumentManager.getInstance().getFile(document);
    FileType type = file.getFileType();
    return new FragmentContent(new DocumentContent(project, document), TextRange.create(rangeMarker), project, type);
  }

  private class MyDocumentsSynchronizer extends DocumentsSynchronizer {
    private final RangeMarker myRangeMarker;

    public MyDocumentsSynchronizer(Project project, @NotNull RangeMarker originalRange) {
      super(project);
      myRangeMarker = originalRange;
    }

    public int getStartOffset() {
      return myRangeMarker.getStartOffset();
    }

    @Override
    protected void onOriginalChanged(@NotNull DocumentEvent event, @NotNull Document copy) {
      if (!myRangeMarker.isValid()) {
        fireContentInvalid();
        return;
      }
      replaceString(copy, 0, copy.getTextLength(), subText(event.getDocument(), myRangeMarker.getStartOffset(), getLength()));
    }

    @Override
    protected void beforeListenersAttached(@NotNull Document original, @NotNull Document copy) {
      boolean readOnly = !copy.isWritable();
      if (readOnly) {
        copy.setReadOnly(false);
      }
      replaceString(copy, 0, copy.getTextLength(), subText(original, myRangeMarker.getStartOffset(), getLength()));
      copy.setReadOnly(readOnly);
    }

    private int getLength() {
      return myRangeMarker.getEndOffset() - myRangeMarker.getStartOffset();
    }

    @Override
    protected Document createOriginal() {
      return myRangeMarker.getDocument();
    }

    @NotNull
    @Override
    protected Document createCopy() {
      final Document originalDocument = myRangeMarker.getDocument();
      String textInRange =
        originalDocument.getCharsSequence().subSequence(myRangeMarker.getStartOffset(), myRangeMarker.getEndOffset()).toString();
      final Document result = EditorFactory.getInstance().createDocument(textInRange);
      result.setReadOnly(myForceReadOnly || !originalDocument.isWritable());
      result.putUserData(ORIGINAL_DOCUMENT, originalDocument);
      return result;
    }

    @Override
    protected void onCopyChanged(@NotNull DocumentEvent event, @NotNull Document original) {
      final int originalOffset = event.getOffset() + myRangeMarker.getStartOffset();
      LOG.assertTrue(originalOffset >= 0);
      if (!original.isWritable()) return;
      final String newText = subText(event.getDocument(), event.getOffset(), event.getNewLength());
      final int originalEnd = originalOffset + event.getOldLength();
      replaceString(original, originalOffset, originalEnd, newText);
    }
  }
}


File: platform/platform-impl/src/com/intellij/openapi/command/impl/UndoManagerImpl.java
/*
 * Copyright 2000-2009 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.intellij.openapi.command.impl;

import com.intellij.CommonBundle;
import com.intellij.ide.DataManager;
import com.intellij.idea.ActionsBundle;
import com.intellij.openapi.Disposable;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.application.Application;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.command.*;
import com.intellij.openapi.command.undo.*;
import com.intellij.openapi.components.ApplicationComponent;
import com.intellij.openapi.components.ProjectComponent;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.diff.FragmentContent;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.EditorFactory;
import com.intellij.openapi.editor.impl.EditorImpl;
import com.intellij.openapi.extensions.Extensions;
import com.intellij.openapi.fileEditor.*;
import com.intellij.openapi.fileEditor.impl.text.TextEditorProvider;
import com.intellij.openapi.ide.CopyPasteManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.project.ex.ProjectEx;
import com.intellij.openapi.startup.StartupManager;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Disposer;
import com.intellij.openapi.util.EmptyRunnable;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.registry.Registry;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.openapi.wm.ex.WindowManagerEx;
import com.intellij.psi.ExternalChangeAction;
import com.intellij.psi.PsiDocumentManager;
import com.intellij.util.containers.HashSet;
import gnu.trove.THashSet;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.annotations.TestOnly;

import java.awt.*;
import java.util.*;
import java.util.List;

public class UndoManagerImpl extends UndoManager implements ProjectComponent, ApplicationComponent, Disposable {
  private static final Logger LOG = Logger.getInstance("#com.intellij.openapi.command.impl.UndoManagerImpl");

  private static final int COMMANDS_TO_KEEP_LIVE_QUEUES = 100;
  private static final int COMMAND_TO_RUN_COMPACT = 20;
  private static final int FREE_QUEUES_LIMIT = 30;

  @Nullable private final ProjectEx myProject;
  private final CommandProcessor myCommandProcessor;
  private final StartupManager myStartupManager;

  private UndoProvider[] myUndoProviders;
  private CurrentEditorProvider myEditorProvider;

  private final UndoRedoStacksHolder myUndoStacksHolder = new UndoRedoStacksHolder(true);
  private final UndoRedoStacksHolder myRedoStacksHolder = new UndoRedoStacksHolder(false);

  private final CommandMerger myMerger;

  private CommandMerger myCurrentMerger;
  private Project myCurrentActionProject = DummyProject.getInstance();

  private int myCommandTimestamp = 1;

  private int myCommandLevel = 0;
  private static final int NONE = 0;
  private static final int UNDO = 1;
  private static final int REDO = 2;
  private int myCurrentOperationState = NONE;

  private DocumentReference myOriginatorReference;

  public static boolean isRefresh() {
    return ApplicationManager.getApplication().hasWriteAction(ExternalChangeAction.class);
  }

  public static int getGlobalUndoLimit() {
    return Registry.intValue("undo.globalUndoLimit");
  }

  public static int getDocumentUndoLimit() {
    return Registry.intValue("undo.documentUndoLimit");
  }

  public UndoManagerImpl(Application application, CommandProcessor commandProcessor) {
    this(application, null, commandProcessor, null);
  }

  public UndoManagerImpl(Application application,
                         ProjectEx project,
                         CommandProcessor commandProcessor,
                         StartupManager startupManager) {
    myProject = project;
    myCommandProcessor = commandProcessor;
    myStartupManager = startupManager;

    init(application);

    myMerger = new CommandMerger(this);
  }

  private void init(Application application) {
    if (myProject == null || application.isUnitTestMode() && !myProject.isDefault()) {
      initialize();
    }
  }

  @Override
  @NotNull
  public String getComponentName() {
    return "UndoManager";
  }

  @Nullable
  public Project getProject() {
    return myProject;
  }

  @Override
  public void initComponent() {
  }

  @Override
  public void projectOpened() {
    if (!ApplicationManager.getApplication().isUnitTestMode()) {
      initialize();
    }
  }

  @Override
  public void projectClosed() {
  }

  @Override
  public void disposeComponent() {
  }

  @Override
  public void dispose() {
  }

  private void initialize() {
    if (myProject == null) {
      runStartupActivity();
    }
    else {
      myStartupManager.registerStartupActivity(new Runnable() {
        @Override
        public void run() {
          runStartupActivity();
        }
      });
    }
  }

  private void runStartupActivity() {
    myEditorProvider = new FocusBasedCurrentEditorProvider();
    CommandListener commandListener = new CommandAdapter() {
      private boolean myStarted = false;

      @Override
      public void commandStarted(CommandEvent event) {
        onCommandStarted(event.getProject(), event.getUndoConfirmationPolicy());
      }

      @Override
      public void commandFinished(CommandEvent event) {
        onCommandFinished(event.getProject(), event.getCommandName(), event.getCommandGroupId());
      }

      @Override
      public void undoTransparentActionStarted() {
        if (!isInsideCommand()) {
          myStarted = true;
          onCommandStarted(myProject, UndoConfirmationPolicy.DEFAULT);
        }
      }

      @Override
      public void undoTransparentActionFinished() {
        if (myStarted) {
          myStarted = false;
          onCommandFinished(myProject, "", null);
        }
      }
    };
    myCommandProcessor.addCommandListener(commandListener, this);

    Disposer.register(this, new DocumentUndoProvider(myProject));

    myUndoProviders = myProject == null
                      ? Extensions.getExtensions(UndoProvider.EP_NAME)
                      : Extensions.getExtensions(UndoProvider.PROJECT_EP_NAME, myProject);
    for (UndoProvider undoProvider : myUndoProviders) {
      if (undoProvider instanceof Disposable) {
        Disposer.register(this, (Disposable)undoProvider);
      }
    }
  }

  public boolean isActive() {
    return Comparing.equal(myProject, myCurrentActionProject);
  }

  private boolean isInsideCommand() {
    return myCommandLevel > 0;
  }

  private void onCommandStarted(final Project project, UndoConfirmationPolicy undoConfirmationPolicy) {
    if (myCommandLevel == 0) {
      for (UndoProvider undoProvider : myUndoProviders) {
        undoProvider.commandStarted(project);
      }
      myCurrentActionProject = project;
    }

    commandStarted(undoConfirmationPolicy, myProject == project);

    LOG.assertTrue(myCommandLevel == 0 || !(myCurrentActionProject instanceof DummyProject));
  }

  private void onCommandFinished(final Project project, final String commandName, final Object commandGroupId) {
    commandFinished(commandName, commandGroupId);
    if (myCommandLevel == 0) {
      for (UndoProvider undoProvider : myUndoProviders) {
        undoProvider.commandFinished(project);
      }
      myCurrentActionProject = DummyProject.getInstance();
    }
    LOG.assertTrue(myCommandLevel == 0 || !(myCurrentActionProject instanceof DummyProject));
  }

  private void commandStarted(UndoConfirmationPolicy undoConfirmationPolicy, boolean recordOriginalReference) {
    if (myCommandLevel == 0) {
      myCurrentMerger = new CommandMerger(this, CommandProcessor.getInstance().isUndoTransparentActionInProgress());

      if (recordOriginalReference && myProject != null) {
        Editor editor = null;
        final Application application = ApplicationManager.getApplication();
        if (application.isUnitTestMode() || application.isHeadlessEnvironment()) {
          editor = CommonDataKeys.EDITOR.getData(DataManager.getInstance().getDataContext());
        }
        else {
          Component component = WindowManagerEx.getInstanceEx().getFocusedComponent(myProject);
          if (component != null) {
            editor = CommonDataKeys.EDITOR.getData(DataManager.getInstance().getDataContext(component));
          }
        }

        if (editor != null) {
          Document document = editor.getDocument();
          VirtualFile file = FileDocumentManager.getInstance().getFile(document);
          if (file != null && file.isValid()) {
            myOriginatorReference = DocumentReferenceManager.getInstance().create(file);
          }
        }
      }
    }
    LOG.assertTrue(myCurrentMerger != null, String.valueOf(myCommandLevel));
    myCurrentMerger.setBeforeState(getCurrentState());
    myCurrentMerger.mergeUndoConfirmationPolicy(undoConfirmationPolicy);

    myCommandLevel++;

  }

  private void commandFinished(String commandName, Object groupId) {
    if (myCommandLevel == 0) return; // possible if command listener was added within command
    myCommandLevel--;
    if (myCommandLevel > 0) return;

    if (myProject != null && myCurrentMerger.hasActions() && !myCurrentMerger.isTransparent() && myCurrentMerger.isPhysical()) {
      addFocusedDocumentAsAffected();
    }
    myOriginatorReference = null;

    myCurrentMerger.setAfterState(getCurrentState());
    myMerger.commandFinished(commandName, groupId, myCurrentMerger);

    disposeCurrentMerger();
  }

  private void addFocusedDocumentAsAffected() {
    if (myOriginatorReference == null || myCurrentMerger.hasChangesOf(myOriginatorReference, true)) return;

    final DocumentReference[] refs = new DocumentReference[]{myOriginatorReference};
    myCurrentMerger.addAction(new BasicUndoableAction() {
      @Override
      public void undo() throws UnexpectedUndoException {
      }

      @Override
      public void redo() throws UnexpectedUndoException {
      }

      @Override
      public DocumentReference[] getAffectedDocuments() {
        return refs;
      }
    });
  }

  private EditorAndState getCurrentState() {
    FileEditor editor = myEditorProvider.getCurrentEditor();
    if (editor == null) {
      return null;
    }
    if (editor instanceof TextEditor) {
      Editor e = ((TextEditor)editor).getEditor();
      if (e instanceof EditorImpl && ((EditorImpl)e).myUseNewRendering && e.isDisposed()) {
        return null;
      }
    }
    return new EditorAndState(editor, editor.getState(FileEditorStateLevel.UNDO));
  }

  private void disposeCurrentMerger() {
    LOG.assertTrue(myCommandLevel == 0);
    if (myCurrentMerger != null) {
      myCurrentMerger = null;
    }
  }

  @Override
  public void nonundoableActionPerformed(final DocumentReference ref, final boolean isGlobal) {
    ApplicationManager.getApplication().assertIsDispatchThread();
    undoableActionPerformed(new NonUndoableAction(ref, isGlobal));
  }

  @Override
  public void undoableActionPerformed(UndoableAction action) {
    ApplicationManager.getApplication().assertIsDispatchThread();

    if (myCurrentOperationState != NONE) return;

    if (myCommandLevel == 0) {
      LOG.assertTrue(action instanceof NonUndoableAction,
                     "Undoable actions allowed inside commands only (see com.intellij.openapi.command.CommandProcessor.executeCommand())");
      commandStarted(UndoConfirmationPolicy.DEFAULT, false);
      myCurrentMerger.addAction(action);
      commandFinished("", null);
      return;
    }

    if (isRefresh()) myOriginatorReference = null;

    myCurrentMerger.addAction(action);
  }

  public void markCurrentCommandAsGlobal() {
    myCurrentMerger.markAsGlobal();
  }

  public void addAffectedDocuments(Document... docs) {
    if (!isInsideCommand()) {
      LOG.error("Must be called inside command");
      return;
    }
    List<DocumentReference> refs = new ArrayList<DocumentReference>(docs.length);
    for (Document each : docs) {
      // is document's file still valid
      VirtualFile file = FileDocumentManager.getInstance().getFile(each);
      if (file != null && !file.isValid()) continue;

      refs.add(DocumentReferenceManager.getInstance().create(each));
    }
    myCurrentMerger.addAdditionalAffectedDocuments(refs);
  }

  public void addAffectedFiles(VirtualFile... files) {
    if (!isInsideCommand()) {
      LOG.error("Must be called inside command");
      return;
    }
    List<DocumentReference> refs = new ArrayList<DocumentReference>(files.length);
    for (VirtualFile each : files) {
      refs.add(DocumentReferenceManager.getInstance().create(each));
    }
    myCurrentMerger.addAdditionalAffectedDocuments(refs);
  }

  public void invalidateActionsFor(DocumentReference ref) {
    ApplicationManager.getApplication().assertIsDispatchThread();
    myMerger.invalidateActionsFor(ref);
    if (myCurrentMerger != null) myCurrentMerger.invalidateActionsFor(ref);
    myUndoStacksHolder.invalidateActionsFor(ref);
    myRedoStacksHolder.invalidateActionsFor(ref);
  }

  @Override
  public void undo(@Nullable FileEditor editor) {
    ApplicationManager.getApplication().assertIsDispatchThread();
    LOG.assertTrue(isUndoAvailable(editor));
    undoOrRedo(editor, true);
  }

  @Override
  public void redo(@Nullable FileEditor editor) {
    ApplicationManager.getApplication().assertIsDispatchThread();
    LOG.assertTrue(isRedoAvailable(editor));
    undoOrRedo(editor, false);
  }

  private void undoOrRedo(final FileEditor editor, final boolean isUndo) {
    myCurrentOperationState = isUndo ? UNDO : REDO;

    final RuntimeException[] exception = new RuntimeException[1];
    Runnable executeUndoOrRedoAction = new Runnable() {
      @Override
      public void run() {
        try {
          if (myProject != null) {
            PsiDocumentManager.getInstance(myProject).commitAllDocuments();
          }
          CopyPasteManager.getInstance().stopKillRings();
          myMerger.undoOrRedo(editor, isUndo);
        }
        catch (RuntimeException ex) {
          exception[0] = ex;
        }
        finally {
          myCurrentOperationState = NONE;
        }
      }
    };

    String name = getUndoOrRedoActionNameAndDescription(editor, isUndoInProgress()).second;
    CommandProcessor.getInstance()
      .executeCommand(myProject, executeUndoOrRedoAction, name, null, myMerger.getUndoConfirmationPolicy());
    if (exception[0] != null) throw exception[0];
  }

  @Override
  public boolean isUndoInProgress() {
    return myCurrentOperationState == UNDO;
  }

  @Override
  public boolean isRedoInProgress() {
    return myCurrentOperationState == REDO;
  }

  @Override
  public boolean isUndoAvailable(@Nullable FileEditor editor) {
    return isUndoOrRedoAvailable(editor, true);
  }

  @Override
  public boolean isRedoAvailable(@Nullable FileEditor editor) {
    return isUndoOrRedoAvailable(editor, false);
  }

  protected boolean isUndoOrRedoAvailable(@Nullable FileEditor editor, boolean undo) {
    ApplicationManager.getApplication().assertIsDispatchThread();

    Collection<DocumentReference> refs = getDocRefs(editor);
    if (refs == null) {
      return false;
    }
    return isUndoOrRedoAvailable(refs, undo);
  }

  public boolean isUndoOrRedoAvailable(@NotNull DocumentReference ref) {
    Set<DocumentReference> refs = Collections.singleton(ref);
    return isUndoOrRedoAvailable(refs, true) || isUndoOrRedoAvailable(refs, false);
  }

  private boolean isUndoOrRedoAvailable(@NotNull Collection<DocumentReference> refs, boolean isUndo) {
    if (isUndo && myMerger.isUndoAvailable(refs)) return true;
    UndoRedoStacksHolder stackHolder = getStackHolder(isUndo);
    return stackHolder.canBeUndoneOrRedone(refs);
  }

  private static Collection<DocumentReference> getDocRefs(@Nullable FileEditor editor) {
    if (editor instanceof TextEditor && ((TextEditor)editor).getEditor().isViewer()) {
      return null;
    }
    if (editor == null) {
      return Collections.emptyList();
    }
    return getDocumentReferences(editor);
  }

  @NotNull
  static Set<DocumentReference> getDocumentReferences(@NotNull FileEditor editor) {
    Set<DocumentReference> result = new THashSet<DocumentReference>();

    if (editor instanceof DocumentReferenceProvider) {
      result.addAll(((DocumentReferenceProvider)editor).getDocumentReferences());
      return result;
    }

    Document[] documents = TextEditorProvider.getDocuments(editor);
    if (documents != null) {
      for (Document each : documents) {
        Document original = getOriginal(each);
        // KirillK : in AnAction.update we may have an editor with an invalid file
        VirtualFile f = FileDocumentManager.getInstance().getFile(each);
        if (f != null && !f.isValid()) continue;
        result.add(DocumentReferenceManager.getInstance().create(original));
      }
    }
    return result;
  }

  @NotNull
  private UndoRedoStacksHolder getStackHolder(boolean isUndo) {
    return isUndo ? myUndoStacksHolder : myRedoStacksHolder;
  }

  @Override
  public Pair<String, String> getUndoActionNameAndDescription(FileEditor editor) {
    return getUndoOrRedoActionNameAndDescription(editor, true);
  }

  @Override
  public Pair<String, String> getRedoActionNameAndDescription(FileEditor editor) {
    return getUndoOrRedoActionNameAndDescription(editor, false);
  }

  private Pair<String, String> getUndoOrRedoActionNameAndDescription(FileEditor editor, boolean undo) {
    String desc = isUndoOrRedoAvailable(editor, undo) ? doFormatAvailableUndoRedoAction(editor, undo) : null;
    if (desc == null) desc = "";
    String shortActionName = StringUtil.first(desc, 30, true);

    if (desc.length() == 0) {
      desc = undo
             ? ActionsBundle.message("action.undo.description.empty")
             : ActionsBundle.message("action.redo.description.empty");
    }

    return Pair.create((undo ? ActionsBundle.message("action.undo.text", shortActionName)
                             : ActionsBundle.message("action.redo.text", shortActionName)).trim(),
                       (undo ? ActionsBundle.message("action.undo.description", desc)
                             : ActionsBundle.message("action.redo.description", desc)).trim());
  }

  @Nullable
  private String doFormatAvailableUndoRedoAction(FileEditor editor, boolean isUndo) {
    Collection<DocumentReference> refs = getDocRefs(editor);
    if (refs == null) return null;
    if (isUndo && myMerger.isUndoAvailable(refs)) return myMerger.getCommandName();
    return getStackHolder(isUndo).getLastAction(refs).getCommandName();
  }

  public UndoRedoStacksHolder getUndoStacksHolder() {
    return myUndoStacksHolder;
  }

  public UndoRedoStacksHolder getRedoStacksHolder() {
    return myRedoStacksHolder;
  }

  public int nextCommandTimestamp() {
    return ++myCommandTimestamp;
  }

  static Document getOriginal(Document document) {
    Document result = document.getUserData(FragmentContent.ORIGINAL_DOCUMENT);
    return result == null ? document : result;
  }

  static boolean isCopy(Document d) {
    return d.getUserData(FragmentContent.ORIGINAL_DOCUMENT) != null;
  }

  protected void compact() {
    if (myCurrentOperationState == NONE && myCommandTimestamp % COMMAND_TO_RUN_COMPACT == 0) {
      doCompact();
    }
  }

  private void doCompact() {
    Collection<DocumentReference> refs = collectReferencesWithoutMergers();

    Collection<DocumentReference> openDocs = new HashSet<DocumentReference>();
    for (DocumentReference each : refs) {
      VirtualFile file = each.getFile();
      if (file == null) {
        Document document = each.getDocument();
        if (document != null && EditorFactory.getInstance().getEditors(document, myProject).length > 0) {
          openDocs.add(each);
        }
      }
      else {
        if (myProject != null && FileEditorManager.getInstance(myProject).isFileOpen(file)) {
          openDocs.add(each);
        }
      }
    }
    refs.removeAll(openDocs);

    if (refs.size() <= FREE_QUEUES_LIMIT) return;

    DocumentReference[] backSorted = refs.toArray(new DocumentReference[refs.size()]);
    Arrays.sort(backSorted, new Comparator<DocumentReference>() {
      @Override
      public int compare(DocumentReference a, DocumentReference b) {
        return getLastCommandTimestamp(a) - getLastCommandTimestamp(b);
      }
    });

    for (int i = 0; i < backSorted.length - FREE_QUEUES_LIMIT; i++) {
      DocumentReference each = backSorted[i];
      if (getLastCommandTimestamp(each) + COMMANDS_TO_KEEP_LIVE_QUEUES > myCommandTimestamp) break;
      clearUndoRedoQueue(each);
    }
  }

  private int getLastCommandTimestamp(DocumentReference ref) {
    return Math.max(myUndoStacksHolder.getLastCommandTimestamp(ref), myRedoStacksHolder.getLastCommandTimestamp(ref));
  }

  private Collection<DocumentReference> collectReferencesWithoutMergers() {
    Set<DocumentReference> result = new THashSet<DocumentReference>();
    myUndoStacksHolder.collectAllAffectedDocuments(result);
    myRedoStacksHolder.collectAllAffectedDocuments(result);
    return result;
  }

  private void clearUndoRedoQueue(DocumentReference docRef) {
    myMerger.flushCurrentCommand();
    disposeCurrentMerger();

    myUndoStacksHolder.clearStacks(false, Collections.singleton(docRef));
    myRedoStacksHolder.clearStacks(false, Collections.singleton(docRef));
  }

  @TestOnly
  public void setEditorProvider(CurrentEditorProvider p) {
    myEditorProvider = p;
  }

  @TestOnly
  public CurrentEditorProvider getEditorProvider() {
    return myEditorProvider;
  }

  @TestOnly
  public void dropHistoryInTests() {
    flushMergers();
    LOG.assertTrue(myCommandLevel == 0);

    myUndoStacksHolder.clearAllStacksInTests();
    myRedoStacksHolder.clearAllStacksInTests();
  }

  @TestOnly
  private void flushMergers() {
    // Run dummy command in order to flush all mergers...
    CommandProcessor.getInstance()
      .executeCommand(myProject, EmptyRunnable.getInstance(), CommonBundle.message("drop.undo.history.command.name"), null);
  }

  @TestOnly
  public void flushCurrentCommandMerger() {
    myMerger.flushCurrentCommand();
  }

  @TestOnly
  public void clearUndoRedoQueueInTests(VirtualFile file) {
    clearUndoRedoQueue(DocumentReferenceManager.getInstance().create(file));
  }

  @TestOnly
  public void clearUndoRedoQueueInTests(Document document) {
    clearUndoRedoQueue(DocumentReferenceManager.getInstance().create(document));
  }
}
