Refactoring Types: ['Extract Method']
e/lang/ide/ui/LangElementImages.java
/*******************************************************************************
 * Copyright (c) 2015, 2015 Bruno Medeiros and other Contributors.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package melnorme.lang.ide.ui;

import melnorme.lang.ide.ui.utils.PluginImagesHelper.ImageHandle;

public interface LangElementImages {

	String CAT_LANG_OBJ = "icons-lang/language_elements";
	
	ImageHandle CA_SNIPPET = LangImages.createManaged(CAT_LANG_OBJ, "CA_Templates.16.gif");
	
	
	ImageHandle ALIAS_ELEMENT = LangImages.createManaged(CAT_LANG_OBJ, "alias_se.png");
	
	ImageHandle ERROR_ELEMENT = LangImages.createManaged(CAT_LANG_OBJ, "error_element.png");
	
	ImageHandle FUNCTION = LangImages.createManaged(CAT_LANG_OBJ, "f_function.png");
	ImageHandle CONSTRUCTOR = LangImages.createManaged(CAT_LANG_OBJ, "f_constructor.png");
	
	ImageHandle MODULE = LangImages.createManaged(CAT_LANG_OBJ, "module.png");
	ImageHandle NAMESPACE = LangImages.createManaged(CAT_LANG_OBJ, "namespace.png");
	ImageHandle PACKAGE = LangImages.createManaged(CAT_LANG_OBJ, "package.png");
	
	ImageHandle T_CLASS = LangImages.createManaged(CAT_LANG_OBJ, "t_class.png");
	ImageHandle T_ENUM = LangImages.createManaged(CAT_LANG_OBJ, "t_enum.png");
	ImageHandle T_INTERFACE = LangImages.createManaged(CAT_LANG_OBJ, "t_interface.png");
	ImageHandle T_NATIVE = LangImages.createManaged(CAT_LANG_OBJ, "t_native.png");
	ImageHandle T_STRUCT = LangImages.createManaged(CAT_LANG_OBJ, "t_struct.png");
	ImageHandle T_TYPE = LangImages.createManaged(CAT_LANG_OBJ, "t_type.png");
//	ImageHandle T_UNION = LangImages.createManaged(CAT_LANG_OBJ, "t_union.gif");
	
	ImageHandle UKKNOWN  = LangImages.createManaged(CAT_LANG_OBJ, "unknown.png");
	
	ImageHandle VARIABLE = LangImages.createManaged(CAT_LANG_OBJ, "variable.png");

}

File: plugin_ide.ui/src-lang/melnorme/lang/ide/ui/actions/AbstractUIOperation.java
/*******************************************************************************
 * Copyright (c) 2014, 2014 Bruno Medeiros and other Contributors.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package melnorme.lang.ide.ui.actions;

import static melnorme.utilbox.core.Assert.AssertNamespace.assertNotNull;
import static melnorme.utilbox.core.Assert.AssertNamespace.assertTrue;

import java.text.MessageFormat;

import melnorme.lang.ide.core.LangCore;
import melnorme.lang.ide.ui.utils.UIOperationExceptionHandler;
import melnorme.utilbox.concurrency.OperationCancellation;
import melnorme.utilbox.core.CommonException;

import org.eclipse.core.runtime.CoreException;
import org.eclipse.core.runtime.IProgressMonitor;
import org.eclipse.core.runtime.NullProgressMonitor;
import org.eclipse.swt.widgets.Display;


public abstract class AbstractUIOperation {
	
	protected static final String MSG_EXECUTING_OPERATION 
		= "Executing {0}.";
	protected static final String MSG_ERROR_EXECUTING_OPERATION 
		= "Error executing {0}.";
	protected static final String MSG_INTERNAL_ERROR_EXECUTING_OPERATION 
		= "Internal error executing {0}.";
	
	
	protected final String operationName;
	
	public AbstractUIOperation(String operationName) {
		this.operationName = assertNotNull(operationName);
	}
	
	public String getOperationName() {
		return operationName;
	}
	
	public final void executeAndHandleResult() {
		executeAndHandle();
	}
	
	protected void executeAndHandle() {
		assertTrue(Display.getCurrent() != null);
		
		try {
			executeOperation();
		} catch (CoreException ce) {
			UIOperationExceptionHandler.handleOperationStatus(
				MessageFormat.format(MSG_ERROR_EXECUTING_OPERATION, operationName), ce);
		} catch (RuntimeException re) {
			UIOperationExceptionHandler.handleError(
				MessageFormat.format(MSG_INTERNAL_ERROR_EXECUTING_OPERATION, operationName), re);
		}
	}
	
	public final void executeOperation() throws CoreException {
		prepareOperation();
		
		try {
			performLongRunningComputation();
			
			validateComputationResult(false);
			
			handleComputationResult();
		} catch (OperationCancellation e) {
			validateComputationResult(true);
		}
	}
	
	protected void prepareOperation() throws CoreException {
	}
	
	protected void performLongRunningComputation() throws OperationCancellation, CoreException {
		if(Display.getCurrent() == null) {
			performLongRunningComputation_inCurrentThread();
			return;
		}
		performLongRunningComputation_usingProgressService();
	}
	
	protected void performLongRunningComputation_inCurrentThread() throws CoreException, OperationCancellation {
		// Perform computation directly in this thread, cancellation won't be possible.
		performLongRunningComputation_toCoreException(new NullProgressMonitor());
	}
	
	protected void performLongRunningComputation_usingProgressService() throws OperationCancellation, CoreException {
		computationRunnable.runUnderWorkbenchProgressService();
	}
	
	protected final OperationRunnableWithProgress computationRunnable = new OperationRunnableWithProgress() {
		@Override
		public void doRun(IProgressMonitor monitor) throws CoreException, OperationCancellation {
			monitor.setTaskName(getTaskName());
			
			performLongRunningComputation_toCoreException(monitor);
		}
	};
	
	/** @return the task name for the progress dialog. This method must be thread-safe. */
	protected String getTaskName() {
		return MessageFormat.format(MSG_EXECUTING_OPERATION, operationName);
	}
	
	protected final void performLongRunningComputation_toCoreException(IProgressMonitor monitor) 
			throws CoreException, OperationCancellation {
		try {
			performLongRunningComputation(monitor);
		} catch(CommonException ce) {
			throw LangCore.createCoreException(ce);
		}
	}
	
	/** Perform the long running computation. Runs in a background thread. */
	protected abstract void performLongRunningComputation(IProgressMonitor monitor) 
			throws CoreException, CommonException, OperationCancellation;
	
	@SuppressWarnings("unused")
	protected void validateComputationResult(boolean isCanceled) throws CoreException {
	}
	
	/** Handle long running computation result. This runs in UI thread. */
	protected void handleComputationResult() throws CoreException {
		// Default: do nothing
	}
	
}

