Refactoring Types: ['Extract Method']
m/intellij/codeInspection/dataFlow/DataFlowInspectionBase.java
/*
 * Copyright 2000-2012 JetBrains s.r.o.
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

/*
 * Created by IntelliJ IDEA.
 * User: max
 * Date: Dec 24, 2001
 * Time: 2:46:32 PM
 * To change template for new class use
 * Code Style | Class Templates options (Tools | IDE Options).
 */
package com.intellij.codeInspection.dataFlow;

import com.intellij.codeInsight.AnnotationUtil;
import com.intellij.codeInsight.FileModificationService;
import com.intellij.codeInsight.NullableNotNullManager;
import com.intellij.codeInsight.daemon.GroupNames;
import com.intellij.codeInsight.daemon.impl.quickfix.SimplifyBooleanExpressionFix;
import com.intellij.codeInsight.intention.impl.AddNullableAnnotationFix;
import com.intellij.codeInspection.*;
import com.intellij.codeInspection.dataFlow.instructions.*;
import com.intellij.codeInspection.dataFlow.value.DfaConstValue;
import com.intellij.codeInspection.dataFlow.value.DfaValue;
import com.intellij.codeInspection.nullable.NullableStuffInspectionBase;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.Condition;
import com.intellij.openapi.util.Pair;
import com.intellij.openapi.util.WriteExternalException;
import com.intellij.openapi.util.text.StringUtil;
import com.intellij.pom.java.LanguageLevel;
import com.intellij.psi.*;
import com.intellij.psi.util.PsiTreeUtil;
import com.intellij.psi.util.PsiUtil;
import com.intellij.psi.util.TypeConversionUtil;
import com.intellij.refactoring.extractMethod.ExtractMethodUtil;
import com.intellij.util.ArrayUtil;
import com.intellij.util.ArrayUtilRt;
import com.intellij.util.IncorrectOperationException;
import com.intellij.util.SmartList;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.MultiMap;
import org.jdom.Element;
import org.jetbrains.annotations.NonNls;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.util.*;

public class DataFlowInspectionBase extends BaseJavaBatchLocalInspectionTool {
  private static final Logger LOG = Logger.getInstance("#com.intellij.codeInspection.dataFlow.DataFlowInspection");
  @NonNls private static final String SHORT_NAME = "ConstantConditions";
  public boolean SUGGEST_NULLABLE_ANNOTATIONS = false;
  public boolean DONT_REPORT_TRUE_ASSERT_STATEMENTS = false;
  public boolean TREAT_UNKNOWN_MEMBERS_AS_NULLABLE = false;
  public boolean IGNORE_ASSERT_STATEMENTS = false;
  public boolean REPORT_CONSTANT_REFERENCE_VALUES = true;

  @Override
  public JComponent createOptionsPanel() {
    throw new RuntimeException("no UI in headless mode");
  }

  @Override
  public void writeSettings(@NotNull Element node) throws WriteExternalException {
    node.addContent(new Element("option").setAttribute("name", "SUGGEST_NULLABLE_ANNOTATIONS").setAttribute("value", String.valueOf(SUGGEST_NULLABLE_ANNOTATIONS)));
    node.addContent(new Element("option").setAttribute("name", "DONT_REPORT_TRUE_ASSERT_STATEMENTS").setAttribute("value", String.valueOf(DONT_REPORT_TRUE_ASSERT_STATEMENTS)));
    if (IGNORE_ASSERT_STATEMENTS) {
      node.addContent(new Element("option").setAttribute("name", "IGNORE_ASSERT_STATEMENTS").setAttribute("value", "true"));
    }
    if (!REPORT_CONSTANT_REFERENCE_VALUES) {
      node.addContent(new Element("option").setAttribute("name", "REPORT_CONSTANT_REFERENCE_VALUES").setAttribute("value", "false"));
    }
    if (TREAT_UNKNOWN_MEMBERS_AS_NULLABLE) {
      node.addContent(new Element("option").setAttribute("name", "TREAT_UNKNOWN_MEMBERS_AS_NULLABLE").setAttribute("value", "true"));
    }
  }

  @Override
  @NotNull
  public PsiElementVisitor buildVisitor(@NotNull final ProblemsHolder holder, final boolean isOnTheFly) {
    return new JavaElementVisitor() {
      @Override
      public void visitField(PsiField field) {
        analyzeCodeBlock(field, holder, isOnTheFly);
      }

      @Override
      public void visitMethod(PsiMethod method) {
        analyzeCodeBlock(method.getBody(), holder, isOnTheFly);
      }

      @Override
      public void visitClassInitializer(PsiClassInitializer initializer) {
        analyzeCodeBlock(initializer.getBody(), holder, isOnTheFly);
      }

      @Override
      public void visitMethodReferenceExpression(PsiMethodReferenceExpression expression) {
        super.visitMethodReferenceExpression(expression);
        final PsiElement resolve = expression.resolve();
        if (resolve instanceof PsiMethod) {
          final PsiType methodReturnType = ((PsiMethod)resolve).getReturnType();
          if (TypeConversionUtil.isPrimitiveWrapper(methodReturnType) && NullableNotNullManager.isNullable((PsiMethod)resolve)) {
            final PsiType returnType = LambdaUtil.getFunctionalInterfaceReturnType(expression);
            if (TypeConversionUtil.isPrimitiveAndNotNull(returnType)) {
              holder.registerProblem(expression, InspectionsBundle.message("dataflow.message.unboxing.method.reference"));
            }
          }
        }
      }

      @Override
      public void visitIfStatement(PsiIfStatement statement) {
        PsiExpression condition = statement.getCondition();
        if (BranchingInstruction.isBoolConst(condition)) {
          LocalQuickFix fix = createSimplifyBooleanExpressionFix(condition, condition.textMatches(PsiKeyword.TRUE));
          holder.registerProblem(condition, "Condition is always " + condition.getText(), fix);
        }
      }

    };
  }

  private void analyzeCodeBlock(@Nullable final PsiElement scope, ProblemsHolder holder, final boolean onTheFly) {
    if (scope == null) return;

    PsiClass containingClass = PsiTreeUtil.getParentOfType(scope, PsiClass.class);
    if (containingClass != null && PsiUtil.isLocalOrAnonymousClass(containingClass) && !(containingClass instanceof PsiEnumConstantInitializer)) return;

    final StandardDataFlowRunner dfaRunner = new StandardDataFlowRunner(TREAT_UNKNOWN_MEMBERS_AS_NULLABLE, !isInsideConstructorOrInitializer(
      scope)) {
      @Override
      protected boolean shouldCheckTimeLimit() {
        if (!onTheFly) return false;
        return super.shouldCheckTimeLimit();
      }
    };
    analyzeDfaWithNestedClosures(scope, holder, dfaRunner, Arrays.asList(dfaRunner.createMemoryState()), onTheFly);
  }

  private static boolean isInsideConstructorOrInitializer(PsiElement element) {
    while (element != null) {
      element = PsiTreeUtil.getParentOfType(element, PsiMethod.class, PsiClassInitializer.class);
      if (element instanceof PsiClassInitializer) return true;
      if (element instanceof PsiMethod && ((PsiMethod)element).isConstructor()) return true;
    }
    return false;
  }

  private void analyzeDfaWithNestedClosures(PsiElement scope,
                                            ProblemsHolder holder,
                                            StandardDataFlowRunner dfaRunner,
                                            Collection<DfaMemoryState> initialStates, final boolean onTheFly) {
    final DataFlowInstructionVisitor visitor = new DataFlowInstructionVisitor(dfaRunner);
    final RunnerResult rc = dfaRunner.analyzeMethod(scope, visitor, IGNORE_ASSERT_STATEMENTS, initialStates);
    if (rc == RunnerResult.OK) {
      createDescription(dfaRunner, holder, visitor, onTheFly, scope);

      MultiMap<PsiElement,DfaMemoryState> nestedClosures = dfaRunner.getNestedClosures();
      for (PsiElement closure : nestedClosures.keySet()) {
        analyzeDfaWithNestedClosures(closure, holder, dfaRunner, nestedClosures.get(closure), onTheFly);
      }
    }
    else if (rc == RunnerResult.TOO_COMPLEX) {
      if (scope.getParent() instanceof PsiMethod) {
        PsiMethod method = (PsiMethod)scope.getParent();
        final PsiIdentifier name = method.getNameIdentifier();
        if (name != null) { // Might be null for synthetic methods like JSP page.
          holder.registerProblem(name, InspectionsBundle.message("dataflow.too.complex"), ProblemHighlightType.WEAK_WARNING);
        }
      }
    }
  }

  @Nullable
  private LocalQuickFix[] createNPEFixes(PsiExpression qualifier, PsiExpression expression, boolean onTheFly) {
    if (qualifier == null || expression == null) return null;
    if (qualifier instanceof PsiMethodCallExpression) return null;

    try {
      final List<LocalQuickFix> fixes = new SmartList<LocalQuickFix>();

      if (!(qualifier instanceof PsiLiteralExpression && ((PsiLiteralExpression)qualifier).getValue() == null))  {
        if (PsiUtil.getLanguageLevel(qualifier).isAtLeast(LanguageLevel.JDK_1_4)) {
          final Project project = qualifier.getProject();
          final PsiElementFactory elementFactory = JavaPsiFacade.getInstance(project).getElementFactory();
          final PsiBinaryExpression binary = (PsiBinaryExpression)elementFactory.createExpressionFromText("a != null", null);
          binary.getLOperand().replace(qualifier);
          ContainerUtil.addIfNotNull(fixes, createAssertFix(binary, expression));
        }

        addSurroundWithIfFix(qualifier, fixes, onTheFly);

        if (ReplaceWithTernaryOperatorFix.isAvailable(qualifier, expression)) {
          fixes.add(new ReplaceWithTernaryOperatorFix(qualifier));
        }
      }

      ContainerUtil.addIfNotNull(fixes, DfaOptionalSupport.registerReplaceOptionalOfWithOfNullableFix(qualifier));
      return fixes.isEmpty() ? null : fixes.toArray(new LocalQuickFix[fixes.size()]);
    }
    catch (IncorrectOperationException e) {
      LOG.error(e);
      return null;
    }
  }

  protected LocalQuickFix createAssertFix(PsiBinaryExpression binary, PsiExpression expression) {
    return null;
  }

  protected void addSurroundWithIfFix(PsiExpression qualifier, List<LocalQuickFix> fixes, boolean onTheFly) {
  }

  private void createDescription(StandardDataFlowRunner runner, ProblemsHolder holder, DataFlowInstructionVisitor visitor, final boolean onTheFly, PsiElement scope) {
    Pair<Set<Instruction>, Set<Instruction>> constConditions = runner.getConstConditionalExpressions();
    Set<Instruction> trueSet = constConditions.getFirst();
    Set<Instruction> falseSet = constConditions.getSecond();

    ArrayList<Instruction> allProblems = new ArrayList<Instruction>();
    allProblems.addAll(trueSet);
    allProblems.addAll(falseSet);
    allProblems.addAll(runner.getCCEInstructions());
    allProblems.addAll(StandardDataFlowRunner.getRedundantInstanceofs(runner, visitor));

    HashSet<PsiElement> reportedAnchors = new HashSet<PsiElement>();
    for (PsiElement element : visitor.getProblems(NullabilityProblem.callNPE)) {
      if (reportedAnchors.add(element)) {
        reportCallMayProduceNpe(holder, (PsiMethodCallExpression)element, holder.isOnTheFly());
      }
    }
    for (PsiElement element : visitor.getProblems(NullabilityProblem.fieldAccessNPE)) {
      if (reportedAnchors.add(element)) {
        PsiElement parent = element.getParent();
        PsiElement fieldAccess = parent instanceof PsiArrayAccessExpression || parent instanceof PsiReferenceExpression ? parent : element;
        reportFieldAccessMayProduceNpe(holder, element, (PsiExpression)fieldAccess);
      }
    }

    for (Instruction instruction : allProblems) {
      if (instruction instanceof TypeCastInstruction &&
               reportedAnchors.add(((TypeCastInstruction)instruction).getCastExpression().getCastType())) {
        reportCastMayFail(holder, (TypeCastInstruction)instruction);
      }
      else if (instruction instanceof BranchingInstruction) {
        handleBranchingInstruction(holder, visitor, trueSet, falseSet, reportedAnchors, (BranchingInstruction)instruction, onTheFly);
      }
    }

    reportNullableArguments(visitor, holder, reportedAnchors);
    reportNullableAssignments(visitor, holder, reportedAnchors);
    reportUnboxedNullables(visitor, holder, reportedAnchors);
    reportNullableReturns(visitor, holder, reportedAnchors, scope);
    if (SUGGEST_NULLABLE_ANNOTATIONS) {
      reportNullableArgumentsPassedToNonAnnotated(visitor, holder, reportedAnchors);
    }

    reportOptionalOfNullableImprovements(holder, reportedAnchors, runner.getInstructions());


    if (REPORT_CONSTANT_REFERENCE_VALUES) {
      reportConstantReferenceValues(holder, visitor, reportedAnchors);
    }
  }

  private static void reportOptionalOfNullableImprovements(ProblemsHolder holder, Set<PsiElement> reportedAnchors, Instruction[] instructions) {
    for (Instruction instruction : instructions) {
      if (instruction instanceof MethodCallInstruction) {
        final PsiExpression[] args = ((MethodCallInstruction)instruction).getArgs();
        if (args.length != 1) continue;

        final PsiExpression expr = args[0];

        if (((MethodCallInstruction)instruction).isOptionalAlwaysNullProblem()) {
          if (!reportedAnchors.add(expr)) continue;
          holder.registerProblem(expr, "Passing <code>null</code> argument to <code>Optional</code>",
                                 DfaOptionalSupport.createReplaceOptionalOfNullableWithEmptyFix(expr));
        }
        else if (((MethodCallInstruction)instruction).isOptionalAlwaysNotNullProblem()) {
          if (!reportedAnchors.add(expr)) continue;
          holder.registerProblem(expr, "Passing a non-null argument to <code>Optional</code>",
                                 DfaOptionalSupport.createReplaceOptionalOfNullableWithOfFix());
        }
        
      }
    }
  }

  private static void reportConstantReferenceValues(ProblemsHolder holder, StandardInstructionVisitor visitor, Set<PsiElement> reportedAnchors) {
    for (Pair<PsiReferenceExpression, DfaConstValue> pair : visitor.getConstantReferenceValues()) {
      PsiReferenceExpression ref = pair.first;
      if (ref.getParent() instanceof PsiReferenceExpression || !reportedAnchors.add(ref)) {
        continue;
      }

      final Object value = pair.second.getValue();
      PsiVariable constant = pair.second.getConstant();
      final String presentableName = constant != null ? constant.getName() : String.valueOf(value);
      final String exprText = String.valueOf(value);
      if (presentableName == null || exprText == null) {
        continue;
      }

      holder.registerProblem(ref, "Value <code>#ref</code> #loc is always '" + presentableName + "'", new LocalQuickFix() {
        @NotNull
        @Override
        public String getName() {
          return "Replace with '" + presentableName + "'";
        }

        @NotNull
        @Override
        public String getFamilyName() {
          return "Replace with constant value";
        }

        @Override
        public void applyFix(@NotNull Project project, @NotNull ProblemDescriptor descriptor) {
          if (!FileModificationService.getInstance().preparePsiElementsForWrite(descriptor.getPsiElement())) {
            return;
          }

          PsiElement problemElement = descriptor.getPsiElement();
          if (problemElement == null) return;

          PsiMethodCallExpression call = problemElement.getParent() instanceof PsiExpressionList &&
                                         problemElement.getParent().getParent() instanceof PsiMethodCallExpression ?
                                         (PsiMethodCallExpression)problemElement.getParent().getParent() :
                                         null;
          PsiMethod targetMethod = call == null ? null : call.resolveMethod();

          JavaPsiFacade facade = JavaPsiFacade.getInstance(project);
          problemElement.replace(facade.getElementFactory().createExpressionFromText(exprText, null));

          if (targetMethod != null) {
            ExtractMethodUtil.addCastsToEnsureResolveTarget(targetMethod, call);
          }
        }
      });
    }
  }

  private void reportNullableArgumentsPassedToNonAnnotated(DataFlowInstructionVisitor visitor, ProblemsHolder holder, Set<PsiElement> reportedAnchors) {
    for (PsiElement expr : visitor.getProblems(NullabilityProblem.passingNullableArgumentToNonAnnotatedParameter)) {
      if (reportedAnchors.contains(expr)) continue;

      final String text = isNullLiteralExpression(expr)
                          ? "Passing <code>null</code> argument to non annotated parameter"
                          : "Argument <code>#ref</code> #loc might be null but passed to non annotated parameter";
      LocalQuickFix[] fixes = createNPEFixes((PsiExpression)expr, (PsiExpression)expr, holder.isOnTheFly());
      final PsiElement parent = expr.getParent();
      if (parent instanceof PsiExpressionList) {
        final int idx = ArrayUtilRt.find(((PsiExpressionList)parent).getExpressions(), expr);
        if (idx > -1) {
          final PsiElement gParent = parent.getParent();
          if (gParent instanceof PsiCallExpression) {
            final PsiMethod psiMethod = ((PsiCallExpression)gParent).resolveMethod();
            if (psiMethod != null && psiMethod.getManager().isInProject(psiMethod) && AnnotationUtil.isAnnotatingApplicable(psiMethod)) {
              final PsiParameter[] parameters = psiMethod.getParameterList().getParameters();
              if (idx < parameters.length) {
                final AddNullableAnnotationFix addNullableAnnotationFix = new AddNullableAnnotationFix(parameters[idx]);
                fixes = fixes == null ? new LocalQuickFix[]{addNullableAnnotationFix} : ArrayUtil.append(fixes, addNullableAnnotationFix);
                holder.registerProblem(expr, text, fixes);
                reportedAnchors.add(expr);
              }
            }
          }
        }
      }

    }
  }

  private void reportCallMayProduceNpe(ProblemsHolder holder, PsiMethodCallExpression callExpression, boolean onTheFly) {
    LocalQuickFix[] fix = createNPEFixes(callExpression.getMethodExpression().getQualifierExpression(), callExpression, onTheFly);

    holder.registerProblem(callExpression,
                           InspectionsBundle.message("dataflow.message.npe.method.invocation"),
                           fix);
  }

  private void reportFieldAccessMayProduceNpe(ProblemsHolder holder, PsiElement elementToAssert, PsiExpression expression) {
    if (expression instanceof PsiArrayAccessExpression) {
      LocalQuickFix[] fix = createNPEFixes((PsiExpression)elementToAssert, expression, holder.isOnTheFly());
      holder.registerProblem(expression,
                             InspectionsBundle.message("dataflow.message.npe.array.access"),
                             fix);
    }
    else {
      LocalQuickFix[] fix = createNPEFixes((PsiExpression)elementToAssert, expression, holder.isOnTheFly());
      assert elementToAssert != null;
      holder.registerProblem(elementToAssert,
                             InspectionsBundle.message("dataflow.message.npe.field.access"),
                             fix);
    }
  }