File: plugin_ide.ui/src-lang/melnorme/lang/ide/ui/actions/CalculateValueUIOperation.java
/*******************************************************************************
 * Copyright (c) 2015, 2015 IBM Corporation and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package melnorme.lang.ide.ui.actions;

import melnorme.utilbox.concurrency.OperationCancellation;
import melnorme.utilbox.core.CommonException;

import org.eclipse.core.runtime.CoreException;
import org.eclipse.core.runtime.IProgressMonitor;

public abstract class CalculateValueUIOperation<VALUE> extends AbstractUIOperation {
	
	protected volatile VALUE resultValue;
	
	public CalculateValueUIOperation(String operationName) {
		super(operationName);
	}
	
	protected VALUE getResultValue() {
		return resultValue;
	}
	
	public VALUE executeAndGetHandledResult() {
		executeAndHandleResult();
		return getResultValue();
	}
	
	public VALUE executeAndGetValidatedResult() throws CoreException {
		executeOperation();
		return getResultValue();
	}
	
	@Override
	protected void performLongRunningComputation(IProgressMonitor monitor) throws CoreException, CommonException,
			OperationCancellation {
		resultValue = calculateValue(monitor);
	}
	
	protected abstract VALUE calculateValue(IProgressMonitor monitor) throws CoreException, CommonException,
		OperationCancellation;
	
	@Override
	protected void validateComputationResult(boolean isCanceled) throws CoreException {
		if(!isCanceled && resultValue == null) {
			handleNonCanceledNullResult();
		}
	}
	
	protected void handleNonCanceledNullResult() throws CoreException {
	}
	
}

File: plugin_ide.ui/src-lang/melnorme/lang/ide/ui/editor/actions/AbstractEditorOperation.java
/*******************************************************************************
 * Copyright (c) 2014, 2014 Bruno Medeiros and other Contributors.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package melnorme.lang.ide.ui.editor.actions;

import static melnorme.utilbox.core.Assert.AssertNamespace.assertNotNull;

import java.nio.file.Path;

import melnorme.lang.ide.core.LangCore;
import melnorme.lang.ide.ui.actions.AbstractUIOperation;
import melnorme.lang.ide.ui.actions.UIUserInteractionsHelper;
import melnorme.lang.ide.ui.editor.EditorUtils;
import melnorme.utilbox.misc.Location;

import org.eclipse.core.runtime.CoreException;
import org.eclipse.jface.text.IDocument;
import org.eclipse.ui.IEditorInput;
import org.eclipse.ui.IWorkbenchWindow;
import org.eclipse.ui.texteditor.ITextEditor;

public abstract class AbstractEditorOperation extends AbstractUIOperation {
	
	protected final ITextEditor editor;
	protected final IWorkbenchWindow window;
	protected final IEditorInput editorInput;
	protected final Location inputLoc;
	protected final IDocument doc;
	
	public AbstractEditorOperation(String operationName, ITextEditor editor) {
		super(operationName);
		this.editor = assertNotNull(editor);
		this.window = editor.getSite().getWorkbenchWindow();
		this.editorInput = editor.getEditorInput();
		Path inputPath = EditorUtils.getFilePathFromEditorInput(editorInput);
		this.inputLoc = Location.createValidOrNull(inputPath);
		this.doc = assertNotNull(editor.getDocumentProvider().getDocument(editor.getEditorInput()));
	}
	
	@Override
	protected void prepareOperation() throws CoreException {
		if(inputLoc == null) {
			throw LangCore.createCoreException("Could not determine filesystem path from editor input", null); 
		}
	}
	
	protected void dialogError(String msg) {
		UIUserInteractionsHelper.openError(window.getShell(), operationName, msg);
	}
	
	protected void dialogWarning(String msg) {
		UIUserInteractionsHelper.openWarning(window.getShell(), operationName, msg);
	}
	
	protected void dialogInfo(String msg) {
		UIUserInteractionsHelper.openInfo(window.getShell(), operationName, msg);
	}
	
}

File: plugin_ide.ui/src-lang/melnorme/lang/ide/ui/editor/actions/AbstractOpenElementOperation.java
/*******************************************************************************
 * Copyright (c) 2014, 2014 Bruno Medeiros and other Contributors.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package melnorme.lang.ide.ui.editor.actions;


import static melnorme.utilbox.core.CoreUtil.areEqual;
import melnorme.lang.ide.core.LangCore;
import melnorme.lang.ide.core.utils.EclipseUtils;
import melnorme.lang.ide.ui.EditorSettings_Actual;
import melnorme.lang.ide.ui.editor.AbstractLangEditor;
import melnorme.lang.ide.ui.editor.EditorUtils;
import melnorme.lang.ide.ui.editor.EditorUtils.OpenNewEditorMode;
import melnorme.lang.tooling.ast.SourceRange;
import melnorme.lang.tooling.ops.FindDefinitionResult;
import melnorme.lang.tooling.ops.SourceLineColumnRange;
import melnorme.utilbox.concurrency.OperationCancellation;
import melnorme.utilbox.core.CommonException;
import melnorme.utilbox.misc.Location;

import org.eclipse.core.resources.IFile;
import org.eclipse.core.resources.IProject;
import org.eclipse.core.runtime.CoreException;
import org.eclipse.core.runtime.IProgressMonitor;
import org.eclipse.jface.text.BadLocationException;
import org.eclipse.jface.text.IDocument;
import org.eclipse.jface.text.ITextViewer;
import org.eclipse.swt.widgets.Display;
import org.eclipse.ui.IEditorInput;
import org.eclipse.ui.texteditor.AbstractTextEditor;
import org.eclipse.ui.texteditor.ITextEditor;

public abstract class AbstractOpenElementOperation extends AbstractEditorOperation {
	
	protected final SourceRange range; // range of element to open. Usually only offset matters
	protected final OpenNewEditorMode openEditorMode;
	protected final IProject project;
	protected final SourceOperationContext context;
	
	// prepare_items
	protected int line_0;
	protected int col_0;
	
	protected String statusErrorMessage;
	protected FindDefinitionResult findResult;
	
	public AbstractOpenElementOperation(String operationName, ITextEditor editor, SourceRange range,
			OpenNewEditorMode openEditorMode) {
		super(operationName, editor);
		
		this.range = range;
		this.openEditorMode = openEditorMode;
		
		IFile file = EditorUtils.findFileOfEditor(editor);
		this.project = file == null ? null : file.getProject();
		
		ITextViewer viewer = null;
		if(editor instanceof AbstractLangEditor) {
			AbstractLangEditor langEditor = (AbstractLangEditor) editor;
			viewer = langEditor.getSourceViewer_();
		}
		
		this.context = new SourceOperationContext(viewer, range, editor);
	}
	
	public int getInvocationOffest() {
		return context.getInvocationOffset();
	}
	
	public SourceOperationContext getContext() {
		return context;
	}
	
	@Override
	protected void prepareOperation() throws CoreException {
		super.prepareOperation();
		
		line_0 = getContext().getInvocationLine_0();
		col_0 = getContext().getInvocationColumn_0();
	}
	
	@Override
	protected void performLongRunningComputation(IProgressMonitor monitor) 
			throws CoreException, CommonException, OperationCancellation {
		findResult = performLongRunningComputation_doAndGetResult(monitor);
	}
	
	protected abstract FindDefinitionResult performLongRunningComputation_doAndGetResult(IProgressMonitor monitor) 
			throws CoreException, CommonException, OperationCancellation;
	
	@Override
	protected void handleComputationResult() throws CoreException {
		if(statusErrorMessage != null) {
			handleStatusErrorMessage();
		}
		if(findResult == null) {
			return;
		}
		
		if(findResult.getErrorMessage() != null) {
			dialogError(findResult.getErrorMessage());
			return;
		}
		
		if(findResult.getInfoMessage() != null) {
			dialogInfo(findResult.getInfoMessage());
		}
		
		SourceLineColumnRange location = findResult.getLocation();
		if(location == null) {
			Display.getCurrent().beep();
			return;
		}
		
		openEditorForLocation(location);
	}
	
	protected void handleStatusErrorMessage() {
		if(editor instanceof AbstractTextEditor) {
			AbstractTextEditor abstractTextEditor = (AbstractTextEditor) editor;
			EditorUtils.setStatusLineErrorMessage(abstractTextEditor, statusErrorMessage, null);
		}
		Display.getCurrent().beep();
	}
	
	protected void openEditorForLocation(SourceLineColumnRange sourceLocation) throws CoreException {
		Location loc = EclipseUtils.location(sourceLocation.path);
		IEditorInput newInput = getNewEditorInput(loc);
		
		ITextEditor newEditor = EditorUtils.openTextEditorAndSetSelection(editor, EditorSettings_Actual.EDITOR_ID, 
			newInput, openEditorMode, null);
		
		IDocument doc = EditorUtils.getEditorDocument(newEditor);
		int selectionOffset = getOffsetFrom(doc, sourceLocation.line, sourceLocation.column);
		
		EditorUtils.setEditorSelection(newEditor, new SourceRange(selectionOffset, 0));
	}
	
	protected IEditorInput getNewEditorInput(Location newEditorFilePath) throws CoreException {
		if(newEditorFilePath == null) {
			throw LangCore.createCoreException("No path provided for new element. ", null);
		}
		
		if(areEqual(newEditorFilePath, inputLoc)) {
			return editor.getEditorInput();
		} else {
			return EditorUtils.getBestEditorInputForLoc(newEditorFilePath);
		}
	}
	
	protected static int getOffsetFrom(IDocument doc, int line_oneBased, int column_oneBased) throws CoreException {
		int lineOffset;
		try {
			lineOffset = doc.getLineOffset(line_oneBased-1);
		} catch (BadLocationException e) {
			throw LangCore.createCoreException("Invalid line number: " + line_oneBased, e);
		}
		
		return lineOffset + column_oneBased-1;
	}
	
}

File: plugin_ide.ui/src-lang/melnorme/lang/ide/ui/views/AbstractLangImageProvider.java
/*******************************************************************************
 * Copyright (c) 2015, 2015 Bruno Medeiros and other Contributors.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package melnorme.lang.ide.ui.views;

import melnorme.lang.ide.ui.LangElementImages;
import melnorme.lang.tooling.CompletionProposalKind;
import melnorme.lang.tooling.CompletionProposalKind.ProposalKindVisitor;
import melnorme.lang.tooling.structure.StructureElementKind.StructureElementKindVisitor;
import melnorme.util.swt.jface.IManagedImage;
import melnorme.util.swt.jface.IManagedImage.NullManagedImage;


public abstract class AbstractLangImageProvider implements 
	ProposalKindVisitor<IManagedImage>, 
	StructureElementKindVisitor<IManagedImage> 
{
	
	public IManagedImage getImageDescriptor(CompletionProposalKind kind) {
		if(kind == null) {
			return null;
		}
		IManagedImage imageDescriptor = kind.switchOnKind(this);
		if(imageDescriptor == null) {
			return getDefaultImage();
		}
		return imageDescriptor;
	}
	
	public static IManagedImage getDefaultImage() {
		return NullManagedImage.INSTANCE;
	}
	
	@Override
	public IManagedImage visitUnknown() {
		return LangElementImages.UKKNOWN;
	}
	
	@Override
	public IManagedImage visitKeyword() {
		return NullManagedImage.INSTANCE;
	}
	
	@Override
	public IManagedImage visitError() {
		return LangElementImages.ERROR_ELEMENT;
	}
	
	@Override
	public IManagedImage visitAlias() {
		return LangElementImages.ALIAS_ELEMENT;
	}
	
	@Override
	public IManagedImage visitModule() {
		return LangElementImages.MODULE;
	}
	
	@Override
	public IManagedImage visitVariable() {
		return LangElementImages.VARIABLE;
	}
	
	@Override
	public IManagedImage visitFunction() {
		return LangElementImages.FUNCTION;
	}
	
	@Override
	public IManagedImage visitConstructor() {
		return LangElementImages.CONSTRUCTOR;
	}
	
	@Override
	public IManagedImage visitClass() {
		return LangElementImages.T_CLASS;
	}
	@Override
	public IManagedImage visitInterface() {
		return LangElementImages.T_INTERFACE;
	}
	@Override
	public IManagedImage visitStruct() {
		return LangElementImages.T_STRUCT;
	}
	@Override
	public IManagedImage visitEnum() {
		return LangElementImages.T_ENUM;
	}
	
	@Override
	public IManagedImage visitNative() {
		return LangElementImages.T_NATIVE;
	}
	
}

File: plugin_ide.ui/src/com/googlecode/goclipse/ui/GoPluginImages.java
/*******************************************************************************
 * Copyright (c) 2014, 2014 Bruno Medeiros and other Contributors.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package com.googlecode.goclipse.ui;

import melnorme.lang.ide.ui.LangElementImages;
import melnorme.lang.ide.ui.LangImages;
import melnorme.lang.ide.ui.utils.PluginImagesHelper.ImageHandle;

import org.eclipse.jface.resource.ImageDescriptor;

public class GoPluginImages extends LangImages {
	
	public static final ImageHandle NAVIGATOR_GOROOT_ENTRY = createManaged("", "navigator/goroot_entry.png");
	public static final ImageHandle NAVIGATOR_GOPATH_ENTRY = createManaged("", "navigator/gopath_entry.gif");
	
	public static final ImageHandle NAVIGATOR_SRC_FOLDER = createManaged("", "navigator/src-folder.png");
	public static final ImageHandle NAVIGATOR_PKG_FOLDER = createManaged("", "navigator/pkg_folder.gif");
	public static final ImageHandle NAVIGATOR_BIN_FOLDER = createManaged("", "navigator/bin_folder.gif");
	public static final ImageHandle NAVIGATOR_GO_PACKAGE_FILE = createManaged("", "navigator/package_file.png");
	public static final ImageHandle NAVIGATOR_SOURCE_PACKAGE_FOLDER = createManaged("", "navigator/source_package.gif");
	
	
	
	public static final ImageHandle SOURCE_OTHER = LangElementImages.UKKNOWN;
	public static final ImageHandle SOURCE_FUNCTION = createManaged("", "function_co.png");
	public static final ImageHandle SOURCE_PRIVATE_FUNCTION = createManaged("", "public_co.gif"); // Is this icon correct?
	public static final ImageHandle SOURCE_METHOD = createManaged("", "public_co.gif");
	
	public static final ImageHandle SOURCE_INTERFACE = LangElementImages.T_INTERFACE;
	public static final ImageHandle SOURCE_STRUCT = LangElementImages.T_STRUCT;
	public static final ImageHandle SOURCE_IMPORT = createManaged("", "imp_obj.gif");
	public static final ImageHandle SOURCE_PRIVATE_VAR = createManaged("", "field_private_obj.gif");
	public static final ImageHandle SOURCE_PUBLIC_VAR = createManaged("", "field_public_obj.gif");
	
	
	public static final ImageDescriptor OVERLAYS_WARNING = createUnmanaged("", "warning_co.gif");
	public static final ImageDescriptor OVERLAYS_ERROR = createUnmanaged("", "error_co.gif");
	
	
	public static final ImageHandle WIZARD_SOURCE_ICON = createManaged("", "sourceicon.png");
	public static final ImageHandle WIZARD_ICON = createManaged("", "go-icon-wizard.png");
	
}

File: plugin_ide.ui/src/com/googlecode/goclipse/ui/actions/GoOracleOpenDefinitionOperation.java
/*******************************************************************************
 * Copyright (c) 2014, 2014 Bruno Medeiros and other Contributors.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *     Bruno Medeiros - initial API and implementation
 *******************************************************************************/