  private static void reportCastMayFail(ProblemsHolder holder, TypeCastInstruction instruction) {
    PsiTypeCastExpression typeCast = instruction.getCastExpression();
    PsiExpression operand = typeCast.getOperand();
    PsiTypeElement castType = typeCast.getCastType();
    assert castType != null;
    assert operand != null;
    holder.registerProblem(castType, InspectionsBundle.message("dataflow.message.cce", operand.getText()));
  }

  private void handleBranchingInstruction(ProblemsHolder holder,
                                          StandardInstructionVisitor visitor,
                                          Set<Instruction> trueSet,
                                          Set<Instruction> falseSet, HashSet<PsiElement> reportedAnchors, BranchingInstruction instruction, final boolean onTheFly) {
    PsiElement psiAnchor = instruction.getPsiAnchor();
    boolean underBinary = isAtRHSOfBooleanAnd(psiAnchor);
    if (instruction instanceof InstanceofInstruction && visitor.isInstanceofRedundant((InstanceofInstruction)instruction)) {
      if (visitor.canBeNull((BinopInstruction)instruction)) {
        holder.registerProblem(psiAnchor,
                               InspectionsBundle.message("dataflow.message.redundant.instanceof"),
                               new RedundantInstanceofFix());
      }
      else {
        final LocalQuickFix localQuickFix = createSimplifyBooleanExpressionFix(psiAnchor, true);
        holder.registerProblem(psiAnchor,
                               InspectionsBundle.message(underBinary ? "dataflow.message.constant.condition.when.reached" : "dataflow.message.constant.condition", Boolean.toString(true)),
                               localQuickFix == null ? null : new LocalQuickFix[]{localQuickFix});
      }
    }
    else if (psiAnchor instanceof PsiSwitchLabelStatement) {
      if (falseSet.contains(instruction)) {
        holder.registerProblem(psiAnchor,
                               InspectionsBundle.message("dataflow.message.unreachable.switch.label"));
      }
    }
    else if (psiAnchor != null && !reportedAnchors.contains(psiAnchor) && !isFlagCheck(psiAnchor)) {
      boolean evaluatesToTrue = trueSet.contains(instruction);
      final PsiElement parent = psiAnchor.getParent();
      if (parent instanceof PsiAssignmentExpression && ((PsiAssignmentExpression)parent).getLExpression() == psiAnchor) {
        holder.registerProblem(
          psiAnchor,
          InspectionsBundle.message("dataflow.message.pointless.assignment.expression", Boolean.toString(evaluatesToTrue)),
          createConditionalAssignmentFixes(evaluatesToTrue, (PsiAssignmentExpression)parent, onTheFly)
        );
      }
      else if (!skipReportingConstantCondition(visitor, psiAnchor, evaluatesToTrue)) {
        final LocalQuickFix fix = createSimplifyBooleanExpressionFix(psiAnchor, evaluatesToTrue);
        String message = InspectionsBundle.message(underBinary ?
                                                   "dataflow.message.constant.condition.when.reached" :
                                                   "dataflow.message.constant.condition", Boolean.toString(evaluatesToTrue));
        holder.registerProblem(psiAnchor, message, fix == null ? null : new LocalQuickFix[]{fix});
      }
      reportedAnchors.add(psiAnchor);
    }
  }

  protected LocalQuickFix[] createConditionalAssignmentFixes(boolean evaluatesToTrue, PsiAssignmentExpression parent, final boolean onTheFly) {
    return LocalQuickFix.EMPTY_ARRAY;
  }

  private boolean skipReportingConstantCondition(StandardInstructionVisitor visitor, PsiElement psiAnchor, boolean evaluatesToTrue) {
    return DONT_REPORT_TRUE_ASSERT_STATEMENTS && isAssertionEffectively(psiAnchor, evaluatesToTrue) ||
           visitor.silenceConstantCondition(psiAnchor);
  }

  private void reportNullableArguments(DataFlowInstructionVisitor visitor, ProblemsHolder holder, Set<PsiElement> reportedAnchors) {
    for (PsiElement expr : visitor.getProblems(NullabilityProblem.passingNullableToNotNullParameter)) {
      if (!reportedAnchors.add(expr)) continue;

      final String text = isNullLiteralExpression(expr)
                          ? InspectionsBundle.message("dataflow.message.passing.null.argument")
                          : InspectionsBundle.message("dataflow.message.passing.nullable.argument");
      LocalQuickFix[] fixes = createNPEFixes((PsiExpression)expr, (PsiExpression)expr, holder.isOnTheFly());
      holder.registerProblem(expr, text, fixes);
    }
  }

  private static void reportNullableAssignments(DataFlowInstructionVisitor visitor, ProblemsHolder holder, Set<PsiElement> reportedAnchors) {
    for (PsiElement expr : visitor.getProblems(NullabilityProblem.assigningToNotNull)) {
      if (!reportedAnchors.add(expr)) continue;

      final String text = isNullLiteralExpression(expr)
                          ? InspectionsBundle.message("dataflow.message.assigning.null")
                          : InspectionsBundle.message("dataflow.message.assigning.nullable");
      holder.registerProblem(expr, text);
    }
  }

  private static void reportUnboxedNullables(DataFlowInstructionVisitor visitor, ProblemsHolder holder, Set<PsiElement> reportedAnchors) {
    for (PsiElement expr : visitor.getProblems(NullabilityProblem.unboxingNullable)) {
      if (!reportedAnchors.add(expr)) continue;
      holder.registerProblem(expr, InspectionsBundle.message("dataflow.message.unboxing"));
    }
  }

  @Nullable
  private static PsiMethod getScopeMethod(PsiElement block) {
    PsiElement parent = block.getParent();
    if (parent instanceof PsiMethod) return (PsiMethod)parent;
    if (parent instanceof PsiLambdaExpression) return LambdaUtil.getFunctionalInterfaceMethod(((PsiLambdaExpression)parent).getFunctionalInterfaceType());
    return null;
  }

  private void reportNullableReturns(DataFlowInstructionVisitor visitor,
                                     ProblemsHolder holder,
                                     Set<PsiElement> reportedAnchors,
                                     @NotNull PsiElement block) {
    final PsiMethod method = getScopeMethod(block);
    if (method == null || NullableStuffInspectionBase.isNullableNotInferred(method, true)) return;

    boolean notNullRequired = NullableNotNullManager.isNotNull(method);
    if (!notNullRequired && !SUGGEST_NULLABLE_ANNOTATIONS) return;

    PsiType returnType = method.getReturnType();
    // no warnings in void lambdas, where the expression is not returned anyway
    if (block instanceof PsiExpression && block.getParent() instanceof PsiLambdaExpression && returnType == PsiType.VOID) return;
    
    // no warnings for Void methods, where only null can be possibly returned
    if (returnType == null || returnType.equalsToText(CommonClassNames.JAVA_LANG_VOID)) return;

    for (PsiElement statement : visitor.getProblems(NullabilityProblem.nullableReturn)) {
      assert statement instanceof PsiExpression; 
      final PsiExpression expr = (PsiExpression)statement;
      if (!reportedAnchors.add(expr)) continue;

      if (notNullRequired) {
        final String text = isNullLiteralExpression(expr)
                            ? InspectionsBundle.message("dataflow.message.return.null.from.notnull")
                            : InspectionsBundle.message("dataflow.message.return.nullable.from.notnull");
        holder.registerProblem(expr, text);
      }
      else if (AnnotationUtil.isAnnotatingApplicable(statement)) {
        final NullableNotNullManager manager = NullableNotNullManager.getInstance(expr.getProject());
        final String defaultNullable = manager.getDefaultNullable();
        final String presentableNullable = StringUtil.getShortName(defaultNullable);
        final String text = isNullLiteralExpression(expr)
                            ? InspectionsBundle.message("dataflow.message.return.null.from.notnullable", presentableNullable)
                            : InspectionsBundle.message("dataflow.message.return.nullable.from.notnullable", presentableNullable);
        final LocalQuickFix[] fixes =
          PsiTreeUtil.getParentOfType(expr, PsiMethod.class, PsiLambdaExpression.class) instanceof PsiLambdaExpression
          ? LocalQuickFix.EMPTY_ARRAY
          : new LocalQuickFix[]{ new AnnotateMethodFix(defaultNullable, ArrayUtil.toStringArray(manager.getNotNulls())) {
            @Override
            public int shouldAnnotateBaseMethod(PsiMethod method, PsiMethod superMethod, Project project) {
              return 1;
            }
          }};
        holder.registerProblem(expr, text, fixes);
      }
    }
  }

  private static boolean isAssertionEffectively(PsiElement psiAnchor, boolean evaluatesToTrue) {
    PsiElement parent = psiAnchor.getParent();
    if (parent instanceof PsiAssertStatement) {
      return evaluatesToTrue;
    }
    if (parent instanceof PsiIfStatement && psiAnchor == ((PsiIfStatement)parent).getCondition()) {
      PsiStatement thenBranch = ((PsiIfStatement)parent).getThenBranch();
      if (thenBranch instanceof PsiThrowStatement) {
        return !evaluatesToTrue;
      }
      if (thenBranch instanceof PsiBlockStatement) {
        PsiStatement[] statements = ((PsiBlockStatement)thenBranch).getCodeBlock().getStatements();
        if (statements.length == 1 && statements[0] instanceof PsiThrowStatement) {
          return !evaluatesToTrue;
        }
      }
    }
    return false;
  }

  private static boolean isAtRHSOfBooleanAnd(PsiElement expr) {
    PsiElement cur = expr;

    while (cur != null && !(cur instanceof PsiMember)) {
      PsiElement parent = cur.getParent();

      if (parent instanceof PsiBinaryExpression && cur == ((PsiBinaryExpression)parent).getROperand()) {
        return true;
      }

      cur = parent;
    }

    return false;
  }

  private static boolean isFlagCheck(PsiElement element) {
    PsiStatement statement = PsiTreeUtil.getParentOfType(element, PsiStatement.class);
    if (!(statement instanceof PsiIfStatement)) return false;

    PsiExpression condition = ((PsiIfStatement)statement).getCondition();
    if (!PsiTreeUtil.isAncestor(condition, element, false)) return false;

    if (isCompileTimeFlagReference(condition)) return true;

    Collection<PsiReferenceExpression> refs = PsiTreeUtil.findChildrenOfType(condition, PsiReferenceExpression.class);
    return ContainerUtil.or(refs, new Condition<PsiReferenceExpression>() {
      @Override
      public boolean value(PsiReferenceExpression ref) {
        return isCompileTimeFlagReference(ref);
      }
    });
  }

  private static boolean isCompileTimeFlagReference(PsiElement element) {
    PsiElement resolved = element instanceof PsiReferenceExpression ? ((PsiReferenceExpression)element).resolve() : null;
    if (!(resolved instanceof PsiField)) return false;
    PsiField field = (PsiField)resolved;
    return field.hasModifierProperty(PsiModifier.FINAL) && field.hasModifierProperty(PsiModifier.STATIC) &&
           PsiType.BOOLEAN.equals(field.getType());
  }

  private static boolean isNullLiteralExpression(PsiElement expr) {
    if (expr instanceof PsiLiteralExpression) {
      final PsiLiteralExpression literalExpression = (PsiLiteralExpression)expr;
      return PsiType.NULL.equals(literalExpression.getType());
    }
    return false;
  }

  @Nullable
  private static LocalQuickFix createSimplifyBooleanExpressionFix(PsiElement element, final boolean value) {
    SimplifyBooleanExpressionFix fix = createIntention(element, value);
    if (fix == null) return null;
    final String text = fix.getText();
    return new LocalQuickFix() {
      @Override
      @NotNull
      public String getName() {
        return text;
      }

      @Override
      public void applyFix(@NotNull Project project, @NotNull ProblemDescriptor descriptor) {
        final PsiElement psiElement = descriptor.getPsiElement();
        if (psiElement == null) return;
        final SimplifyBooleanExpressionFix fix = createIntention(psiElement, value);
        if (fix == null) return;
        try {
          LOG.assertTrue(psiElement.isValid());
          fix.applyFix();
        }
        catch (IncorrectOperationException e) {
          LOG.error(e);
        }
      }

      @Override
      @NotNull
      public String getFamilyName() {
        return InspectionsBundle.message("inspection.data.flow.simplify.boolean.expression.quickfix");
      }
    };
  }

  @NotNull
  protected static LocalQuickFix createSimplifyToAssignmentFix() {
    return new LocalQuickFix() {
      @NotNull
      @Override
      public String getName() {
        return InspectionsBundle.message("inspection.data.flow.simplify.to.assignment.quickfix.name");
      }

      @NotNull
      @Override
      public String getFamilyName() {
        return InspectionsBundle.message("inspection.data.flow.simplify.boolean.expression.quickfix");
      }

      @Override
      public void applyFix(@NotNull Project project, @NotNull ProblemDescriptor descriptor) {
        final PsiElement psiElement = descriptor.getPsiElement();
        if (psiElement == null) return;

        final PsiAssignmentExpression assignmentExpression = PsiTreeUtil.getParentOfType(psiElement, PsiAssignmentExpression.class);
        if (assignmentExpression == null) {
          return;
        }

        final PsiElementFactory factory = JavaPsiFacade.getElementFactory(project);
        final String lExpressionText = assignmentExpression.getLExpression().getText();
        final PsiExpression rExpression = assignmentExpression.getRExpression();
        final String rExpressionText = rExpression != null ? rExpression.getText() : "";
        assignmentExpression.replace(factory.createExpressionFromText(lExpressionText + " = " + rExpressionText, psiElement));
      }
    };
  }

  private static SimplifyBooleanExpressionFix createIntention(PsiElement element, boolean value) {
    if (!(element instanceof PsiExpression)) return null;
    final PsiExpression expression = (PsiExpression)element;
    while (element.getParent() instanceof PsiExpression) {
      element = element.getParent();
    }
    final SimplifyBooleanExpressionFix fix = new SimplifyBooleanExpressionFix(expression, value);
    // simplify intention already active
    if (!fix.isAvailable() ||
        SimplifyBooleanExpressionFix.canBeSimplified((PsiExpression)element)) {
      return null;
    }
    return fix;
  }

  private static class RedundantInstanceofFix implements LocalQuickFix {
    @Override
    @NotNull
    public String getName() {
      return InspectionsBundle.message("inspection.data.flow.redundant.instanceof.quickfix");
    }

    @Override
    public void applyFix(@NotNull Project project, @NotNull ProblemDescriptor descriptor) {
      if (!FileModificationService.getInstance().preparePsiElementForWrite(descriptor.getPsiElement())) return;
      final PsiElement psiElement = descriptor.getPsiElement();
      if (psiElement instanceof PsiInstanceOfExpression) {
        try {
          final PsiExpression compareToNull = JavaPsiFacade.getInstance(psiElement.getProject()).getElementFactory().
            createExpressionFromText(((PsiInstanceOfExpression)psiElement).getOperand().getText() + " != null", psiElement.getParent());
          psiElement.replace(compareToNull);
        }
        catch (IncorrectOperationException e) {
          LOG.error(e);
        }
      }
    }

    @Override
    @NotNull
    public String getFamilyName() {
      return getName();
    }
  }


  @Override
  @NotNull
  public String getDisplayName() {
    return InspectionsBundle.message("inspection.data.flow.display.name");
  }

  @Override
  @NotNull
  public String getGroupDisplayName() {
    return GroupNames.BUGS_GROUP_NAME;
  }

  @Override
  @NotNull
  public String getShortName() {
    return SHORT_NAME;
  }

  private static class DataFlowInstructionVisitor extends StandardInstructionVisitor {
    private final StandardDataFlowRunner myRunner;
    private final MultiMap<NullabilityProblem, PsiElement> myProblems = new MultiMap<NullabilityProblem, PsiElement>();
    private final Map<Pair<NullabilityProblem, PsiElement>, StateInfo> myStateInfos = ContainerUtil.newHashMap();

    private DataFlowInstructionVisitor(StandardDataFlowRunner runner) {
      myRunner = runner;
    }

    @Override
    protected void onInstructionProducesCCE(TypeCastInstruction instruction) {
      myRunner.onInstructionProducesCCE(instruction);
    }
    
    Collection<PsiElement> getProblems(final NullabilityProblem kind) {
      return ContainerUtil.filter(myProblems.get(kind), new Condition<PsiElement>() {
        @Override
        public boolean value(PsiElement psiElement) {
          StateInfo info = myStateInfos.get(Pair.create(kind, psiElement));
          // non-ephemeral NPE should be reported
          // ephemeral NPE should also be reported if only ephemeral states have reached a particular problematic instruction
          //  (e.g. if it's inside "if (var == null)" check after contract method invocation
          return info.normalNpe || info.ephemeralNpe && !info.normalOk;
        }
      });
    }

    @Override
    protected boolean checkNotNullable(DfaMemoryState state, DfaValue value, NullabilityProblem problem, PsiElement anchor) {
      boolean ok = super.checkNotNullable(state, value, problem, anchor);
      if (!ok && anchor != null) {
        myProblems.putValue(problem, anchor);
      }
      Pair<NullabilityProblem, PsiElement> key = Pair.create(problem, anchor);
      StateInfo info = myStateInfos.get(key);
      if (info == null) {
        myStateInfos.put(key, info = new StateInfo());
      }
      if (state.isEphemeral() && !ok) {
        info.ephemeralNpe = true;
      } else if (!state.isEphemeral()) {
        if (ok) info.normalOk = true;
        else info.normalNpe = true;
      }
      return ok;
    }
    
    private static class StateInfo {
      boolean ephemeralNpe;
      boolean normalNpe;
      boolean normalOk;
    }
  }
}


File: java/java-analysis-impl/src/com/intellij/codeInspection/dataFlow/DfaPsiUtil.java
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
package com.intellij.codeInspection.dataFlow;

import com.intellij.codeInsight.NullableNotNullManager;
import com.intellij.codeInspection.dataFlow.instructions.Instruction;
import com.intellij.codeInspection.dataFlow.instructions.MethodCallInstruction;
import com.intellij.codeInspection.dataFlow.instructions.ReturnInstruction;
import com.intellij.codeInspection.dataFlow.value.DfaValueFactory;
import com.intellij.lang.java.JavaLanguage;
import com.intellij.openapi.util.Ref;
import com.intellij.psi.*;
import com.intellij.psi.search.LocalSearchScope;
import com.intellij.psi.search.searches.ReferencesSearch;
import com.intellij.psi.tree.IElementType;
import com.intellij.psi.util.*;
import com.intellij.util.NullableFunction;
import com.intellij.util.containers.ContainerUtil;
import com.intellij.util.containers.MultiMap;
import com.intellij.util.containers.Stack;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;

public class DfaPsiUtil {

  public static boolean isFinalField(PsiVariable var) {
    return var.hasModifierProperty(PsiModifier.FINAL) && !var.hasModifierProperty(PsiModifier.TRANSIENT) && var instanceof PsiField;
  }