package com.googlecode.goclipse.ui.actions;

import melnorme.lang.ide.core.LangCore;
import melnorme.lang.ide.ui.editor.actions.AbstractOpenElementOperation;
import melnorme.lang.ide.ui.editor.EditorUtils.OpenNewEditorMode;
import melnorme.lang.ide.ui.tools.console.DaemonToolMessageConsole;
import melnorme.lang.tooling.ast.SourceRange;
import melnorme.lang.tooling.ops.FindDefinitionResult;
import melnorme.utilbox.concurrency.OperationCancellation;
import melnorme.utilbox.core.CommonException;
import melnorme.utilbox.process.ExternalProcessHelper.ExternalProcessResult;

import org.eclipse.core.runtime.CoreException;
import org.eclipse.core.runtime.IProgressMonitor;
import org.eclipse.core.runtime.NullProgressMonitor;
import org.eclipse.ui.texteditor.ITextEditor;

import com.googlecode.goclipse.core.GoProjectEnvironment;
import com.googlecode.goclipse.core.GoToolPreferences;
import com.googlecode.goclipse.core.operations.GoToolManager;
import com.googlecode.goclipse.tooling.env.GoEnvironment;
import com.googlecode.goclipse.tooling.oracle.GoOracleFindDefinitionOperation;