  static PsiElement getEnclosingCodeBlock(final PsiVariable variable, final PsiElement context) {
    PsiElement codeBlock;
    if (variable instanceof PsiParameter) {
      codeBlock = ((PsiParameter)variable).getDeclarationScope();
      if (codeBlock instanceof PsiMethod) {
        codeBlock = ((PsiMethod)codeBlock).getBody();
      }
    }
    else if (variable instanceof PsiLocalVariable) {
      codeBlock = PsiTreeUtil.getParentOfType(variable, PsiCodeBlock.class);
    }
    else {
      codeBlock = getTopmostBlockInSameClass(context);
    }
    while (codeBlock != null) {
      PsiAnonymousClass anon = PsiTreeUtil.getParentOfType(codeBlock, PsiAnonymousClass.class);
      if (anon == null) break;
      codeBlock = PsiTreeUtil.getParentOfType(anon, PsiCodeBlock.class);
    }
    return codeBlock;
  }

  @NotNull
  public static Nullness getElementNullability(@Nullable PsiType resultType, @Nullable PsiModifierListOwner owner) {
    if (owner == null) {
      return Nullness.UNKNOWN;
    }

    if (resultType != null) {
      NullableNotNullManager nnn = NullableNotNullManager.getInstance(owner.getProject());
      for (PsiAnnotation annotation : resultType.getAnnotations()) {
        if (!annotation.isValid()) {
          PsiUtilCore.ensureValid(owner);
          PsiUtil.ensureValidType(resultType, owner + " of " + owner.getClass());
          PsiUtilCore.ensureValid(annotation); //should fail
        }
        String qualifiedName = annotation.getQualifiedName();
        if (nnn.getNullables().contains(qualifiedName)) {
          return Nullness.NULLABLE;
        }
        if (nnn.getNotNulls().contains(qualifiedName)) {
          return Nullness.NOT_NULL;
        }
      }
    }

    if (NullableNotNullManager.isNullable(owner)) {
      return Nullness.NULLABLE;
    }
    if (NullableNotNullManager.isNotNull(owner)) {
      return Nullness.NOT_NULL;
    }

    return Nullness.UNKNOWN;
  }

  public static boolean isInitializedNotNull(PsiField field) {
    PsiClass containingClass = field.getContainingClass();
    if (containingClass == null) return false;

    PsiMethod[] constructors = containingClass.getConstructors();
    if (constructors.length == 0) return false;
    
    for (PsiMethod method : constructors) {
      if (!getNotNullInitializedFields(method, containingClass).contains(field)) {
        return false;
      }
    }
    return true;
  }

  private static Set<PsiField> getNotNullInitializedFields(final PsiMethod constructor, final PsiClass containingClass) {
    if (!constructor.getLanguage().isKindOf(JavaLanguage.INSTANCE)) return Collections.emptySet();
    
    final PsiCodeBlock body = constructor.getBody();
    if (body == null) return Collections.emptySet();
    
    return CachedValuesManager.getCachedValue(constructor, new CachedValueProvider<Set<PsiField>>() {
      @Nullable
      @Override
      public Result<Set<PsiField>> compute() {
        final PsiCodeBlock body = constructor.getBody();
        final Map<PsiField, Boolean> map = ContainerUtil.newHashMap();
        final StandardDataFlowRunner dfaRunner = new StandardDataFlowRunner(false, false) {

          private boolean isCallExposingNonInitializedFields(Instruction instruction) {
            if (!(instruction instanceof MethodCallInstruction) ||
                ((MethodCallInstruction)instruction).getMethodType() != MethodCallInstruction.MethodType.REGULAR_METHOD_CALL) {
              return false;
            }

            PsiCallExpression call = ((MethodCallInstruction)instruction).getCallExpression();
            if (call == null) return false;

            if (call instanceof PsiMethodCallExpression &&
                DfaValueFactory.isEffectivelyUnqualified(((PsiMethodCallExpression)call).getMethodExpression())) {
              return true;
            }

            PsiExpressionList argumentList = call.getArgumentList();
            if (argumentList != null) {
              for (PsiExpression expression : argumentList.getExpressions()) {
                if (expression instanceof PsiThisExpression) return true;
              }
            }

            return false;
          }

          @Override
          protected DfaInstructionState[] acceptInstruction(InstructionVisitor visitor, DfaInstructionState instructionState) {
            Instruction instruction = instructionState.getInstruction();
            if (isCallExposingNonInitializedFields(instruction) ||
                instruction instanceof ReturnInstruction && !((ReturnInstruction)instruction).isViaException()) {
              for (PsiField field : containingClass.getFields()) {
                if (!instructionState.getMemoryState().isNotNull(getFactory().getVarFactory().createVariableValue(field, false))) {
                  map.put(field, false);
                } else if (!map.containsKey(field)) {
                  map.put(field, true);
                }
              }
              return DfaInstructionState.EMPTY_ARRAY;
            }
            return super.acceptInstruction(visitor, instructionState);
          }
        };
        final RunnerResult rc = dfaRunner.analyzeMethod(body, new StandardInstructionVisitor());
        Set<PsiField> notNullFields = ContainerUtil.newHashSet();
        if (rc == RunnerResult.OK) {
          for (PsiField field : map.keySet()) {
            if (map.get(field)) {
              notNullFields.add(field);
            }
          }
        }
        return Result.create(notNullFields, constructor, PsiModificationTracker.JAVA_STRUCTURE_MODIFICATION_COUNT);
      }
    });
  }

  public static List<PsiExpression> findAllConstructorInitializers(PsiField field) {
    final List<PsiExpression> result = ContainerUtil.createLockFreeCopyOnWriteList();
    ContainerUtil.addIfNotNull(result, field.getInitializer());

    final PsiClass containingClass = field.getContainingClass();
    if (containingClass != null && !(containingClass instanceof PsiCompiledElement)) {
      result.addAll(getAllConstructorFieldInitializers(containingClass).get(field));
    }
    return result;
  }

  private static MultiMap<PsiField, PsiExpression> getAllConstructorFieldInitializers(final PsiClass psiClass) {
    if (psiClass instanceof PsiCompiledElement) {
      //noinspection unchecked
      return MultiMap.EMPTY;
    }

    return CachedValuesManager.getCachedValue(psiClass, new CachedValueProvider<MultiMap<PsiField, PsiExpression>>() {
      @Nullable
      @Override
      public Result<MultiMap<PsiField, PsiExpression>> compute() {
        final Set<String> fieldNames = ContainerUtil.newHashSet();
        for (PsiField field : psiClass.getFields()) {
          ContainerUtil.addIfNotNull(fieldNames, field.getName());
        }

        final MultiMap<PsiField, PsiExpression> result = new MultiMap<PsiField, PsiExpression>();
        JavaRecursiveElementWalkingVisitor visitor = new JavaRecursiveElementWalkingVisitor() {
          @Override
          public void visitAssignmentExpression(PsiAssignmentExpression assignment) {
            super.visitAssignmentExpression(assignment);
            PsiExpression lExpression = assignment.getLExpression();
            PsiExpression rExpression = assignment.getRExpression();
            if (rExpression != null &&
                lExpression instanceof PsiReferenceExpression &&
                fieldNames.contains(((PsiReferenceExpression)lExpression).getReferenceName())) {
              PsiElement target = ((PsiReferenceExpression)lExpression).resolve();
              if (target instanceof PsiField && ((PsiField)target).getContainingClass() == psiClass) {
                result.putValue((PsiField)target, rExpression);
              }
            }
          }
        };

        for (PsiMethod constructor : psiClass.getConstructors()) {
          if (constructor.getLanguage().isKindOf(JavaLanguage.INSTANCE)) {
            constructor.accept(visitor);
          }
        }

        return Result.create(result, psiClass);
      }
    });
  }

  @Nullable
  public static PsiCodeBlock getTopmostBlockInSameClass(@NotNull PsiElement position) {
    PsiCodeBlock block = PsiTreeUtil.getParentOfType(position, PsiCodeBlock.class, false, PsiMember.class, PsiFile.class);
    if (block == null) {
      return null;
    }

    PsiCodeBlock lastBlock = block;
    while (true) {
      block = PsiTreeUtil.getParentOfType(block, PsiCodeBlock.class, true, PsiMember.class, PsiFile.class);
      if (block == null) {
        return lastBlock;
      }
      lastBlock = block;
    }
  }

  @NotNull
  public static Collection<PsiExpression> getVariableAssignmentsInFile(@NotNull PsiVariable psiVariable,
                                                                       final boolean literalsOnly,
                                                                       final PsiElement place) {
    final Ref<Boolean> modificationRef = Ref.create(Boolean.FALSE);
    final PsiCodeBlock codeBlock = place == null? null : getTopmostBlockInSameClass(place);
    final int placeOffset = codeBlock != null? place.getTextRange().getStartOffset() : 0;
    List<PsiExpression> list = ContainerUtil.mapNotNull(
      ReferencesSearch.search(psiVariable, new LocalSearchScope(new PsiElement[] {psiVariable.getContainingFile()}, null, true)).findAll(),
      new NullableFunction<PsiReference, PsiExpression>() {
        @Override
        public PsiExpression fun(final PsiReference psiReference) {
          if (modificationRef.get()) return null;
          final PsiElement parent = psiReference.getElement().getParent();
          if (parent instanceof PsiAssignmentExpression) {
            final PsiAssignmentExpression assignmentExpression = (PsiAssignmentExpression)parent;
            final IElementType operation = assignmentExpression.getOperationTokenType();
            if (assignmentExpression.getLExpression() == psiReference) {
              if (JavaTokenType.EQ.equals(operation)) {
                final PsiExpression rValue = assignmentExpression.getRExpression();
                if (!literalsOnly || allOperandsAreLiterals(rValue)) {
                  // if there's a codeBlock omit the values assigned later
                  if (codeBlock != null && PsiTreeUtil.isAncestor(codeBlock, parent, true)
                      && placeOffset < parent.getTextRange().getStartOffset()) {
                    return null;
                  }
                  return rValue;
                }
                else {
                  modificationRef.set(Boolean.TRUE);
                }
              }
              else if (JavaTokenType.PLUSEQ.equals(operation)) {
                modificationRef.set(Boolean.TRUE);
              }
            }
          }
          return null;
        }
      });
    if (modificationRef.get()) return Collections.emptyList();
    PsiExpression initializer = psiVariable.getInitializer();
    if (initializer != null && (!literalsOnly || allOperandsAreLiterals(initializer))) {
      list = ContainerUtil.concat(list, Collections.singletonList(initializer));
    }
    return list;
  }

  public static boolean allOperandsAreLiterals(@Nullable final PsiExpression expression) {
    if (expression == null) return false;
    if (expression instanceof PsiLiteralExpression) return true;
    if (expression instanceof PsiPolyadicExpression) {
      Stack<PsiExpression> stack = new Stack<PsiExpression>();
      stack.add(expression);
      while (!stack.isEmpty()) {
        PsiExpression psiExpression = stack.pop();
        if (psiExpression instanceof PsiPolyadicExpression) {
          PsiPolyadicExpression binaryExpression = (PsiPolyadicExpression)psiExpression;
          for (PsiExpression op : binaryExpression.getOperands()) {
            stack.push(op);
          }
        }
        else if (!(psiExpression instanceof PsiLiteralExpression)) {
          return false;
        }
      }
      return true;
    }
    return false;
  }
}


File: java/java-analysis-impl/src/com/intellij/codeInspection/dataFlow/value/DfaVariableValue.java
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

/*
 * Created by IntelliJ IDEA.
 * User: max
 * Date: Jan 28, 2002
 * Time: 6:31:08 PM
 * To change template for new class use
 * Code Style | Class Templates options (Tools | IDE Options).
 */
package com.intellij.codeInspection.dataFlow.value;

import com.intellij.codeInsight.NullableNotNullManager;
import com.intellij.codeInsight.daemon.impl.analysis.JavaGenericsUtil;
import com.intellij.codeInspection.dataFlow.DfaPsiUtil;
import com.intellij.codeInspection.dataFlow.Nullness;
import com.intellij.openapi.util.Comparing;
import com.intellij.openapi.util.Trinity;
import com.intellij.patterns.ElementPattern;
import com.intellij.psi.*;
import com.intellij.psi.util.PsiUtil;
import com.intellij.psi.util.TypeConversionUtil;
import com.intellij.util.SmartList;
import com.intellij.util.containers.MultiMap;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

import static com.intellij.patterns.PsiJavaPatterns.*;

public class DfaVariableValue extends DfaValue {

  private static final ElementPattern<? extends PsiModifierListOwner> MEMBER_OR_METHOD_PARAMETER =
    or(psiMember(), psiParameter().withSuperParent(2, psiMember()));

  public static class Factory {
    private final MultiMap<Trinity<Boolean,String,DfaVariableValue>,DfaVariableValue> myExistingVars = new MultiMap<Trinity<Boolean, String, DfaVariableValue>, DfaVariableValue>();
    private final DfaValueFactory myFactory;

    Factory(DfaValueFactory factory) {
      myFactory = factory;
    }

    public DfaVariableValue createVariableValue(PsiVariable myVariable, boolean isNegated) {
      PsiType varType = myVariable.getType();
      if (varType instanceof PsiEllipsisType) {
        varType = new PsiArrayType(((PsiEllipsisType)varType).getComponentType());
      }
      return createVariableValue(myVariable, varType, isNegated, null);
    }
    @NotNull
    public DfaVariableValue createVariableValue(@NotNull PsiModifierListOwner myVariable,
                                                @Nullable PsiType varType,
                                                boolean isNegated,
                                                @Nullable DfaVariableValue qualifier) {
      Trinity<Boolean,String,DfaVariableValue> key = Trinity.create(isNegated, ((PsiNamedElement)myVariable).getName(), qualifier);
      for (DfaVariableValue aVar : myExistingVars.get(key)) {
        if (aVar.hardEquals(myVariable, varType, isNegated, qualifier)) return aVar;
      }

      DfaVariableValue result = new DfaVariableValue(myVariable, varType, isNegated, myFactory, qualifier);
      myExistingVars.putValue(key, result);
      while (qualifier != null) {
        qualifier.myDependents.add(result);
        qualifier = qualifier.getQualifier();
      }
      return result;
    }

    public List<DfaVariableValue> getAllQualifiedBy(DfaVariableValue value) {
      return value.myDependents;
    }

  }

  private final PsiModifierListOwner myVariable;
  private final PsiType myVarType;
  @Nullable private final DfaVariableValue myQualifier;
  private DfaVariableValue myNegatedValue;
  private final boolean myIsNegated;
  private Nullness myInherentNullability;
  private final DfaTypeValue myTypeValue;
  private final List<DfaVariableValue> myDependents = new SmartList<DfaVariableValue>();

  private DfaVariableValue(@NotNull PsiModifierListOwner variable, @Nullable PsiType varType, boolean isNegated, DfaValueFactory factory, @Nullable DfaVariableValue qualifier) {
    super(factory);
    myVariable = variable;
    myIsNegated = isNegated;
    myQualifier = qualifier;
    myVarType = varType;
    DfaValue typeValue = myFactory.createTypeValue(varType, Nullness.UNKNOWN);
    myTypeValue = typeValue instanceof DfaTypeValue ? (DfaTypeValue)typeValue : null;
    if (varType != null && !varType.isValid()) {
      PsiUtil.ensureValidType(varType, "Variable: " + variable + " of class " + variable.getClass());
    }
  }

  @Nullable
  public DfaTypeValue getTypeValue() {
    return myTypeValue;
  }

  @NotNull
  public PsiModifierListOwner getPsiVariable() {
    return myVariable;
  }

  @Nullable
  public PsiType getVariableType() {
    return myVarType;
  }

  public boolean isNegated() {
    return myIsNegated;
  }

  @Nullable
  public DfaVariableValue getNegatedValue() {
    return myNegatedValue;
  }

  @Override
  public DfaVariableValue createNegated() {
    if (myNegatedValue != null) {
      return myNegatedValue;
    }
    return myNegatedValue = myFactory.getVarFactory().createVariableValue(myVariable, myVarType, !myIsNegated, myQualifier);
  }

  @SuppressWarnings({"HardCodedStringLiteral"})
  public String toString() {
    return (myIsNegated ? "!" : "") + ((PsiNamedElement)myVariable).getName() + (myQualifier == null ? "" : "|" + myQualifier.toString());
  }

  private boolean hardEquals(PsiModifierListOwner psiVar, PsiType varType, boolean negated, DfaVariableValue qualifier) {
    return psiVar == myVariable &&
           Comparing.equal(TypeConversionUtil.erasure(varType), TypeConversionUtil.erasure(myVarType)) &&
           negated == myIsNegated &&
           (myQualifier == null ? qualifier == null : myQualifier.hardEquals(qualifier.getPsiVariable(), qualifier.getVariableType(),
                                                                             qualifier.isNegated(), qualifier.getQualifier()));
  }

  @Nullable
  public DfaVariableValue getQualifier() {
    return myQualifier;
  }

  public Nullness getInherentNullability() {
    if (myInherentNullability != null) {
      return myInherentNullability;
    }

    return myInherentNullability = calcInherentNullability();
  }

  private Nullness calcInherentNullability() {
    PsiModifierListOwner var = getPsiVariable();
    Nullness nullability = DfaPsiUtil.getElementNullability(getVariableType(), var);
    if (nullability != Nullness.UNKNOWN) {
      return nullability;
    }

    Nullness defaultNullability = myFactory.isUnknownMembersAreNullable() && MEMBER_OR_METHOD_PARAMETER.accepts(var) ? Nullness.NULLABLE : Nullness.UNKNOWN;

    if (var instanceof PsiParameter && var.getParent() instanceof PsiForeachStatement) {
      PsiExpression iteratedValue = ((PsiForeachStatement)var.getParent()).getIteratedValue();
      if (iteratedValue != null) {
        PsiType itemType = JavaGenericsUtil.getCollectionItemType(iteratedValue);
        if (itemType != null) {
          return DfaPsiUtil.getElementNullability(itemType, var);
        }
      }
    }

    if (var instanceof PsiField && DfaPsiUtil.isFinalField((PsiVariable)var) && myFactory.isHonorFieldInitializers()) {
      List<PsiExpression> initializers = DfaPsiUtil.findAllConstructorInitializers((PsiField)var);
      if (initializers.isEmpty()) {
        return defaultNullability;
      }

      boolean hasUnknowns = false;
      for (PsiExpression expression : initializers) {
        if (!(expression instanceof PsiReferenceExpression)) {
          hasUnknowns = true;
          continue;
        }
        PsiElement target = ((PsiReferenceExpression)expression).resolve();
        if (!(target instanceof PsiParameter)) {
          hasUnknowns = true;
          continue;
        }
        if (NullableNotNullManager.isNullable((PsiParameter)target)) {
          return Nullness.NULLABLE;
        }
        if (!NullableNotNullManager.isNotNull((PsiParameter)target)) {
          hasUnknowns = true;
        }
      }
      
      if (hasUnknowns) {
        if (DfaPsiUtil.isInitializedNotNull((PsiField)var)) {
          return Nullness.NOT_NULL;
        }
        return defaultNullability;
      }
      
      return Nullness.NOT_NULL;
    }

    return defaultNullability;
  }