public class GoOracleOpenDefinitionOperation extends AbstractOpenElementOperation {
	
	public static final String OPEN_DEFINITION_OpName = "Open definition (go oracle)";
	
	public GoOracleOpenDefinitionOperation(ITextEditor editor, SourceRange range, OpenNewEditorMode openEditorMode) {
		super(OPEN_DEFINITION_OpName, editor, range, openEditorMode);
	}
	
	@Override
	protected void prepareOperation() throws CoreException {
		super.prepareOperation();
		
		editor.doSave(new NullProgressMonitor());
	}
	
	@Override
	protected FindDefinitionResult performLongRunningComputation_doAndGetResult(IProgressMonitor monitor) 
			throws CoreException, OperationCancellation {
		String goOraclePath = GoToolPreferences.GO_ORACLE_Path.get();
		
		GoEnvironment goEnv = GoProjectEnvironment.getGoEnvironment(project);
		
		try {
			GoOracleFindDefinitionOperation op = new GoOracleFindDefinitionOperation(goOraclePath);
			ProcessBuilder pb = op.createProcessBuilder(goEnv, inputLoc, range.getOffset());
			
			ExternalProcessResult result = GoToolManager.getDefault().runEngineTool(pb, null, monitor);
			if(result.exitValue != 0) {
				statusErrorMessage = "Go oracle did not complete successfully.";
				return null;
			}
			
			return op.parseToolResult(result);
		} catch (CommonException se) {
			throw LangCore.createCoreException(se.getMessage(), se.getCause());
		}
	}
	