  public boolean isFlushableByCalls() {
    if (myVariable instanceof PsiLocalVariable || myVariable instanceof PsiParameter) return false;
    if (myVariable instanceof PsiVariable && myVariable.hasModifierProperty(PsiModifier.FINAL)) {
      return myQualifier != null && myQualifier.isFlushableByCalls();
    }
    return true;
  }

  public boolean containsCalls() {
    return myVariable instanceof PsiMethod || myQualifier != null && myQualifier.containsCalls();
  }

}


File: java/java-tests/testSrc/com/intellij/codeInspection/DataFlowInspectionTest.java
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
package com.intellij.codeInspection;

import com.intellij.JavaTestUtil;
import com.intellij.codeInspection.dataFlow.DataFlowInspection;
import com.intellij.testFramework.LightProjectDescriptor;
import com.intellij.testFramework.fixtures.JavaCodeInsightTestFixture;
import com.intellij.testFramework.fixtures.LightCodeInsightFixtureTestCase;
import org.jetbrains.annotations.NotNull;

/**
 * @author peter
 */
public class DataFlowInspectionTest extends LightCodeInsightFixtureTestCase {

  @NotNull
  @Override
  protected LightProjectDescriptor getProjectDescriptor() {
    return JAVA_1_7;
  }

  @Override
  protected String getTestDataPath() {
    return JavaTestUtil.getJavaTestDataPath() + "/inspection/dataFlow/fixture/";
  }

  private void doTest() {
    final DataFlowInspection inspection = new DataFlowInspection();
    inspection.SUGGEST_NULLABLE_ANNOTATIONS = true;
    inspection.REPORT_CONSTANT_REFERENCE_VALUES = false;
    myFixture.enableInspections(inspection);
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testTryInAnonymous() throws Throwable { doTest(); }
  public void testNullableAnonymousMethod() throws Throwable { doTest(); }
  public void testNullableAnonymousParameter() throws Throwable { doTest(); }
  public void testNullableAnonymousVolatile() throws Throwable { doTest(); }
  public void testNullableAnonymousVolatileNotNull() throws Throwable { doTest(); }
  public void testLocalClass() throws Throwable { doTest(); }

  public void testFieldInAnonymous() throws Throwable { doTest(); }
  public void testFieldInitializerInAnonymous() throws Throwable { doTest(); }
  public void testNullableField() throws Throwable { doTest(); }
  public void testCanBeNullDoesntImplyIsNull() throws Throwable { doTest(); }
  public void testAnnReport() throws Throwable { doTest(); }

  public void testBigMethodNotComplex() throws Throwable { doTest(); }
  public void testBuildRegexpNotComplex() throws Throwable { doTest(); }
  public void testTernaryInWhileNotComplex() throws Throwable { doTest(); }
  public void testTryCatchInForNotComplex() throws Throwable { doTest(); }
  public void testNestedTryInWhileNotComplex() throws Throwable { doTest(); }
  public void testExceptionFromFinally() throws Throwable { doTest(); }
  public void testExceptionFromFinallyNesting() throws Throwable { doTest(); }
  public void testNestedFinally() { doTest(); }
  public void testTryFinallyInsideFinally() { doTest(); }
  public void testFieldChangedBetweenSynchronizedBlocks() throws Throwable { doTest(); }

  public void testGeneratedEquals() throws Throwable { doTest(); }

  public void testIDEA84489() throws Throwable { doTest(); }
  public void testComparingNullToNotNull() { doTest(); }
  public void testComparingNullableToNullable() { doTest(); }
  public void testComparingNullableToUnknown() { doTest(); }
  public void testComparingToNotNullShouldNotAffectNullity() throws Throwable { doTest(); }
  public void testComparingToNullableShouldNotAffectNullity() throws Throwable { doTest(); }
  public void testStringTernaryAlwaysTrue() throws Throwable { doTest(); }
  public void testStringConcatAlwaysNotNull() throws Throwable { doTest(); }

  public void testNotNullPrimitive() throws Throwable { doTest(); }
  public void testBoxing128() throws Throwable { doTest(); }
  public void testFinalFieldsInitializedByAnnotatedParameters() throws Throwable { doTest(); }
  public void testFinalFieldsInitializedNotNull() throws Throwable { doTest(); }
  public void testMultiCatch() throws Throwable { doTest(); }
  public void testContinueFlushesLoopVariable() throws Throwable { doTest(); }

  public void testEqualsNotNull() throws Throwable { doTest(); }
  public void testVisitFinallyOnce() throws Throwable { doTest(); }
  public void testNotEqualsDoesntImplyNotNullity() throws Throwable { doTest(); }
  public void testEqualsEnumConstant() throws Throwable { doTest(); }
  public void testSwitchEnumConstant() { doTest(); }
  public void testEnumConstantNotNull() throws Throwable { doTest(); }
  public void testEqualsConstant() throws Throwable { doTest(); }
  public void testDontSaveTypeValue() { doTest(); }
  public void testFinalLoopVariableInstanceof() throws Throwable { doTest(); }
  public void testGreaterIsNotEquals() throws Throwable { doTest(); }
  public void testNotGreaterIsNotEquals() throws Throwable { doTest(); }

  public void testChainedFinalFieldsDfa() throws Throwable { doTest(); }
  public void testFinalFieldsDifferentInstances() throws Throwable { doTest(); }
  public void testThisFieldGetters() throws Throwable { doTest(); }
  public void testChainedFinalFieldAccessorsDfa() throws Throwable { doTest(); }
  public void testAccessorPlusMutator() throws Throwable { doTest(); }
  public void testClosureVariableField() throws Throwable { doTest(); }
  public void testOptionalThis() { doTest(); }
  public void testQualifiedThis() { doTest(); }

  public void testAssigningNullableToNotNull() throws Throwable { doTest(); }
  public void testAssigningUnknownToNullable() throws Throwable { doTest(); }
  public void testAssigningClassLiteralToNullable() throws Throwable { doTest(); }

  public void testSynchronizingOnNullable() throws Throwable { doTest(); }
  public void testSwitchOnNullable() { doTest(); }
  public void testReturningNullFromVoidMethod() throws Throwable { doTest(); }
  public void testReturningNullConstant() { doTest(); }

  public void testCatchRuntimeException() throws Throwable { doTest(); }
  // IDEA-129331
  //public void testCatchThrowable() throws Throwable { doTest(); }
  public void testNotNullCatchParameter() { doTest(); }

  public void testAssertFailInCatch() throws Throwable {
    myFixture.addClass("package org.junit; public class Assert { public static void fail() {}}");
    doTest();
  }

  public void testPreserveNullableOnUncheckedCast() throws Throwable { doTest(); }
  public void testPrimitiveCastMayChangeValue() throws Throwable { doTest(); }

  public void testPassingNullableIntoVararg() throws Throwable { doTest(); }
  public void testEqualsImpliesNotNull() throws Throwable { doTestReportConstantReferences(); }
  public void testEffectivelyUnqualified() throws Throwable { doTest(); }

  public void testSkipAssertions() {
    final DataFlowInspection inspection = new DataFlowInspection();
    inspection.DONT_REPORT_TRUE_ASSERT_STATEMENTS = true;
    myFixture.enableInspections(inspection);
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testParanoidMode() {
    final DataFlowInspection inspection = new DataFlowInspection();
    inspection.TREAT_UNKNOWN_MEMBERS_AS_NULLABLE = true;
    myFixture.enableInspections(inspection);
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testReportConstantReferences() {
    doTestReportConstantReferences();
    myFixture.launchAction(myFixture.findSingleIntention("Replace with 'null'"));
    myFixture.checkResultByFile(getTestName(false) + "_after.java");
  }

  public void testReportConstantReferences_OverloadedCall() {
    doTestReportConstantReferences();
    myFixture.launchAction(myFixture.findSingleIntention("Replace with 'null'"));
    myFixture.checkResultByFile(getTestName(false) + "_after.java");
  }

  public void testReportConstantReferencesAfterFinalFieldAccess() { doTestReportConstantReferences(); }

  private void doTestReportConstantReferences() {
    DataFlowInspection inspection = new DataFlowInspection();
    inspection.SUGGEST_NULLABLE_ANNOTATIONS = true;
    myFixture.enableInspections(inspection);
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testCheckFieldInitializers() {
    doTest();
  }

  public void testConstantDoubleComparisons() { doTest(); }
  public void testInherentNumberRanges() { doTest(); }

  public void testMutableNullableFieldsTreatment() { doTest(); }
  public void testMutableVolatileNullableFieldsTreatment() { doTest(); }
  public void testMutableNotAnnotatedFieldsTreatment() { doTest(); }
  public void testSuperCallMayChangeFields() { doTest(); }
  public void testOtherCallMayChangeFields() { doTest(); }

  public void testMethodCallFlushesField() { doTest(); }
  public void testUnknownFloatMayBeNaN() { doTest(); }
  public void testFloatEquality() { doTest(); }
  public void testLastConstantConditionInAnd() { doTest(); }
  
  public void testCompileTimeConstant() { doTest(); }
  public void testNoParenthesesWarnings() { doTest(); }

  public void testTransientFinalField() { doTest(); }
  public void testRememberLocalTransientFieldState() { doTest(); }
  public void testFinalFieldDuringInitialization() { doTest(); }
  public void testFinalFieldDuringSuperInitialization() { doTest(); }
  public void testFinalFieldInConstructorAnonymous() { doTest(); }
  public void _testSymmetricUncheckedCast() { doTest(); } // https://youtrack.jetbrains.com/issue/IDEABKL-6871
  public void testNullCheckDoesntAffectUncheckedCast() { doTest(); }
  public void testThrowNull() { doTest(); }

  public void testExplicitlyNullableLocalVar() { doTest(); }

  public void testTryWithResourcesNullability() { doTest(); }
  public void testTryWithResourcesInstanceOf() { doTest(); }
  public void testOmnipresentExceptions() { doTest(); }

  public void testEqualsHasNoSideEffects() { doTest(); }

  public void testHonorGetterAnnotation() { doTest(); }

  public void testIgnoreAssertions() {
    final DataFlowInspection inspection = new DataFlowInspection();
    inspection.IGNORE_ASSERT_STATEMENTS = true;
    myFixture.enableInspections(inspection);
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testContractAnnotation() { doTest(); }
  public void testContractInapplicableComparison() { doTest(); }
  public void testContractInLoopNotTooComplex() { doTest(); }
  public void testContractWithManyParameters() { doTest(); }
  public void testContractWithNullable() { doTest(); }
  public void testContractWithNotNull() { doTest(); }
  public void testContractPreservesUnknownNullability() { doTest(); }
  public void testContractPreservesUnknownMethodNullability() { doTest(); }
  public void testContractSeveralClauses() { doTest(); }
  public void testContractVarargs() { doTest(); }

  public void testBoxingImpliesNotNull() { doTest(); }
  public void testLargeIntegersAreNotEqualWhenBoxed() { doTest(); }
  public void testNoGenericCCE() { doTest(); }
  public void testLongCircuitOperations() { doTest(); }
  public void testUnconditionalForLoop() { doTest(); }
  public void testAnonymousMethodIndependence() { doTest(); }
  public void testAnonymousFieldIndependence() { doTest(); }
  public void testNoConfusionWithAnonymousConstantInitializer() { doTest(); }
  public void testForeachOverWildcards() { doTest(); }
  public void testFinalGetter() { doTest(); }
  public void testGetterResultsNotSame() { doTest(); }

  public void testByteBufferGetter() {
    myFixture.addClass("package java.nio; public class MappedByteBuffer { public int getInt() {} }");
    doTest();
  }

  public void testManySequentialIfsNotComplex() { doTest(); }
  public void testManySequentialInstanceofsNotComplex() { doTest(); }
  public void testLongDisjunctionsNotComplex() { doTest(); }
  public void testWhileNotComplex() { doTest(); }
  public void testAssertTrueNotComplex() { doTest(); }
  public void testAssertThrowsAssertionError() { doTest(); }
  public void testManyDisjunctiveFieldAssignmentsInLoopNotComplex() { doTest(); }
  public void testManyContinuesNotComplex() { doTest(); }
  public void testFinallyNotComplex() { doTest(); }
  public void testFlushFurtherUnusedVariables() { doTest(); }
  public void testDontFlushVariablesUsedInClosures() { doTest(); }

  public void testVariablesDiverge() { doTest(); }
  public void testMergeByNullability() { doTest(); }
  public void testCheckComplementarityWhenMerge() { doTest(); }
  public void testDontForgetInstanceofInfoWhenMerging() { doTest(); }
  public void testDontForgetEqInfoWhenMergingByType() { doTest(); }
  public void testDontMakeNullableAfterInstanceof() { doTest(); }
  public void testDontMakeUnrelatedVariableNotNullWhenMerging() { doTest(); }
  public void testDontMakeUnrelatedVariableFalseWhenMerging() { doTest(); }
  public void testDontLoseInequalityInformation() { doTest(); }
  
  public void testNotEqualsTypo() { doTest(); }
  public void testAndEquals() { doTest(); }
  public void testXor() { doTest(); }

  public void testUnusedCallDoesNotMakeUnknown() { doTest(); }
  public void testEmptyCallDoesNotMakeNullable() { doTest(); }
  public void testGettersAndPureNoFlushing() { doTest(); }
  public void testFalseGetters() { doTest(); }
  
  public void testNotNullAfterDereference() { doTest(); }

  public void testNullableBoolean() { doTest(); }

  public void testSameComparisonTwice() { doTest(); }
  public void testRootThrowableCause() { doTest(); }

  public void testNotNullOverridesNullable() { doTest(); }

  public void testOverridingInferredNotNullMethod() { doTest(); }
  public void testUseInferredContracts() { doTest(); }
  public void testContractWithNoArgs() { doTest(); }
  public void testContractInferenceBewareOverriding() { doTest(); }

  public void testNumberComparisonsWhenValueIsKnown() { doTest(); }
  public void testFloatComparisons() { doTest(); }
  public void testComparingIntToDouble() { doTest(); }

  public void testNullableArray() { doTest(); }

  public void testAccessingSameArrayElements() { doTest(); }

  public void testParametersAreNonnullByDefault() {
    addJavaxNullabilityAnnotations(myFixture);
    addJavaxDefaultNullabilityAnnotations(myFixture);
    
    myFixture.addClass("package foo; public class AnotherPackageNotNull { public static void foo(String s) {}}");
    myFixture.addFileToProject("foo/package-info.java", "@javax.annotation.ParametersAreNonnullByDefault package foo;");
    
    doTest(); 
  }

  public static void addJavaxDefaultNullabilityAnnotations(final JavaCodeInsightTestFixture fixture) {
    fixture.addClass("package javax.annotation;" +
                     "@javax.annotation.meta.TypeQualifierDefault(java.lang.annotation.ElementType.PARAMETER) @javax.annotation.Nonnull " +
                     "public @interface ParametersAreNonnullByDefault {}");
    fixture.addClass("package javax.annotation;" +
                     "@javax.annotation.meta.TypeQualifierDefault(java.lang.annotation.ElementType.PARAMETER) @javax.annotation.Nullable " +
                     "public @interface ParametersAreNullableByDefault {}");
  }

  public static void addJavaxNullabilityAnnotations(final JavaCodeInsightTestFixture fixture) {
    fixture.addClass("package javax.annotation;" +
                     "public @interface Nonnull {}");
    fixture.addClass("package javax.annotation;" +
                     "public @interface Nullable {}");
    fixture.addClass("package javax.annotation.meta;" +
                     "public @interface TypeQualifierDefault { java.lang.annotation.ElementType[] value() default {};}");
  }

  public void testCustomTypeQualifierDefault() {
    addJavaxNullabilityAnnotations(myFixture);
    myFixture.addClass("package bar;" +
                       "@javax.annotation.meta.TypeQualifierDefault(java.lang.annotation.ElementType.METHOD) @javax.annotation.Nonnull " +
                       "public @interface MethodsAreNotNullByDefault {}");

    myFixture.addClass("package foo; public class AnotherPackageNotNull { public static native Object foo(String s); }");
    myFixture.addFileToProject("foo/package-info.java", "@bar.MethodsAreNotNullByDefault package foo;");

    myFixture.enableInspections(new DataFlowInspection());
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testCustomDefaultInEnums() {
    DataFlowInspectionTest.addJavaxNullabilityAnnotations(myFixture);
    myFixture.addClass("package foo;" +
                       "import static java.lang.annotation.ElementType.*;" +
                       "@javax.annotation.meta.TypeQualifierDefault({PARAMETER, FIELD, METHOD, LOCAL_VARIABLE}) " +
                       "@javax.annotation.Nonnull " +
                       "public @interface NonnullByDefault {}");

    myFixture.addFileToProject("foo/package-info.java", "@NonnullByDefault package foo;");

    myFixture.configureFromExistingVirtualFile(myFixture.copyFileToProject(getTestName(false) + ".java", "foo/Classes.java"));
    myFixture.enableInspections(new DataFlowInspection());
    myFixture.checkHighlighting(true, false, true);
  }

  public void testTrueOrEqualsSomething() {
    doTest();
    myFixture.launchAction(myFixture.findSingleIntention("Remove redundant assignment"));
    myFixture.checkResultByFile(getTestName(false) + "_after.java");
  }

  public void testAssertThat() {
    myFixture.addClass("package org.hamcrest; public class CoreMatchers { " +
                       "public static <T> Matcher<T> notNullValue() {}\n" +
                       "public static <T> Matcher<T> not(Matcher<T> matcher) {}\n" +
                       "public static <T> Matcher<T> equalTo(T operand) {}\n" +
                       "}");
    myFixture.addClass("package org.hamcrest; public interface Matcher<T> {}");
    myFixture.addClass("package org.junit; public class Assert { " +
                       "public static <T> void assertThat(T actual, org.hamcrest.Matcher<? super T> matcher) {}\n" +
                       "public static <T> void assertThat(String msg, T actual, org.hamcrest.Matcher<? super T> matcher) {}\n" +
                       "}");
    myFixture.enableInspections(new DataFlowInspection());
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testGoogleTruth() {
    myFixture.addClass("package com.google.common.truth; public class Truth { " +
                       "public static Subject assertThat(Object o) {}\n" +
                       "}");
    myFixture.addClass("package com.google.common.truth; public class Subject { public void isNotNull() {} }");
    myFixture.enableInspections(new DataFlowInspection());
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testBooleanPreconditions() {
    myFixture.addClass("package com.google.common.base; public class Preconditions { " +
                       "public static <T> T checkArgument(boolean b) {}\n" +
                       "public static <T> T checkArgument(boolean b, String msg) {}\n" +
                       "public static <T> T checkState(boolean b, String msg) {}\n" +
                       "}");
    myFixture.enableInspections(new DataFlowInspection());
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void testGuavaCheckNotNull() {
    myFixture.addClass("package com.google.common.base; public class Preconditions { " +
                       "public static <T> T checkNotNull(T reference) {}\n" +
                       "}");
    myFixture.enableInspections(new DataFlowInspection());
    myFixture.testHighlighting(true, false, true, getTestName(false) + ".java");
  }

  public void _testNullCheckBeforeInstanceof() { doTest(); } // https://youtrack.jetbrains.com/issue/IDEA-113220

  public void testSkipConstantConditionsWithAssignmentsInside() { doTest(); }
}