	@Override
	protected void handleStatusErrorMessage() {
		DaemonToolMessageConsole engineToolsConsole = DaemonToolMessageConsole.getConsole();
		engineToolsConsole.activate();
		
		super.handleStatusErrorMessage();
	}
	
}

File: plugin_tooling/src-lang/melnorme/lang/tooling/ast/SourceRange.java
package melnorme.lang.tooling.ast;

import static melnorme.utilbox.core.Assert.AssertNamespace.assertTrue;
import static melnorme.utilbox.core.CoreUtil.downCast;
import melnorme.utilbox.misc.NumberUtil;


public final class SourceRange implements Comparable<SourceRange> {
	
	private final int offset;
	private final int length;
	
	public SourceRange(int offset, int length) {
		assertTrue(offset >= 0);
		assertTrue(length >= 0);
		this.offset = offset;
		this.length = length;
	}
	
	public static SourceRange srStartToEnd(int startPos, int endPos) {
		assertTrue(startPos >= 0 && endPos >= startPos);
		return new SourceRange(startPos, endPos - startPos);
	}
	
	public final int getOffset() {
		return offset;
	}
	
	public final int getLength() {
		return length;
	}
	
	public final int getStartPos() {
		return getOffset();
	}
	
	public final int getEndPos() {
		return getOffset() + getLength();
	}
	
	@Override
	public final String toString() {
		return "[" + offset + "+" + length + "]";
	}
	
	@Override
	public final boolean equals(Object obj) {
		if(!(obj instanceof SourceRange))
			return false;
		
		SourceRange other = downCast(obj);
		return this.offset == other.offset && this.length == other.length;
	}
	
	@Override
	public int compareTo(SourceRange other) {
		if(offset == other.offset) {
			return length - other.length;
		}
		return offset - other.offset;
	}
	
	/** @return a substring of given source using the range of the receiver. */
	public String getRangeSubString(String source) {
		return source.substring(getStartPos(), getEndPos());
	}
	
	public boolean inclusiveContains(int otherOffset) {
		return NumberUtil.isInRange(getStartPos(), otherOffset, getEndPos());
	}
	
	public boolean inclusiveContains(SourceRange other) {
		return inclusiveContains(other.getStartPos()) && inclusiveContains(other.getEndPos());
	}
	
}